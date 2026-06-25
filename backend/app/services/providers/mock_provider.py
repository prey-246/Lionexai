import hashlib
import math
import random
from datetime import datetime, timedelta, timezone
from typing import List

from .base import MarketDataProvider, Bar, TIMEFRAME_SECONDS

# Reasonable anchor prices so simulated non-crypto series look plausible.
_ANCHORS = {
    "GC=F": 2350.0,    # Gold
    "SI=F": 30.0,      # Silver
    "CL=F": 78.0,      # WTI Crude
    "^GSPC": 5400.0,   # S&P 500
    "^NDX": 19000.0,   # Nasdaq 100
    "^IXIC": 17500.0,  # Nasdaq Composite
    "EURUSD=X": 1.08,
    "GBPUSD=X": 1.27,
    "BTC/USDT": 65000.0,
    "ETH/USDT": 3500.0,
    "SOL/USDT": 150.0,
}


class MockProvider(MarketDataProvider):
    """Deterministic geometric-random-walk generator for offline/paper use."""

    name = "mock"

    def _anchor(self, data_symbol: str) -> float:
        if data_symbol in _ANCHORS:
            return _ANCHORS[data_symbol]
        # Stable pseudo-anchor derived from the symbol so repeated runs are consistent.
        h = int(hashlib.sha256(data_symbol.encode()).hexdigest(), 16) % 9000
        return float(50 + h / 10.0)

    def _series(self, data_symbol: str, timeframe: str, limit: int) -> List[Bar]:
        seed = int(hashlib.sha256(f"{data_symbol}:{timeframe}".encode()).hexdigest(), 16) % (2 ** 32)
        rng = random.Random(seed)
        step = TIMEFRAME_SECONDS.get(timeframe, 86400)
        now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        # Daily vol scaled by sqrt(timeframe / 1d); crypto a touch more volatile.
        base_vol = 0.012 if "USDT" in data_symbol else 0.008
        vol = base_vol * math.sqrt(step / 86400)

        price = self._anchor(data_symbol)
        # Walk backwards to set a starting point, then forward to "now".
        prices = []
        p = price
        for _ in range(limit):
            drift = rng.uniform(-vol, vol) + 0.0002
            p = max(0.0001, p * (1 + drift))
            prices.append(p)

        bars: List[Bar] = []
        for i, close in enumerate(prices):
            ts = now - timedelta(seconds=step * (limit - 1 - i))
            open_ = prices[i - 1] if i > 0 else close * (1 - vol / 2)
            high = max(open_, close) * (1 + abs(rng.uniform(0, vol)))
            low = min(open_, close) * (1 - abs(rng.uniform(0, vol)))
            bars.append(Bar(
                timestamp=ts,
                open=round(open_, 6),
                high=round(high, 6),
                low=round(low, 6),
                close=round(close, 6),
                volume=round(rng.uniform(1000, 100000), 2),
            ))
        return bars

    def fetch_ohlcv(self, data_symbol: str, timeframe: str = "1d", limit: int = 400) -> List[Bar]:
        return self._series(data_symbol, timeframe, limit)

    def fetch_live_price(self, data_symbol: str) -> float:
        bars = self._series(data_symbol, "1d", 2)
        return bars[-1].close if bars else self._anchor(data_symbol)
