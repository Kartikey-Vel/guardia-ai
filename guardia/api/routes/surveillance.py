"""
Surveillance API routes for Guardia AI Enhanced System

This module provides endpoints for surveillance operations including:
- Starting/stopping surveillance sessions
- Real-time camera feeds and WebSocket connections
- Live detection monitoring
- Session management and status
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
import asyncio
import json
import cv2
import logging

from ...models.schemas import (
    SurveillanceSession,
    SurveillanceSessionCreate,
    SurveillanceSessionUpdate,
    DetectionEvent,
    CameraStatus,
    AlertCreate
)
from ...services.surveillance_service import SurveillanceService
from ...services.user_service import UserService
from ...core.camera_manager import MultiCameraManager
from ...db.connection import get_database
from ..dependencies import get_current_user, get_surveillance_service

router = APIRouter(prefix="/surveillance", tags=["surveillance"])
logger = logging.getLogger(__name__)

# WebSocket connection manager for real-time updates
class ConnectionManager:
    """Manages WebSocket connections for real-time surveillance updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and register user"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: str, user_id: str):
        """Send message to specific user's connections"""
        if user_id in self.user_connections:
            disconnected = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn, user_id)
    
    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

# Global connection manager instance
manager = ConnectionManager()

@router.post("/sessions", response_model=SurveillanceSession)
async def start_surveillance_session(
    session_data: SurveillanceSessionCreate,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """
    Start a new surveillance session
    
    - Creates a new surveillance session for the current user
    - Initializes cameras and detection systems
    - Returns session details including session ID
    """
    try:
        session = await surveillance_service.start_session(
            user_id=current_user["user_id"],
            session_data=session_data
        )
        
        logger.info(f"Started surveillance session {session.session_id} for user {current_user['user_id']}")
        
        # Notify connected WebSocket clients
        await manager.send_personal_message(
            json.dumps({
                "type": "session_started",
                "session_id": session.session_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            current_user["user_id"]
        )
        
        return session
        
    except Exception as e:
        logger.error(f"Failed to start surveillance session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start surveillance session: {str(e)}"
        )

@router.get("/sessions", response_model=List[SurveillanceSession])
async def get_surveillance_sessions(
    active_only: bool = False,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """
    Get surveillance sessions for the current user
    
    - Returns list of sessions (active or all)
    - Supports pagination with limit parameter
    - Includes session status and statistics
    """
    try:
        sessions = await surveillance_service.get_user_sessions(
            user_id=current_user["user_id"],
            active_only=active_only,
            limit=limit
        )
        
        return sessions
        
    except Exception as e:
        logger.error(f"Failed to get surveillance sessions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get surveillance sessions: {str(e)}"
        )

@router.get("/sessions/{session_id}", response_model=SurveillanceSession)
async def get_surveillance_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """Get specific surveillance session details"""
    try:
        session = await surveillance_service.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surveillance session not found"
            )
        
        # Verify user owns this session
        if session.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this surveillance session"
            )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get surveillance session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get surveillance session: {str(e)}"
        )

@router.put("/sessions/{session_id}", response_model=SurveillanceSession)
async def update_surveillance_session(
    session_id: str,
    update_data: SurveillanceSessionUpdate,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """Update surveillance session configuration"""
    try:
        session = await surveillance_service.update_session(
            session_id=session_id,
            user_id=current_user["user_id"],
            update_data=update_data
        )
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surveillance session not found"
            )
        
        # Notify connected WebSocket clients
        await manager.send_personal_message(
            json.dumps({
                "type": "session_updated",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            current_user["user_id"]
        )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update surveillance session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update surveillance session: {str(e)}"
        )

@router.delete("/sessions/{session_id}")
async def stop_surveillance_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """Stop and cleanup surveillance session"""
    try:
        success = await surveillance_service.stop_session(
            session_id=session_id,
            user_id=current_user["user_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surveillance session not found or already stopped"
            )
        
        logger.info(f"Stopped surveillance session {session_id} for user {current_user['user_id']}")
        
        # Notify connected WebSocket clients
        await manager.send_personal_message(
            json.dumps({
                "type": "session_stopped",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }),
            current_user["user_id"]
        )
        
        return {"message": "Surveillance session stopped successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to stop surveillance session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop surveillance session: {str(e)}"
        )

@router.get("/cameras/status", response_model=List[CameraStatus])
async def get_camera_status(
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """Get status of all configured cameras"""
    try:
        camera_statuses = await surveillance_service.get_camera_status(
            user_id=current_user["user_id"]
        )
        
        return camera_statuses
        
    except Exception as e:
        logger.error(f"Failed to get camera status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get camera status: {str(e)}"
        )

@router.get("/cameras/{camera_id}/stream")
async def get_camera_stream(
    camera_id: str,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """Get live camera stream for specific camera"""
    try:
        # Verify user has access to this camera
        has_access = await surveillance_service.verify_camera_access(
            user_id=current_user["user_id"],
            camera_id=camera_id
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this camera"
            )
        
        async def generate_stream():
            """Generate video stream frames"""
            try:
                async for frame in surveillance_service.get_camera_stream(camera_id):
                    # Encode frame as JPEG
                    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    frame_bytes = buffer.tobytes()
                    
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                    )
                    
                    # Small delay to control frame rate
                    await asyncio.sleep(0.033)  # ~30 FPS
                    
            except Exception as e:
                logger.error(f"Stream generation error: {str(e)}")
                yield b'--frame\r\n\r\n'
        
        return StreamingResponse(
            generate_stream(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get camera stream: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get camera stream: {str(e)}"
        )

@router.get("/detections/recent", response_model=List[DetectionEvent])
async def get_recent_detections(
    limit: int = 20,
    camera_id: Optional[str] = None,
    detection_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """Get recent detection events"""
    try:
        detections = await surveillance_service.get_recent_detections(
            user_id=current_user["user_id"],
            limit=limit,
            camera_id=camera_id,
            detection_type=detection_type
        )
        
        return detections
        
    except Exception as e:
        logger.error(f"Failed to get recent detections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent detections: {str(e)}"
        )

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time surveillance updates
    
    Provides real-time updates for:
    - New detection events
    - Alert notifications
    - Session status changes
    - Camera status updates
    """
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Parse and handle client messages if needed
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {str(e)}")
        manager.disconnect(websocket, user_id)

# Function to send real-time updates (called by surveillance service)
async def send_detection_update(user_id: str, detection_event: DetectionEvent):
    """Send detection event to user's WebSocket connections"""
    message = {
        "type": "detection_event",
        "data": detection_event.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_personal_message(json.dumps(message), user_id)

async def send_alert_notification(user_id: str, alert: AlertCreate):
    """Send alert notification to user's WebSocket connections"""
    message = {
        "type": "alert_notification",
        "data": alert.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_personal_message(json.dumps(message), user_id)

async def send_camera_status_update(user_id: str, camera_status: CameraStatus):
    """Send camera status update to user's WebSocket connections"""
    message = {
        "type": "camera_status_update",
        "data": camera_status.dict(),
        "timestamp": datetime.utcnow().isoformat()
    }
    await manager.send_personal_message(json.dumps(message), user_id)
