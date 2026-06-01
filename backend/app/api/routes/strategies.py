from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.domain import Strategy, BacktestResult
from typing import Optional, Dict, Any
import json

router = APIRouter()

class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: str  # moving_average, rsi, atr, custom
    parameters: Dict[str, Any]

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

@router.post("/", summary="Create a new strategy")
def create_strategy(request: StrategyCreate, db: Session = Depends(get_db)):
    strategy = Strategy(
        name=request.name,
        description=request.description,
        strategy_type=request.strategy_type,
        parameters=request.parameters,
        is_active=False
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy

@router.get("/", summary="List all strategies")
def list_strategies(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Strategy)
    if active_only:
        query = query.filter(Strategy.is_active == True)
    return query.all()

@router.get("/{strategy_id}", summary="Get strategy details")
def get_strategy(strategy_id: str, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

@router.put("/{strategy_id}", summary="Update strategy")
def update_strategy(strategy_id: str, request: StrategyUpdate, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if request.name:
        strategy.name = request.name
    if request.description:
        strategy.description = request.description
    if request.parameters:
        strategy.parameters = request.parameters
    if request.is_active is not None:
        strategy.is_active = request.is_active

    db.commit()
    db.refresh(strategy)
    return strategy

@router.delete("/{strategy_id}", summary="Delete strategy")
def delete_strategy(strategy_id: str, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    db.delete(strategy)
    db.commit()
    return {"status": "deleted"}

@router.get("/{strategy_id}/backtest-results", summary="Get backtest results for strategy")
def get_strategy_backtest_results(strategy_id: str, limit: int = 10, db: Session = Depends(get_db)):
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    results = db.query(BacktestResult).filter(
        BacktestResult.strategy_id == strategy_id
    ).order_by(BacktestResult.created_at.desc()).limit(limit).all()

    return results
