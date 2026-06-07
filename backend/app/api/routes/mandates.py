from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import domain
from app.api.deps import get_current_user, require_role
from app.services.audit_service import create_audit_log


# Pydantic Schemas for Mandate Management
class MandateBase(BaseModel):
    id: str = Field(..., description="Mandate Code, e.g., 'ALPHA'. Must be uppercase.", pattern=r'^[A-Z_]+$')
    name: str = Field(...)
    description: str = Field(...)
    risk_tier: str = Field(..., description="Low, Medium, or High")
    max_position_size_pct: float = Field(..., gt=0)
    max_portfolio_exposure_pct: float = Field(..., gt=0)
    max_leverage: float = Field(..., gt=0)
    daily_loss_limit_pct: float = Field(..., gt=0, lt=100)
    max_drawdown_pct: float = Field(..., gt=0, lt=100)
    max_open_positions: int = Field(..., gt=0)
    restricted_assets_enabled: bool = Field(...)
    kill_switch_enabled: bool = Field(...)
    allowed_assets: List[str] = Field(...)

class MandateCreate(MandateBase):
    pass

class MandateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    risk_tier: str | None = None
    max_position_size_pct: float | None = None
    max_portfolio_exposure_pct: float | None = None
    max_leverage: float | None = None
    max_drawdown_pct: float | None = None
    daily_loss_limit_pct: float | None = None
    max_open_positions: int | None = None
    restricted_assets_enabled: bool | None = None
    kill_switch_enabled: bool | None = None
    allowed_assets: List[str] | None = None

class MandateResponse(MandateBase):
    pk_id: int
    version: int
    is_active: bool
    kill_switch_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


router = APIRouter()

@router.post("/seed-defaults", response_model=List[MandateResponse], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
def seed_default_mandates(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    defaults = [
        {
            "id": "PRESERVE", "name": "Capital Preservation", "description": "Designed for conservative investors focused on preserving capital with minimal volatility.",
            "risk_tier": "Low", "max_position_size_pct": 10.0, "max_portfolio_exposure_pct": 50.0, "max_leverage": 1.0,
            "daily_loss_limit_pct": 1.0, "max_drawdown_pct": 5.0, "max_open_positions": 5, "restricted_assets_enabled": True, "kill_switch_enabled": True,
            "allowed_assets": ["BTC/USDT", "ETH/USDT"]
        },
        {
            "id": "BALANCE", "name": "Balanced Growth", "description": "Designed for moderate growth while maintaining controlled risk.",
            "risk_tier": "Medium", "max_position_size_pct": 20.0, "max_portfolio_exposure_pct": 75.0, "max_leverage": 2.0,
            "daily_loss_limit_pct": 2.0, "max_drawdown_pct": 10.0, "max_open_positions": 10, "restricted_assets_enabled": True, "kill_switch_enabled": True,
            "allowed_assets": ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        },
        {
            "id": "ALPHA", "name": "Aggressive Growth", "description": "Designed for aggressive strategies seeking higher returns while operating within defined risk controls.",
            "risk_tier": "High", "max_position_size_pct": 30.0, "max_portfolio_exposure_pct": 100.0, "max_leverage": 3.0,
            "daily_loss_limit_pct": 5.0, "max_drawdown_pct": 20.0, "max_open_positions": 20, "restricted_assets_enabled": False, "kill_switch_enabled": True,
            "allowed_assets": ["ALL"]
        }
    ]
    
    created_mandates = []
    for d in defaults:
        if not db.query(domain.Mandate).filter(domain.Mandate.id == d["id"], domain.Mandate.is_active == True).first():
            new_m = domain.Mandate(**d, version=1, created_by_id=current_user.id)
            db.add(new_m)
            created_mandates.append(new_m)
            
    db.commit()
    for m in created_mandates: db.refresh(m)
    return created_mandates

@router.post("/", response_model=MandateResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin", "risk_manager"]))])
def create_mandate(mandate: MandateCreate, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    db_mandate = db.query(domain.Mandate).filter(domain.Mandate.id == mandate.id, domain.Mandate.is_active == True).first()
    if db_mandate:
        raise HTTPException(status_code=400, detail="An active mandate with this ID already exists")
    
    new_mandate = domain.Mandate(**mandate.dict(), version=1, created_by_id=current_user.id)
    db.add(new_mandate)

    create_audit_log(
        db,
        action_type="MANDATE_CREATE",
        description=f"User '{current_user.email}' created new mandate '{new_mandate.id}' (v1).",
        metadata_json={"mandate_id": new_mandate.id, "user_id": current_user.id}
    )
    db.commit()
    db.refresh(new_mandate)
    return new_mandate

@router.get("/", response_model=List[MandateResponse])
def list_mandates(db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """
    Retrieve the latest ACTIVE version of all risk mandates.
    """
    return db.query(domain.Mandate).filter(domain.Mandate.is_active == True).order_by(domain.Mandate.id).all()

@router.get("/{mandate_id}", response_model=MandateResponse)
def get_mandate(mandate_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    """
    Retrieve the latest active version of a single risk mandate by its ID.
    """
    mandate = db.query(domain.Mandate).filter(domain.Mandate.id == mandate_id, domain.Mandate.is_active == True).order_by(domain.Mandate.version.desc()).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")
    return mandate

@router.put("/{pk_id}", response_model=MandateResponse, dependencies=[Depends(require_role(["admin", "risk_manager"]))])
def update_mandate(pk_id: int, mandate_update: MandateUpdate, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    db_mandate = db.query(domain.Mandate).filter(domain.Mandate.pk_id == pk_id).first()
    if not db_mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")
    if not db_mandate.is_active:
        raise HTTPException(status_code=400, detail="Cannot update an inactive mandate version. Please update the active version.")
    
    update_data = mandate_update.dict(exclude_unset=True)
        
    # Build the new version by carrying over all old attributes
    new_version_data = {
        c.name: getattr(db_mandate, c.name) 
        for c in db_mandate.__table__.columns 
        if c.name not in ["pk_id", "created_at", "updated_at", "version", "previous_version_pk_id", "created_by_id"]
    }
    
    # Apply updates from the request
    for key, value in update_data.items():
        new_version_data[key] = value

    new_mandate = domain.Mandate(
        **new_version_data,
        version=db_mandate.version + 1,
        previous_version_pk_id=db_mandate.pk_id,
        created_by_id=current_user.id
    )
    
    # Deactivate the old version
    db_mandate.is_active = False
    db.add(new_mandate)
    db.add(db_mandate)
    db.flush() # Flush to populate new_mandate.pk_id
    
    # Auto-migrate all portfolios that were assigned to the old version
    db.query(domain.Portfolio).filter(domain.Portfolio.mandate_pk_id == db_mandate.pk_id).update(
        {"mandate_pk_id": new_mandate.pk_id}
    )
    
    create_audit_log(
        db,
        action_type="MANDATE_UPDATE",
        description=f"User '{current_user.email}' created v{new_mandate.version} of mandate '{db_mandate.id}'.",
        metadata_json={"old_pk_id": db_mandate.pk_id, "new_pk_id": new_mandate.pk_id, "user_id": current_user.id, "changes": update_data}
    )
    db.commit()
    db.refresh(new_mandate)
    return new_mandate

@router.post("/{pk_id}/activate", response_model=MandateResponse, dependencies=[Depends(require_role(["admin", "risk_manager"]))])
def activate_mandate(pk_id: int, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    db_mandate = db.query(domain.Mandate).filter(domain.Mandate.pk_id == pk_id).first()
    if not db_mandate: raise HTTPException(status_code=404, detail="Mandate not found")
    
    db_mandate.is_active = True
    create_audit_log(db, action_type="MANDATE_ACTIVATED", description=f"Activated mandate {db_mandate.id} v{db_mandate.version}", metadata_json={"pk_id": pk_id, "user_id": current_user.id})
    db.commit()
    db.refresh(db_mandate)
    return db_mandate

@router.post("/{pk_id}/deactivate", response_model=MandateResponse, dependencies=[Depends(require_role(["admin", "risk_manager"]))])
def deactivate_mandate(pk_id: int, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    db_mandate = db.query(domain.Mandate).filter(domain.Mandate.pk_id == pk_id).first()
    if not db_mandate: raise HTTPException(status_code=404, detail="Mandate not found")
    
    db_mandate.is_active = False
    create_audit_log(db, action_type="MANDATE_DEACTIVATED", description=f"Deactivated mandate {db_mandate.id} v{db_mandate.version}", metadata_json={"pk_id": pk_id, "user_id": current_user.id})
    db.commit()
    db.refresh(db_mandate)
    return db_mandate