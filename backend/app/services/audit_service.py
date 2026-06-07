import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models import domain

logger = logging.getLogger(__name__)

def create_audit_log(
    db: Session,
    action_type: str,
    description: str,
    metadata_json: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
):
    """Creates and stores an audit log entry."""
    # Gracefully extract user_id from metadata_json if it was passed there
    if not user_id and metadata_json and "user_id" in metadata_json:
        user_id = str(metadata_json.get("user_id"))

    try:
        audit_log_entry = domain.AuditLog(
            action_type=action_type,
            description=description,
            metadata_json=metadata_json,
            user_id=user_id
        )
        db.add(audit_log_entry)
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")