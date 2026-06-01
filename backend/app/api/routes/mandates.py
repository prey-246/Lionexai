from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.domain import Mandate
from app.models.schemas import Mandate as MandateSchema

router = APIRouter()

@router.get("/mandates", response_model=List[MandateSchema], tags=["Mandates"])
def get_all_mandates(db: Session = Depends(get_db)):
    mandates = db.query(Mandate).all()
    return mandates

@router.get("/mandates/{mandate_id}", response_model=MandateSchema, tags=["Mandates"])
def get_mandate_by_id(mandate_id: str, db: Session = Depends(get_db)):
    mandate = db.query(Mandate).filter(Mandate.id == mandate_id).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")
    return mandate