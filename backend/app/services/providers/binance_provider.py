import logging
from datetime import datetime, timezone
from typing import List

import ccxt

from .base import MarketDataProvider, Bar

logger = logging.getLogger("nexa.providers.binance")

# Mock fallbacks so local/dev environments without exchange connectivity still function.
_MOCK_PRICES = {
    "BTC/USDT": 65000.0,
    "ETH/USDT": 3500.0,
    "SOL/USDT": 150.0,
    "DOGE/USDT": 0.15,
}


class BinanceProvider(MarketDataProvider):
    name = "binance"

    def __init__(self):
        self._exchange = ccxt.binance({"enableRateLimit": True})

    def fetch_ohlcv(self, data_symbol: str, timeframe: str = "1d", limit: int = 400) -> List[Bar]:
        try:
            ms_per_bar = 86400000 if timeframe == "1d" else 3600000
            since = self._exchange.milliseconds() - limit * ms_per_bar
            bars: List[Bar] = []
            while len(bars) < limit:
                batch = self._exchange.fetch_ohlcv(
                    data_symbol, timeframe, since=since, limit=min(1000, limit - len(bars)),
                )
                if not batch:
                    break
                for r in batch:
                    bars.append(Bar(
                        timestamp=datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc).replace(tzinfo=None),
                        open=float(r[1]),
                        high=float(r[2]),
                        low=float(r[3]),
                        close=float(r[4]),
                        volume=float(r[5] or 0.0),
                    ))
                since = batch[-1][0] + 1
                if len(batch) < min(1000, limit - len(bars) + len(batch)):
                    break
            dedup: dict[datetime, Bar] = {}
            for b in bars:
                dedup[b.timestamp] = b
            return sorted(dedup.values(), key=lambda b: b.timestamp)[-limit:]
        except Exception as e:
            logger.warning("Binance OHLCV fetch failed for %s (%s): %s", data_symbol, timeframe, e)
            return []

    def fetch_live_price(self, data_symbol: str) -> float:
        try:
            ticker = self._exchange.fetch_ticker(data_symbol)
            return float(ticker["last"])
        except Exception as e:
            logger.warning("Binance live price blocked for %s, using mock. %s", data_symbol, e)
            return _MOCK_PRICES.get(data_symbol, 100.0)
