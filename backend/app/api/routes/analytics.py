from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.database import get_db
from app.models import domain
from app.services.analytics_service import (
    compare_portfolios,
    compare_strategies,
    get_strategy_analytics,
    search_trades,
)

router = APIRouter()


class StrategyAnalyticsItem(BaseModel):
    strategy_name: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl: float
    avg_pnl: float


class PortfolioCompareItem(BaseModel):
    portfolio_id: str
    total_equity: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_pnl: float
    current_drawdown_pct: float
    equity_curve: list[dict]


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


@router.get("/strategies", response_model=list[StrategyAnalyticsItem])
def list_strategy_analytics(
    trade_source: str | None = Query(None, description="AUTONOMOUS, MANUAL, SEED, or omit for all"),
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    return get_strategy_analytics(db, trade_source=trade_source.upper() if trade_source else None)


@router.get("/portfolios/compare", response_model=list[PortfolioCompareItem])
def portfolio_comparison(
    ids: str = Query(..., description="Comma-separated portfolio IDs"),
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user),
):
    portfolio_ids = [p.strip() for p in ids.split(",") if p.strip()]
    if len(portfolio_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two portfolio IDs to compare.")
    if len(portfolio_ids) > 6:
        raise HTTPException(status_code=400, detail="Maximum 6 portfolios per comparison.")

    if not _is_privileged(current_user):
        owned = {
            p.id
            for p in db.query(domain.Portfolio.id)
            .filter(domain.Portfolio.user_id == current_user.id)
            .all()
        }
        if not all(pid in owned for pid in portfolio_ids):
            raise HTTPException(status_code=403, detail="Cannot compare portfolios you do not own.")

    return compare_portfolios(db, portfolio_ids)


@router.get("/strategies/compare", response_model=list[StrategyAnalyticsItem])
def strategy_comparison(
    names: str = Query(..., description="Comma-separated strategy names"),
    trade_source: str | None = Query("AUTONOMOUS"),
    db: Session = Depends(get_db),
    _: domain.User = Depends(require_role(["admin", "operator", "risk_manager"])),
):
    strategy_names = [n.strip() for n in names.split(",") if n.strip()]
    if len(strategy_names) < 2:
        raise HTTPException(status_code=400, detail="Provide at least two strategy names to compare.")
    source = trade_source.upper() if trade_source else None
    return compare_strategies(db, strategy_names, trade_source=source)
