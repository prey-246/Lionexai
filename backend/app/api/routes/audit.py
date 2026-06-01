from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.domain import AuditLog
from app.models.schemas import PaginatedAuditLogs
from sqlalchemy import desc

router = APIRouter()

@router.get("/audit/", response_model=PaginatedAuditLogs, tags=["Audit"])
def get_audit_logs(
    action_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)
    
    total = query.count()
    logs = query.order_by(desc(AuditLog.timestamp)).limit(limit).offset(offset).all()
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": logs
    }