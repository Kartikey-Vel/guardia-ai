from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
from src.api.tweety_auth import get_current_user, get_password_hash
from src.utils.tasmanian_logger import setup_logger
from src.config.yosemite_config import settings

router = APIRouter()
logger = setup_logger(__name__)

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        # Store client connections with their authorization info
        self.active_connections: List[WebSocket] = []
        self.client_info: Dict[WebSocket, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a new client and store its information."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_info[websocket] = {"client_id": client_id, "connected_at": datetime.now()}
        logger.info(f"WebSocket client connected: {client_id}")
        
    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected client."""
        if websocket in self.active_connections:
            client_id = self.client_info[websocket]["client_id"] if websocket in self.client_info else "unknown"
            self.active_connections.remove(websocket)
            if websocket in self.client_info:
                del self.client_info[websocket]
            logger.info(f"WebSocket client disconnected: {client_id}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            logger.warning("No active WebSocket connections for broadcast")
            return
            
        # Convert message to JSON string
        json_message = json.dumps(message)
        
        # Send to all connected clients
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json_message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.append(websocket)
        
        # Clean up any disconnected clients
        for websocket in disconnected:
            self.disconnect(websocket)
            
        if len(self.active_connections) > 0:
            logger.info(f"Broadcast message sent to {len(self.active_connections)} clients")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

# Create a connection manager instance
manager = ConnectionManager()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time security alerts."""
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            # Process incoming message (could be acknowledgments or commands)
            try:
                message = json.loads(data)
                logger.info(f"Received message from client {client_id}: {message}")
                
                # Send acknowledgment back to the client
                await manager.send_personal_message(
                    {"type": "ack", "message": "Message received", "timestamp": datetime.now().isoformat()},
                    websocket
                )
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON format"},
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def broadcast_security_alert(event: Dict[str, Any]):
    """
    Broadcast a security alert to all connected clients.
    This function is meant to be called from other parts of the application.
    """
    # Add message type and timestamp if not present
    if "type" not in event:
        event["type"] = "security_alert"
    if "broadcast_time" not in event:
        event["broadcast_time"] = datetime.now().isoformat()
    
    await manager.broadcast(event)
    return {"status": "broadcast_sent", "recipients": len(manager.active_connections)}
