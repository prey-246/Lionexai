from fastapi import APIRouter, Depends
from app.models import schemas, domain
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: domain.User = Depends(get_current_user)):
    """
    Get current logged-in user.
    """
    return current_user