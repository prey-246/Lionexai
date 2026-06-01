from fastapi import WebSocket
from typing import List, Dict
import json

class ConnectionManager:
    def __init__(self):
        self.channels: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.channels:
            self.channels[channel] = []
        self.channels[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.channels and websocket in self.channels[channel]:
            self.channels[channel].remove(websocket)

    async def broadcast(self, message: dict, channel: str):
        if channel in self.channels:
            payload = json.dumps(message)
            for connection in list(self.channels[channel]):
                try:
                    await connection.send_text(payload)
                except Exception:
                    self.disconnect(connection, channel)

manager = ConnectionManager()