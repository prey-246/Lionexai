import uuid
from sqlalchemy.orm import Session
from app.models import domain

def create_audit_log(
    db: Session,
    action_type: str,
    description: str,
    metadata: dict | None = None,
):
    """
    Creates and saves a new audit log entry.
    """
    log_entry = domain.AuditLog(
        id=f"log_{uuid.uuid4().hex[:12]}",
        action_type=action_type,
        description=description,
        metadata_json=metadata,
    )
    db.add(log_entry)
    db.commit()
    return log_entry