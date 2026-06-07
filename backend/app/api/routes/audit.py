from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api import deps
from app.models import domain
from app.models.schemas import PaginatedAuditLogs

router = APIRouter()

@router.get("/", response_model=PaginatedAuditLogs)
def get_audit_logs(
    db: Session = Depends(deps.get_db),
    current_user: domain.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    action_type: Optional[str] = None,
):
    """
    Retrieve audit logs for the current user.
    """
    query = db.query(domain.AuditLog)

    # The fix: Filter on the correct 'user_id' column directly.
    query = query.filter(domain.AuditLog.user_id == current_user.id)

    if action_type:
        query = query.filter(domain.AuditLog.action_type == action_type)

    total = query.count()
    logs = query.order_by(domain.AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    return {"logs": logs, "total": total, "limit": limit, "offset": skip}