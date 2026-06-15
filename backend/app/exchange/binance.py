import ccxt.async_support as ccxt
from typing import List, Dict, Literal
import asyncio
from datetime import datetime

from .base import ExchangeAdapter, Balance, Order, Trade, Position

class BinanceAdapter(ExchangeAdapter):
    """Adapter for Binance Spot Testnet."""

    def __init__(self, api_key: str, secret_key: str):
        super().__init__(api_key, secret_key)
        self.exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.secret_key,
            'options': {
                'defaultType': 'spot',
                # Suppress the warning about fetching open orders without a symbol
                'warnOnFetchOpenOrdersWithoutSymbol': False,
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
        """Fetches the account balance from Binance Testnet."""
        balance_data = await self.exchange.fetch_balance()
        if balance_data is None:
            return {}
        
        balances: Dict[str, Balance] = {}
        
        # First, try to parse the raw 'info' field, which is more reliable on testnets.
        raw_balances = balance_data.get('info', {}).get('balances', [])
        if raw_balances and isinstance(raw_balances, list):
            for bal in raw_balances:
                asset = bal.get('asset')
                free = float(bal.get('free', 0.0))
                locked = float(bal.get('locked', 0.0))
                total = free + locked
                if asset and total > 0:
                    balances[asset] = Balance(asset=asset, free=free, used=locked, total=total)
            return balances

        # Fallback to the parsed fields if the 'info' field is not structured as expected.
        if balance_data.get('total'):
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
        """Places a new market order on Binance Testnet."""
        order = await self.exchange.create_order(symbol, 'market', side, amount)
        return self._parse_order(order)

    async def place_limit_order(self, symbol: str, side: Literal['buy', 'sell'], amount: float, price: float) -> Order:
        """Places a new limit order on Binance Testnet."""
        order = await self.exchange.create_order(symbol, 'limit', side, amount, price)
        return self._parse_order(order)

    async def get_open_orders(self, symbol: str | None = None) -> List[Order]:
        """Fetches all open orders from Binance Testnet."""
        orders_data = await self.exchange.fetch_open_orders(symbol)
        if not isinstance(orders_data, list):
            return []
        return [self._parse_order(o) for o in orders_data if o is not None]

    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        """Fetches the status of a single order by its ID."""
        order = await self.exchange.fetch_order(order_id, symbol)
        return self._parse_order(order)

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        """Cancels an open order on Binance Testnet."""
        order = await self.exchange.cancel_order(order_id, symbol)
        return self._parse_order(order)

    async def fetch_my_trades(self, symbol: str | None = None, limit: int = 20) -> List[Trade]:
        """Fetches recent trades from Binance Testnet."""
        if symbol:
            trades_data = await self.exchange.fetch_my_trades(symbol=symbol, limit=limit)
            if not isinstance(trades_data, list):
                return []
            return [self._parse_trade(t) for t in trades_data if t is not None]

        # If no symbol, fetch for a few major pairs and combine them for a richer history
        major_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        all_trades = []
        tasks = [self.exchange.fetch_my_trades(s, limit=limit) for s in major_symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if not isinstance(result, Exception) and isinstance(result, list):
                all_trades.extend(result)
        
        # Sort by timestamp descending and take the limit
        all_trades.sort(key=lambda t: t.get('timestamp', 0), reverse=True)
        parsed_trades = [self._parse_trade(t) for t in all_trades[:limit] if t is not None]
        return parsed_trades

    async def fetch_positions(self, symbols: List[str] | None = None) -> List[Position]:
        """Spot accounts don't have positions; we return an empty list."""
        return []

    async def heartbeat(self) -> bool:
        """Checks if the Binance Testnet connection is alive."""
        # fetch_time is a lightweight way to check for connectivity and authentication
        await self.exchange.fetch_time()
        return True

    async def close(self):
        """Closes the exchange connection."""
        await self.exchange.close()
