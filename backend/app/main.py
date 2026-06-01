from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import asyncio
import random
from app.api.routes import stream
from app.core.sockets import manager
from app.core.database import engine, Base, get_db
from app.models.domain import Mandate, User, Portfolio
from app.api.routes import mandates, backtest

# 1. Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nexa.system")

# 2. Create Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="UnifyX / NEXA Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def seed_database():
    db = next(get_db())
    # Seed Mandates
    if not db.query(Mandate).first():
        logger.info("Seeding Initial Risk Mandates...")
        mandates_data = [
            Mandate(id="PRESERVE", name="Capital Preservation", max_leverage=1.0, max_drawdown_pct=5.0, daily_loss_limit_pct=2.0, allowed_assets=["BTC/USDT", "ETH/USDT"]),
            Mandate(id="BALANCE", name="Balanced Growth", max_leverage=3.0, max_drawdown_pct=10.0, daily_loss_limit_pct=4.0, allowed_assets=["BTC/USDT", "ETH/USDT", "SOL/USDT"]),
            Mandate(id="VAULT", name="NEXA Vault (Unrestricted)", max_leverage=10.0, max_drawdown_pct=25.0, daily_loss_limit_pct=10.0, allowed_assets=["ALL"]),
        ]
        db.add_all(mandates_data)
        db.commit()
    
    # Seed Operations User & Paper Portfolio
    if not db.query(User).first():
        logger.info("Seeding Default Operations User & Portfolio...")
        ops_user = User(id="admin_01", email="ops@nexa.internal", role_tier="ops_admin")
        db.add(ops_user)
        db.commit()
        
        # Attach the 'BALANCE' mandate by default
        sim_portfolio = Portfolio(id="port_sim_01", user_id="admin_01", mandate_id="BALANCE", total_equity=100000.0, available_margin=100000.0)
        db.add(sim_portfolio)
        db.commit()
        
    db.close()

# Routers
app.include_router(mandates.router, prefix="/api/mandates", tags=["Risk Mandates"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Quant Engine"])
from app.api.routes import trading, portfolios, audit, reports, strategies
app.include_router(trading.router, prefix="/api/trading", tags=["Execution Layer"])
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolio Management"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit Logs"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reporting"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["Strategy Management"])

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    return {"status": "online", "database": "connected"}

app.include_router(stream.router, tags=["WebSockets"])

# --- BACKGROUND TELEMETRY ENGINE ---
async def telemetry_streamer():
    """Simulates high-frequency pricing data broadcast"""
    base_prices = {"BTC/USDT": 65000.0, "ETH/USDT": 3500.0}
    while True:
        await asyncio.sleep(1.5) # Update every 1.5 seconds
        
        # Add slight random walk to prices
        base_prices["BTC/USDT"] *= (1 + random.uniform(-0.001, 0.001))
        base_prices["ETH/USDT"] *= (1 + random.uniform(-0.002, 0.002))
        
        payload = {
            "type": "MARKET_TICK",
            "data": {
                "BTC/USDT": round(base_prices["BTC/USDT"], 2),
                "ETH/USDT": round(base_prices["ETH/USDT"], 2)
            }
        }
        await manager.broadcast(payload)

@app.on_event("startup")
async def startup_event():
    seed_database()
    # Spin up the WebSocket daemon in the background
    asyncio.create_task(telemetry_streamer())