from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.domain import Mandate

router = APIRouter()

@router.get("/", summary="List all active risk mandates")
def get_mandates(db: Session = Depends(get_db)):
    mandates = db.query(Mandate).all()
    return mandates

@router.get("/{mandate_id}", summary="Get specific mandate parameters")
def get_mandate(mandate_id: str, db: Session = Depends(get_db)):
    mandate = db.query(Mandate).filter(Mandate.id == mandate_id.upper()).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")
    return mandate