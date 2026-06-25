"""Allocation Integrity Monitor — alerts when weights violate mandate or drift thresholds."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models import domain
from app.services.portfolio_nav import allocation_summary, current_weight_pct, portfolio_nav

logger = logging.getLogger("nexa.allocation_integrity")

TARGET_DEVIATION_PCT = 10.0


def check_portfolio(db: Session, portfolio: domain.Portfolio) -> list[dict[str, Any]]:
    if not portfolio.auto_managed:
        return []

    fund = portfolio.fund
    mandate = portfolio.mandate
    policy = (fund.allocation_policy or {}) if fund else {}
    cash_floor = float(policy.get("cash_floor_pct", 0.0))
    max_position = float(mandate.max_position_size_pct) if mandate and mandate.max_position_size_pct else 100.0

    rows = (
        db.query(domain.PortfolioAllocation)
        .options(joinedload(domain.PortfolioAllocation.asset))
        .filter(domain.PortfolioAllocation.portfolio_id == portfolio.pk_id)
        .all()
    )
    if not rows:
        return []

    summary = allocation_summary(db, portfolio, rows)
    alerts: list[dict[str, Any]] = []

    if abs(summary["target_weight_sum_pct"] - min(100.0, 100.0 - cash_floor)) > 15 and summary["target_weight_sum_pct"] > 100.5:
        alerts.append(_alert(
            portfolio, "TARGET_SUM_INVALID",
            f"Target weights sum to {summary['target_weight_sum_pct']}% (expected ≤ {100 - cash_floor:.1f}%).",
            severity="HIGH",
            metadata=summary,
        ))

    if summary["current_weight_sum_pct"] > 100.0 + 0.5:
        alerts.append(_alert(
            portfolio, "EXPOSURE_OVER_100",
            f"Total marked exposure is {summary['current_weight_sum_pct']}% of NAV (max 100%).",
            severity="CRITICAL",
            metadata=summary,
        ))

    if summary["cash_weight_pct"] < cash_floor - 5.0:
        alerts.append(_alert(
            portfolio, "CASH_FLOOR_VIOLATION",
            f"Implied cash {summary['cash_weight_pct']:.1f}% below fund floor {cash_floor:.1f}%.",
            severity="HIGH",
            metadata=summary,
        ))

    for row in rows:
        sym = row.asset.symbol if row.asset else "?"
        actual = summary["current_by_symbol"].get(sym, 0.0)
        target = row.target_weight_pct or 0.0
        drift = abs(actual - target)
        if drift > TARGET_DEVIATION_PCT:
            alerts.append(_alert(
                portfolio, "TARGET_DEVIATION",
                f"{sym}: actual {actual:.1f}% vs target {target:.1f}% (drift {drift:.1f}%).",
                severity="MEDIUM" if drift < 25 else "HIGH",
                metadata={"symbol": sym, "actual": actual, "target": target, "drift": drift},
            ))
        if actual > max_position + 0.5:
            alerts.append(_alert(
                portfolio, "MANDATE_POSITION_LIMIT",
                f"{sym}: exposure {actual:.1f}% exceeds mandate cap {max_position:.1f}%.",
                severity="CRITICAL",
                metadata={"symbol": sym, "actual": actual, "limit": max_position},
            ))

    return alerts


def persist_alerts(db: Session, alerts: list[dict[str, Any]]) -> int:
    stored = 0
    for a in alerts:
        existing = (
            db.query(domain.AllocationIntegrityAlert)
            .filter(
                domain.AllocationIntegrityAlert.portfolio_id == a["portfolio_id"],
                domain.AllocationIntegrityAlert.alert_type == a["alert_type"],
                domain.AllocationIntegrityAlert.resolved == False,
                domain.AllocationIntegrityAlert.symbol == a.get("symbol"),
            )
            .first()
        )
        if existing:
            existing.message = a["message"]
            existing.metadata_json = a.get("metadata")
            existing.severity = a["severity"]
            existing.updated_at = datetime.utcnow()
            continue
        db.add(domain.AllocationIntegrityAlert(
            id=f"ala_{uuid.uuid4().hex[:12]}",
            portfolio_id=a["portfolio_id"],
            alert_type=a["alert_type"],
            severity=a["severity"],
            message=a["message"],
            symbol=a.get("symbol"),
            metadata_json=a.get("metadata"),
        ))
        stored += 1
    if stored:
        db.commit()
    return stored


def run_integrity_scan(db: Session | None = None) -> dict[str, int]:
    from app.core.database import SessionLocal

    own = db is None
    db = db or SessionLocal()
    try:
        portfolios = db.query(domain.Portfolio).filter(domain.Portfolio.auto_managed == True).all()
        all_alerts: list[dict] = []
        for p in portfolios:
            all_alerts.extend(check_portfolio(db, p))
        stored = persist_alerts(db, all_alerts)
        logger.info("Allocation integrity scan: %d alerts, %d new.", len(all_alerts), stored)
        return {"portfolios_scanned": len(portfolios), "alerts": len(all_alerts), "new_alerts": stored}
    finally:
        if own:
            db.close()


def _alert(portfolio: domain.Portfolio, alert_type: str, message: str, severity: str, metadata: dict) -> dict:
    sym = metadata.get("symbol") if isinstance(metadata, dict) else None
    return {
        "portfolio_id": portfolio.pk_id,
        "portfolio_code": portfolio.id,
        "alert_type": alert_type,
        "severity": severity,
        "message": message,
        "symbol": sym,
        "metadata": metadata,
    }
