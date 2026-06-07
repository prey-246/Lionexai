import os
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Literal, get_args
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import domain
from app.services.historical_data import HistoricalDataService
from app.core.database import SessionLocal
import logging
import ccxt as ccxt_sync

logger = logging.getLogger(__name__)

router = APIRouter()

Environment = Literal['PAPER', 'BACKTEST', 'DEMO', 'LIVE_DISABLED']

class EnvironmentState(BaseModel):
    environment: Environment = Field(..., description="The current global operating environment of the platform.")

class EngineHealth(BaseModel):
    status: str
    database: str
    active_mandates: int
    timestamp: datetime

@router.get("/system/environment", response_model=EnvironmentState, tags=["System"])
def get_environment_state():
    """
    Returns the current global operating environment of the platform.
    This state dictates UI presentation and certain backend behaviors.
    """
    env_state = os.getenv("ENVIRONMENT_STATE", "PAPER").upper()
    if env_state not in get_args(Environment):
        env_state = "PAPER" # Default to a safe value if invalid
    return {"environment": env_state}

@router.get("/system/health", response_model=EngineHealth, tags=["System"])
def get_health(db: Session = Depends(get_db)):
    """
    Provides a health check for the application, including database connectivity.
    """
    db_status = "disconnected"
    active_mandates = 0
    try:
        # A simple query to check if the DB is responsive
        active_mandates = db.query(domain.Mandate).filter(domain.Mandate.is_active == True).count()
        db_status = "connected"
    except Exception:
        pass

    return {
        "status": "online",
        "database": db_status,
        "active_mandates": active_mandates,
        "timestamp": datetime.now(timezone.utc)
    }

def run_backfill_task(symbol: str, days: int):
    """Synchronous task for fetching historical data."""
    logger.info(f"BACKGROUND TASK: Starting for {symbol} ({days} days).")
    db = SessionLocal()
    service = HistoricalDataService()
    try:
        # We need to calculate 'since' here because the service object doesn't have a sync exchange instance by default
        sync_exchange = ccxt_sync.binance()
        since = sync_exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
        
        # Call the new synchronous method
        service.fetch_and_store_ohlcv_sync(db, symbol, '1d', since=since, limit=days + 5)
        logger.info(f"BACKGROUND TASK: Completed for {symbol}.")
    except Exception as e:
        logger.error(f"BACKGROUND TASK: Error for {symbol}: {e}", exc_info=True)
    finally:
        db.close()

@router.post("/system/debug/backfill-data", tags=["Debug"], status_code=202)
async def trigger_backfill(
    background_tasks: BackgroundTasks,
    symbol: str = "BTC/USDT",
    days: int = 365
):
    """
    [DEBUG ONLY] Triggers a historical data backfill in the background.
    Check the backend container logs for progress.
    """
    background_tasks.add_task(run_backfill_task, symbol, days)
    return {"message": f"Accepted: Backfill task for {symbol} started in the background. Check backend logs for progress."}