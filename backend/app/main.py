import asyncio
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.scheduler import scheduler
from app.core.database import SessionLocal
from app.services.validation_service import update_validation_snapshots_job
from app.api.routes import auth, system, audit, portfolios, reports, trading, backtest, stream, mandates, users, intelligence, treasury, strategies, execution_health, validation, stress_test, analytics, trades
from app.core.sockets import manager as ws_manager
from app.services.market_data import market_data_streamer, periodic_price_updater
from scripts.scrape_news import scrape_crypto_news
from scripts.scrape_economic_events import fetch_and_store_events
from scripts.yield_sweep import perform_yield_sweep
from app.services.nlp_service import run_nlp_analysis
from app.services.portfolio_manager import run_portfolio_manager_cycle
from app.engines.strategy_optimizer import run_strategy_optimizer
from app.services.market_data_service import run_market_ingestion, run_backfill
from app.engines.regime_engine import run_regime_detection
from app.engines.macro_intelligence import run_global_market_state
from app.engines.allocation_engine import run_allocation_cycle
from app.services.settlement_engine import run_weekly_settlement
from app.engines.lnx_index import run_lnx_snapshot
from app.api.routes import exchange as exchange_router
from app.api.routes import funds as funds_router
from app.api.routes import market as market_router
from app.api.routes import assets as assets_router
from app.api.routes import lnx as lnx_router
from app.api.routes import market_intel as market_intel_router
from app.services.market_intelligence_service import run_market_intelligence_ingestion
from app.services.paper_trading_validation_service import update_paper_validation_snapshots
from app.services.allocation_integrity_monitor import run_integrity_scan
from app.services.live_validation_engine import update_live_validation_snapshots
from app.services.asset_classification import seed_extended_assets
from app.services.lnx_attribution_engine import LNXAttributionEngine
from app.services.treasury_verification_engine import TreasuryVerificationEngine
from app.api.routes import validated_performance as validated_performance_router
from app.api.routes import institutional as institutional_router


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
    # Start the autonomous trading engine (multi-asset when autonomous_v2 is enabled)
    asyncio.create_task(periodic_algo_executor())
    # Phase 4: one-shot bootstrap so multi-asset data + allocations exist on first run
    asyncio.create_task(phase4_bootstrap())

    # Validation snapshots: immediate run + every 15 min + daily archive at 00:05 UTC
    scheduler.add_job(update_validation_snapshots_job, 'interval', minutes=15, id="update_validation_snapshots")
    scheduler.add_job(update_validation_snapshots_job, 'cron', hour=0, minute=5, id="archive_validation_snapshots")

    # Phase 4 background jobs: multi-asset ingestion + regime/macro intelligence + allocation
    scheduler.add_job(run_market_ingestion, 'interval', hours=1, id="market_ingestion")
    scheduler.add_job(run_regime_detection, 'interval', hours=1, id="regime_detection")
    scheduler.add_job(run_global_market_state, 'interval', hours=1, id="global_market_state")
    scheduler.add_job(run_allocation_cycle, 'cron', hour=0, minute=10, id="allocation_cycle")
    scheduler.add_job(run_weekly_settlement, 'cron', day_of_week='mon', hour=1, minute=0, id="weekly_settlement")
    scheduler.add_job(run_lnx_snapshot, 'cron', hour=2, minute=0, id="lnx_snapshot")
    scheduler.add_job(run_strategy_optimizer, 'cron', day_of_week='mon', hour=3, minute=0, id="strategy_optimizer")
    scheduler.add_job(run_market_intelligence_ingestion, 'interval', hours=2, id="market_intel_ingestion")
    scheduler.add_job(update_paper_validation_snapshots, 'interval', hours=6, id="paper_trading_validation")
    scheduler.add_job(update_live_validation_snapshots, 'interval', hours=6, id="live_validation")
    scheduler.add_job(run_integrity_scan, 'interval', hours=1, id="allocation_integrity_scan")
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
            await run_portfolio_manager_cycle()
        except Exception as e:
            logger.error(f"Error in autonomous executor: {e}")
        await asyncio.sleep(60)  # Run every 60 seconds


def _phase6_bootstrap():
    db = SessionLocal()
    try:
        seed_extended_assets(db)
    finally:
        db.close()


async def phase4_bootstrap():
    """One-shot Phase 4 warm-up: backfill multi-asset bars, detect regimes, compute
    the global market state, and produce initial allocations for auto-managed
    portfolios. Each step is sync and opens its own DB session, so we run them in a
    thread to avoid blocking the event loop."""
    logger.info("Phase 4 bootstrap starting (backfill -> regime -> macro -> allocation)...")
    try:
        await asyncio.to_thread(run_backfill)
        await asyncio.to_thread(run_regime_detection)
        await asyncio.to_thread(run_global_market_state)
        await asyncio.to_thread(run_allocation_cycle, True, "BOOTSTRAP")
        await asyncio.to_thread(_phase6_bootstrap)
        logger.info("Phase 4 bootstrap complete.")
    except Exception as e:
        logger.error(f"Phase 4 bootstrap failed: {e}", exc_info=True)

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
# Phase 4: multi-asset autonomous fund manager
app.include_router(assets_router.router, prefix="/api/assets", tags=["Assets"])
app.include_router(funds_router.router, prefix="/api/funds", tags=["AI Funds"])
app.include_router(market_router.router, prefix="/api/market", tags=["Market Intelligence"])
app.include_router(lnx_router.router, prefix="/api/lnx", tags=["LNX Index"])
app.include_router(market_intel_router.router, prefix="/api/market-intelligence", tags=["Market Intelligence"])
app.include_router(validated_performance_router.router, prefix="/api/validated", tags=["Validated Performance"])
app.include_router(institutional_router.router, prefix="/api/institutional", tags=["Institutional"])
