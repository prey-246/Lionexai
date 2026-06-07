from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.models import schemas, domain
from app.services import user_service
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.api.deps import get_current_user
from app.services.audit_service import create_audit_log

router = APIRouter()

@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    """
    db_user = user_service.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_service.create_user(db=db, user=user)


@router.post("/token", response_model=schemas.Token, tags=["Auth"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = user_service.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    create_audit_log(
        db,
        action_type="USER_LOGIN",
        description=f"User '{user.email}' logged in successfully."
    )
    db.commit() # This is crucial to save the audit log
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.User, tags=["Auth"])
def read_users_me(current_user: domain.User = Depends(get_current_user)):
    """
    Fetch the current logged in user.
    """
    return current_user

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["Auth"])
def logout(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """
    Logs a user out by creating an audit log entry.
    The frontend is responsible for deleting the client-side token.
    """
    create_audit_log(
        db,
        action_type="USER_LOGOUT",
        description=f"User '{current_user.email}' logged out successfully."
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)