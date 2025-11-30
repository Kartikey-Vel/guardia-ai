"""
Camera Ingest Service for Guardia AI
Handles RTSP/ONVIF camera connections and frame extraction
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import cv2
import numpy as np
import zmq
import zmq.asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import yaml
import redis.asyncio as redis

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Camera configuration"""
    camera_id: str
    name: str
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    fps: int = 10
    enabled: bool = True
    roi: Optional[Dict] = None


class CameraStream:
    """Manages a single camera video stream"""
    
    def __init__(self, config: CameraConfig, zmq_publisher, redis_client):
        self.config = config
        self.zmq_publisher = zmq_publisher
        self.redis_client = redis_client
        self.capture: Optional[cv2.VideoCapture] = None
        self.running = False
        self.frame_count = 0
        self.last_frame_time = None
        
    async def connect(self) -> bool:
        """Connect to camera stream"""
        try:
            # Build RTSP URL with credentials if provided
            url = self.config.url
            if self.config.username and self.config.password:
                # Insert credentials into RTSP URL
                if "rtsp://" in url:
                    url = url.replace("rtsp://", f"rtsp://{self.config.username}:{self.config.password}@")
            
            self.capture = cv2.VideoCapture(url)
            
            if not self.capture.isOpened():
                logger.error(f"Failed to open camera {self.config.camera_id}: {url}")
                return False
            
            # Set buffer size to reduce latency
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            logger.info(f"Connected to camera {self.config.camera_id} ({self.config.name})")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to camera {self.config.camera_id}: {e}")
            return False
    
    async def start(self):
        """Start capturing frames from camera"""
        self.running = True
        frame_interval = 1.0 / self.config.fps
        
        while self.running:
            try:
                if not self.capture or not self.capture.isOpened():
                    logger.warning(f"Camera {self.config.camera_id} disconnected, attempting reconnect...")
                    await asyncio.sleep(5)
                    if not await self.connect():
                        continue
                
                ret, frame = self.capture.read()
                
                if not ret or frame is None:
                    logger.warning(f"Failed to read frame from camera {self.config.camera_id}")
                    await asyncio.sleep(1)
                    continue
                
                # Process and publish frame
                await self.publish_frame(frame)
                
                # Control frame rate
                await asyncio.sleep(frame_interval)
                
            except Exception as e:
                logger.error(f"Error in camera {self.config.camera_id} capture loop: {e}")
                await asyncio.sleep(1)
    
    async def publish_frame(self, frame: np.ndarray):
        """Publish frame to preprocessing service"""
        try:
            timestamp = datetime.utcnow().isoformat()
            self.frame_count += 1
            self.last_frame_time = timestamp
            
            # Encode frame as JPEG for efficient transmission
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()
            
            # Create frame metadata
            metadata = {
                "camera_id": self.config.camera_id,
                "camera_name": self.config.name,
                "timestamp": timestamp,
                "frame_number": self.frame_count,
                "shape": frame.shape,
                "roi": self.config.roi
            }
            
            # Publish via ZeroMQ
            await self.zmq_publisher.send_multipart([
                b"frames",  # topic
                yaml.dump(metadata).encode('utf-8'),
                frame_bytes
            ])
            
            # Update Redis with latest frame info (for health monitoring)
            await self.redis_client.setex(
                f"camera:{self.config.camera_id}:last_frame",
                60,  # expire after 60 seconds
                timestamp
            )
            
        except Exception as e:
            logger.error(f"Error publishing frame from camera {self.config.camera_id}: {e}")
    
    async def stop(self):
        """Stop capturing frames"""
        self.running = False
        if self.capture:
            self.capture.release()
            logger.info(f"Stopped camera {self.config.camera_id}")
    
    def get_status(self) -> Dict:
        """Get camera status"""
        return {
            "camera_id": self.config.camera_id,
            "name": self.config.name,
            "enabled": self.config.enabled,
            "running": self.running,
            "frame_count": self.frame_count,
            "last_frame_time": self.last_frame_time,
            "fps": self.config.fps
        }


class CameraIngestService:
    """Main service for managing multiple camera streams"""
    
    def __init__(self):
        self.cameras: Dict[str, CameraStream] = {}
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
        self.redis_client: Optional[redis.Redis] = None
        self.config_path = os.getenv("CONFIG_PATH", "/app/config/cameras.yaml")
        
    async def initialize(self):
        """Initialize service"""
        try:
            # Bind ZeroMQ publisher
            zmq_port = os.getenv("ZMQ_PORT", "5555")
            self.zmq_publisher.bind(f"tcp://*:{zmq_port}")
            logger.info(f"ZeroMQ publisher bound to port {zmq_port}")
            
            # Connect to Redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = await redis.from_url(redis_url)
            logger.info(f"Connected to Redis: {redis_url}")
            
            # Load camera configurations
            await self.load_cameras()
            
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    async def load_cameras(self):
        """Load camera configurations from file"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found: {self.config_path}")
                # Create default config
                default_config = {
                    "cameras": [
                        {
                            "camera_id": "cam_demo",
                            "name": "Demo Camera",
                            "url": "rtsp://demo.url/stream",
                            "fps": 10,
                            "enabled": False
                        }
                    ]
                }
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, 'w') as f:
                    yaml.dump(default_config, f)
                logger.info(f"Created default config at {self.config_path}")
                return
            
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            for cam_data in config.get('cameras', []):
                camera_config = CameraConfig(**cam_data)
                
                if not camera_config.enabled:
                    logger.info(f"Camera {camera_config.camera_id} is disabled, skipping")
                    continue
                
                camera = CameraStream(camera_config, self.zmq_publisher, self.redis_client)
                self.cameras[camera_config.camera_id] = camera
                
                logger.info(f"Loaded camera config: {camera_config.camera_id} ({camera_config.name})")
            
        except Exception as e:
            logger.error(f"Error loading camera configurations: {e}")
            raise
    
    async def start_all_cameras(self):
        """Start all configured cameras"""
        tasks = []
        for camera_id, camera in self.cameras.items():
            if await camera.connect():
                task = asyncio.create_task(camera.start())
                tasks.append(task)
                logger.info(f"Started camera {camera_id}")
            else:
                logger.error(f"Failed to start camera {camera_id}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_all_cameras(self):
        """Stop all cameras"""
        for camera in self.cameras.values():
            await camera.stop()
    
    def get_camera_status(self, camera_id: str) -> Optional[Dict]:
        """Get status of specific camera"""
        camera = self.cameras.get(camera_id)
        return camera.get_status() if camera else None
    
    def get_all_statuses(self) -> List[Dict]:
        """Get status of all cameras"""
        return [camera.get_status() for camera in self.cameras.values()]
    
    async def cleanup(self):
        """Clean up resources"""
        await self.stop_all_cameras()
        self.zmq_publisher.close()
        if self.redis_client:
            await self.redis_client.close()
        self.zmq_context.term()


# FastAPI application
app = FastAPI(title="Guardia Camera Ingest Service", version="1.0.0")
service = CameraIngestService()


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await service.initialize()
    # Start cameras in background
    asyncio.create_task(service.start_all_cameras())


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    await service.cleanup()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "camera-ingest"}


@app.get("/status")
async def get_status():
    """Get service status"""
    statuses = service.get_all_statuses()
    return {
        "service": "camera-ingest",
        "cameras": statuses,
        "total_cameras": len(statuses),
        "active_cameras": sum(1 for s in statuses if s['running'])
    }


@app.get("/cameras")
async def list_cameras():
    """List all configured cameras"""
    return {"cameras": service.get_all_statuses()}


@app.get("/cameras/{camera_id}")
async def get_camera(camera_id: str):
    """Get specific camera status"""
    status = service.get_camera_status(camera_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return status


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
