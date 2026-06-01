import ccxt
import pandas as pd
import logging

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