from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    """
    Check if the API and database are online.
    """
    db.execute(text('SELECT 1'))
    return {"status": "online", "database": "connected"}


@router.get("/mandates", response_model=List[schemas.Mandate], tags=["System"])
def read_mandates(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Retrieve all risk mandates. Requires authentication.
    """
    mandates = db.query(domain.Mandate).all()
    return mandates

@router.get("/mandates/{mandate_id}", response_model=schemas.Mandate, tags=["System"])
def get_mandate_by_id(
    mandate_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Retrieve a single risk mandate by its ID. Requires authentication.
    """
    mandate = db.query(domain.Mandate).filter(domain.Mandate.id == mandate_id).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")
    return mandate