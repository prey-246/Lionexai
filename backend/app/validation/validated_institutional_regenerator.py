"""Regenerate institutional portfolios from validated best-config runs."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from app.models import domain
from app.services.audit_service import create_audit_log
from app.services.settlement_constants import PROFIT_ROUTING_SPLIT
from app.services.validated_fund_service import get_latest_validated_fund_run
from app.services import market_data_service
from app.engines.lnx_index import LNXIndexEngine

logger = logging.getLogger("nexa.validated_regenerator")

VALIDATED_PORTFOLIO_IDS = {
    "PRESERVE": "LNX-PRESERVE-VALIDATED",
    "BALANCE": "LNX-BALANCE-VALIDATED",
    "ALPHA": "LNX-ALPHA-VALIDATED",
}


class ValidatedInstitutionalRegenerator:
    def __init__(self, db: Session, admin_user_id: str | None = None):
        self.db = db
        self.admin_user_id = admin_user_id

    def regenerate_all(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for fund_id, pid in VALIDATED_PORTFOLIO_IDS.items():
            try:
                results[fund_id] = self.regenerate_fund_portfolio(fund_id, pid)
            except Exception as e:
                logger.error("Regenerate failed %s: %s", fund_id, e, exc_info=True)
                results[fund_id] = {"error": str(e)}
        results["treasury"] = self._recompute_treasury_from_validated()
        results["lnx"] = self._recompute_lnx_index()
        return results

    def regenerate_fund_portfolio(self, fund_id: str, portfolio_id: str) -> dict[str, Any]:
        fund = self.db.query(domain.Fund).filter(domain.Fund.id == fund_id.upper()).first()
        if not fund:
            raise ValueError(f"Fund {fund_id} not found")

        run = get_latest_validated_fund_run(self.db, fund_id)
        if not run or not run.equity_curve:
            raise ValueError(f"No validated run for {fund_id}")

        admin = self._admin_user()
        portfolio = self.db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id).first()
        initial = float(run.initial_capital or 1_000_000)
        final = float((run.metrics or {}).get("final_equity") or initial)

        if not portfolio:
            portfolio = domain.Portfolio(
                id=portfolio_id,
                user_id=admin.id,
                mandate_pk_id=fund.mandate_pk_id,
                fund_pk_id=fund.pk_id,
                auto_managed=True,
                principal=initial,
                total_equity=final,
                available_margin=final * 0.9,
                created_at=run.period_start or datetime.utcnow(),
            )
            self.db.add(portfolio)
            self.db.flush()
        else:
            portfolio.total_equity = final
            portfolio.principal = initial
            portfolio.available_margin = final * 0.9
            portfolio.fund_pk_id = fund.pk_id
            portfolio.auto_managed = True

        self._clear_portfolio_history(portfolio.pk_id)
        self._seed_equity_curve(portfolio.pk_id, run.equity_curve)
        self._seed_rebalances(portfolio.pk_id, run.rebalance_log or [])
        self._seed_allocations(portfolio.pk_id, run.rebalance_log or [])
        self._seed_validated_trades(portfolio, run)
        self._seed_settlements(portfolio, run)
        self._apply_validated_risk_state(portfolio, run)

        create_audit_log(
            self.db,
            action_type="VALIDATED_REGENERATE",
            description=f"Regenerated {portfolio_id} from validated run {run.id}",
            metadata_json={"fund_id": fund_id, "run_id": run.id, "provenance": "VALIDATED_HISTORICAL"},
        )
        self.db.commit()
        return {
            "portfolio_id": portfolio_id,
            "run_id": run.id,
            "initial_capital": initial,
            "final_equity": final,
            "metrics": run.metrics,
        }

    def _admin_user(self) -> domain.User:
        if self.admin_user_id:
            user = self.db.query(domain.User).filter(domain.User.id == self.admin_user_id).first()
            if user:
                return user
        user = self.db.query(domain.User).filter(domain.User.email == "admin@google.com").first()
        if not user:
            raise ValueError("Admin user required for validated portfolio regeneration")
        return user

    def _clear_portfolio_history(self, portfolio_pk: int) -> None:
        self.db.query(domain.EquityCurve).filter(domain.EquityCurve.portfolio_id == portfolio_pk).delete()
        self.db.query(domain.PortfolioAllocation).filter(
            domain.PortfolioAllocation.portfolio_id == portfolio_pk
        ).delete()
        self.db.query(domain.RebalanceEvent).filter(
            domain.RebalanceEvent.portfolio_id == portfolio_pk
        ).delete()
        self.db.query(domain.ClientSettlement).filter(
            domain.ClientSettlement.portfolio_id == portfolio_pk
        ).delete()
        self.db.query(domain.Trade).filter(domain.Trade.portfolio_id == portfolio_pk).delete()

    def _seed_equity_curve(self, portfolio_pk: int, curve: list[dict]) -> None:
        for pt in curve:
            ts = datetime.utcfromtimestamp(pt["time"]) if pt.get("time") else datetime.utcnow()
            self.db.add(domain.EquityCurve(
                portfolio_id=portfolio_pk,
                timestamp=ts,
                equity=float(pt["value"]),
            ))

    def _seed_rebalances(self, portfolio_pk: int, rebalance_log: list[dict]) -> None:
        for entry in rebalance_log:
            ts = pd.Timestamp(entry.get("date")).to_pydatetime() if entry.get("date") else datetime.utcnow()
            self.db.add(domain.RebalanceEvent(
                id=f"rbe_val_{uuid.uuid4().hex[:10]}",
                portfolio_id=portfolio_pk,
                trigger="VALIDATED_HISTORICAL",
                regime=entry.get("regime"),
                decisions={
                    "weights": entry.get("weights"),
                    "regime_v2": entry.get("regime_v2"),
                    "cash_pct": entry.get("cash_pct"),
                    "nav": entry.get("nav"),
                    "trade_cost": entry.get("trade_cost"),
                    "provenance": "VALIDATED_HISTORICAL",
                },
                created_at=ts,
            ))

    def _seed_allocations(self, portfolio_pk: int, rebalance_log: list[dict]) -> None:
        if not rebalance_log:
            return
        last = rebalance_log[-1]
        for sym, wt in (last.get("weights") or {}).items():
            asset = self.db.query(domain.Asset).filter(domain.Asset.symbol == sym).first()
            if not asset:
                continue
            weight_pct = float(wt)
            self.db.add(domain.PortfolioAllocation(
                portfolio_id=portfolio_pk,
                asset_pk_id=asset.pk_id,
                target_weight_pct=weight_pct,
                current_weight_pct=weight_pct,
            ))

    def _seed_validated_trades(self, portfolio: domain.Portfolio, run: domain.ValidatedFundRun) -> None:
        """Synthetic rebalance-period trades + open positions so UI stats/allocation work."""
        import uuid as _uuid

        rebalance_log = run.rebalance_log or []
        initial = float(run.initial_capital or portfolio.principal or 1_000_000)
        prev_nav = initial

        for i, entry in enumerate(rebalance_log):
            if i == 0:
                prev_nav = float(entry.get("nav") or initial)
                continue
            ts = pd.Timestamp(entry.get("date")).to_pydatetime() if entry.get("date") else datetime.utcnow()
            nav = float(entry.get("nav") or prev_nav)
            period_pnl = round(nav - prev_nav, 2)
            weights = entry.get("weights") or {}
            if not weights:
                prev_nav = nav
                continue

            sym = max(weights, key=lambda s: weights[s])
            asset = self.db.query(domain.Asset).filter(domain.Asset.symbol == sym).first()
            if not asset:
                prev_nav = nav
                continue

            price = market_data_service.latest_close(self.db, sym) or 100.0
            weight_pct = float(weights[sym])
            notional = nav * weight_pct / 100.0
            qty = notional / price if price > 0 else 0.0
            side = "BUY" if period_pnl >= 0 else "SELL"

            self.db.add(domain.Trade(
                id=f"trd_val_{_uuid.uuid4().hex[:10]}",
                portfolio_id=portfolio.pk_id,
                asset_pk_id=asset.pk_id,
                symbol=sym,
                side=side,
                quantity=round(qty, 6),
                entry_price=round(price, 4),
                exit_price=round(price, 4),
                status="CLOSED",
                pnl=period_pnl,
                trade_source="VALIDATED_HISTORICAL",
                strategy_name="ENSEMBLE_REBALANCE",
                created_at=ts,
                closed_at=ts,
            ))
            prev_nav = nav

        # Final holdings as open positions from last rebalance
        if rebalance_log:
            last = rebalance_log[-1]
            nav = float(portfolio.total_equity or last.get("nav") or initial)
            cash_pct = float(last.get("cash_pct") or 5.0)
            portfolio.available_margin = round(nav * cash_pct / 100.0, 2)
            for sym, wt in (last.get("weights") or {}).items():
                weight_pct = float(wt)
                if weight_pct <= 0:
                    continue
                asset = self.db.query(domain.Asset).filter(domain.Asset.symbol == sym).first()
                if not asset:
                    continue
                existing = (
                    self.db.query(domain.Trade)
                    .filter(
                        domain.Trade.portfolio_id == portfolio.pk_id,
                        domain.Trade.symbol == sym,
                        domain.Trade.status == "OPEN",
                        domain.Trade.trade_source == "VALIDATED_HISTORICAL",
                    )
                    .first()
                )
                if existing:
                    continue
                price = market_data_service.latest_close(self.db, sym) or 100.0
                notional = nav * weight_pct / 100.0
                qty = notional / price if price > 0 else 0.0
                self.db.add(domain.Trade(
                    id=f"trd_val_{_uuid.uuid4().hex[:10]}",
                    portfolio_id=portfolio.pk_id,
                    asset_pk_id=asset.pk_id,
                    symbol=sym,
                    side="BUY",
                    quantity=round(qty, 6),
                    entry_price=round(price, 4),
                    status="OPEN",
                    trade_source="VALIDATED_HISTORICAL",
                    strategy_name="ENSEMBLE_REBALANCE",
                    created_at=datetime.utcnow(),
                ))

    def _apply_validated_risk_state(self, portfolio: domain.Portfolio, run: domain.ValidatedFundRun) -> None:
        metrics = run.metrics or {}
        mdd = float(metrics.get("max_drawdown_pct") or 0.0)
        portfolio.current_drawdown_pct = 0.0
        if portfolio.mandate:
            portfolio.current_drawdown_pct = min(
                float(portfolio.mandate.max_drawdown_pct or mdd),
                mdd * 0.1,
            )

    def _seed_settlements(self, portfolio: domain.Portfolio, run: domain.ValidatedFundRun) -> None:
        """Weekly settlement proxy from validated NAV growth."""
        curve = run.equity_curve or []
        if len(curve) < 14:
            return
        eq = pd.Series(
            [p["value"] for p in curve],
            index=pd.DatetimeIndex([pd.Timestamp(p["time"], unit="s") for p in curve]),
        )
        weekly = eq.resample("W").last().dropna()
        principal = portfolio.principal or run.initial_capital
        target_weekly_pct = 2.5
        if portfolio.fund and portfolio.fund.target_weekly_return_pct:
            target_weekly_pct = float(portfolio.fund.target_weekly_return_pct)

        prev = float(principal)
        for ts, nav in weekly.items():
            nav = float(nav)
            period_pnl = nav - prev
            target_gain = prev * (target_weekly_pct / 100.0)
            excess = max(0.0, period_pnl - target_gain)
            iso = ts.isocalendar()
            week_key = f"{iso.year}-W{iso.week:02d}"
            period_start = ts.to_pydatetime()
            period_end = (ts + pd.Timedelta(days=7)).to_pydatetime()
            self.db.add(domain.ClientSettlement(
                id=f"stl_val_{uuid.uuid4().hex[:10]}",
                portfolio_id=portfolio.pk_id,
                period_start=period_start,
                period_end=period_end,
                iso_week_key=week_key,
                opening_equity=round(prev, 2),
                closing_marked_equity=round(nav, 2),
                period_pnl=round(period_pnl, 2),
                target_return_pct=target_weekly_pct,
                client_entitlement=round(min(target_gain, max(0.0, period_pnl)), 2),
                excess_routed=round(excess, 2),
                shortfall_topup=0.0,
                uncovered=round(max(0.0, target_gain - period_pnl), 2),
                status="SETTLED",
                breakdown={"provenance": "VALIDATED_HISTORICAL"},
                created_at=period_end,
            ))
            prev = nav

    def _recompute_treasury_from_validated(self) -> dict[str, Any]:
        settlements = self.db.query(domain.ClientSettlement).filter(
            domain.ClientSettlement.id.like("stl_val_%")
        ).all()
        total_routed = sum(s.excess_routed or 0 for s in settlements)
        pools = {p.id: p for p in self.db.query(domain.TreasuryPool).all()}
        if total_routed > 0 and pools:
            for pool_id, share in PROFIT_ROUTING_SPLIT.items():
                pool = pools.get(pool_id)
                if pool:
                    pool.balance = (pool.balance or 0) + total_routed * share
            self.db.commit()
        return {"total_routed": round(total_routed, 2), "settlement_count": len(settlements)}

    def _recompute_lnx_index(self) -> dict[str, Any]:
        try:
            snap = LNXIndexEngine(self.db).compute(store=True)
            return {"composite_index": snap.composite_index}
        except Exception as e:
            return {"error": str(e)}
