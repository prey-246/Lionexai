import os
import random
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Literal, get_args, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import domain
from app.models import schemas
from app.services.historical_data import HistoricalDataService
from app.core.database import SessionLocal
from app.api.deps import require_role, get_current_user
from app.services.audit_service import create_audit_log
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
    trades_today: int = 0
    active_users: int = 0
    timestamp: datetime

class BackgroundTaskStatus(BaseModel):
    name: str
    status: Literal["OPERATIONAL", "DEGRADED", "OFFLINE"]
    last_run: datetime
    frequency: str

@router.get("/system/environment", response_model=EnvironmentState, tags=["System"])
def get_environment_state(db: Session = Depends(get_db)):
    """
    Returns the current global operating environment of the platform.
    This state dictates UI presentation and certain backend behaviors.
    """
    settings = db.query(domain.GlobalSettings).filter_by(id="default").first()
    if settings:
        env_state = settings.environment_state.upper()
    else:
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
    trades_today = 0
    active_users = 0
    try:
        # A simple query to check if the DB is responsive
        active_mandates = db.query(domain.Mandate).filter(domain.Mandate.is_active == True).count()
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        trades_today = db.query(domain.Trade).filter(domain.Trade.created_at >= today_start).count()
        
        active_users = db.query(domain.User).filter(domain.User.is_active == True).count()
        
        db_status = "connected"
    except Exception:
        pass

    return {
        "status": "online",
        "database": db_status,
        "active_mandates": active_mandates,
        "trades_today": trades_today,
        "active_users": active_users,
        "timestamp": datetime.now(timezone.utc)
    }

@router.get("/system/background-tasks", response_model=List[BackgroundTaskStatus], tags=["System"])
def get_background_task_statuses():
    """Returns the operational status of all background daemon processes."""
    now = datetime.now(timezone.utc)
    # For demo purposes, we return a healthy status for all defined tasks.
    # A real implementation would use a shared state (like Redis) to track heartbeats.
    tasks = [
        {"name": "Market Data Streamer", "status": "OPERATIONAL", "last_run": now - timedelta(seconds=random.randint(1, 3)), "frequency": "Continuous"},
        {"name": "Autonomous Executor", "status": "OPERATIONAL", "last_run": now - timedelta(seconds=random.randint(20, 50)), "frequency": "Every 60s"},
        {"name": "NLP Analyzer", "status": "OPERATIONAL", "last_run": now - timedelta(minutes=random.randint(1, 9)), "frequency": "Every 10m"},
        {"name": "Price Updater", "status": "OPERATIONAL", "last_run": now - timedelta(minutes=random.randint(10, 50)), "frequency": "Every 1h"},
        {"name": "News Scraper", "status": "OPERATIONAL", "last_run": now - timedelta(minutes=random.randint(10, 50)), "frequency": "Every 1h"},
        {"name": "Yield Sweeper", "status": "OPERATIONAL", "last_run": now - timedelta(minutes=random.randint(10, 50)), "frequency": "Every 1h"},
        {"name": "Economic Scraper", "status": "OPERATIONAL", "last_run": now - timedelta(hours=random.randint(1, 5)), "frequency": "Every 6h"},
    ]
    return tasks

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

@router.get("/system/settings", response_model=schemas.GlobalSettings, tags=["System"])
def get_global_settings(db: Session = Depends(get_db)):
    """Retrieves the global platform settings."""
    settings = db.query(domain.GlobalSettings).filter_by(id="default").first()
    if not settings:
        # Initialize default settings if they don't exist yet
        settings = domain.GlobalSettings(id="default")
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("/system/settings", response_model=schemas.GlobalSettings, tags=["System"], dependencies=[Depends(require_role(["admin"]))])
def update_global_settings(
    settings_in: schemas.GlobalSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: domain.User = Depends(get_current_user)
):
    """Updates the global platform settings."""
    settings = db.query(domain.GlobalSettings).filter_by(id="default").first()
    if not settings:
        settings = domain.GlobalSettings(id="default")
        db.add(settings)

    update_data = settings_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
        
    db.commit()

    create_audit_log(
        db,
        action_type="SETTINGS_UPDATE",
        description=f"User '{current_user.email}' updated global platform settings.",
        metadata_json={"user_id": current_user.id, "changes": update_data}
    )
    
    db.refresh(settings)
    return settings