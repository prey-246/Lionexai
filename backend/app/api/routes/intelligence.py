from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user
from app.services.sentiment_service import resolve_sentiment, list_pulse_scores

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

@router.get("/sentiment", response_model=List[schemas.MarketSensitivityScore])
def list_market_sentiment(
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    """Batch sentiment for Intelligence Hub — avoids N+1 per-asset 404s."""
    return list_pulse_scores(db, limit=limit)


@router.get("/sentiment/{symbol:path}", response_model=schemas.MarketSensitivityScore)
def get_market_sentiment(
    symbol: str, 
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Fetch AI sentiment — returns neutral with coverage metadata when no direct data."""
    return resolve_sentiment(db, symbol)