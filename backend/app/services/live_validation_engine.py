"""Real paper-live validation — long-running autonomous performance tracking.

Stored separately from DEMO operational snapshots and VALIDATED_HISTORICAL backtests.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.analytics.performance_engine import PerformanceEngine, detect_provenance_from_trades
from app.core.database import SessionLocal
from app.models import domain

logger = logging.getLogger("nexa.live_validation")

PERIODS = {"7D": 7, "30D": 30, "60D": 60, "90D": 90, "180D": 180, "365D": 365}
PAPER_LIVE = "PAPER_LIVE"


def _is_paper_live_portfolio(db: Session, portfolio: domain.Portfolio) -> bool:
    trades = (
        db.query(domain.Trade)
        .filter(domain.Trade.portfolio_id == portfolio.pk_id)
        .limit(100)
        .all()
    )
    if not trades:
        return portfolio.auto_managed
    return detect_provenance_from_trades(trades) in ("PAPER_LIVE", "MIXED")


def _allocation_drift(db: Session, portfolio: domain.Portfolio) -> float | None:
    rows = (
        db.query(domain.PortfolioAllocation)
        .filter(domain.PortfolioAllocation.portfolio_id == portfolio.pk_id)
        .all()
    )
    if not rows:
        return None
    return round(sum(abs((r.current_weight_pct or 0) - (r.target_weight_pct or 0)) for r in rows), 2)


def _exposure_pct(db: Session, portfolio: domain.Portfolio) -> float:
    equity = portfolio.total_equity or 0.0
    if equity <= 0:
        return 0.0
    open_trades = (
        db.query(domain.Trade)
        .filter(domain.Trade.portfolio_id == portfolio.pk_id, domain.Trade.status == "OPEN")
        .all()
    )
    exposure = sum((t.quantity or 0) * (t.entry_price or 0) for t in open_trades)
    return round(exposure / equity * 100, 2)


def _treasury_contributions(db: Session, portfolio_pk: int, since: datetime) -> float:
    settlements = (
        db.query(domain.ClientSettlement)
        .filter(
            domain.ClientSettlement.portfolio_id == portfolio_pk,
            domain.ClientSettlement.period_end >= since,
        )
        .all()
    )
    return round(sum(s.excess_routed or 0 for s in settlements), 2)


def compute_live_validation_metrics(
    db: Session,
    portfolio: domain.Portfolio,
    period_days: int,
) -> dict[str, Any]:
    engine = PerformanceEngine(db)
    analytics = engine.portfolio_equity_analytics(portfolio.pk_id, days=period_days)
    since = datetime.utcnow() - timedelta(days=period_days)

    if not _is_paper_live_portfolio(db, portfolio):
        provenance = "DEMO"
    else:
        provenance = PAPER_LIVE

    return {
        "portfolio_id": portfolio.id,
        "period_days": period_days,
        "provenance": provenance,
        "nav": round(portfolio.total_equity or 0, 2),
        "daily_return_pct": analytics.get("daily_return_pct"),
        "weekly_return_pct": analytics.get("weekly_return_pct"),
        "monthly_return_pct": analytics.get("monthly_return_pct"),
        "sharpe_ratio": analytics.get("sharpe_ratio"),
        "sortino_ratio": analytics.get("sortino_ratio"),
        "max_drawdown_pct": analytics.get("max_drawdown_pct"),
        "volatility_annualized": analytics.get("volatility_annualized"),
        "win_rate_pct": analytics.get("win_rate_pct"),
        "profit_factor": analytics.get("profit_factor"),
        "exposure_pct": _exposure_pct(db, portfolio),
        "allocation_drift_pct": _allocation_drift(db, portfolio),
        "treasury_contributions": _treasury_contributions(db, portfolio.pk_id, since),
        "rolling_sharpe": analytics.get("rolling_sharpe", [])[-30:],
        "rolling_sortino": analytics.get("rolling_sortino", [])[-30:],
        "rolling_drawdown": analytics.get("rolling_drawdown", [])[-30:],
        "equity_curve": analytics.get("equity_curve", [])[-120:],
    }


def _aggregate_portfolios(metrics: list[dict]) -> dict[str, Any]:
    paper = [m for m in metrics if m.get("provenance") == PAPER_LIVE]
    source = paper if paper else metrics

    def avg(key: str) -> float | None:
        vals = [m[key] for m in source if m.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    return {
        "portfolio_count": len(metrics),
        "paper_live_count": len(paper),
        "avg_weekly_return_pct": avg("weekly_return_pct"),
        "avg_monthly_return_pct": avg("monthly_return_pct"),
        "avg_sharpe_ratio": avg("sharpe_ratio"),
        "avg_sortino_ratio": avg("sortino_ratio"),
        "avg_max_drawdown_pct": avg("max_drawdown_pct"),
        "avg_win_rate_pct": avg("win_rate_pct"),
        "total_treasury_contributions": round(sum(m.get("treasury_contributions") or 0 for m in source), 2),
        "provenance": PAPER_LIVE if paper else "DEMO",
    }


def update_live_validation_snapshots(db: Session | None = None) -> int:
    own = db is None
    db = db or SessionLocal()
    updated = 0
    try:
        portfolios = db.query(domain.Portfolio).filter(domain.Portfolio.auto_managed == True).all()
        for period_label, days in PERIODS.items():
            by_portfolio = [compute_live_validation_metrics(db, p, days) for p in portfolios]
            aggregate = _aggregate_portfolios(by_portfolio)
            snapshot_id = f"LIVE_VAL_GLOBAL_{period_label}"

            existing = db.query(domain.LiveValidationSnapshot).filter(
                domain.LiveValidationSnapshot.id == snapshot_id
            ).first()

            payload = {
                "aggregate": aggregate,
                "by_portfolio": by_portfolio[:50],
            }
            prov = aggregate.get("provenance", PAPER_LIVE)

            if existing:
                existing.metrics = payload
                existing.provenance = prov
                existing.computed_at = datetime.utcnow()
            else:
                db.add(domain.LiveValidationSnapshot(
                    id=snapshot_id,
                    period=period_label,
                    scope="GLOBAL",
                    metrics=payload,
                    provenance=prov,
                ))
            updated += 1

            for fund in db.query(domain.Fund).filter(domain.Fund.is_active == True).all():
                fund_ports = [p for p in portfolios if p.fund_pk_id == fund.pk_id]
                if not fund_ports:
                    continue
                fund_metrics = [compute_live_validation_metrics(db, p, days) for p in fund_ports]
                fund_id = f"LIVE_VAL_{fund.id}_{period_label}"
                fund_agg = _aggregate_portfolios(fund_metrics)
                existing_f = db.query(domain.LiveValidationSnapshot).filter(
                    domain.LiveValidationSnapshot.id == fund_id
                ).first()
                fpayload = {"aggregate": fund_agg, "by_portfolio": fund_metrics}
                if existing_f:
                    existing_f.metrics = fpayload
                    existing_f.provenance = fund_agg.get("provenance", prov)
                    existing_f.computed_at = datetime.utcnow()
                else:
                    db.add(domain.LiveValidationSnapshot(
                        id=fund_id,
                        period=period_label,
                        scope="FUND",
                        scope_id=fund.id,
                        metrics=fpayload,
                        provenance=fund_agg.get("provenance", prov),
                    ))
                updated += 1

        db.commit()
        logger.info("Live validation: updated %d snapshots", updated)
        return updated
    except Exception as e:
        logger.error("Live validation update failed: %s", e, exc_info=True)
        db.rollback()
        raise
    finally:
        if own:
            db.close()
