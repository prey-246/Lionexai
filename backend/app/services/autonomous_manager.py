"""Autonomous multi-asset portfolio manager.

Replaces the hardcoded BTC-only `scripts/algo_executor.py`. For every auto-managed
portfolio it diffs current positions against the target weights in
`portfolio_allocations` and emits per-asset orders, routed to the correct execution
venue (real crypto testnet when keys + env allow, otherwise the SimulatedAdapter).
Every order passes through the RiskEngine. Gated behind the
`global_settings.autonomous_v2_enabled` feature flag.
"""
import os
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional

from app.core.database import SessionLocal
from app.models import domain
from app.exchange import ExchangeAdapter
from app.exchange.simulated import SimulatedAdapter
from app.assets import get_asset_adapter
from app.services import market_data_service
from app.engines.allocation_engine import AllocationEngine
from app.engines.macro_intelligence import MacroIntelligenceEngine
from app.services.validated_portfolio_service import is_validated_portfolio

try:
    from app.engines.risk_engine import RiskEngine, RiskRejectionError
except ImportError:  # pragma: no cover
    RiskEngine = None
    RiskRejectionError = Exception

logger = logging.getLogger("nexa.autonomous_manager")

# Don't trade tiny deltas: only act when the gap to target exceeds this band.
REBALANCE_BAND_PCT = 2.0
MIN_TRADE_VALUE = 10.0


def _keys_present(venue: str) -> bool:
    key = os.environ.get(f"{venue.upper()}_API_KEY")
    return bool(key) and "YOUR_" not in key


class AutonomousManager:
    def __init__(self, db):
        self.db = db
        self._adapters: Dict[str, ExchangeAdapter] = {}
        self.global_settings = db.query(domain.GlobalSettings).filter_by(id="default").first()
        self.env = self.global_settings.environment_state if self.global_settings else "PAPER"

    # --- venue routing ---------------------------------------------------
    async def _adapter_for(self, asset: domain.Asset) -> ExchangeAdapter | SimulatedAdapter:
        """Route execution through the AssetAdapter registry (crypto vs metals/FX)."""
        slippage = self.global_settings.default_slippage_pct if self.global_settings else 0.1
        commission = self.global_settings.default_commission_pct if self.global_settings else 0.1
        venue = (asset.execution_venue or "SIMULATED").lower()
        cache_key = f"{asset.asset_class}:{venue}"

        if cache_key not in self._adapters:
            route = get_asset_adapter(asset)
            adapter = await route.get_adapter(asset)
            if isinstance(adapter, SimulatedAdapter):
                adapter = SimulatedAdapter(slippage_pct=slippage, commission_pct=commission)
            elif asset.asset_class == "CRYPTO" and self.env != "LIVE":
                adapter = SimulatedAdapter(slippage_pct=slippage, commission_pct=commission)
            elif asset.asset_class == "CRYPTO" and not _keys_present(venue):
                adapter = SimulatedAdapter(slippage_pct=slippage, commission_pct=commission)
            self._adapters[cache_key] = adapter
        return self._adapters[cache_key]

    # --- helpers ---------------------------------------------------------
    def _open_position(self, portfolio: domain.Portfolio, symbol: str):
        open_trades = [t for t in portfolio.trades if t.symbol == symbol and t.status == "OPEN" and t.side == "BUY"]
        qty = sum(t.quantity or 0 for t in open_trades)
        value = sum((t.quantity or 0) * (t.entry_price or 0) for t in open_trades)
        return qty, value, open_trades

    def _risk_ok(self, portfolio, mandate, order) -> Optional[str]:
        """Return None if allowed, else a rejection reason. De-risking SELLs bypass
        capital-protection checks (kill switch still applies)."""
        if not RiskEngine:
            return None
        engine = RiskEngine(self.db)
        try:
            if order["side"] == "SELL":
                engine._check_kill_switch(portfolio, mandate, order)
                return None
            engine.evaluate_pre_trade(portfolio, mandate, order)
            return None
        except RiskRejectionError as e:
            return str(e)
        except Exception as e:  # pragma: no cover
            return f"RISK_ERROR: {e}"

    # --- core ------------------------------------------------------------
    async def manage_portfolio(self, portfolio: domain.Portfolio, global_state):
        if is_validated_portfolio(portfolio):
            return
        mandate = portfolio.mandate
        fund = self.db.query(domain.Fund).filter(domain.Fund.pk_id == portfolio.fund_pk_id).first()
        if not mandate or not fund:
            return

        allocations = list(portfolio.allocations)
        if not allocations:
            # First run: produce an initial target allocation, then proceed.
            AllocationEngine(self.db).rebalance_portfolio(portfolio, trigger="INITIAL", global_state=global_state)
            self.db.refresh(portfolio)
            allocations = list(portfolio.allocations)

        equity = portfolio.total_equity or 0.0
        if equity <= 0:
            return

        for alloc in allocations:
            asset = alloc.asset
            if not asset:
                continue
            symbol = asset.symbol
            price = market_data_service.get_live_price(asset) or market_data_service.latest_close(self.db, symbol)
            if not price or price <= 0:
                continue

            cur_qty, cur_value, open_buys = self._open_position(portfolio, symbol)
            target_value = equity * (alloc.target_weight_pct or 0.0) / 100.0
            diff_value = target_value - cur_value

            if abs(diff_value) < max(equity * REBALANCE_BAND_PCT / 100.0, MIN_TRADE_VALUE):
                # Close enough; just refresh the recorded current weight.
                alloc.current_weight_pct = round(cur_value / equity * 100.0, 4) if equity else 0.0
                continue

            side = "BUY" if diff_value > 0 else "SELL"
            if side == "BUY":
                qty = diff_value / price
            else:
                qty = min(cur_qty, abs(diff_value) / price)
            if qty <= 0:
                continue

            stop_loss = price * 0.9 if side == "BUY" else price * 1.1
            order = {"symbol": symbol, "size": qty, "current_price": price, "side": side, "stop_loss": stop_loss}

            reason = self._risk_ok(portfolio, mandate, order)
            if reason:
                self._record_rejection(portfolio, asset, side, qty, price, reason)
                continue

            await self._execute(portfolio, asset, side, qty, price, open_buys, fund)

        # Refresh recorded current weights + write an equity-curve point.
        for alloc in allocations:
            _, cur_value, _ = self._open_position(portfolio, alloc.asset.symbol) if alloc.asset else (0, 0, [])
            alloc.current_weight_pct = round(cur_value / equity * 100.0, 4) if equity else 0.0
        self.db.add(domain.EquityCurve(portfolio_id=portfolio.pk_id, equity=portfolio.total_equity))
        self.db.commit()

    async def _execute(self, portfolio, asset, side, qty, price, open_buys, fund):
        adapter = await self._adapter_for(asset)
        venue = (asset.execution_venue or "SIMULATED").lower()
        try:
            if not isinstance(adapter, SimulatedAdapter):
                await adapter.connect()
            start = time.time()
            if isinstance(adapter, SimulatedAdapter):
                exchange_order = await adapter.place_market_order(asset.symbol, side.lower(), qty, price=price)
            else:
                exchange_order = await adapter.place_market_order(asset.symbol, side.lower(), qty)
            latency_ms = round((time.time() - start) * 1000, 2)

            fill_price = exchange_order.price or price
            filled_qty = exchange_order.filled or qty
            notional = fill_price * filled_qty

            new_trade = domain.Trade(
                id=f"trd_{uuid.uuid4().hex[:12]}",
                portfolio_id=portfolio.pk_id,
                asset_pk_id=asset.pk_id,
                symbol=asset.symbol,
                side=side,
                quantity=filled_qty,
                entry_price=fill_price,
                status="OPEN" if side == "BUY" else "CLOSED",
                pnl=0.0,
                exchange=venue,
                execution_latency_ms=latency_ms,
                strategy_name=f"AUTO:{fund.id}",
                trade_source="AUTONOMOUS",
            )

            if side == "BUY":
                portfolio.available_margin = max(0.0, (portfolio.available_margin or 0.0) - notional)
            else:
                # Close matching open BUYs FIFO, realize PnL.
                remaining = filled_qty
                realized = 0.0
                for buy in open_buys:
                    if remaining <= 0:
                        break
                    close_qty = min(buy.quantity, remaining)
                    realized += (fill_price - buy.entry_price) * close_qty
                    if close_qty >= buy.quantity:
                        buy.status = "CLOSED"
                        buy.exit_price = fill_price
                        buy.closed_at = datetime.utcnow()
                        buy.pnl = (fill_price - buy.entry_price) * buy.quantity
                    else:
                        buy.quantity -= close_qty
                    remaining -= close_qty
                new_trade.pnl = round(realized, 6)
                new_trade.closed_at = datetime.utcnow()
                portfolio.total_equity = (portfolio.total_equity or 0.0) + realized
                portfolio.available_margin = (portfolio.available_margin or 0.0) + notional

            self.db.add(new_trade)
            self.db.add(domain.AuditLog(
                action_type="AUTONOMOUS_TRADE_EXECUTED",
                description=f"Fund {fund.id} {side} {asset.symbol} via {venue.upper()}.",
                metadata_json={
                    "portfolio": portfolio.id,
                    "fund": fund.id,
                    "asset": asset.symbol,
                    "asset_class": asset.asset_class,
                    "venue": venue,
                    "side": side,
                    "quantity": filled_qty,
                    "price": fill_price,
                    "latency_ms": latency_ms,
                    "simulated": isinstance(adapter, SimulatedAdapter),
                },
            ))
            self.db.commit()
            self.db.refresh(new_trade)
            from app.services.execution_lifecycle_service import record_lifecycle_event
            record_lifecycle_event(
                self.db, "ORDER_SUBMITTED", trade_id=new_trade.id, portfolio_id=portfolio.id, symbol=asset.symbol,
                metadata={"side": side, "venue": venue},
            )
            record_lifecycle_event(
                self.db, "ORDER_FILLED", trade_id=new_trade.id, portfolio_id=portfolio.id, symbol=asset.symbol,
                metadata={"latency_ms": latency_ms, "price": fill_price},
            )
            stage = "POSITION_CLOSED" if new_trade.status == "CLOSED" else "POSITION_OPENED"
            record_lifecycle_event(self.db, stage, trade_id=new_trade.id, portfolio_id=portfolio.id, symbol=asset.symbol)
            self.db.commit()
        except Exception as e:
            logger.error("Autonomous order failed for %s %s: %s", asset.symbol, side, e, exc_info=True)
            self.db.rollback()
            self._record_rejection(portfolio, asset, side, qty, price, f"EXECUTION_ERROR: {e}")

    def _record_rejection(self, portfolio, asset, side, qty, price, reason):
        try:
            self.db.add(domain.Trade(
                id=f"trd_{uuid.uuid4().hex[:12]}",
                portfolio_id=portfolio.pk_id,
                asset_pk_id=asset.pk_id,
                symbol=asset.symbol,
                side=side,
                quantity=qty,
                entry_price=price,
                status="REJECTED",
                pnl=0.0,
                exchange=(asset.execution_venue or "SIMULATED").lower(),
                strategy_name="AUTONOMOUS",
                rejection_reason=reason,
                trade_source="AUTONOMOUS",
                created_at=datetime.utcnow(),
                closed_at=datetime.utcnow(),
            ))
            self.db.add(domain.AuditLog(
                action_type="ORDER_REJECTED",
                description=f"Autonomous {side} {asset.symbol} rejected: {reason}",
                metadata_json={"portfolio": portfolio.id, "asset": asset.symbol, "side": side, "reason": reason},
            ))
            self.db.commit()
        except Exception:
            self.db.rollback()

    async def run(self):
        global_state = MacroIntelligenceEngine(self.db).latest()
        portfolios = self.db.query(domain.Portfolio).filter(domain.Portfolio.auto_managed == True).all()
        for p in portfolios:
            try:
                await self.manage_portfolio(p, global_state)
            except Exception as e:
                logger.error("Failed managing portfolio %s: %s", p.id, e, exc_info=True)
                self.db.rollback()
        for adapter in self._adapters.values():
            try:
                if not isinstance(adapter, SimulatedAdapter):
                    await adapter.close()
            except Exception:
                pass


async def run_autonomous_cycle():
    """Dispatcher used by the background loop.

    Runs the new multi-asset manager when `autonomous_v2_enabled` is set, otherwise
    falls back to the legacy single-asset executor for a safe rollout.
    """
    db = SessionLocal()
    try:
        gs = db.query(domain.GlobalSettings).filter_by(id="default").first()
        enabled = bool(gs and gs.autonomous_v2_enabled)
    finally:
        db.close()

    if not enabled:
        from scripts.algo_executor import run_autonomous_execution
        await run_autonomous_execution()
        return

    db = SessionLocal()
    try:
        manager = AutonomousManager(db)
        await manager.run()
    finally:
        db.close()
