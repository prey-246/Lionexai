from sqlalchemy.orm import Session
from app.models import domain, schemas
from app.core.security import get_password_hash

def get_user_by_email(db: Session, email: str) -> domain.User | None:
    return db.query(domain.User).filter(domain.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate) -> domain.User:
    hashed_password = get_password_hash(user.password)
    db_user = domain.User(
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user