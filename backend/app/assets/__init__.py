from abc import ABC, abstractmethod
from typing import Optional

from app.models import domain
from app.exchange import get_exchange_adapter, ExchangeAdapter
from app.exchange.simulated import SimulatedAdapter
from app.services import market_data_service


class AssetAdapter(ABC):
    """Unified execution interface per asset class (mirrors ExchangeAdapter)."""

    asset_class: str = "BASE"

    @abstractmethod
    async def get_adapter(self, asset: domain.Asset) -> ExchangeAdapter | SimulatedAdapter:
        raise NotImplementedError

    def get_price(self, db, asset: domain.Asset) -> Optional[float]:
        try:
            return market_data_service.get_live_price(asset)
        except Exception:
            return market_data_service.latest_close(db, asset.symbol)


class CryptoAdapter(AssetAdapter):
    asset_class = "CRYPTO"

    async def get_adapter(self, asset: domain.Asset) -> ExchangeAdapter | SimulatedAdapter:
        venue = (asset.execution_venue or "binance").lower()
        import os
        if venue in ("binance", "bybit"):
            key = os.environ.get(f"{venue.upper()}_API_KEY", "")
            secret = os.environ.get(f"{venue.upper()}_SECRET_KEY", "")
            if key and "YOUR_" not in key:
                try:
                    adapter = get_exchange_adapter(venue, key, secret)
                    await adapter.connect()
                    return adapter
                except Exception:
                    pass
        return SimulatedAdapter()


class SimulatedAssetAdapter(AssetAdapter):
    """Paper trading for metals, FX, indices, energy."""

    asset_class = "SIMULATED"

    async def get_adapter(self, asset: domain.Asset) -> SimulatedAdapter:
        return SimulatedAdapter()


_ADAPTERS = {
    "CRYPTO": CryptoAdapter(),
    "METAL": SimulatedAssetAdapter(),
    "ENERGY": SimulatedAssetAdapter(),
    "EQUITY_INDEX": SimulatedAssetAdapter(),
    "FX": SimulatedAssetAdapter(),
    "BOND": SimulatedAssetAdapter(),
    "SECTOR_ETF": SimulatedAssetAdapter(),
    "VOLATILITY": SimulatedAssetAdapter(),
    "COMMODITY_BASKET": SimulatedAssetAdapter(),
}


def get_asset_adapter(asset: domain.Asset) -> AssetAdapter:
    return _ADAPTERS.get(asset.asset_class, SimulatedAssetAdapter())
