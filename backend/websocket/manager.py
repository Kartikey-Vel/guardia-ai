"""WebSocket connection manager — tracks active dashboard connections."""

import json
import logging
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages a list of active WebSocket connections.
    Provides broadcast helpers for alert and status messages.
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket connected — total clients: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            "WebSocket disconnected — total clients: %d",
            len(self.active_connections),
        )

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        """Send a JSON payload to every connected client."""
        message = json.dumps(payload)
        dead: List[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_alert(self, event_data: Dict[str, Any]) -> None:
        """Wrap event data in a typed envelope and broadcast."""
        await self.broadcast({"type": "ALERT", "payload": event_data})

    async def broadcast_status(self, status_data: Dict[str, Any]) -> None:
        """Broadcast a system status ping."""
        await self.broadcast({"type": "STATUS", "payload": status_data})

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()
