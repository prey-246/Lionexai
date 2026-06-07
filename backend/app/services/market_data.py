import asyncio
import random
import ccxt
import pandas as pd
import logging
from datetime import datetime, timezone

from app.core.sockets import ConnectionManager
from app.core.database import SessionLocal
from app.models import domain

logger = logging.getLogger("nexa.market_data")

class MarketDataService:
    def __init__(self):
        self.exchange = ccxt.binance({'enableRateLimit': True})

    def fetch_live_price(self, symbol: str) -> float:
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.warning(f"CCXT feed blocked for {symbol}. Using mock price. Error: {e}")
            # Robust fallback for local MVP testing
            mocks = {"BTC/USDT": 65000.0, "ETH/USDT": 3500.0, "SOL/USDT": 150.0, "DOGE/USDT": 0.15}
            return mocks.get(symbol, 100.0)

    def fetch_historical_data(self, symbol: str, timeframe: str = '1h', limit: int = 1000) -> pd.DataFrame:
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            return df
        except Exception as e:
            logger.error(f"Failed to fetch market data: {str(e)}")
            raise e

async def market_data_streamer(conn_manager: ConnectionManager):
    """Replays historical market data from the database for a realistic feed."""
    logger.info("Starting market data streamer with historical replay.")
    
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    historical_data = {sym: [] for sym in symbols}
    
    # Load data into memory once for high-performance replay
    db = SessionLocal()
    try:
        for sym in symbols:
            records = db.query(domain.MarketDataOHLCV).filter(
                domain.MarketDataOHLCV.symbol == sym
            ).order_by(domain.MarketDataOHLCV.timestamp.asc()).all()
            
            if records:
                historical_data[sym] = [r.close for r in records]
            else:
                # Fallback static prices if no data backfilled yet
                historical_data[sym] = [65000.0 if sym == "BTC/USDT" else 3500.0 if sym == "ETH/USDT" else 150.0]
    except Exception as e:
        logger.error(f"Failed to load historical data for replay: {e}")
    finally:
        db.close()
        
    indices = {sym: 0 for sym in symbols}

    while True:
        await asyncio.sleep(2) # Broadcast every 2 seconds for a realistic ticker speed
        if "market" in conn_manager.channels and conn_manager.channels["market"]:
            tick_data = {}
            for sym in symbols:
                data_list = historical_data[sym]
                idx = indices[sym]
                
                if data_list:
                    # Add a tiny bit of micro-volatility to the static daily close to make the UI feel "alive"
                    base_price = data_list[idx]
                    micro_change = (random.random() - 0.5) * 2 * 0.0002 * base_price
                    tick_data[sym] = round(base_price + micro_change, 2)
                    
                    # Advance the index, loop around if we reach the end of the historical dataset
                    indices[sym] = (idx + 1) % len(data_list)

            await conn_manager.broadcast({"type": "MARKET_TICK", "data": tick_data}, "market")

def _update_prices_sync(service: MarketDataService, symbols: list):
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for sym in symbols:
            price = service.fetch_live_price(sym)
            tick = domain.MarketDataOHLCV(
                timestamp=now,
                symbol=sym,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=0.0
            )
            db.merge(tick)
        db.commit()
        logger.info("Successfully updated live market prices for the terminal.")
    except Exception as e:
        logger.error(f"Failed to update live market prices: {e}")
        db.rollback()
    finally:
        db.close()

async def periodic_price_updater():
    """Fetches live prices from CCXT every hour and saves them to the database."""
    logger.info("Starting background periodic price updater...")
    service = MarketDataService()
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    
    while True:
        try:
            await asyncio.to_thread(_update_prices_sync, service, symbols)
        except Exception as e:
            logger.error(f"Error in periodic price updater: {e}")
        
        await asyncio.sleep(3600)  # Sleep for 1 hour