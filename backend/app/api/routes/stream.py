from fastapi import APIRouter, WebSocketException
from fastapi.websockets import WebSocket
from app.core.sockets import manager

router = APIRouter()

@router.websocket("/ws/market")
async def websocket_market_feed(websocket: WebSocket):
    await manager.connect(websocket, "market")
    try:
        while True:
            data = await websocket.receive_text()
    except Exception as e:
        manager.disconnect(websocket, "market")

@router.websocket("/ws/portfolio")
async def websocket_portfolio_updates(websocket: WebSocket):
    await manager.connect(websocket, "portfolio")
    try:
        while True:
            data = await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket, "portfolio")

@router.websocket("/ws/alerts")
async def websocket_risk_alerts(websocket: WebSocket):
    await manager.connect(websocket, "alerts")
    try:
        while True:
            data = await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket, "alerts")
