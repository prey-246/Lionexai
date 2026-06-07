from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel

class AuditLogBase(BaseModel):
    action_type: str
    details: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

class AuditLog(AuditLogBase):
    pk_id: int
    timestamp: datetime

    class Config:
        from_attributes = True