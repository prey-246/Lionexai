from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.domain import AuditLog
from typing import Optional

router = APIRouter()

@router.get("/", summary="Get audit logs")
def get_audit_logs(
    action_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)

    if action_type:
        query = query.filter(AuditLog.action_type == action_type)

    logs = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit).all()
    total = query.count()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": logs
    }

@router.get("/{log_id}", summary="Get specific audit log entry")
def get_audit_log(log_id: str, db: Session = Depends(get_db)):
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Audit log entry not found")
    return log

@router.get("/events/risk-rejections", summary="Get all risk rejections")
def get_risk_rejections(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(
        AuditLog.action_type == "RISK_REJECTION"
    ).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    return logs

@router.get("/events/kill-switch", summary="Get all kill switch events")
def get_kill_switch_events(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(
        AuditLog.action_type == "KILL_SWITCH_TRIGGERED"
    ).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    return logs
