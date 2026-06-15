import ccxt.async_support as ccxt
from typing import List, Dict, Literal
from datetime import datetime
import asyncio

from .base import ExchangeAdapter, Balance, Order, Trade, Position

class BybitAdapter(ExchangeAdapter):
    """Adapter for Bybit Spot Testnet."""

    def __init__(self, api_key: str, secret_key: str):
        super().__init__(api_key, secret_key)
        self.exchange = ccxt.bybit({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'options': {
                'defaultType': 'spot',
            },
        })
        # CRITICAL: This enables testnet mode for paper trading.
        self.exchange.set_sandbox_mode(True)

    async def connect(self) -> bool:
        return await self.heartbeat()

    def _parse_order(self, order_data: dict) -> Order:
        """Helper to parse CCXT order data into our standardized Order model."""
        return Order(
            id=order_data['id'],
            symbol=order_data['symbol'],
            type=order_data['type'],
            side=order_data['side'],
            price=order_data.get('price'),
            amount=order_data['amount'],
            cost=order_data['cost'],
            filled=order_data['filled'],
            remaining=order_data['remaining'],
            status=order_data['status'],
            timestamp=datetime.fromtimestamp(order_data['timestamp'] / 1000.0),
            fee=order_data.get('fee')
        )

    def _parse_trade(self, trade_data: dict) -> Trade:
        """Helper to parse CCXT trade data into our standardized Trade model."""
        return Trade(
            id=trade_data['id'],
            order_id=trade_data.get('order'),
            symbol=trade_data['symbol'],
            side=trade_data['side'],
            price=trade_data['price'],
            amount=trade_data['amount'],
            cost=trade_data['cost'],
            timestamp=datetime.fromtimestamp(trade_data['timestamp'] / 1000.0),
            fee=trade_data.get('fee')
        )

    async def get_balance(self) -> Dict[str, Balance]:
        """Fetches the account balance from Bybit Testnet."""
        balance_data = await self.exchange.fetch_balance()
        # Add a guard against a None response from the exchange
        if balance_data is None:
            return {}
        balances: Dict[str, Balance] = {}
        if balance_data.get('total'): # More robust check for existence and not None
            for asset, total_balance in balance_data['total'].items():
                if total_balance > 0:
                    balances[asset] = Balance(
                        asset=asset,
                        free=balance_data.get('free', {}).get(asset, 0.0),
                        used=balance_data.get('used', {}).get(asset, 0.0),
                        total=total_balance
                    )
        return balances

    async def place_market_order(self, symbol: str, side: Literal['buy', 'sell'], amount: float) -> Order:
        """Places a new market order on Bybit Testnet."""
        order = await self.exchange.create_order(symbol, 'market', side, amount)
        return self._parse_order(order)

    async def place_limit_order(self, symbol: str, side: Literal['buy', 'sell'], amount: float, price: float) -> Order:
        """Places a new limit order on Bybit Testnet."""
        order = await self.exchange.create_order(symbol, 'limit', side, amount, price)
        return self._parse_order(order)

    async def get_open_orders(self, symbol: str | None = None) -> List[Order]:
        # Bybit requires a symbol for fetch_open_orders.
        # If no symbol is provided, we return an empty list as we can't fetch for all.
        if symbol is None:
            return []
        orders_data = await self.exchange.fetch_open_orders(symbol)
        if not isinstance(orders_data, list):
            return []
        return [self._parse_order(o) for o in orders_data if o is not None]

    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Fetches the status of a single order by its ID."""
        order = await self.exchange.fetch_order(order_id, symbol)
        return self._parse_order(order)

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        order = await self.exchange.cancel_order(order_id, symbol)
        return self._parse_order(order)

    async def fetch_my_trades(self, symbol: str | None = None, limit: int = 20) -> List[Trade]:
        if symbol:
            trades_data = await self.exchange.fetch_my_trades(symbol=symbol, limit=limit)
            if not isinstance(trades_data, list):
                return []
            return [self._parse_trade(t) for t in trades_data if t is not None]

        major_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        all_trades = []
        results = await asyncio.gather(
            *[self.exchange.fetch_my_trades(s, limit=limit) for s in major_symbols],
            return_exceptions=True,
        )
        for result in results:
            if not isinstance(result, Exception) and isinstance(result, list):
                all_trades.extend(result)

        all_trades.sort(key=lambda t: t.get('timestamp', 0), reverse=True)
        return [self._parse_trade(t) for t in all_trades[:limit] if t is not None]

    async def fetch_positions(self, symbols: List[str] | None = None) -> List[Position]:
        # Spot accounts don't have positions in the same way as futures.
        # The 'balance' is the source of truth for holdings.
        return []

    async def heartbeat(self) -> bool:
        """Checks if the Bybit Testnet connection is alive."""
        # fetch_time is a lightweight way to check for connectivity and authentication
        await self.exchange.fetch_time()
        return True

    async def close(self):
        """Closes the exchange connection."""
        await self.exchange.close()