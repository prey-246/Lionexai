"""Simulated execution adapter for paper trading and non-crypto assets.

Fills orders against the latest known price plus configurable slippage and
commission. Implements the full ExchangeAdapter interface so the autonomous
manager can treat simulated and real venues uniformly. Stays broker-ready: a real
adapter (Alpaca/IBKR) can be slotted in for non-crypto assets in a later milestone.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from .base import ExchangeAdapter, Order, Balance, Trade, Position

logger = logging.getLogger("nexa.exchange.simulated")


class SimulatedAdapter(ExchangeAdapter):
    venue = "SIMULATED"

    def __init__(self, api_key: str = "", secret_key: str = "",
                 slippage_pct: float = 0.1, commission_pct: float = 0.1):
        super().__init__(api_key, secret_key)
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct

    def _resolve_price(self, symbol: str, price: Optional[float]) -> float:
        if price is not None:
            return float(price)
        # Lazy import to avoid a hard dependency cycle at module import time.
        try:
            from app.core.database import SessionLocal
            from app.services import market_data_service
            db = SessionLocal()
            try:
                p = market_data_service.get_live_price_for_symbol(db, symbol)
                if p:
                    return float(p)
                last = market_data_service.latest_close(db, symbol)
                if last:
                    return float(last)
            finally:
                db.close()
        except Exception as e:  # pragma: no cover
            logger.warning("SimulatedAdapter price resolution failed for %s: %s", symbol, e)
        return 0.0

    async def connect(self) -> bool:
        return True

    async def heartbeat(self) -> bool:
        return True

    async def close(self):
        return None

    async def get_balance(self) -> Dict[str, Balance]:
        return {}

    async def place_market_order(self, symbol: str, side: Literal['buy', 'sell'],
                                 amount: float, price: Optional[float] = None) -> Order:
        ref_price = self._resolve_price(symbol, price)
        slip = self.slippage_pct / 100.0
        fill_price = ref_price * (1 + slip) if side == "buy" else ref_price * (1 - slip)
        cost = fill_price * amount
        fee = {"cost": round(cost * self.commission_pct / 100.0, 8), "currency": "USD"}
        now = datetime.now(timezone.utc)
        return Order(
            id=f"sim_{uuid.uuid4().hex[:16]}",
            symbol=symbol,
            type="market",
            side=side,
            price=round(fill_price, 8),
            amount=amount,
            cost=round(cost, 8),
            filled=amount,
            remaining=0.0,
            status="closed",
            timestamp=now,
            fee=fee,
        )

    async def place_limit_order(self, symbol: str, side: Literal['buy', 'sell'],
                                amount: float, price: float) -> Order:
        # Treat limit as immediately marketable in the simulator.
        return await self.place_market_order(symbol, side, amount, price=price)

    async def get_open_orders(self, symbol: str | None = None) -> List[Order]:
        return []

    async def get_order_status(self, order_id: str, symbol: str) -> Order:
        raise NotImplementedError("Simulated orders fill immediately; no status lookup.")

    async def cancel_order(self, order_id: str, symbol: str) -> Order:
        raise NotImplementedError("Simulated orders cannot be cancelled.")

    async def fetch_my_trades(self, symbol: str | None = None, limit: int = 20) -> List[Trade]:
        return []

    async def fetch_positions(self, symbols: List[str] | None = None) -> List[Position]:
        return []
