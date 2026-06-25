from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Bar:
    """A single OHLCV candle, provider-agnostic."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


# Map of canonical timeframes -> approximate seconds, used for backfill windows.
TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


class MarketDataProvider(ABC):
    """Common interface every market-data source must implement."""

    name: str = "base"

    @abstractmethod
    def fetch_ohlcv(self, data_symbol: str, timeframe: str = "1d", limit: int = 400) -> List[Bar]:
        """Return up to `limit` most-recent OHLCV bars (oldest-first)."""
        raise NotImplementedError

    @abstractmethod
    def fetch_live_price(self, data_symbol: str) -> float:
        """Return the latest traded/observed price for the instrument."""
        raise NotImplementedError
