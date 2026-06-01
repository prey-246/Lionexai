from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.market_data import MarketDataService
from app.engines.backtester import BacktestEngine

router = APIRouter()
market_service = MarketDataService()
engine = BacktestEngine()

class BacktestRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1d"
    strategy: str = "MA_CROSSOVER"

@router.post("/run", summary="Execute historical strategy simulation")
def run_backtest(request: BacktestRequest):
    try:
        # 1. Fetch Data
        df = market_service.fetch_historical_data(symbol=request.symbol, timeframe=request.timeframe, limit=500)
        
        # 2. Execute Strategy
        if request.strategy == "MA_CROSSOVER":
            results = engine.run_moving_average_crossover(df)
        else:
            raise HTTPException(status_code=400, detail="Strategy not implemented")
            
        return {
            "status": "success",
            "symbol": request.symbol,
            "metrics": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))