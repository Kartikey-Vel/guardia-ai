"""
Surveillance Service - Main orchestrator for surveillance operations
Coordinates all AI detection and monitoring activities
"""
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import time
from loguru import logger
import json
from pathlib import Path

from ..core.camera_manager import EnhancedCameraManager, MultiCameraManager
from ..core.face_detector import EnhancedFaceDetector
from ..core.object_detector import EnhancedObjectDetector
from ..models.schemas import (
    SurveillanceSession, SurveillanceSessionCreate, DetectionResult,
    DetectionType, SurveillanceFrame, AlertCreate
)
from ..db.repository import BaseRepository
from .user_service import UserService
from .alert_service import AlertService
from ..config.settings import settings

class SurveillanceSessionRepository(BaseRepository[SurveillanceSession]):
    """Repository for surveillance session operations"""
    
    def __init__(self):
        super().__init__("surveillance_sessions", SurveillanceSession)
    
    async def get_active_sessions(self) -> List[SurveillanceSession]:
        """Get all active surveillance sessions"""
        return await self.find_many({"is_active": True})
    
    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[SurveillanceSession]:
        """Get surveillance sessions for a user"""
        return await self.find_many(
            {"user_id": user_id}, 
            limit=limit, 
            sort_by="start_time", 
            sort_order=-1
        )
    
    async def end_session(self, session_id: str):
        """End a surveillance session"""
        await self.update(session_id, {
            "end_time": datetime.utcnow(),
            "is_active": False
        })

class SurveillanceFrameRepository(BaseRepository[SurveillanceFrame]):
    """Repository for surveillance frame operations"""
    
    def __init__(self):
        super().__init__("surveillance_frames", SurveillanceFrame)
    
    async def get_session_frames(self, session_id: str, limit: int = 100) -> List[SurveillanceFrame]:
        """Get frames for a surveillance session"""
        return await self.find_many(
            {"session_id": session_id},
            limit=limit,
            sort_by="timestamp",
            sort_order=-1
        )
    
    async def get_unprocessed_frames(self, limit: int = 50) -> List[SurveillanceFrame]:
        """Get unprocessed frames"""
        return await self.find_many(
            {"processed": False},
            limit=limit,
            sort_by="timestamp"
        )

class SurveillanceService:
    """Main surveillance service orchestrating all detection activities"""
    
    def __init__(self):
        # Repositories
        self.session_repo = SurveillanceSessionRepository()
        self.frame_repo = SurveillanceFrameRepository()
        
        # Services
        self.user_service = UserService()
        self.alert_service = AlertService()
        
        # AI Components
        self.camera_manager: Optional[MultiCameraManager] = None
        self.face_detector: Optional[EnhancedFaceDetector] = None
        self.object_detector: Optional[EnhancedObjectDetector] = None
        
        # Session management
        self.active_sessions: Dict[str, SurveillanceSession] = {}
        self.detection_callbacks: List[Callable] = []
        
        # Processing control
        self.is_processing = False
        self.processing_task: Optional[asyncio.Task] = None
        self.frame_processing_queue = asyncio.Queue(maxsize=100)
        
        # Performance tracking
        self.frames_processed = 0
        self.detections_made = 0
        self.alerts_generated = 0
        self.start_time = None
    
    async def initialize(self):
        """Initialize surveillance service"""
        try:
            logger.info("🔄 Initializing surveillance service...")
            
            # Initialize AI components
            self.face_detector = EnhancedFaceDetector()
            self.object_detector = EnhancedObjectDetector()
            self.camera_manager = MultiCameraManager()
            
            # Wait for models to load
            await asyncio.sleep(2)
            
            logger.info("✅ Surveillance service initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize surveillance service: {e}")
            raise
    
    async def start_surveillance_session(self, user_id: str, camera_configs: List[Dict[str, Any]], 
                                       session_name: Optional[str] = None) -> SurveillanceSession:
        """Start a new surveillance session"""
        try:
            logger.info(f"🎬 Starting surveillance session for user {user_id}")
            
            # Load known faces for the user
            known_faces = await self.user_service.get_all_known_faces(user_id)
            await self.face_detector.load_known_faces(known_faces)
            
            # Initialize cameras
            for camera_config in camera_configs:
                camera_id = camera_config.get("camera_id", "default")
                camera_index = camera_config.get("camera_index", 0)
                
                success = await self.camera_manager.add_camera(camera_id, camera_index)
                if not success:
                    logger.warning(f"Failed to initialize camera {camera_id}")
            
            # Create surveillance session
            session_data = SurveillanceSessionCreate(
                user_id=user_id,
                name=session_name or f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                camera_id=",".join([c.get("camera_id", "default") for c in camera_configs]),
                settings={
                    "cameras": camera_configs,
                    "detection_enabled": True,
                    "recording_enabled": True
                }
            )
            
            session = SurveillanceSession(**session_data.dict())
            created_session = await self.session_repo.create(session)
            
            # Store active session
            self.active_sessions[str(created_session.id)] = created_session
            
            # Start processing if not already running
            if not self.is_processing:
                await self.start_processing()
            
            logger.info(f"✅ Surveillance session started: {created_session.id}")
            return created_session
            
        except Exception as e:
            logger.error(f"❌ Failed to start surveillance session: {e}")
            raise
    
    async def stop_surveillance_session(self, session_id: str) -> bool:
        """Stop a surveillance session"""
        try:
            if session_id in self.active_sessions:
                # End session in database
                await self.session_repo.end_session(session_id)
                
                # Remove from active sessions
                del self.active_sessions[session_id]
                
                # Stop processing if no active sessions
                if not self.active_sessions and self.is_processing:
                    await self.stop_processing()
                
                logger.info(f"✅ Surveillance session stopped: {session_id}")
                return True
            else:
                logger.warning(f"Session not found: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to stop surveillance session: {e}")
            return False
    
    async def start_processing(self):
        """Start the main processing loop"""
        if self.is_processing:
            logger.warning("Processing already active")
            return
        
        self.is_processing = True
        self.start_time = time.time()
        
        # Start frame processing task
        self.processing_task = asyncio.create_task(self._processing_loop())
        
        # Set up camera frame callbacks
        for camera_id, camera in self.camera_manager.cameras.items():
            camera.add_frame_callback(self._on_frame_captured)
        
        logger.info("🎯 Started surveillance processing")
    
    async def stop_processing(self):
        """Stop the main processing loop"""
        if not self.is_processing:
            return
        
        self.is_processing = False
        
        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        # Stop all cameras
        if self.camera_manager:
            await self.camera_manager.cleanup()
        
        logger.info("⏹️ Stopped surveillance processing")
    
    def _on_frame_captured(self, frame, camera_id: str):
        """Callback when a frame is captured"""
        try:
            # Add frame to processing queue (non-blocking)
            frame_data = {
                "frame": frame,
                "camera_id": camera_id,
                "timestamp": datetime.utcnow()
            }
            
            try:
                self.frame_processing_queue.put_nowait(frame_data)
            except asyncio.QueueFull:
                # Drop oldest frame if queue is full
                try:
                    self.frame_processing_queue.get_nowait()
                    self.frame_processing_queue.put_nowait(frame_data)
                except asyncio.QueueEmpty:
                    pass
                
        except Exception as e:
            logger.error(f"Frame callback error: {e}")
    
    async def _processing_loop(self):
        """Main processing loop"""
        logger.info("🔄 Processing loop started")
        
        try:
            while self.is_processing:
                try:
                    # Get frame from queue with timeout
                    frame_data = await asyncio.wait_for(
                        self.frame_processing_queue.get(), 
                        timeout=1.0
                    )
                    
                    # Process frame
                    await self._process_frame(frame_data)
                    
                    # Control processing rate
                    await asyncio.sleep(settings.frame_processing_interval)
                    
                except asyncio.TimeoutError:
                    # No frames to process, continue
                    continue
                except Exception as e:
                    logger.error(f"Processing loop error: {e}")
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            logger.info("Processing loop cancelled")
        except Exception as e:
            logger.error(f"Processing loop failed: {e}")
    
    async def _process_frame(self, frame_data: Dict[str, Any]):
        """Process a single frame"""
        try:
            frame = frame_data["frame"]
            camera_id = frame_data["camera_id"]
            timestamp = frame_data["timestamp"]
            
            self.frames_processed += 1
            
            # Create surveillance frame record
            surveillance_frame = SurveillanceFrame(
                camera_id=camera_id,
                timestamp=timestamp
            )
            
            # Detect objects/persons first
            object_detections = await self.object_detector.detect_objects(frame)
            
            # If persons detected, perform face recognition
            face_detections = []
            if object_detections:
                # Extract face regions from person detections
                face_locations = [det.bounding_box for det in object_detections]
                face_detections = await self.face_detector.recognize_faces(frame, face_locations)
            
            # Combine detections
            all_detections = object_detections + face_detections
            
            # Update surveillance frame with detections
            surveillance_frame.detections = all_detections
            surveillance_frame.processed = True
            
            # Save frame to database
            await self.frame_repo.create(surveillance_frame)
            
            # Process detections and generate alerts
            await self._handle_detections(all_detections, camera_id, surveillance_frame.frame_id)
            
            # Call registered callbacks
            for callback in self.detection_callbacks:
                try:
                    await callback(surveillance_frame, all_detections)
                except Exception as e:
                    logger.error(f"Detection callback error: {e}")
            
            self.detections_made += len(all_detections)
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
    
    async def _handle_detections(self, detections: List[DetectionResult], 
                               camera_id: str, frame_id: str):
        """Handle detection results and generate alerts"""
        try:
            for detection in detections:
                # Skip known persons (no alert needed)
                if detection.detection_type == DetectionType.KNOWN_PERSON:
                    continue
                
                # Find the user for this camera/session
                user_id = await self._get_user_for_camera(camera_id)
                if not user_id:
                    continue
                
                # Create alert for significant detections
                detection_data = {
                    "confidence": detection.confidence,
                    "bounding_box": detection.bounding_box.dict(),
                    "person_name": detection.person_name,
                    "is_masked": getattr(detection, 'is_masked', False)
                }
                
                alert = await self.alert_service.handle_detection_result(
                    user_id=user_id,
                    detection_type=detection.detection_type,
                    camera_id=camera_id,
                    detection_data=detection_data,
                    frame_id=frame_id
                )
                
                if alert:
                    self.alerts_generated += 1
                    logger.info(f"🚨 Alert generated: {alert.detection_type}")
                    
        except Exception as e:
            logger.error(f"Detection handling error: {e}")
    
    async def _get_user_for_camera(self, camera_id: str) -> Optional[str]:
        """Get user ID for a camera (from active sessions)"""
        for session in self.active_sessions.values():
            if camera_id in session.camera_id:
                return str(session.user_id)
        return None
    
    def add_detection_callback(self, callback: Callable):
        """Add a callback to be called for each detection"""
        self.detection_callbacks.append(callback)
    
    def remove_detection_callback(self, callback: Callable):
        """Remove a detection callback"""
        if callback in self.detection_callbacks:
            self.detection_callbacks.remove(callback)
    
    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a surveillance session"""
        try:
            session = await self.session_repo.get_by_id(session_id)
            if not session:
                return {}
            
            # Get session frames
            frames = await self.frame_repo.get_session_frames(session_id)
            
            # Calculate statistics
            total_detections = sum(len(frame.detections) for frame in frames)
            detection_types = {}
            
            for frame in frames:
                for detection in frame.detections:
                    det_type = detection.detection_type.value
                    detection_types[det_type] = detection_types.get(det_type, 0) + 1
            
            # Calculate session duration
            duration = None
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds()
            elif session.is_active:
                duration = (datetime.utcnow() - session.start_time).total_seconds()
            
            stats = {
                "session_id": session_id,
                "is_active": session.is_active,
                "start_time": session.start_time,
                "end_time": session.end_time,
                "duration_seconds": duration,
                "total_frames": len(frames),
                "total_detections": total_detections,
                "detection_types": detection_types,
                "alerts_generated": session.alerts_generated
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            return {}
    
    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get overall system statistics"""
        try:
            uptime = time.time() - self.start_time if self.start_time else 0
            
            # Get AI component stats
            face_detector_stats = self.face_detector.get_performance_stats() if self.face_detector else {}
            object_detector_stats = await self.object_detector.get_detection_statistics() if self.object_detector else {}
            camera_stats = await self.camera_manager.get_all_statistics() if self.camera_manager else {}
            
            stats = {
                "system": {
                    "is_processing": self.is_processing,
                    "uptime_seconds": uptime,
                    "active_sessions": len(self.active_sessions),
                    "frames_processed": self.frames_processed,
                    "detections_made": self.detections_made,
                    "alerts_generated": self.alerts_generated
                },
                "performance": {
                    "face_detection": face_detector_stats,
                    "object_detection": object_detector_stats,
                    "cameras": camera_stats
                }
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get system statistics: {e}")
            return {}
    
    async def cleanup(self):
        """Cleanup surveillance service"""
        try:
            # Stop processing
            await self.stop_processing()
            
            # End all active sessions
            for session_id in list(self.active_sessions.keys()):
                await self.stop_surveillance_session(session_id)
            
            # Cleanup AI components
            if self.face_detector:
                await self.face_detector.cleanup()
            
            if self.object_detector:
                await self.object_detector.cleanup()
            
            logger.info("🧹 Surveillance service cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# Global surveillance service instance
surveillance_service = SurveillanceService()
