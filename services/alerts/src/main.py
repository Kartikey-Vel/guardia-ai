"""
Alerting Service for Guardia AI
Real-time event delivery via WebSocket and webhooks
"""

import asyncio
import logging
import os
from typing import Dict, Set
import zmq
import zmq.asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import yaml
import httpx
import redis.asyncio as redis
import json

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        self.active_connections -= disconnected


class AlertingService:
    """Main alerting service"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_subscriber = None
        self.redis_client: redis.Redis = None
        self.running = False
        self.alert_count = 0
        
        # Webhook configuration
        self.webhook_enabled = os.getenv("WEBHOOK_ENABLED", "false").lower() == "true"
        self.webhook_url = os.getenv("WEBHOOK_URL", "")
        
        # Alert filtering
        self.min_severity = os.getenv("MIN_ALERT_SEVERITY", "medium")
        self.severity_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    
    async def initialize(self):
        """Initialize service"""
        try:
            # Connect to FusionController events
            fusion_host = os.getenv("FUSION_CONTROLLER_HOST", "fusion-controller")
            fusion_port = os.getenv("FUSION_CONTROLLER_ZMQ_PORT", "5560")
            self.zmq_subscriber = self.zmq_context.socket(zmq.SUB)
            self.zmq_subscriber.connect(f"tcp://{fusion_host}:{fusion_port}")
            self.zmq_subscriber.setsockopt_string(zmq.SUBSCRIBE, "event")
            logger.info(f"Subscribed to FusionController at {fusion_host}:{fusion_port}")
            
            # Connect to Redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = await redis.from_url(redis_url)
            logger.info(f"Connected to Redis")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    def should_alert(self, event: Dict) -> bool:
        """Determine if event should trigger alert"""
        severity = event.get("severity", "low")
        min_level = self.severity_levels.get(self.min_severity, 1)
        event_level = self.severity_levels.get(severity, 0)
        
        return event_level >= min_level
    
    async def send_webhook(self, event: Dict):
        """Send webhook notification"""
        if not self.webhook_enabled or not self.webhook_url:
            return
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    json=event,
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Webhook sent for event {event.get('event_id')}")
                else:
                    logger.warning(f"Webhook failed: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Webhook error: {e}")
    
    async def process_events(self):
        """Process events from FusionController"""
        self.running = True
        logger.info("Starting event processing loop")
        
        while self.running:
            try:
                message = await self.zmq_subscriber.recv_multipart()
                
                if len(message) != 2:
                    continue
                
                topic, event_bytes = message
                event = yaml.safe_load(event_bytes.decode('utf-8'))
                
                # Check if should alert
                if not self.should_alert(event):
                    logger.debug(f"Event {event.get('event_id')} below alert threshold")
                    continue
                
                # Create alert message
                alert = {
                    "type": "alert",
                    "event": event,
                    "timestamp": event.get("timestamp"),
                    "severity": event.get("severity"),
                    "camera_id": event.get("camera_id")
                }
                
                # Broadcast via WebSocket
                await self.connection_manager.broadcast(alert)
                
                # Send webhook
                if self.webhook_enabled:
                    await self.send_webhook(event)
                
                # Store in Redis for recent alerts
                await self.redis_client.lpush(
                    "recent_alerts",
                    json.dumps(alert)
                )
                await self.redis_client.ltrim("recent_alerts", 0, 99)  # Keep last 100
                
                self.alert_count += 1
                logger.info(f"Alert sent: {event.get('event_class')} ({event.get('severity')})")
                
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                await asyncio.sleep(0.1)
    
    async def stop(self):
        """Stop service"""
        self.running = False
        if self.zmq_subscriber:
            self.zmq_subscriber.close()
        self.zmq_context.term()
        if self.redis_client:
            await self.redis_client.close()


# FastAPI application
app = FastAPI(title="Guardia Alerting Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = AlertingService()


@app.on_event("startup")
async def startup_event():
    await service.initialize()
    asyncio.create_task(service.process_events())


@app.on_event("shutdown")
async def shutdown_event():
    await service.stop()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "alerts"}


@app.get("/status")
async def get_status():
    return {
        "service": "alerts",
        "running": service.running,
        "alert_count": service.alert_count,
        "active_connections": len(service.connection_manager.active_connections),
        "webhook_enabled": service.webhook_enabled
    }


@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts"""
    await service.connection_manager.connect(websocket)
    
    try:
        # Keep connection alive
        while True:
            # Receive any messages from client (e.g., ping)
            data = await websocket.receive_text()
            
            # Echo back or ignore
            if data == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        service.connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        service.connection_manager.disconnect(websocket)


@app.get("/alerts/recent")
async def get_recent_alerts():
    """Get recent alerts from Redis"""
    try:
        alerts_json = await service.redis_client.lrange("recent_alerts", 0, 19)
        alerts = [json.loads(a) for a in alerts_json]
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Error fetching recent alerts: {e}")
        return {"alerts": []}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8007"))
    uvicorn.run(app, host="0.0.0.0", port=port)
