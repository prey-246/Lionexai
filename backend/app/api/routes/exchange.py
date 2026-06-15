import os
import random
import time
import asyncio
from datetime import datetime
from typing import List, Dict

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user, require_role
from app.exchange import get_exchange_adapter
from app.exchange.base import Balance, Order, Trade, Position
from app.models import domain

logger = logging.getLogger(__name__)


class ExchangeStatusResponse(BaseModel):
    exchange_id: str
    status: str
    balance: Dict[str, Balance]
    open_orders: List[Order]
    trade_history: List[Trade]
    positions: List[Position]
    api_latency_ms: float
    trade_count: int
    success_rate_pct: float


class HeartbeatResponse(BaseModel):
    exchange_id: str
    status: str
    connected: bool
    latency_ms: float
    timestamp: datetime


router = APIRouter()


@router.get(
    "/{exchange_id}/status",
    response_model=ExchangeStatusResponse,
    dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))],
)
async def get_exchange_status(
    exchange_id: str, current_user: domain.User = Depends(get_current_user)
):
    api_key = os.environ.get(f"{exchange_id.upper()}_API_KEY")
    secret_key = os.environ.get(f"{exchange_id.upper()}_SECRET_KEY")

    if not api_key or "YOUR_" in api_key:
        raise HTTPException(
            status_code=404, detail=f"API keys for {exchange_id} not configured on server."
        )

    adapter = None
    try:
        start_time = time.time()
        adapter = get_exchange_adapter(exchange_id, api_key, secret_key)

        balance, open_orders, trades, positions = await asyncio.gather(
            adapter.get_balance(),
            adapter.get_open_orders(),
            adapter.fetch_my_trades(limit=25),
            adapter.fetch_positions(),
        )
        latency = (time.time() - start_time) * 1000

        return ExchangeStatusResponse(
            exchange_id=exchange_id,
            status="OPERATIONAL",
            balance=balance,
            open_orders=open_orders,
            trade_history=trades,
            positions=positions,
            api_latency_ms=latency,
            trade_count=len(trades),
            success_rate_pct=round(random.uniform(55.0, 75.0), 2),  # Mocked for UI
        )
    except Exception as e:
        logger.error(f"Failed to connect to {exchange_id}: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to {exchange_id}: {str(e)}")
    finally:
        if adapter:
            await adapter.close()


class CancelOrderRequest(BaseModel):
    symbol: str


@router.delete(
    "/{exchange_id}/orders/{order_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))],
)
async def cancel_exchange_order(
    exchange_id: str,
    order_id: str,
    body: CancelOrderRequest,
    current_user: domain.User = Depends(get_current_user),
):
    api_key = os.environ.get(f"{exchange_id.upper()}_API_KEY")
    secret_key = os.environ.get(f"{exchange_id.upper()}_SECRET_KEY")
    if not api_key or "YOUR_" in api_key:
        raise HTTPException(status_code=404, detail=f"API keys for {exchange_id} not configured.")

    adapter = get_exchange_adapter(exchange_id, api_key, secret_key)
    try:
        cancelled_order = await adapter.cancel_order(order_id, body.symbol)
        return {"status": "success", "order": cancelled_order}
    finally:
        await adapter.close()


@router.get(
    "/{exchange_id}/heartbeat",
    response_model=HeartbeatResponse,
    dependencies=[Depends(require_role(["admin", "operator", "risk_manager"]))],
)
async def check_exchange_heartbeat(exchange_id: str):
    api_key = os.environ.get(f"{exchange_id.upper()}_API_KEY")
    secret_key = os.environ.get(f"{exchange_id.upper()}_SECRET_KEY")
    if not api_key or "YOUR_" in api_key:
        raise HTTPException(status_code=404, detail=f"API keys for {exchange_id} not configured.")

    adapter = None
    start = time.time()
    try:
        adapter = get_exchange_adapter(exchange_id, api_key, secret_key)
        is_alive = await adapter.heartbeat()
        if not is_alive:
            raise HTTPException(status_code=503, detail="Heartbeat check failed.")
        return HeartbeatResponse(
            exchange_id=exchange_id,
            status="connected",
            connected=True,
            latency_ms=round((time.time() - start) * 1000, 2),
            timestamp=datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Heartbeat failed: {e}")
    finally:
        if adapter:
            await adapter.close()
