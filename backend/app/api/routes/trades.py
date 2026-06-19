from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import domain
from app.services.analytics_service import search_trades

router = APIRouter()


class TradeExplorerItem(BaseModel):
    id: str
    portfolio_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float | None
    status: str
    pnl: float | None
    exchange: str | None
    execution_latency_ms: float | None
    strategy_name: str | None
    rejection_reason: str | None
    trade_source: str
    created_at: datetime
    closed_at: datetime | None


class PaginatedTrades(BaseModel):
    trades: list[TradeExplorerItem]
    total: int
    limit: int
    offset: int


def _is_privileged(user: domain.User) -> bool:
    return user.role_tier in ("admin", "operator", "risk_manager")


@router.get("/", response_model=PaginatedTrades)
def explore_trades(
    portfolio_id: str | None = None,
    symbol: str | None = None,
    strategy_name: str | None = None,
    exchange: str | None = None,
    trade_source: str | None = None,
    status: str | None = None,
    side: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    """Historical trade explorer with advanced filtering and pagination."""
    privileged = _is_privileged(current_user)
    trades, total = search_trades(
        db,
        portfolio_id=portfolio_id,
        symbol=symbol,
        strategy_name=strategy_name,
        exchange=exchange,
        trade_source=trade_source,
        status=status,
        side=side,
        start_date=start_date,
        end_date=end_date,
        search=search,
        skip=skip,
        limit=limit,
        user_id=current_user.id if not privileged else None,
        is_privileged=privileged,
    )
    return PaginatedTrades(trades=trades, total=total, limit=limit, offset=skip)
