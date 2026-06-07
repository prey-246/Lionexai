import asyncio
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import auth, system, audit, portfolios, reports, trading, backtest, stream, mandates, users
from app.core.sockets import manager as ws_manager
from app.services.market_data import market_data_streamer

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def on_startup():
    # Seeding the database on every application startup is not recommended for production.
    # This can lead to errors or duplicate data on service restarts.
    # This should be a one-time setup step or a separate "Job" in your deployment platform (see render.yaml).
    # For local development, you might run this once.
    # db = SessionLocal()
    # seed_db(db)
    # db.close()
    # Start the live market data background task
    logger.info("Starting background market data streamer...")
    asyncio.create_task(market_data_streamer(ws_manager))

# IMPORTANT: For production, restrict this to your frontend's domain.
# Using a wildcard ("*") is a security risk.
origins = [
    "http://localhost:3000", # For local development
    # "https://your-frontend-app.onrender.com" # Add your production frontend URL here from Render
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your API routers here
app.include_router(system.router, prefix="/api", tags=["System"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit"],)
app.include_router(mandates.router, prefix="/api/mandates", tags=["Mandates"])
app.include_router(portfolios.router, prefix="/api/portfolios", tags=["Portfolios"],)
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"],)
app.include_router(trading.router, prefix="/api/trading", tags=["Trading"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtesting"])
app.include_router(stream.router, prefix="/api", tags=["Streaming"])
