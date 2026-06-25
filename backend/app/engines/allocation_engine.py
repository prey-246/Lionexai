"""Autonomous allocation engine.

Given an auto-managed portfolio (linked to a Fund), computes target weights across
the fund's asset universe using regime-tilted inverse-volatility (risk-parity-style)
within mandate caps, scaling cash up in risk-off / crisis. Writes the result to
`portfolio_allocations` (source of truth) and records a `rebalance_events` audit row.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import domain
from app.services.portfolio_nav import current_weight_pct
from app.services import market_data_service
from app.engines.regime_engine import _annualized_vol
from app.engines.macro_intelligence import MacroIntelligenceEngine, SAFE_HAVENS

logger = logging.getLogger("nexa.allocation_engine")

VOL_FLOOR = 0.05
MOMENTUM_K = 2.0


class AllocationEngine:
    def __init__(self, db: Session):
        self.db = db

    # --- helpers ---------------------------------------------------------
    def _allowed_symbols(self, mandate: Optional[domain.Mandate]) -> Optional[set]:
        """Return the whitelist set, or None when everything is allowed."""
        if not mandate or not mandate.allowed_assets:
            return None
        allowed = mandate.allowed_assets
        if isinstance(allowed, dict):
            allowed = allowed.get("symbols", [])
        if "ALL" in allowed:
            return None
        return set(allowed)

    def _asset_signal(self, symbol: str) -> Optional[Dict[str, float]]:
        df = market_data_service.get_bars_df(self.db, symbol, timeframe="1d", limit=200)
        if df is None or df.empty or len(df) < 20:
            return None
        close = df["close"].astype(float).reset_index(drop=True)
        returns = close.pct_change()
        vol = max(_annualized_vol(returns), VOL_FLOOR)
        mom_window = min(63, len(close) - 1)
        momentum = (float(close.iloc[-1]) / float(close.iloc[-1 - mom_window]) - 1.0) if len(close) > mom_window else 0.0
        return {"vol": vol, "momentum": momentum, "inv_vol": 1.0 / vol}

    def _asset_regime(self, symbol: str) -> Optional[str]:
        row = (
            self.db.query(domain.MarketRegime.regime)
            .filter(domain.MarketRegime.scope == symbol)
            .order_by(domain.MarketRegime.detected_at.desc())
            .first()
        )
        return row[0] if row else None

    def _current_weight(self, portfolio: domain.Portfolio, symbol: str) -> float:
        return current_weight_pct(self.db, portfolio, symbol)

    # --- core ------------------------------------------------------------
    def compute_targets(self, portfolio: domain.Portfolio, fund: domain.Fund,
                        global_state: Optional[domain.GlobalMarketState]) -> Dict:
        policy = fund.allocation_policy or {}
        method = policy.get("method", "inverse_vol")
        base_cash_floor = float(policy.get("cash_floor_pct", 10.0))
        max_assets = int(policy.get("max_assets", 8))

        mandate = portfolio.mandate
        allowed = self._allowed_symbols(mandate)
        max_position_cap = float(mandate.max_position_size_pct) if mandate else 100.0

        regime = global_state.market_regime if global_state else "SIDEWAYS"
        risk_on_off = global_state.risk_on_off if global_state else "NEUTRAL"

        # Effective cash floor scales up when the world is risk-off / in crisis.
        cash_floor = base_cash_floor
        if risk_on_off == "RISK_OFF":
            cash_floor += 15.0
        if regime == "CRISIS":
            cash_floor = max(cash_floor, 60.0)
        cash_floor = max(0.0, min(95.0, cash_floor))
        invested_pct = 100.0 - cash_floor

        # Build raw weights for each eligible asset in the fund universe.
        candidates: List[Dict] = []
        for fau in fund.asset_universe:
            asset = fau.asset
            if not asset or not asset.is_active:
                continue
            if allowed is not None and asset.symbol not in allowed:
                continue
            sig = self._asset_signal(asset.symbol)
            if not sig:
                continue
            asset_regime = self._asset_regime(asset.symbol)

            raw = sig["inv_vol"]
            if method == "regime_momentum":
                raw *= (1.0 + max(sig["momentum"], 0.0) * MOMENTUM_K)

            # Per-asset regime tilt.
            if asset_regime == "BULL":
                raw *= 1.25
            elif asset_regime == "BEAR":
                raw *= 0.4
            elif asset_regime == "CRISIS":
                raw *= 0.1

            # Safe-haven tilt in risk-off.
            if risk_on_off == "RISK_OFF" and asset.symbol in SAFE_HAVENS:
                raw *= 1.5

            raw = max(raw, 0.0)
            candidates.append({
                "asset": asset,
                "symbol": asset.symbol,
                "raw": raw,
                "vol": round(sig["vol"], 4),
                "momentum": round(sig["momentum"], 4),
                "regime": asset_regime or "UNKNOWN",
                "max_weight_pct": fau.max_weight_pct,
            })

        # Keep the strongest N candidates.
        candidates.sort(key=lambda c: c["raw"], reverse=True)
        candidates = [c for c in candidates if c["raw"] > 0][:max_assets]

        total_raw = sum(c["raw"] for c in candidates)
        decisions: List[Dict] = []
        if total_raw <= 0:
            return {"cash_pct": 100.0, "invested_pct": 0.0, "regime": regime,
                    "risk_on_off": risk_on_off, "cash_floor": cash_floor, "allocations": [], "decisions": []}

        for c in candidates:
            norm = c["raw"] / total_raw
            target = norm * invested_pct
            cap = min(max_position_cap, c["max_weight_pct"])
            capped = target > cap
            target = min(target, cap)
            c["target_weight_pct"] = round(target, 4)
            decisions.append({
                "symbol": c["symbol"],
                "target_weight_pct": round(target, 4),
                "current_weight_pct": self._current_weight(portfolio, c["symbol"]),
                "vol": c["vol"],
                "momentum": c["momentum"],
                "regime": c["regime"],
                "capped": capped,
            })

        invested_total = sum(c["target_weight_pct"] for c in candidates)
        return {
            "cash_pct": round(100.0 - invested_total, 4),
            "invested_pct": round(invested_total, 4),
            "regime": regime,
            "risk_on_off": risk_on_off,
            "cash_floor": cash_floor,
            "allocations": candidates,
            "decisions": decisions,
        }

    def rebalance_portfolio(self, portfolio: domain.Portfolio, trigger: str = "SCHEDULED",
                            global_state: Optional[domain.GlobalMarketState] = None) -> Optional[domain.RebalanceEvent]:
        if not portfolio.auto_managed or not portfolio.fund_pk_id:
            return None
        fund = self.db.query(domain.Fund).filter(domain.Fund.pk_id == portfolio.fund_pk_id).first()
        if not fund:
            logger.warning("Auto-managed portfolio %s has no fund; skipping.", portfolio.id)
            return None

        if global_state is None:
            global_state = MacroIntelligenceEngine(self.db).latest()

        result = self.compute_targets(portfolio, fund, global_state)

        # Replace existing target allocations with the freshly computed set.
        self.db.query(domain.PortfolioAllocation).filter(
            domain.PortfolioAllocation.portfolio_id == portfolio.pk_id
        ).delete(synchronize_session=False)

        for c in result["allocations"]:
            self.db.add(domain.PortfolioAllocation(
                portfolio_id=portfolio.pk_id,
                asset_pk_id=c["asset"].pk_id,
                strategy_pk_id=None,
                target_weight_pct=c["target_weight_pct"],
                current_weight_pct=self._current_weight(portfolio, c["symbol"]),
            ))

        event = domain.RebalanceEvent(
            portfolio_id=portfolio.pk_id,
            trigger=trigger,
            regime=result["regime"],
            global_risk_score=global_state.global_risk_score if global_state else None,
            decisions={
                "risk_on_off": result["risk_on_off"],
                "cash_floor_pct": result["cash_floor"],
                "cash_pct": result["cash_pct"],
                "invested_pct": result["invested_pct"],
                "targets": result["decisions"],
            },
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        logger.info("Rebalanced %s (%s): %d assets, cash=%.1f%%",
                    portfolio.id, trigger, len(result["allocations"]), result["cash_pct"])
        return event


def _should_rebalance(db: Session, portfolio: domain.Portfolio, fund: domain.Fund) -> bool:
    policy = fund.allocation_policy or {}
    freq_days = int(policy.get("rebalance_freq_days", 7))
    last = (
        db.query(domain.RebalanceEvent)
        .filter(domain.RebalanceEvent.portfolio_id == portfolio.pk_id)
        .order_by(domain.RebalanceEvent.created_at.desc())
        .first()
    )
    if not last:
        return True
    return last.created_at <= datetime.utcnow() - timedelta(days=freq_days)


def run_allocation_cycle(force: bool = False, trigger: str = "SCHEDULED"):
    """Scheduled job: rebalance auto-managed portfolios whose cadence is due.

    `force=True` (e.g. on regime change) rebalances every auto-managed portfolio.
    """
    db = SessionLocal()
    try:
        global_state = MacroIntelligenceEngine(db).latest()
        engine = AllocationEngine(db)
        portfolios = db.query(domain.Portfolio).filter(domain.Portfolio.auto_managed == True).all()
        count = 0
        for p in portfolios:
            fund = db.query(domain.Fund).filter(domain.Fund.pk_id == p.fund_pk_id).first()
            if not fund:
                continue
            if force or _should_rebalance(db, p, fund):
                engine.rebalance_portfolio(p, trigger=trigger, global_state=global_state)
                count += 1
        logger.info("Allocation cycle complete: %d/%d portfolios rebalanced (force=%s).",
                    count, len(portfolios), force)
    except Exception as e:
        logger.error("Allocation cycle failed: %s", e, exc_info=True)
        db.rollback()
    finally:
        db.close()
