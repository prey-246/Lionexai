from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import domain
from app.api.deps import get_current_user
from app.services.market_intelligence_service import MarketIntelligenceService

router = APIRouter()


@router.get("/dashboard")
def get_market_intelligence_dashboard(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    """Unified global market intelligence dashboard payload."""
    return MarketIntelligenceService(db).dashboard()
