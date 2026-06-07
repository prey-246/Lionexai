import asyncio
import random
import ccxt
import pandas as pd
import logging

from app.core.sockets import ConnectionManager

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
    """Simulates a high-frequency market data feed with a random walk."""
    prices = {"BTC/USDT": 65000.0, "ETH/USDT": 3500.0, "SOL/USDT": 150.0}
    
    logger.info("Starting market data streamer with random walk.")

    while True:
        await asyncio.sleep(1) # Broadcast every 1 second
        if "market" in conn_manager.channels and conn_manager.channels["market"]:
            tick_data = {}
            for sym in prices:
                # Random walk: max 0.05% movement per second
                change = (random.random() - 0.5) * 2 * 0.0005 * prices[sym]
                prices[sym] = round(prices[sym] + change, 2)
                tick_data[sym] = prices[sym]

            await conn_manager.broadcast({"type": "MARKET_TICK", "data": tick_data}, "market")