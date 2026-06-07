from collections import defaultdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[session_id].add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(session_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(session_id, None)

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        connections = self._connections.get(session_id, set())
        for websocket in list(connections):
            try:
                await websocket.send_json(message)
            except (WebSocketDisconnect, RuntimeError, OSError):
                self.disconnect(session_id, websocket)
