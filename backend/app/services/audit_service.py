import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models import domain
from app.services.audit_constants import (
    categorize_action,
    EXCHANGE_RECONNECT_ACTION,
    EXCHANGE_DISCONNECT_ACTION,
    INFRASTRUCTURE_SUMMARY_ACTION,
)

logger = logging.getLogger(__name__)

_RECONNECT_COALESCE_HOURS = 6


def create_audit_log(
    db: Session,
    action_type: str,
    description: str,
    metadata_json: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
):
    """Creates and stores an audit log entry with automatic category tagging."""
    meta = dict(metadata_json or {})
    if not user_id and meta.get("user_id"):
        user_id = str(meta.get("user_id"))
    meta.setdefault("category", categorize_action(action_type))

    try:
        audit_log_entry = domain.AuditLog(
            action_type=action_type,
            description=description,
            metadata_json=meta,
            user_id=user_id,
        )
        db.add(audit_log_entry)
        return audit_log_entry
    except Exception as e:
        logger.error("Failed to create audit log: %s", e)
        return None


def should_log_exchange_reconnect(db: Session, exchange: str) -> bool:
    """Return False if a reconnect for this exchange was logged recently."""
    cutoff = datetime.utcnow() - timedelta(hours=_RECONNECT_COALESCE_HOURS)
    recent = (
        db.query(domain.AuditLog)
        .filter(
            domain.AuditLog.action_type == EXCHANGE_RECONNECT_ACTION,
            domain.AuditLog.timestamp >= cutoff,
            domain.AuditLog.metadata_json.op("->>")("exchange") == exchange.lower(),
        )
        .first()
    )
    return recent is None


def log_exchange_reconnect(db: Session, exchange: str, description: str | None = None) -> None:
    if not should_log_exchange_reconnect(db, exchange):
        return
    create_audit_log(
        db,
        action_type=EXCHANGE_RECONNECT_ACTION,
        description=description or f"{exchange.upper()} adapter connected.",
        metadata_json={"exchange": exchange.lower(), "category": "Infrastructure"},
    )


def log_exchange_disconnect(db: Session, exchange: str, error: str) -> None:
    create_audit_log(
        db,
        action_type=EXCHANGE_DISCONNECT_ACTION,
        description=f"Failed to connect to {exchange.upper()}: {error}",
        metadata_json={"exchange": exchange.lower(), "error": error, "category": "Infrastructure"},
    )


def collapse_infrastructure_reconnect_logs(db: Session, keep_recent_hours: int = 24) -> int:
    """Replace repetitive EXCHANGE_RECONNECTED rows with one daily summary per exchange."""
    cutoff = datetime.utcnow() - timedelta(hours=keep_recent_hours)
    rows = (
        db.query(domain.AuditLog)
        .filter(
            domain.AuditLog.action_type == EXCHANGE_RECONNECT_ACTION,
            domain.AuditLog.timestamp >= cutoff,
        )
        .order_by(domain.AuditLog.timestamp.asc())
        .all()
    )
    if len(rows) <= 3:
        return 0

    by_exchange: dict[str, list] = {}
    for row in rows:
        ex = (row.metadata_json or {}).get("exchange", "unknown")
        by_exchange.setdefault(ex, []).append(row)

    removed = 0
    for exchange, group in by_exchange.items():
        if len(group) <= 1:
            continue
        summary_ts = group[-1].timestamp
        create_audit_log(
            db,
            action_type=INFRASTRUCTURE_SUMMARY_ACTION,
            description=f"{exchange.upper()}: {len(group)} reconnect events consolidated (last {keep_recent_hours}h).",
            metadata_json={
                "exchange": exchange,
                "category": "Infrastructure",
                "event_count": len(group),
                "consolidated_from": EXCHANGE_RECONNECT_ACTION,
            },
        )
        for row in group[:-1]:
            db.delete(row)
            removed += 1
    return removed
