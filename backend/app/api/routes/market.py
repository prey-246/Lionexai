from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/global-state", response_model=Optional[schemas.GlobalMarketStateResponse])
def get_global_state(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    """Latest Global Market Intelligence snapshot (risk score, regime, risk-on/off, ranking)."""
    state = (
        db.query(domain.GlobalMarketState)
        .order_by(domain.GlobalMarketState.computed_at.desc())
        .first()
    )
    return state


@router.get("/regime", response_model=List[schemas.MarketRegimeResponse])
def get_regimes(
    scope: str = "GLOBAL",
    history: int = 1,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    """Regime snapshots for a scope (GLOBAL or an asset symbol). `history` controls
    how many recent records to return (newest first)."""
    rows = (
        db.query(domain.MarketRegime)
        .filter(domain.MarketRegime.scope == scope)
        .order_by(domain.MarketRegime.detected_at.desc())
        .limit(max(1, min(history, 200)))
        .all()
    )
    return rows


@router.get("/regime/all", response_model=List[schemas.MarketRegimeResponse])
def get_latest_regime_per_asset(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    """The most-recent regime for every active asset (one row per scope)."""
    assets = db.query(domain.Asset).filter(domain.Asset.is_active == True).all()
    out = []
    for asset in assets:
        row = (
            db.query(domain.MarketRegime)
            .filter(domain.MarketRegime.scope == asset.symbol)
            .order_by(domain.MarketRegime.detected_at.desc())
            .first()
        )
        if row:
            out.append(row)
    return out
