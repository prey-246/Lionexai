from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import random
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models import schemas, domain
from app.api.deps import get_current_user
from app.engines.risk_engine import RiskEngine, RiskRejectionError
from app.services import audit_service
from app.core.sockets import manager

router = APIRouter()

@router.post("/{portfolio_id}/execute", response_model=schemas.TradeResponse)
def execute_trade(
    portfolio_id: str,
    trade_in: schemas.TradeExecute,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """
    Execute a simulated trade after passing through a simplified risk check.
    """
    # 1. Find the portfolio and verify ownership
    query = db.query(domain.Portfolio).filter(domain.Portfolio.id == portfolio_id)
    if current_user.role_tier == "client":
        query = query.filter(domain.Portfolio.user_id == current_user.id)
        
    portfolio = query.first()

    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # --- Use the dedicated Risk Engine ---
    risk_engine = RiskEngine(db, background_tasks)
    mandate = db.query(domain.Mandate).filter(domain.Mandate.pk_id == portfolio.mandate_pk_id).first()
    
    # Fetch the latest realistic price from the historical database instead of hardcoding
    latest_market_data = db.query(domain.MarketDataOHLCV).filter(
        domain.MarketDataOHLCV.symbol == trade_in.symbol
    ).order_by(domain.MarketDataOHLCV.timestamp.desc()).first()
    
    current_price = latest_market_data.close if latest_market_data else (65000.0 if trade_in.symbol == "BTC/USDT" else 3500.0)

    order_details = {
        "symbol": trade_in.symbol,
        "size": trade_in.size,
        "current_price": current_price,
        "stop_loss": trade_in.stop_loss,
    }

    try:
        risk_engine.evaluate_pre_trade(portfolio, mandate, order_details)
    except RiskRejectionError as e:
        # Save the rejected trade so it appears in the UI
        rejected_trade = domain.Trade(
            id=f"trade_{uuid.uuid4().hex[:12]}",
            portfolio_id=portfolio.pk_id,
            symbol=trade_in.symbol,
            side=trade_in.side,
            quantity=trade_in.size,
            entry_price=current_price,
            status="REJECTED",
            created_at=datetime.utcnow(),
            closed_at=datetime.utcnow(),
            pnl=0.0
        )
        db.add(rejected_trade)
        audit_service.create_audit_log(
            db,
            action_type="RISK_REJECTION",
            description=str(e),
            metadata_json={"portfolio_id": portfolio_id, "user_id": current_user.id, "user_email": current_user.email, "order": order_details, "trade_id": rejected_trade.id}
        )
        db.commit() # Ensure both the trade and log are saved!
        background_tasks.add_task(
            manager.broadcast,
            {
                "type": "RISK_ALERT",
                "data": {"severity": "CRITICAL", "event_type": "RISK_REJECTION", "description": str(e), "triggered_at": datetime.utcnow().isoformat()}
            },
            "alerts"
        )
        return JSONResponse(
            status_code=403,
            content={"detail": str(e)},
            background=background_tasks
        )

    # --- Trade Execution Simulation ---
    # Create a new trade record
    new_trade = domain.Trade(
        id=f"trade_{uuid.uuid4().hex[:12]}",
        portfolio_id=portfolio.pk_id,
        symbol=trade_in.symbol,
        side=trade_in.side,
        quantity=trade_in.size,
        entry_price=current_price,
        status="OPEN",
        created_at=datetime.utcnow()
    )
    
    required_margin = (trade_in.size * current_price) / mandate.max_leverage
    portfolio.available_margin -= required_margin
    db.add(new_trade)
    db.commit()

    # For the MVP, immediately close the trade with a random outcome
    if trade_in.symbol == "ETH/USDT":
        # Force a guaranteed massive loss to test the Kill Switch
        exit_price_delta = -5000.0 if trade_in.side == "BUY" else 5000.0
    else:
        exit_price_delta = (random.random() - 0.45) * (current_price * 0.02) # 2% realistic simulated volatility
    exit_price = current_price + exit_price_delta
    pnl = (exit_price - current_price) * trade_in.size if trade_in.side == "BUY" else (current_price - exit_price) * trade_in.size

    new_trade.exit_price = exit_price
    new_trade.status = "CLOSED"
    new_trade.pnl = pnl
    new_trade.closed_at = datetime.utcnow()

    portfolio.available_margin += required_margin
    portfolio.total_equity += pnl
    
    equity_point = domain.EquityCurve(
        portfolio_id=portfolio.pk_id,
        equity=portfolio.total_equity
    )
    db.add(equity_point)
    db.flush()

    # Calculate Portfolio High-Water Mark and Current Drawdown
    max_eq = db.query(func.max(domain.EquityCurve.equity)).filter(domain.EquityCurve.portfolio_id == portfolio.pk_id).scalar()
    if max_eq and portfolio.total_equity < max_eq:
        portfolio.current_drawdown_pct = ((max_eq - portfolio.total_equity) / max_eq) * 100
    else:
        portfolio.current_drawdown_pct = 0.0
        
    db.commit()

    audit_service.create_audit_log(
        db,
        action_type="TRADE_EXECUTED",
        description=f"Trade {new_trade.id} ({trade_in.side} {trade_in.size} {trade_in.symbol}) executed and closed with P&L: ${pnl:,.2f}.",
        metadata_json={
            "trade_id": new_trade.id,
            "portfolio_id": portfolio.id,
            "user_id": current_user.id,
            "user_email": current_user.email,
            "pnl": pnl
        }
    )
    
    # Broadcast portfolio updates
    background_tasks.add_task(
        manager.broadcast,
        {
            "type": "PORTFOLIO_UPDATE",
            "data": {
                "portfolio_id": portfolio.id,
                "total_equity": portfolio.total_equity,
                "available_margin": portfolio.available_margin,
            }
        },
        "portfolio"
    )

    return schemas.TradeResponse(
        status="FILLED",
        trade_id=new_trade.id,
        fill_price=current_price
    )

@router.post("/mandates/{mandate_id}/reset")
def reset_kill_switch(
    mandate_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Admin endpoint to reset a triggered kill switch."""
    mandate = db.query(domain.Mandate).filter(domain.Mandate.id == mandate_id).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="Mandate not found")
    
    mandate.kill_switch_active = False
    
    audit_service.create_audit_log(
        db,
        action_type="KILL_SWITCH_RESET",
        description=f"Kill switch manually reset for mandate {mandate_id} by {current_user.email}",
        metadata_json={"mandate_id": mandate_id, "user_id": current_user.id}
    )
    db.commit()

    background_tasks.add_task(
        manager.broadcast,
        {
            "type": "RISK_ALERT",
            "data": {"severity": "INFO", "event_type": "KILL_SWITCH_RESET", "description": f"Mandate {mandate_id} unlocked.", "triggered_at": datetime.utcnow().isoformat()}
        },
        "alerts"
    )
    
    return {"status": "success", "message": f"Kill switch reset for {mandate_id}"}