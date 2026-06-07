from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.domain import Strategy, BacktestResult, User
from app.api.deps import get_current_user, require_role
from app.services.audit_service import create_audit_log
from typing import Optional, Dict, Any
import json
import uuid

router = APIRouter()

# Pydantic Schemas for Strategy Management
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

@router.post("/", summary="Create a new strategy", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_role(["admin"]))])
def create_strategy(request: StrategyCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    strategy = Strategy(
        name=request.name,
        description=request.description,
        strategy_type=request.strategy_type,
        parameters=request.parameters,
        is_active=False # Strategies are inactive by default
    )
    db.add(strategy)
    db.flush() # Use flush to get the auto-generated ID before commit

    create_audit_log(
        db,
        action_type="STRATEGY_CREATE",
        description=f"User '{current_user.email}' created new strategy '{strategy.name}'.",
        metadata_json={"strategy_id": str(strategy.id), "user_id": current_user.id}
    )

    db.commit()
    db.refresh(strategy)
    return strategy

@router.get("/", summary="List all strategies")
def list_strategies(active_only: bool = False, db: Session = Depends(get_db)):
    """
    Lists all strategies. Can be filtered to show only active strategies.
    """
    query = db.query(Strategy)
    if active_only:
        query = query.filter(Strategy.is_active == True)
    return query.all()

@router.get("/{strategy_id}", summary="Get strategy details")
def get_strategy(strategy_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the details of a single strategy by its ID.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy

@router.put("/{strategy_id}", summary="Update strategy", dependencies=[Depends(require_role(["admin"]))])
def update_strategy(strategy_id: str, request: StrategyUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Updates an existing strategy. Only provided fields will be updated.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(strategy, key, value)

    create_audit_log(
        db,
        action_type="STRATEGY_UPDATE",
        description=f"User '{current_user.email}' updated strategy '{strategy.name}'.",
        metadata_json={
            "strategy_id": str(strategy.id),
            "user_id": current_user.id,
            "changes": update_data
        }
    )
    db.commit()
    db.refresh(strategy)
    return strategy

@router.delete("/{strategy_id}", summary="Delete strategy", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(["admin"]))])
def delete_strategy(strategy_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Deletes a strategy. This is a permanent action.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Capture details for audit log before deleting
    strategy_name = strategy.name
    strategy_id_str = str(strategy.id)

    db.delete(strategy)

    create_audit_log(
        db,
        action_type="STRATEGY_DELETE",
        description=f"User '{current_user.email}' deleted strategy '{strategy_name}'.",
        metadata_json={"strategy_id": strategy_id_str, "user_id": current_user.id}
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{strategy_id}/backtest-results", summary="Get backtest results for strategy")
def get_strategy_backtest_results(strategy_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    Retrieves a list of the most recent backtest results for a given strategy.
    """
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    results = db.query(BacktestResult).filter(
        BacktestResult.strategy_id == strategy.pk_id
    ).order_by(BacktestResult.created_at.desc()).limit(limit).all()

    return results
