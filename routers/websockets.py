import logging
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("emr_ws")

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        logger.info(f"[WS BROADCAST] Sending message to {len(self.active_connections)} active connections: {message}")
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to websocket: {e}")
                self.disconnect(connection)

customer_notifier = ConnectionManager()
queue_notifier = customer_notifier

@router.websocket("/customer")
async def websocket_customer_endpoint(websocket: WebSocket):
    await customer_notifier.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        customer_notifier.disconnect(websocket)
