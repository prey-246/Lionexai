from abc import ABC, abstractmethod
from typing import List, Literal, Dict
from pydantic import BaseModel
from datetime import datetime

class Balance(BaseModel):
    """Represents the balance of a single asset in the exchange account."""
    asset: str
    free: float
    used: float
    total: float

class Trade(BaseModel):
    """Represents a single trade execution."""
    id: str
    order_id: str | None = None
    symbol: str
    side: Literal['buy', 'sell']
    price: float
    amount: float
    cost: float
    timestamp: datetime
    fee: Dict | None = None

class Position(BaseModel):
    """Represents an open position (more relevant for derivatives)."""
    symbol: str
    contracts: float
    entryPrice: float | None = None
    markPrice: float | None = None
    unrealizedPnl: float | None = None
    leverage: float | None = None
    side: Literal['long', 'short'] | None = None

class Order(BaseModel):
    """Represents a single order on the exchange."""
    id: str
    symbol: str
    type: Literal['limit', 'market']
    side: Literal['buy', 'sell']
    price: float | None = None
    amount: float
    cost: float
    filled: float
    remaining: float
    status: str # e.g., 'open', 'closed', 'canceled'
    timestamp: datetime
    fee: Dict | None = None

class ExchangeAdapter(ABC):
    """Abstract Base Class for an exchange adapter, defining the required interface."""

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key

    @abstractmethod
    async def get_balance(self) -> Dict[str, Balance]:
        """Fetches the account balance."""
        pass

    @abstractmethod
    async def place_market_order(self, symbol: str, side: Literal['buy', 'sell'], amount: float) -> Order:
        """Places a new market order."""
        pass

    @abstractmethod
    async def place_limit_order(self, symbol: str, side: Literal['buy', 'sell'], amount: float, price: float) -> Order:
        """Places a new limit order."""
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: str | None = None) -> List[Order]:
        """Fetches all open orders."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Fetches the status of a single order by its ID."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        """Cancels an open order."""
        pass

    @abstractmethod
    async def fetch_my_trades(self, symbol: str | None = None, limit: int = 20) -> List[Trade]:
        """Fetches recent trades for the account."""
        pass

    @abstractmethod
    async def fetch_positions(self, symbols: List[str] | None = None) -> List[Position]:
        """Fetches open positions."""
        pass

    async def get_positions(self, symbols: List[str] | None = None) -> List[Position]:
        """Alias for fetch_positions."""
        return await self.fetch_positions(symbols)

    async def get_order_history(self, symbol: str | None = None, limit: int = 20) -> List[Trade]:
        """Alias for fetch_my_trades."""
        return await self.fetch_my_trades(symbol=symbol, limit=limit)

    @abstractmethod
    async def connect(self) -> bool:
        """Validates exchange connectivity and credentials."""
        pass

    @abstractmethod
    async def heartbeat(self) -> bool:
        """Checks if the exchange connection is alive."""
        pass

    @abstractmethod
    async def close(self):
        """Closes the exchange connection."""
        pass