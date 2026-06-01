from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.domain import Portfolio, EquityCurve, Trade, RiskEvent
from datetime import datetime
from typing import List, Optional

router = APIRouter()

class PortfolioUpdateRequest(BaseModel):
    mandate_id: Optional[str] = None
    total_equity: Optional[float] = None

class PortfolioResponse(BaseModel):
    id: str
    user_id: str
    mandate_id: str
    total_equity: float
    available_margin: float
    current_drawdown_pct: float

    class Config:
        from_attributes = True

@router.get("/", summary="List all portfolios")
def list_portfolios(db: Session = Depends(get_db)):
    portfolios = db.query(Portfolio).all()
    return portfolios

@router.get("/{portfolio_id}", summary="Get portfolio details")
def get_portfolio(portfolio_id: str, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio

@router.get("/{portfolio_id}/equity-curve", summary="Get equity curve history")
def get_equity_curve(portfolio_id: str, limit: int = 100, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    curves = db.query(EquityCurve).filter(
        EquityCurve.portfolio_id == portfolio_id
    ).order_by(desc(EquityCurve.timestamp)).limit(limit).all()

    return [{"timestamp": c.timestamp, "equity": c.equity, "drawdown_pct": c.drawdown_pct} for c in curves]

@router.get("/{portfolio_id}/trades", summary="Get portfolio trades")
def get_portfolio_trades(portfolio_id: str, status: Optional[str] = None, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    query = db.query(Trade).filter(Trade.portfolio_id == portfolio_id)
    if status:
        query = query.filter(Trade.status == status)

    trades = query.order_by(desc(Trade.created_at)).all()
    return trades

@router.get("/{portfolio_id}/risk-events", summary="Get risk events for portfolio")
def get_risk_events(portfolio_id: str, limit: int = 50, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    events = db.query(RiskEvent).filter(
        RiskEvent.portfolio_id == portfolio_id
    ).order_by(desc(RiskEvent.triggered_at)).limit(limit).all()

    return events

@router.get("/{portfolio_id}/stats", summary="Get portfolio performance statistics")
def get_portfolio_stats(portfolio_id: str, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    total_trades = db.query(Trade).filter(
        Trade.portfolio_id == portfolio_id,
        Trade.status == "CLOSED"
    ).count()

    winning_trades = db.query(Trade).filter(
        Trade.portfolio_id == portfolio_id,
        Trade.status == "CLOSED",
        Trade.pnl > 0
    ).count()

    total_pnl = db.query(Trade).filter(
        Trade.portfolio_id == portfolio_id,
        Trade.status == "CLOSED"
    ).with_entities(
        db.func.sum(Trade.pnl).label("total")
    ).first()[0] or 0.0

    return {
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0,
        "total_pnl": total_pnl,
        "current_equity": portfolio.total_equity,
        "available_margin": portfolio.available_margin,
        "current_drawdown_pct": portfolio.current_drawdown_pct
    }

@router.put("/{portfolio_id}", summary="Update portfolio settings")
def update_portfolio(portfolio_id: str, request: PortfolioUpdateRequest, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if request.mandate_id:
        portfolio.mandate_id = request.mandate_id
    if request.total_equity is not None:
        portfolio.total_equity = request.total_equity
        portfolio.available_margin = request.total_equity

    db.commit()
    return portfolio
