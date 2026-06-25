"""Paper trading validation — live prices, no real money, separate from demo ledger."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models import domain
from app.services.portfolio_nav import portfolio_nav

logger = logging.getLogger("nexa.paper_trading_validation")

PERIODS = {"30D": 30, "60D": 60, "90D": 90, "180D": 180, "365D": 365}


def _period_return(curves: list, days: int) -> float | None:
    if len(curves) < 2:
        return None
    last = curves[-1]
    cutoff = last.timestamp - timedelta(days=days)
    baseline = curves[0]
    for c in curves:
        if c.timestamp <= cutoff:
            baseline = c
    if not baseline.equity or baseline.equity <= 0:
        return None
    return round((last.equity - baseline.equity) / baseline.equity * 100, 2)


def compute_paper_metrics(db: Session, portfolio: domain.Portfolio, days: int) -> dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=days)
    trades = (
        db.query(domain.Trade)
        .filter(
            domain.Trade.portfolio_id == portfolio.pk_id,
            domain.Trade.trade_source == "AUTONOMOUS",
            domain.Trade.created_at >= since,
        )
        .all()
    )
    closed = [t for t in trades if t.status == "CLOSED" and t.pnl is not None]
    wins = sum(1 for t in closed if t.pnl > 0)
    latencies = [t.execution_latency_ms for t in closed if t.execution_latency_ms]
    curves = (
        db.query(domain.EquityCurve)
        .filter(domain.EquityCurve.portfolio_id == portfolio.pk_id)
        .order_by(domain.EquityCurve.timestamp.asc())
        .all()
    )

    nav = portfolio_nav(db, portfolio)
    period_ret = _period_return(curves, days)

    return {
        "portfolio_id": portfolio.id,
        "period_days": days,
        "nav": round(nav, 2),
        "daily_return_pct": period_ret,  # simplified trailing
        "weekly_return_pct": _period_return(curves, min(7, days)),
        "monthly_return_pct": _period_return(curves, min(30, days)),
        "win_rate_pct": round(wins / len(closed) * 100, 2) if closed else None,
        "total_trades": len(closed),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "simulated_fill_pct": round(
            sum(1 for t in trades if t.exchange == "simulated") / max(len(trades), 1) * 100, 2
        ),
        "provenance": "PAPER_LIVE",
    }


def update_paper_validation_snapshots(db: Session | None = None) -> int:
    from app.core.database import SessionLocal

    own = db is None
    db = db or SessionLocal()
    updated = 0
    try:
        portfolios = db.query(domain.Portfolio).filter(domain.Portfolio.auto_managed == True).all()
        for period_label, days in PERIODS.items():
            agg_metrics: list[dict] = []
            for p in portfolios:
                agg_metrics.append(compute_paper_metrics(db, p, days))

            snapshot_key = f"PAPER_GLOBAL_{period_label}"
            existing = db.query(domain.PaperTradingValidationSnapshot).filter(
                domain.PaperTradingValidationSnapshot.id == snapshot_key
            ).first()

            payload = {
                "portfolios": len(agg_metrics),
                "aggregate": _aggregate(agg_metrics),
                "by_portfolio": agg_metrics[:50],
            }
            if existing:
                existing.metrics = payload
                existing.computed_at = datetime.utcnow()
            else:
                db.add(domain.PaperTradingValidationSnapshot(
                    id=snapshot_key,
                    period=period_label,
                    scope="GLOBAL",
                    metrics=payload,
                    provenance="PAPER_LIVE",
                ))
            updated += 1
        db.commit()
        logger.info("Paper trading validation: updated %d period snapshots.", updated)
        return updated
    finally:
        if own:
            db.close()


def _aggregate(metrics: list[dict]) -> dict:
    rets = [m["monthly_return_pct"] for m in metrics if m.get("monthly_return_pct") is not None]
    wins = [m["win_rate_pct"] for m in metrics if m.get("win_rate_pct") is not None]
    return {
        "avg_monthly_return_pct": round(sum(rets) / len(rets), 2) if rets else None,
        "avg_win_rate_pct": round(sum(wins) / len(wins), 2) if wins else None,
        "portfolio_count": len(metrics),
    }
