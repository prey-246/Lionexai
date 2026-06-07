from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.models import schemas, domain
from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.services.audit_service import create_audit_log

router = APIRouter()

class RoleUpdate(BaseModel):
    role_tier: str

@router.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: domain.User = Depends(get_current_user)):
    """
    Get current logged-in user.
    """
    return current_user

@router.get("/users", response_model=List[schemas.User], dependencies=[Depends(require_role(["admin"]))])
def list_users(db: Session = Depends(get_db)):
    """
    List all registered users.
    """
    return db.query(domain.User).order_by(domain.User.email.asc()).all()

@router.put("/users/{user_id}/role", response_model=schemas.User, dependencies=[Depends(require_role(["admin"]))])
def update_user_role(
    user_id: str,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Updates the role of a user.
    """
    user = db.query(domain.User).filter(domain.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.role_tier
    user.role_tier = role_update.role_tier
    
    create_audit_log(
        db,
        action_type="USER_ROLE_UPDATE",
        description=f"Admin {current_user.email} updated role for {user.email} from {old_role} to {user.role_tier}.",
        metadata_json={"target_user_id": user.id, "old_role": old_role, "new_role": user.role_tier}
    )
    db.commit()
    db.refresh(user)
    return user