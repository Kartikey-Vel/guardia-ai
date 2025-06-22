"""
Enhanced Camera Management System
Modern implementation with multiple camera support and advanced features
"""
import asyncio
import cv2
import numpy as np
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path
import threading
import queue
import time
from datetime import datetime
from loguru import logger

from ..config.settings import settings
from ..models.schemas import CameraInfo, SurveillanceFrame, DetectionResult

class EnhancedCameraManager:
    """Enhanced camera management with multi-camera support and advanced features"""
    
    def __init__(self, camera_id: str = "default", camera_index: int = None):
        self.camera_id = camera_id
        self.camera_index = camera_index or settings.camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_initialized = False
        self.is_recording = False
        self.is_streaming = False
        
        # Frame management
        self.current_frame = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.frame_callbacks: List[Callable] = []
        
        # Recording management
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.recording_path: Optional[Path] = None
        self.recording_start_time: Optional[datetime] = None
        
        # Performance tracking
        self.frame_count = 0
        self.fps_counter = 0
        self.last_fps_time = time.time()
        self.actual_fps = 0.0
        
        # Threading
        self.capture_thread: Optional[threading.Thread] = None
        self.should_stop = threading.Event()
        
        # Camera info
        self.camera_info = CameraInfo(
            camera_id=camera_id,
            name=f"Camera {camera_index}",
            location="Unknown"
        )
    
    async def initialize(self) -> bool:
        """Initialize camera with error handling and retry logic"""
        try:
            logger.info(f"🔄 Initializing camera {self.camera_id} (index: {self.camera_index})")
            
            # Try to open camera with retries
            max_retries = 3
            for attempt in range(max_retries):
                self.cap = cv2.VideoCapture(self.camera_index)
                
                if self.cap.isOpened():
                    break
                    
                logger.warning(f"Camera initialization attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(1)
                
                if self.cap:
                    self.cap.release()
            
            if not self.cap or not self.cap.isOpened():
                raise Exception(f"Could not open camera {self.camera_index} after {max_retries} attempts")
            
            # Configure camera properties
            await self._configure_camera()
            
            # Get camera information
            await self._update_camera_info()
            
            self.is_initialized = True
            logger.info(f"✅ Camera {self.camera_id} initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize camera {self.camera_id}: {e}")
            self.is_initialized = False
            if self.cap:
                self.cap.release()
            return False
    
    async def _configure_camera(self):
        """Configure camera properties for optimal performance"""
        try:
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.frame_height)
            
            # Set FPS
            self.cap.set(cv2.CAP_PROP_FPS, settings.fps)
            
            # Set buffer size to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Auto-exposure and auto-focus settings
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Enable auto-exposure
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable auto-focus
            
            logger.info(f"Camera {self.camera_id} configured: {settings.frame_width}x{settings.frame_height}@{settings.fps}fps")
            
        except Exception as e:
            logger.warning(f"Some camera properties could not be set: {e}")
    
    async def _update_camera_info(self):
        """Update camera information"""
        try:
            # Get actual camera properties
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            
            self.camera_info.resolution = f"{width}x{height}"
            self.camera_info.fps = fps
            self.camera_info.is_active = True
            self.camera_info.last_frame = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Failed to update camera info: {e}")
    
    async def start_capture(self):
        """Start continuous frame capture in background thread"""
        if not self.is_initialized:
            raise Exception("Camera not initialized")
        
        if self.capture_thread and self.capture_thread.is_alive():
            logger.warning("Capture thread already running")
            return
        
        self.should_stop.clear()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        self.is_streaming = True
        
        logger.info(f"📹 Started capture for camera {self.camera_id}")
    
    def _capture_loop(self):
        """Main capture loop running in background thread"""
        while not self.should_stop.is_set():
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.error("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue
                
                # Update frame tracking
                self.frame_count += 1
                self.current_frame = frame.copy()
                self.camera_info.last_frame = datetime.utcnow()
                
                # Calculate FPS
                self._update_fps()
                
                # Add frame to queue (non-blocking)
                try:
                    self.frame_queue.put_nowait(frame.copy())
                except queue.Full:
                    # Remove oldest frame if queue is full
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame.copy())
                    except queue.Empty:
                        pass
                
                # Record frame if recording
                if self.is_recording and self.video_writer:
                    self.video_writer.write(frame)
                
                # Call frame callbacks
                for callback in self.frame_callbacks:
                    try:
                        callback(frame.copy(), self.camera_id)
                    except Exception as e:
                        logger.error(f"Frame callback error: {e}")
                
                # Control frame rate
                time.sleep(max(0, 1.0 / settings.fps - 0.001))
                
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                time.sleep(0.1)
    
    def _update_fps(self):
        """Update FPS calculation"""
        current_time = time.time()
        self.fps_counter += 1
        
        if current_time - self.last_fps_time >= 1.0:  # Update every second
            self.actual_fps = self.fps_counter / (current_time - self.last_fps_time)
            self.fps_counter = 0
            self.last_fps_time = current_time
    
    async def get_frame(self) -> Optional[np.ndarray]:
        """Get the latest frame (non-blocking)"""
        if not self.is_streaming:
            # Single frame capture
            if not self.cap or not self.cap.isOpened():
                return None
            
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame.copy()
                return frame
            return None
        
        # Get frame from queue
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return self.current_frame
    
    async def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get the most recent frame"""
        return self.current_frame
    
    def add_frame_callback(self, callback: Callable[[np.ndarray, str], None]):
        """Add a callback to be called for each frame"""
        self.frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable):
        """Remove a frame callback"""
        if callback in self.frame_callbacks:
            self.frame_callbacks.remove(callback)
    
    async def start_recording(self, output_path: Optional[Path] = None) -> bool:
        """Start video recording"""
        try:
            if self.is_recording:
                logger.warning("Recording already in progress")
                return False
            
            if not self.is_streaming:
                logger.error("Cannot start recording without active capture")
                return False
            
            # Generate output path if not provided
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = settings.data_dir / "recordings" / f"recording_{self.camera_id}_{timestamp}.mp4"
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*settings.video_codec)
            self.video_writer = cv2.VideoWriter(
                str(output_path),
                fourcc,
                settings.fps,
                (settings.frame_width, settings.frame_height)
            )
            
            if not self.video_writer.isOpened():
                raise Exception("Failed to initialize video writer")
            
            self.recording_path = output_path
            self.recording_start_time = datetime.utcnow()
            self.is_recording = True
            
            logger.info(f"📼 Started recording to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            return False
    
    async def stop_recording(self) -> Optional[Path]:
        """Stop video recording and return the recording path"""
        if not self.is_recording:
            logger.warning("No recording in progress")
            return None
        
        try:
            self.is_recording = False
            
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            
            recording_path = self.recording_path
            duration = datetime.utcnow() - self.recording_start_time
            
            logger.info(f"⏹️ Recording stopped: {recording_path} (duration: {duration})")
            
            return recording_path
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            return None
    
    async def capture_snapshot(self, output_path: Optional[Path] = None) -> Optional[Path]:
        """Capture a single snapshot"""
        try:
            frame = await self.get_latest_frame()
            if frame is None:
                logger.error("No frame available for snapshot")
                return None
            
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = settings.data_dir / "snapshots" / f"snapshot_{self.camera_id}_{timestamp}.jpg"
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save frame
            success = cv2.imwrite(str(output_path), frame)
            
            if success:
                logger.info(f"📸 Snapshot saved: {output_path}")
                return output_path
            else:
                logger.error("Failed to save snapshot")
                return None
                
        except Exception as e:
            logger.error(f"Snapshot capture error: {e}")
            return None
    
    async def get_camera_info(self) -> CameraInfo:
        """Get current camera information"""
        if self.is_streaming:
            self.camera_info.is_active = True
            # Update with current performance data
        return self.camera_info
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get camera performance statistics"""
        return {
            "camera_id": self.camera_id,
            "is_active": self.is_streaming,
            "is_recording": self.is_recording,
            "frame_count": self.frame_count,
            "actual_fps": round(self.actual_fps, 2),
            "target_fps": settings.fps,
            "resolution": f"{settings.frame_width}x{settings.frame_height}",
            "queue_size": self.frame_queue.qsize(),
            "recording_duration": str(datetime.utcnow() - self.recording_start_time) if self.is_recording else None
        }
    
    async def stop_capture(self):
        """Stop frame capture"""
        if self.capture_thread and self.capture_thread.is_alive():
            self.should_stop.set()
            self.capture_thread.join(timeout=5)
        
        if self.is_recording:
            await self.stop_recording()
        
        self.is_streaming = False
        logger.info(f"⏹️ Stopped capture for camera {self.camera_id}")
    
    async def release(self):
        """Release camera resources"""
        await self.stop_capture()
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.is_initialized = False
        self.camera_info.is_active = False
        
        logger.info(f"🔌 Released camera {self.camera_id}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()

class MultiCameraManager:
    """Manage multiple cameras simultaneously"""
    
    def __init__(self):
        self.cameras: Dict[str, EnhancedCameraManager] = {}
        self.is_active = False
    
    async def add_camera(self, camera_id: str, camera_index: int, auto_start: bool = True) -> bool:
        """Add a new camera"""
        try:
            camera = EnhancedCameraManager(camera_id, camera_index)
            
            if await camera.initialize():
                self.cameras[camera_id] = camera
                
                if auto_start:
                    await camera.start_capture()
                
                logger.info(f"✅ Added camera {camera_id}")
                return True
            else:
                logger.error(f"❌ Failed to add camera {camera_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding camera {camera_id}: {e}")
            return False
    
    async def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera"""
        if camera_id in self.cameras:
            await self.cameras[camera_id].release()
            del self.cameras[camera_id]
            logger.info(f"🗑️ Removed camera {camera_id}")
            return True
        return False
    
    async def get_all_frames(self) -> Dict[str, np.ndarray]:
        """Get latest frames from all cameras"""
        frames = {}
        for camera_id, camera in self.cameras.items():
            frame = await camera.get_latest_frame()
            if frame is not None:
                frames[camera_id] = frame
        return frames
    
    async def start_all_recordings(self) -> Dict[str, bool]:
        """Start recording on all cameras"""
        results = {}
        for camera_id, camera in self.cameras.items():
            results[camera_id] = await camera.start_recording()
        return results
    
    async def stop_all_recordings(self) -> Dict[str, Optional[Path]]:
        """Stop recording on all cameras"""
        results = {}
        for camera_id, camera in self.cameras.items():
            results[camera_id] = await camera.stop_recording()
        return results
    
    async def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics from all cameras"""
        stats = {}
        for camera_id, camera in self.cameras.items():
            stats[camera_id] = await camera.get_statistics()
        return stats
    
    async def cleanup(self):
        """Cleanup all cameras"""
        for camera in self.cameras.values():
            await camera.release()
        self.cameras.clear()
        logger.info("🧹 Multi-camera manager cleaned up")
