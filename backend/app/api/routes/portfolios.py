from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user, require_role
from app.services.audit_service import create_audit_log

router = APIRouter()

@router.post("/", response_model=schemas.PortfolioResponse, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    portfolio_in: schemas.PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Create a new portfolio for the current user.
    """
    db_portfolio = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_in.id).first()
    if db_portfolio:
        raise HTTPException(status_code=400, detail="Portfolio with this ID already exists")

    mandate = db.query(domain.Mandate).filter(domain.Mandate.pk_id == portfolio_in.mandate_pk_id).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")

    new_portfolio = domain.Portfolio(
        id=portfolio_in.id,
        user_id=current_user.id,
        mandate_pk_id=portfolio_in.mandate_pk_id,
        total_equity=portfolio_in.total_equity,
        available_margin=portfolio_in.total_equity,
    )
    db.add(new_portfolio)
    db.flush() # Ensure the new_portfolio.pk_id is generated
    
    # Save the initial equity curve point
    initial_curve = domain.EquityCurve(
        portfolio_id=new_portfolio.pk_id,
        equity=new_portfolio.total_equity
    )
    db.add(initial_curve)
    
    create_audit_log(
        db,
        action_type="PORTFOLIO_CREATE",
        description=f"User '{current_user.email}' created portfolio '{new_portfolio.id}'.",
        metadata_json={"portfolio_id": new_portfolio.id, "user_id": current_user.id}
    )
    
    db.commit()
    # Eagerly load relationships for the response
    db.refresh(new_portfolio)
    return new_portfolio

@router.get("/", response_model=List[schemas.PortfolioResponse])
def list_portfolios(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    List all portfolios for the current user, including their full risk context.
    """
    query = db.query(domain.Portfolio)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolios = query.options(
        # Eager load relationships to prevent N+1 query problem
        joinedload(domain.Portfolio.mandate),
        joinedload(domain.Portfolio.trades)
    ).order_by(domain.Portfolio.id).all()
    return portfolios

@router.get("/summary", response_model=schemas.PortfolioSummary)
def get_portfolio_summary(
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Get a summary of all portfolios for the current user.
    """
    query = db.query(domain.Portfolio)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolios = query.all()
    
    if not portfolios:
        return schemas.PortfolioSummary(
            portfolio_count=0, total_equity=0, total_pnl=0, overall_win_rate_pct=0
        )

    total_equity = sum(p.total_equity for p in portfolios)
    
    portfolio_pk_ids = [p.pk_id for p in portfolios]
    total_pnl = db.query(func.sum(domain.Trade.pnl)).filter(
        domain.Trade.portfolio_id.in_(portfolio_pk_ids), domain.Trade.status == 'CLOSED'
    ).scalar() or 0

    total_trades = db.query(func.count(domain.Trade.id)).filter(
        domain.Trade.portfolio_id.in_(portfolio_pk_ids), domain.Trade.status == 'CLOSED'
    ).scalar() or 0

    winning_trades = db.query(func.count(domain.Trade.id)).filter(
        domain.Trade.portfolio_id.in_(portfolio_pk_ids), domain.Trade.status == 'CLOSED', domain.Trade.pnl > 0
    ).scalar() or 0

    win_rate = round((winning_trades / total_trades * 100), 2) if total_trades > 0 else 0.0
    
    # Calculate Best and Worst Portfolios by PNL
    portfolio_pnls = {p.pk_id: 0.0 for p in portfolios}
    pnl_by_portfolio = db.query(
        domain.Trade.portfolio_id, func.sum(domain.Trade.pnl)
    ).filter(
        domain.Trade.portfolio_id.in_(portfolio_pk_ids), 
        domain.Trade.status == 'CLOSED'
    ).group_by(domain.Trade.portfolio_id).all()

    for pk_id, pnl in pnl_by_portfolio:
        if pnl is not None:
            portfolio_pnls[pk_id] = pnl

    best_pk = max(portfolio_pnls, key=portfolio_pnls.get) if portfolio_pnls else None
    worst_pk = min(portfolio_pnls, key=portfolio_pnls.get) if portfolio_pnls else None
    pk_to_id = {p.pk_id: p.id for p in portfolios}

    return schemas.PortfolioSummary(
        portfolio_count=len(portfolios),
        total_equity=total_equity,
        total_pnl=total_pnl,
        overall_win_rate_pct=win_rate,
        best_performing_id=pk_to_id.get(best_pk) if best_pk else None,
        worst_performing_id=pk_to_id.get(worst_pk) if worst_pk else None
    )

@router.get("/{portfolio_id}", response_model=schemas.PortfolioResponse)
def get_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Get a single portfolio by ID, including its full risk context.
    """
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolio = query.options(
        # Eager load relationships to prevent N+1 query problem
        joinedload(domain.Portfolio.mandate),
        joinedload(domain.Portfolio.trades)
    ).first()

    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
    
    return portfolio

@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Delete a portfolio.
    """
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolio = query.first()

    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    create_audit_log(
        db,
        action_type="PORTFOLIO_DELETE",
        description=f"User '{current_user.email}' deleted portfolio '{portfolio.id}'.",
        metadata_json={"portfolio_id": portfolio.id, "user_id": current_user.id}
    )

    db.delete(portfolio)
    db.commit()
    return

@router.get("/{portfolio_id}/stats", response_model=schemas.PortfolioStats)
def get_portfolio_stats(portfolio_id: str, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio: raise HTTPException(status_code=404, detail="Portfolio not found")

    trades = db.query(domain.Trade).filter(domain.Trade.portfolio_id == portfolio.pk_id, domain.Trade.status == 'CLOSED').all()
    
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
    losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
    total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
    
    win_rate = round((winning_trades / total_trades * 100), 2) if total_trades > 0 else 0.0
    avg_pnl = round((total_pnl / total_trades), 2) if total_trades > 0 else 0.0
    pnl_values = [t.pnl for t in trades if t.pnl is not None]
    best_trade = max(pnl_values, default=0.0)
    worst_trade = min(pnl_values, default=0.0)

    return schemas.PortfolioStats(
        total_trades=total_trades, winning_trades=winning_trades, losing_trades=losing_trades,
        win_rate_pct=win_rate, total_pnl=total_pnl, avg_pnl_per_trade=avg_pnl,
        best_trade_pnl=best_trade, worst_trade_pnl=worst_trade
    )

@router.get("/{portfolio_id}/trades", response_model=List[schemas.Trade])
def get_portfolio_trades(portfolio_id: str, status: str = None, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio: raise HTTPException(status_code=404, detail="Portfolio not found")

    query = db.query(domain.Trade).filter(domain.Trade.portfolio_id == portfolio.pk_id)
    if status: query = query.filter(domain.Trade.status == status)
    return query.order_by(domain.Trade.created_at.desc()).all()

@router.get("/{portfolio_id}/risk-events", response_model=List[schemas.RiskEvent])
def get_portfolio_risk_events(portfolio_id: str, limit: int = 50, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio: raise HTTPException(status_code=404, detail="Portfolio not found")
    
    return db.query(domain.RiskEvent).filter(domain.RiskEvent.portfolio_id == portfolio.pk_id).order_by(domain.RiskEvent.triggered_at.desc()).limit(limit).all()

@router.get("/{portfolio_id}/equity-curve")
def get_portfolio_equity_curve(portfolio_id: str, limit: int = 100, db: Session = Depends(get_db), current_user: domain.User = Depends(get_current_user)):
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
    portfolio = query.first()
    if not portfolio: raise HTTPException(status_code=404, detail="Portfolio not found")

    curves = db.query(domain.EquityCurve).filter(domain.EquityCurve.portfolio_id == portfolio.pk_id).order_by(domain.EquityCurve.timestamp.asc()).limit(limit).all()
    
    # AUTO-HEAL: If the portfolio is missing historical curve data, automatically generate a baseline
    if not curves:
        baseline = domain.EquityCurve(portfolio_id=portfolio.pk_id, equity=portfolio.total_equity)
        db.add(baseline)
        db.commit()
        db.refresh(baseline)
        curves = [baseline]
        
    return [{"timestamp": c.timestamp, "equity": float(c.equity or 0.0), "drawdown_pct": 0.0} for c in curves]