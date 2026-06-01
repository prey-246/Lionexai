from fastapi import APIRouter, WebSocketException
from fastapi.websockets import WebSocket
from app.core.sockets import manager

router = APIRouter()

@router.websocket("/ws/market")
async def websocket_market_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast({"type": "MARKET_SUBSCRIBE", "data": data})
    except Exception as e:
        manager.disconnect(websocket)

@router.websocket("/ws/portfolio")
async def websocket_portfolio_updates(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast({"type": "PORTFOLIO_UPDATE", "data": data})
    except Exception:
        manager.disconnect(websocket)

@router.websocket("/ws/alerts")
async def websocket_risk_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast({"type": "RISK_ALERT", "data": data})
    except Exception:
        manager.disconnect(websocket)
