from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.models import domain
from app.models.schemas import PaginatedAuditLogs

router = APIRouter()

PRIVILEGED_ROLES = ("admin", "operator", "risk_manager")


@router.get("/", response_model=PaginatedAuditLogs)
def get_audit_logs(
    db: Session = Depends(deps.get_db),
    current_user: domain.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    action_type: Optional[str] = None,
    exchange: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
):
    """Retrieve audit logs. Privileged roles see system-wide trail; clients see own actions."""
    query = db.query(domain.AuditLog)

    if current_user.role_tier not in PRIVILEGED_ROLES:
        query = query.filter(domain.AuditLog.user_id == current_user.id)

    if action_type:
        query = query.filter(domain.AuditLog.action_type == action_type)
    if exchange:
        query = query.filter(domain.AuditLog.metadata_json.op("->>")("exchange") == exchange.lower())
    if start_date:
        query = query.filter(domain.AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(domain.AuditLog.timestamp <= end_date)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (domain.AuditLog.description.ilike(like))
            | (domain.AuditLog.action_type.ilike(like))
        )

    total = query.count()
    logs = query.order_by(domain.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return {"logs": logs, "total": total, "limit": limit, "offset": skip}
