from .base import MarketDataProvider, Bar
from .binance_provider import BinanceProvider
from .yfinance_provider import YFinanceProvider
from .mock_provider import MockProvider

# Singleton provider instances keyed by the `data_provider` field on an Asset.
_PROVIDERS = {
    "binance": BinanceProvider(),
    "yfinance": YFinanceProvider(),
    "mock": MockProvider(),
}


def get_provider(name: str) -> MarketDataProvider:
    """Return a provider by name, defaulting to the mock provider when unknown."""
    return _PROVIDERS.get((name or "mock").lower(), _PROVIDERS["mock"])


__all__ = ["MarketDataProvider", "Bar", "get_provider"]
