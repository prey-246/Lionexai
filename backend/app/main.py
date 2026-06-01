import asyncio
import random
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.api.routes import auth, system, audit, portfolios, reports, trading, backtest, stream
from app.initial_data import seed_db
from app.core.sockets import manager
from app.services.market_data import MarketDataService

app = FastAPI(title=settings.PROJECT_NAME)

async def market_data_streamer():
    """Simulates a high-frequency market data feed based on initial real prices."""
    mds = MarketDataService()
    prices = {"BTC/USDT": 65000.0, "ETH/USDT": 3500.0, "SOL/USDT": 150.0}
    
    try:
        for sym in prices:
            prices[sym] = mds.fetch_live_price(sym)
    except Exception:
        pass

    while True:
        await asyncio.sleep(1) # Broadcast every 1 second
        if "market" in manager.channels and manager.channels["market"]:
            tick_data = {}
            for sym in prices:
                # Random walk: max 0.05% movement per second to simulate live market noise
                change = (random.random() - 0.5) * 2 * 0.0005 * prices[sym]
                prices[sym] = round(prices[sym] + change, 2)
                tick_data[sym] = prices[sym]
            
            await manager.broadcast({"type": "MARKET_TICK", "data": tick_data}, "market")

@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    seed_db(db)
    db.close()
    # Start the live market data background task
    asyncio.create_task(market_data_streamer())

# In a real application, you would want to restrict this to your frontend's domain
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your API routers here
app.include_router(auth.router, prefix="/api/auth")
app.include_router(system.router, prefix="/api")
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"],)
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolios"],)
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"],)
app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtesting"])
app.include_router(stream.router, prefix="/api", tags=["Streaming"])