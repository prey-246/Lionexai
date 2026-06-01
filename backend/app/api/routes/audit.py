from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/", response_model=schemas.PaginatedAuditLogs)
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
    action_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Retrieve audit logs with pagination.
    """
    # Base query for audit logs
    query = db.query(domain.AuditLog)

    # For now, all users can only see their own audit logs.
    # In a future version, an 'admin' role could bypass this filter.
    query = query.filter(domain.AuditLog.metadata_json['user_id'].as_string() == current_user.id)
    if action_type:
        query = query.filter(domain.AuditLog.action_type == action_type)

    total = query.count()
    logs = query.order_by(domain.AuditLog.timestamp.desc()).limit(limit).offset(offset).all()

    return schemas.PaginatedAuditLogs(total=total, limit=limit, offset=offset, logs=logs)