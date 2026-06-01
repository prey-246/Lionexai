from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.domain import Portfolio, AuditLog, Trade
from app.engines.risk_engine import RiskEngine, RiskRejectionError
from app.services.market_data import MarketDataService
import uuid

router = APIRouter()
market = MarketDataService()

class TradeRequest(BaseModel):
    symbol: str
    side: str
    size: float

@router.get("/portfolio", summary="Get active simulator portfolio")
def get_active_portfolio(db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="System initialization pending")
    return portfolio

@router.post("/execute", summary="Process simulated order via Risk Engine")
def execute_trade(req: TradeRequest, db: Session = Depends(get_db)):
    portfolio = db.query(Portfolio).first()
    mandate = portfolio.mandate
    risk = RiskEngine(db)

    # 1. Fetch live execution price
    try:
        ticker = market.exchange.fetch_ticker(req.symbol)
        current_price = float(ticker['last'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market feed offline: {str(e)}")

    order_context = {
        "symbol": req.symbol,
        "side": req.side,
        "size": req.size,
        "current_price": current_price
    }

    # 2. Institutional Risk Gatekeeper
    try:
        risk.evaluate_pre_trade(portfolio, mandate, order_context)
    except RiskRejectionError as e:
        # Create immutable audit log of rejection
        log = AuditLog(id=str(uuid.uuid4()), action_type="RISK_REJECTION", description=str(e), metadata_json=order_context)
        db.add(log)
        db.commit()
        raise HTTPException(status_code=403, detail=str(e))

    # 3. Simulate Fill & Portfolio Update
    trade_id = str(uuid.uuid4())
    notional_value = req.size * current_price

    if req.side == "BUY":
        portfolio.available_margin -= notional_value
    else:
        portfolio.available_margin += notional_value

    trade = Trade(
        id=trade_id,
        portfolio_id=portfolio.id,
        symbol=req.symbol,
        side=req.side,
        size=req.size,
        entry_price=current_price,
        status="OPEN"
    )

    db.add(trade)
    db.commit()

    return {
        "status": "FILLED",
        "trade_id": trade_id,
        "fill_price": current_price,
        "margin_impact": notional_value
    }