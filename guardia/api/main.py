"""
FastAPI Application - Main API Server
Modern async web API with comprehensive surveillance endpoints
"""
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    # FastAPI not available, create placeholder classes for development
    FASTAPI_AVAILABLE = False
    class FastAPI:
        def __init__(self, **kwargs): 
            self.title = kwargs.get("title", "API")
            self.description = kwargs.get("description", "")
            self.version = kwargs.get("version", "1.0.0")
        def add_middleware(self, *args, **kwargs): pass
        def include_router(self, *args, **kwargs): pass
    
    class CORSMiddleware: pass
    class HTTPBearer: pass
    class HTTPException(Exception): pass
    class WebSocket: pass
    class WebSocketDisconnect(Exception): pass

from ..config.settings import get_settings
from ..db.connection import startup_event, shutdown_event
from ..models.schemas import APIResponse

logger = logging.getLogger(__name__)
settings = get_settings()

# Import route modules conditionally
try:
    from .routes import auth, users
    AUTH_ROUTES_AVAILABLE = True
except ImportError:
    logger.warning("Auth and Users routes not available")
    AUTH_ROUTES_AVAILABLE = False

try:
    from .routes import surveillance
    SURVEILLANCE_ROUTES_AVAILABLE = True
except ImportError:
    logger.warning("Surveillance routes not available")
    SURVEILLANCE_ROUTES_AVAILABLE = False

try:
    from .routes import alerts
    ALERTS_ROUTES_AVAILABLE = True
except ImportError:
    logger.warning("Alerts routes not available")
    ALERTS_ROUTES_AVAILABLE = False

try:
    from .routes import system
    SYSTEM_ROUTES_AVAILABLE = True
except ImportError:
    logger.warning("System routes not available")
    SYSTEM_ROUTES_AVAILABLE = False

# Import surveillance service conditionally
try:
    from ..services.surveillance_service import SurveillanceService
    surveillance_service = None  # Will be initialized in lifespan
    SURVEILLANCE_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("Surveillance service not available")
    SURVEILLANCE_SERVICE_AVAILABLE = False

# Security
if FASTAPI_AVAILABLE:
    security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global surveillance_service
    try:
        # Startup
        await startup_event()
        if SURVEILLANCE_SERVICE_AVAILABLE:
            from ..db.repository import Repository
            from ..db.connection import get_database
            db = await get_database()
            repository = Repository(db)
            surveillance_service = SurveillanceService(repository)
            await surveillance_service.initialize()
        logger.info("Application startup completed")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        yield
    finally:
        # Shutdown
        try:
            if surveillance_service:
                await surveillance_service.cleanup()
            await shutdown_event()
            logger.info("Application shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Create FastAPI app
app = FastAPI(
    title="Guardia AI Enhanced",
    description="Modern AI-powered surveillance system with advanced detection capabilities",
    version="2.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan if FASTAPI_AVAILABLE else None
)

# CORS middleware
if FASTAPI_AVAILABLE:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers conditionally
if AUTH_ROUTES_AVAILABLE:
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

if SURVEILLANCE_ROUTES_AVAILABLE:
    app.include_router(surveillance.router, prefix="/api/v1/surveillance", tags=["Surveillance"])

if ALERTS_ROUTES_AVAILABLE:
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])

if SYSTEM_ROUTES_AVAILABLE:
    app.include_router(system.router, prefix="/api/v1/system", tags=["System"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        if FASTAPI_AVAILABLE:
            await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    if FASTAPI_AVAILABLE:
                        await connection.send_json(message)
                except:
                    # Remove stale connections
                    self.disconnect(connection, user_id)

    async def broadcast(self, message: dict):
        for connection in self.active_connections[:]:  # Copy list to avoid modification during iteration
            try:
                if FASTAPI_AVAILABLE:
                    await connection.send_json(message)
            except:
                # Remove stale connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return APIResponse(
        success=True,
        message="Guardia AI Enhanced API",
        data={
            "version": "2.0.0",
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "features": {
                "fastapi_available": FASTAPI_AVAILABLE,
                "auth_routes": AUTH_ROUTES_AVAILABLE,
                "surveillance_routes": SURVEILLANCE_ROUTES_AVAILABLE,
                "alerts_routes": ALERTS_ROUTES_AVAILABLE,
                "system_routes": SYSTEM_ROUTES_AVAILABLE,
                "surveillance_service": SURVEILLANCE_SERVICE_AVAILABLE
            }
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0",
            "components": {
                "api": "ok",
                "database": "unknown",  # Would check database connection
                "surveillance": "unknown"  # Would check surveillance service
            }
        }
        
        # Check database connection if available
        try:
            from ..db.connection import get_database_status
            db_status = await get_database_status()
            health_data["components"]["database"] = "ok" if db_status.get("connected") else "error"
        except Exception:
            health_data["components"]["database"] = "error"
        
        # Check surveillance service if available
        if surveillance_service:
            try:
                health_data["components"]["surveillance"] = "ok"
            except Exception:
                health_data["components"]["surveillance"] = "error"
        
        return health_data
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        if FASTAPI_AVAILABLE:
            raise HTTPException(status_code=500, detail="Health check failed")
        return {"status": "error", "message": str(e)}

# WebSocket endpoint for real-time updates
if FASTAPI_AVAILABLE:
    @app.websocket("/ws/{user_id}")
    async def websocket_endpoint(websocket: WebSocket, user_id: str):
        """WebSocket endpoint for real-time updates"""
        await manager.connect(websocket, user_id)
        try:
            while True:
                data = await websocket.receive_text()
                # Echo back for testing
                await websocket.send_text(f"Message received: {data}")
        except WebSocketDisconnect:
            manager.disconnect(websocket, user_id)

# Error handlers
if FASTAPI_AVAILABLE:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content=APIResponse(
                success=False,
                message=exc.detail,
                data=None
            ).dict()
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc: Exception):
        """Handle general exceptions"""
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                success=False,
                message="Internal server error",
                data=None
            ).dict()
        )

# Detection callback for real-time updates
async def detection_callback(detection_data: dict):
    """Callback for real-time detection updates"""
    try:
        user_id = detection_data.get("user_id")
        if user_id:
            message = {
                "type": "detection",
                "data": detection_data,
                "timestamp": datetime.utcnow().isoformat()
            }
            await manager.send_personal_message(message, user_id)
    except Exception as e:
        logger.error(f"Error in detection callback: {e}")

# Register callback with surveillance service if available
if SURVEILLANCE_SERVICE_AVAILABLE and surveillance_service:
    try:
        # This would be called after service initialization
        pass  # surveillance_service.add_detection_callback(detection_callback)
    except Exception as e:
        logger.error(f"Error registering detection callback: {e}")

def create_app():
    """Factory function to create the FastAPI app"""
    return app

if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        uvicorn.run(
            "main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.debug,
            log_level="info"
        )
    else:
        logger.error("FastAPI not available. Please install the required dependencies.")
        print("FastAPI not available. Please install requirements_enhanced.txt")

manager = ConnectionManager()

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return APIResponse(
        success=True,
        message="Guardia AI Enhanced API",
        data={
            "version": "2.0.0",
            "status": "active",
            "timestamp": datetime.utcnow().isoformat(),
            "docs": "/docs" if settings.debug else "disabled",
            "features": [
                "Advanced Face Recognition",
                "YOLO Object Detection", 
                "Real-time Surveillance",
                "Smart Alerts",
                "Multi-camera Support",
                "Cloud Integration"
            ]
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        from ..db.connection import db_manager
        
        # Check database connection
        db_health = await db_manager.health_check()
        
        # Check surveillance service
        surveillance_stats = await surveillance_service.get_system_statistics()
        
        # Overall health status
        is_healthy = (
            db_health.get("status") == "healthy" and
            surveillance_stats.get("system", {}).get("is_processing") is not None
        )
        
        return APIResponse(
            success=is_healthy,
            message="System healthy" if is_healthy else "System has issues",
            data={
                "status": "healthy" if is_healthy else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": db_health,
                "surveillance": surveillance_stats.get("system", {}),
                "version": "2.0.0"
            }
        )
        
    except Exception as e:
        return APIResponse(
            success=False,
            message="Health check failed",
            errors=[str(e)]
        )

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time notifications and updates"""
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to Guardia AI Enhanced",
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages
                data = await websocket.receive_json()
                
                # Handle different message types
                message_type = data.get("type")
                
                if message_type == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                elif message_type == "subscribe":
                    # Handle subscription to specific events
                    await websocket.send_json({
                        "type": "subscribed",
                        "events": data.get("events", []),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, user_id)

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            message=exc.detail,
            errors=[exc.detail]
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global general exception handler"""
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            message="Internal server error",
            errors=[str(exc) if settings.debug else "An unexpected error occurred"]
        ).dict()
    )

# Startup message
@app.on_event("startup")
async def startup_message():
    """Print startup message"""
    print("🛡️" + "="*60)
    print("🛡️  GUARDIA AI ENHANCED - SURVEILLANCE SYSTEM")
    print("🛡️" + "="*60)
    print(f"🛡️  Version: 2.0.0")
    print(f"🛡️  Environment: {settings.environment}")
    print(f"🛡️  Debug Mode: {settings.debug}")
    print(f"🛡️  API Host: {settings.api_host}:{settings.api_port}")
    print(f"🛡️  Database: {settings.mongodb_database}")
    print("🛡️" + "="*60)
    print("🛡️  Features:")
    print("🛡️  ✅ Advanced Face Recognition")
    print("🛡️  ✅ YOLO Object Detection")
    print("🛡️  ✅ Real-time Surveillance")
    print("🛡️  ✅ Smart Alert System")
    print("🛡️  ✅ Multi-camera Support")
    print("🛡️  ✅ WebSocket Real-time Updates")
    print("🛡️  ✅ RESTful API")
    print("🛡️" + "="*60)

# Add surveillance detection callback for real-time updates
async def detection_callback(surveillance_frame, detections):
    """Callback for broadcasting detection results via WebSocket"""
    try:
        # Find user for this frame's camera
        user_id = None
        for session in surveillance_service.active_sessions.values():
            if surveillance_frame.camera_id in session.camera_id:
                user_id = str(session.user_id)
                break
        
        if user_id and detections:
            # Broadcast detection update
            message = {
                "type": "detection",
                "camera_id": surveillance_frame.camera_id,
                "timestamp": surveillance_frame.timestamp.isoformat(),
                "detections": [
                    {
                        "type": det.detection_type,
                        "confidence": det.confidence,
                        "person_name": det.person_name,
                        "bounding_box": det.bounding_box.dict()
                    }
                    for det in detections
                ]
            }
            
            await manager.send_personal_message(message, user_id)
            
    except Exception as e:
        print(f"Detection callback error: {e}")

# Register detection callback
surveillance_service.add_detection_callback(detection_callback)

# Run server function
def run_server():
    """Run the FastAPI server"""
    uvicorn.run(
        "guardia.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload and settings.debug,
        log_level="info" if settings.debug else "warning"
    )

if __name__ == "__main__":
    run_server()
