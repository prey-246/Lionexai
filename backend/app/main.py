import asyncio
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.scheduler import scheduler
from app.services.validation_service import update_validation_snapshots_job
from app.api.routes import auth, system, audit, portfolios, reports, trading, backtest, stream, mandates, users, intelligence, treasury, strategies, execution_health, validation, stress_test, analytics, trades
from app.core.sockets import manager as ws_manager
from app.services.market_data import market_data_streamer, periodic_price_updater
from scripts.scrape_news import scrape_crypto_news
from scripts.scrape_economic_events import fetch_and_store_events
from scripts.yield_sweep import perform_yield_sweep
from app.services.nlp_service import run_nlp_analysis
from scripts.algo_executor import run_autonomous_execution
from app.api.routes import exchange as exchange_router


logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup
    logger.info("Starting background tasks...")
    # Start the live market data background task
    asyncio.create_task(market_data_streamer(ws_manager))
    # Start the periodic news scraper
    asyncio.create_task(periodic_news_scraper())
    # Start the NLP Analyzer
    asyncio.create_task(periodic_nlp_analyzer())
    # Start the Economic Events Scraper
    asyncio.create_task(periodic_economic_scraper())
    # Start the periodic price updater for the trading terminal
    asyncio.create_task(periodic_price_updater())
    # Start the automated yield generation sweep
    asyncio.create_task(periodic_yield_sweeper())
    # Start the autonomous trading engine
    asyncio.create_task(periodic_algo_executor())

    # Validation snapshots: immediate run + every 15 min + daily archive at 00:05 UTC
    scheduler.add_job(update_validation_snapshots_job, 'interval', minutes=15, id="update_validation_snapshots")
    scheduler.add_job(update_validation_snapshots_job, 'cron', hour=0, minute=5, id="archive_validation_snapshots")
    scheduler.start()
    logger.info("Scheduler started. Validation snapshots will be updated periodically.")
    # Run once immediately so the validation dashboard has data on first load
    try:
        update_validation_snapshots_job()
        logger.info("Initial validation snapshots computed on startup.")
    except Exception as e:
        logger.error(f"Initial validation snapshot run failed: {e}", exc_info=True)
    
    yield
    
    # On shutdown
    logger.info("Shutting down scheduler...")
    scheduler.shutdown()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

async def periodic_news_scraper():
    """Runs the news scraper in the background every hour."""
    logger.info("Starting background periodic news scraper...")
    while True:
        try:
            # Run sync function in a thread to prevent blocking the async loop
            await asyncio.to_thread(scrape_crypto_news)
        except Exception as e:
            logger.error(f"Error in periodic scraper: {e}")
        await asyncio.sleep(3600)  # Sleep for 1 hour (3600 seconds)

async def periodic_nlp_analyzer():
    """Runs the NLP Sentiment engine in the background to process new data."""
    logger.info("Starting background NLP Sentiment Analyzer...")
    while True:
        try:
            # Run sync function in a thread to prevent blocking
            await asyncio.to_thread(run_nlp_analysis)
        except Exception as e:
            logger.error(f"Error in periodic NLP analyzer: {e}")
        await asyncio.sleep(600)  # Run every 10 minutes to process incoming news

async def periodic_economic_scraper():
    """Runs the economic events scraper in the background."""
    logger.info("Starting background periodic economic events scraper...")
    while True:
        try:
            await asyncio.to_thread(fetch_and_store_events)
        except Exception as e:
            logger.error(f"Error in periodic economic scraper: {e}")
        await asyncio.sleep(21600)  # Run every 6 hours (21600 seconds)

async def periodic_yield_sweeper():
    """Runs the automated yield sweep in the background."""
    logger.info("Starting background periodic yield sweeper...")
    while True:
        try:
            await asyncio.to_thread(perform_yield_sweep)
        except Exception as e:
            logger.error(f"Error in periodic yield sweeper: {e}")
        await asyncio.sleep(3600)  # Run every hour (3600 seconds)

async def periodic_algo_executor():
    """Runs the autonomous trading engine in the background."""
    logger.info("Starting background autonomous strategy executor...")
    while True:
        try:
            await run_autonomous_execution()
        except Exception as e:
            logger.error(f"Error in autonomous executor: {e}")
        await asyncio.sleep(60)  # Run every 60 seconds

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
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["NEXA Intelligence"])
app.include_router(treasury.router, prefix="/api/treasury", tags=["Treasury Foundation"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["Strategies"])
app.include_router(exchange_router.router, prefix="/api/exchange", tags=["Exchange"])
app.include_router(execution_health.router, prefix="/api/execution", tags=["Execution Health"])
app.include_router(validation.router, prefix="/api/validation", tags=["Validation"])
app.include_router(stress_test.router, prefix="/api/stress-test", tags=["Stress Test"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(trades.router, prefix="/api/trades", tags=["Trade Explorer"])
