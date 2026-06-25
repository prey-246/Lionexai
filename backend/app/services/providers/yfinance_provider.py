import logging
from typing import List

from .base import MarketDataProvider, Bar
from .mock_provider import MockProvider

logger = logging.getLogger("nexa.providers.yfinance")

try:
    import yfinance as yf  # type: ignore
    _YF_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    yf = None
    _YF_AVAILABLE = False

# yfinance interval per canonical timeframe.
_INTERVAL = {"1d": "1d", "1h": "1h", "4h": "1h", "15m": "15m", "5m": "5m", "1m": "1m"}


def _period_for(timeframe: str, limit: int) -> str:
    if timeframe == "1d":
        days = limit + 5
        if days <= 30:
            return "1mo"
        if days <= 95:
            return "3mo"
        if days <= 185:
            return "6mo"
        if days <= 370:
            return "1y"
        if days <= 740:
            return "2y"
        return "5y"
    # intraday: yfinance caps history; keep it short
    return "60d" if timeframe in ("1h", "4h") else "7d"


class YFinanceProvider(MarketDataProvider):
    """Free EOD/delayed feed for metals, energy, equity indices and FX.

    Non-crypto runs as paper, so delayed data is acceptable. Falls back to the
    deterministic mock generator whenever yfinance is unavailable or returns empty.
    """

    name = "yfinance"

    def __init__(self):
        self._mock = MockProvider()

    def fetch_ohlcv(self, data_symbol: str, timeframe: str = "1d", limit: int = 400) -> List[Bar]:
        if not _YF_AVAILABLE:
            logger.info("yfinance unavailable; using mock series for %s.", data_symbol)
            return self._mock.fetch_ohlcv(data_symbol, timeframe, limit)
        try:
            interval = _INTERVAL.get(timeframe, "1d")
            period = _period_for(timeframe, limit)
            df = yf.download(
                data_symbol,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                threads=False,
            )
            if df is None or df.empty:
                logger.warning("yfinance returned no data for %s; using mock.", data_symbol)
                return self._mock.fetch_ohlcv(data_symbol, timeframe, limit)

            bars: List[Bar] = []
            for ts, row in df.iterrows():
                def _val(col):
                    v = row[col]
                    # yfinance can return a 1-element Series with multiindex columns
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        return float(v.iloc[0])
                ts_naive = ts.to_pydatetime().replace(tzinfo=None)
                bars.append(Bar(
                    timestamp=ts_naive,
                    open=_val("Open"),
                    high=_val("High"),
                    low=_val("Low"),
                    close=_val("Close"),
                    volume=_val("Volume") if "Volume" in row else 0.0,
                ))
            return bars[-limit:]
        except Exception as e:
            logger.warning("yfinance fetch failed for %s: %s; using mock.", data_symbol, e)
            return self._mock.fetch_ohlcv(data_symbol, timeframe, limit)

    def fetch_live_price(self, data_symbol: str) -> float:
        if not _YF_AVAILABLE:
            return self._mock.fetch_live_price(data_symbol)
        try:
            ticker = yf.Ticker(data_symbol)
            fast = getattr(ticker, "fast_info", None)
            if fast:
                price = fast.get("last_price") or fast.get("lastPrice")
                if price:
                    return float(price)
            hist = ticker.history(period="5d", interval="1d")
            if hist is not None and not hist.empty:
                return float(hist["Close"].iloc[-1])
        except Exception as e:
            logger.warning("yfinance live price failed for %s: %s; using mock.", data_symbol, e)
        return self._mock.fetch_live_price(data_symbol)
