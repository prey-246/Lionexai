"""Execution lifecycle monitoring — full trade traceability."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import domain

logger = logging.getLogger("nexa.execution_lifecycle")

STAGES = (
    "SIGNAL_GENERATED",
    "ALLOCATION_DECISION",
    "ORDER_SUBMITTED",
    "ORDER_FILLED",
    "POSITION_OPENED",
    "POSITION_CLOSED",
    "SETTLEMENT_GENERATED",
    "TREASURY_ROUTED",
)


def record_lifecycle_event(
    db: Session,
    stage: str,
    *,
    trade_id: str | None = None,
    portfolio_id: str | None = None,
    symbol: str | None = None,
    metadata: dict | None = None,
    reference_id: str | None = None,
) -> domain.ExecutionLifecycleEvent:
    if stage not in STAGES:
        logger.warning("Unknown lifecycle stage: %s", stage)
    event = domain.ExecutionLifecycleEvent(
        id=f"exec_{uuid.uuid4().hex[:12]}",
        stage=stage,
        trade_id=trade_id,
        portfolio_id=portfolio_id,
        symbol=symbol,
        reference_id=reference_id,
        metadata_json=metadata or {},
    )
    db.add(event)
    return event


def trace_trade(db: Session, trade_id: str) -> dict[str, Any]:
    """Reconstruct full lifecycle for a trade."""
    trade = db.query(domain.Trade).filter(domain.Trade.id == trade_id).first()
    if not trade:
        return {"trade_id": trade_id, "found": False, "events": []}

    portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.pk_id == trade.portfolio_id).first()
    events = (
        db.query(domain.ExecutionLifecycleEvent)
        .filter(domain.ExecutionLifecycleEvent.trade_id == trade_id)
        .order_by(domain.ExecutionLifecycleEvent.timestamp.asc())
        .all()
    )

    settlements = (
        db.query(domain.ClientSettlement)
        .filter(domain.ClientSettlement.portfolio_id == trade.portfolio_id)
        .order_by(domain.ClientSettlement.period_end.desc())
        .limit(5)
        .all()
    )

    treasury_txs = []
    if settlements:
        s_pks = [s.pk_id for s in settlements]
        treasury_txs = (
            db.query(domain.TreasuryTransaction)
            .filter(domain.TreasuryTransaction.settlement_pk_id.in_(s_pks))
            .all()
        )

    rebalance = (
        db.query(domain.RebalanceEvent)
        .filter(domain.RebalanceEvent.portfolio_id == trade.portfolio_id)
        .order_by(domain.RebalanceEvent.created_at.desc())
        .first()
    )

    timeline = [
        {
            "stage": e.stage,
            "timestamp": e.timestamp.isoformat(),
            "metadata": e.metadata_json,
        }
        for e in events
    ]

    # Synthesize missing stages from trade record
    if not timeline and trade:
        timeline = _synthesize_from_trade(trade, portfolio, rebalance)

    return {
        "trade_id": trade_id,
        "found": True,
        "symbol": trade.symbol,
        "side": trade.side,
        "status": trade.status,
        "strategy": trade.strategy_name,
        "portfolio_id": portfolio.id if portfolio else None,
        "events": timeline,
        "settlements_linked": len(settlements),
        "treasury_routed": sum(t.amount for t in treasury_txs if t.amount > 0),
        "rebalance_trigger": rebalance.trigger if rebalance else None,
        "data_provenance": "DEMO" if (trade.exchange or "").lower() == "simulated" else "PAPER_LIVE",
    }


def _synthesize_from_trade(
    trade: domain.Trade,
    portfolio: domain.Portfolio | None,
    rebalance: domain.RebalanceEvent | None,
) -> list[dict]:
    """Backfill timeline from existing records when lifecycle events weren't recorded."""
    items = []
    if rebalance:
        items.append({
            "stage": "ALLOCATION_DECISION",
            "timestamp": rebalance.created_at.isoformat(),
            "metadata": {"trigger": rebalance.trigger, "regime": rebalance.regime},
        })
    items.append({
        "stage": "ORDER_SUBMITTED",
        "timestamp": trade.created_at.isoformat(),
        "metadata": {"exchange": trade.exchange, "source": trade.trade_source},
    })
    if trade.status in ("OPEN", "CLOSED"):
        items.append({
            "stage": "ORDER_FILLED",
            "timestamp": trade.created_at.isoformat(),
            "metadata": {"latency_ms": trade.execution_latency_ms},
        })
        items.append({"stage": "POSITION_OPENED", "timestamp": trade.created_at.isoformat(), "metadata": {}})
    if trade.status == "CLOSED" and trade.closed_at:
        items.append({
            "stage": "POSITION_CLOSED",
            "timestamp": trade.closed_at.isoformat(),
            "metadata": {"pnl": trade.pnl},
        })
    return items


def recent_events(db: Session, limit: int = 100, stage: str | None = None) -> list[dict]:
    q = db.query(domain.ExecutionLifecycleEvent).order_by(
        domain.ExecutionLifecycleEvent.timestamp.desc()
    )
    if stage:
        q = q.filter(domain.ExecutionLifecycleEvent.stage == stage.upper())
    return [
        {
            "id": e.id,
            "stage": e.stage,
            "trade_id": e.trade_id,
            "portfolio_id": e.portfolio_id,
            "symbol": e.symbol,
            "timestamp": e.timestamp,
            "metadata": e.metadata_json,
        }
        for e in q.limit(limit).all()
    ]
