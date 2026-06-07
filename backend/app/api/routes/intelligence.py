from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/news", response_model=List[schemas.MarketNewsArticle])
def get_market_news(
    limit: int = 20, 
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Fetch the latest market news headlines and articles."""
    return db.query(domain.MarketNewsArticle).order_by(domain.MarketNewsArticle.published_at.desc()).limit(limit).all()

@router.get("/events", response_model=List[schemas.EconomicEvent])
def get_economic_events(
    limit: int = 20, 
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Fetch upcoming and past macro-economic events."""
    return db.query(domain.EconomicEvent).order_by(domain.EconomicEvent.timestamp.desc()).limit(limit).all()

@router.get("/sentiment/{symbol:path}", response_model=schemas.MarketSensitivityScore)
def get_market_sentiment(
    symbol: str, 
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Fetch the aggregated AI sentiment score for a specific asset."""
    score = db.query(domain.MarketSensitivityScore).filter(domain.MarketSensitivityScore.symbol == symbol).order_by(domain.MarketSensitivityScore.timestamp.desc()).first()
    if not score:
        raise HTTPException(status_code=404, detail="No sentiment data available for this asset yet.")
    return score