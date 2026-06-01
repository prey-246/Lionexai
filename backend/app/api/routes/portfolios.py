from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user

router = APIRouter()

@router.get("", response_model=List[schemas.Portfolio])
def list_portfolios(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """List all portfolios for the current user."""
    return db.query(domain.Portfolio).filter(domain.Portfolio.user_id == current_user.id).all()

@router.get("/summary", response_model=schemas.PortfolioSummary)
def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Get an aggregate summary of all user portfolios."""
    portfolios = db.query(domain.Portfolio).filter(domain.Portfolio.user_id == current_user.id).all()

    if not portfolios:
        return schemas.PortfolioSummary(
            portfolio_count=0,
            total_equity=0,
            total_pnl=0,
            overall_win_rate_pct=0,
            best_performing_portfolio=None,
            worst_performing_portfolio=None
        )

    portfolio_ids = [p.id for p in portfolios]
    total_equity = sum(p.total_equity for p in portfolios)

    trades = db.query(domain.Trade).filter(
        domain.Trade.portfolio_id.in_(portfolio_ids),
        domain.Trade.status == "CLOSED"
    ).all()

    total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.pnl is not None and t.pnl > 0])
    
    overall_win_rate_pct = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

    pnl_by_portfolio = {p_id: sum(t.pnl for t in trades if t.pnl is not None and t.portfolio_id == p_id) for p_id in portfolio_ids}

    best_performing_portfolio = max(pnl_by_portfolio, key=pnl_by_portfolio.get) if pnl_by_portfolio and any(pnl_by_portfolio.values()) else None
    worst_performing_portfolio = min(pnl_by_portfolio, key=pnl_by_portfolio.get) if pnl_by_portfolio and any(pnl_by_portfolio.values()) else None

    return schemas.PortfolioSummary(
        portfolio_count=len(portfolios),
        total_equity=round(total_equity, 2),
        total_pnl=round(total_pnl, 2),
        overall_win_rate_pct=round(overall_win_rate_pct, 2),
        best_performing_portfolio=best_performing_portfolio,
        worst_performing_portfolio=worst_performing_portfolio,
    )

@router.post("", response_model=schemas.Portfolio, status_code=201)
def create_portfolio(
    portfolio_in: schemas.PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Create a new portfolio."""
    existing_portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_in.id).first()
    if existing_portfolio:
        raise HTTPException(status_code=400, detail=f"Portfolio ID '{portfolio_in.id}' already exists.")

    new_portfolio = domain.Portfolio(
        **portfolio_in.dict(),
        user_id=current_user.id,
        available_margin=portfolio_in.total_equity # Initially, all equity is available
    )
    db.add(new_portfolio)
    db.commit()
    db.refresh(new_portfolio)
    return new_portfolio

@router.get("/{portfolio_id}", response_model=schemas.Portfolio)
def get_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Get details for a specific portfolio."""
    portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id, domain.Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.delete("/{portfolio_id}", status_code=204)
def delete_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Delete a portfolio."""
    portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id, domain.Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    db.delete(portfolio)
    db.commit()
    return

@router.get("/{portfolio_id}/trades", response_model=List[schemas.Trade])
def get_trades_for_portfolio(
    portfolio_id: str,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Get trades for a specific portfolio, with optional status filter."""
    # First, verify the user has access to this portfolio
    portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id, domain.Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    query = db.query(domain.Trade).filter(domain.Trade.portfolio_id == portfolio_id)
    
    if status:
        query = query.filter(domain.Trade.status == status)
        
    return query.order_by(domain.Trade.created_at.desc()).all()

@router.get("/{portfolio_id}/stats", response_model=schemas.PortfolioStats)
def get_portfolio_stats(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Calculate and return performance statistics for a portfolio."""
    trades = db.query(domain.Trade).filter(
        domain.Trade.portfolio_id == portfolio_id,
        domain.Trade.status == "CLOSED"
    ).all()

    if not trades:
        return schemas.PortfolioStats(total_trades=0, winning_trades=0, losing_trades=0, win_rate_pct=0, total_pnl=0, avg_pnl_per_trade=0, best_trade_pnl=0, worst_trade_pnl=0)

    total_trades = len(trades)
    pnls = [t.pnl for t in trades if t.pnl is not None]
    winning_trades = len([pnl for pnl in pnls if pnl > 0])
    losing_trades = len([pnl for pnl in pnls if pnl < 0])
    total_pnl = sum(pnls)
    win_rate_pct = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0
    best_trade_pnl = max(pnls) if pnls else 0
    worst_trade_pnl = min(pnls) if pnls else 0

    return schemas.PortfolioStats(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate_pct=round(win_rate_pct, 2),
        total_pnl=round(total_pnl, 2),
        avg_pnl_per_trade=round(avg_pnl_per_trade, 2),
        best_trade_pnl=round(best_trade_pnl, 2),
        worst_trade_pnl=round(worst_trade_pnl, 2),
    )

@router.get("/{portfolio_id}/equity-curve", response_model=List[schemas.EquityDataPoint])
def get_equity_curve(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Generate the equity curve for a portfolio."""
    portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id, domain.Portfolio.user_id == current_user.id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    trades = db.query(domain.Trade).filter(
        domain.Trade.portfolio_id == portfolio_id,
        domain.Trade.status == "CLOSED"
    ).order_by(domain.Trade.closed_at.asc()).all()

    if not trades:
        # No closed trades, so no historical equity curve to show.
        return []

    equity_curve = []
    initial_equity = portfolio.total_equity - sum(t.pnl for t in trades if t.pnl)
    
    # Use the timestamp of the first closed trade as a reference point for the start of the curve.
    # We place the "initial equity" point 1 second before the first trade closes to ensure a correct timeline.
    start_time = int(trades[0].closed_at.timestamp()) - 1 if trades[0].closed_at else int(datetime.utcnow().timestamp())

    # Start with the initial equity at portfolio creation time
    equity_curve.append(schemas.EquityDataPoint(
        time=start_time,
        value=initial_equity
    ))

    current_equity = initial_equity
    for trade in trades:
        if trade.pnl is not None and trade.closed_at is not None:
            current_equity += trade.pnl
            equity_curve.append(schemas.EquityDataPoint(
                time=int(trade.closed_at.timestamp()),
                value=round(current_equity, 2)
            ))

    return equity_curve