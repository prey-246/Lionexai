from .base import ExchangeAdapter
from .binance import BinanceAdapter
from .bybit import BybitAdapter

def get_exchange_adapter(
    exchange_id: str, 
    api_key: str, 
    secret_key: str
) -> ExchangeAdapter:
    """
    Factory function to get an instance of an exchange adapter.
    This is the single entry point for creating exchange connections.
    """
    if exchange_id.lower() == 'binance':
        return BinanceAdapter(api_key, secret_key)
    elif exchange_id.lower() == 'bybit':
        return BybitAdapter(api_key, secret_key)
    else:
        raise ValueError(f"Unsupported or unknown exchange: {exchange_id}")