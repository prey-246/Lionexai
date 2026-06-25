from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user, require_role
from app.services.audit_service import create_audit_log

router = APIRouter()


@router.get("/", response_model=List[schemas.Asset])
def list_assets(
    asset_class: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    q = db.query(domain.Asset)
    if active_only:
        q = q.filter(domain.Asset.is_active == True)
    if asset_class:
        q = q.filter(domain.Asset.asset_class == asset_class.upper())
    return q.order_by(domain.Asset.asset_class, domain.Asset.symbol).all()


@router.post("/", response_model=schemas.Asset, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_in: schemas.AssetCreate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(require_role(["admin", "operator"])),
):
    if db.query(domain.Asset).filter(domain.Asset.symbol == asset_in.symbol).first():
        raise HTTPException(status_code=400, detail="Asset with this symbol already exists.")
    asset = domain.Asset(**asset_in.model_dump())
    db.add(asset)
    create_audit_log(
        db, action_type="ASSET_CREATE",
        description=f"Asset {asset.symbol} created by {current_user.email}.",
        metadata_json={"symbol": asset.symbol, "asset_class": asset.asset_class},
    )
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/{symbol}", response_model=schemas.Asset)
def update_asset(
    symbol: str,
    asset_in: schemas.AssetUpdate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(require_role(["admin", "operator"])),
):
    asset = db.query(domain.Asset).filter(domain.Asset.symbol == symbol).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")
    for field, value in asset_in.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    create_audit_log(
        db, action_type="ASSET_UPDATE",
        description=f"Asset {symbol} updated by {current_user.email}.",
        metadata_json={"symbol": symbol},
    )
    db.commit()
    db.refresh(asset)
    return asset
