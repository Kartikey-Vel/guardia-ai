"""
Camera Manager Service for Guardia AI
Advanced multi-camera management with DroidCam support, failover, and hot-plug detection
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import cv2
import numpy as np
import zmq
import zmq.asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import yaml
import json
import redis.asyncio as redis
from pydantic import BaseModel
import psutil
import socket
import struct
from contextlib import asynccontextmanager
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
camera_count = Gauge('guardia_cameras_total', 'Total cameras configured')
active_camera_count = Gauge('guardia_cameras_active', 'Active camera streams')
frame_counter = Counter('guardia_frames_total', 'Total frames processed', ['camera_id'])
camera_errors = Counter('guardia_camera_errors_total', 'Camera errors', ['camera_id', 'error_type'])


class CameraType(str, Enum):
    USB = "usb"
    DROIDCAM = "droidcam"
    RTSP = "rtsp"
    HTTP = "http"
    ONVIF = "onvif"


class CameraStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class CameraConfig:
    """Camera configuration"""
    id: str
    name: str
    type: CameraType
    enabled: bool = True
    priority: int = 5
    fps: int = 15
    width: int = 640
    height: int = 480
    
    # Type-specific settings
    device_index: Optional[int] = None  # For USB cameras
    host: Optional[str] = None  # For IP cameras
    port: Optional[int] = None  # For IP cameras
    url: Optional[str] = None  # For RTSP/HTTP streams
    username: Optional[str] = None
    password: Optional[str] = None
    
    # Region of interest
    roi: Optional[Dict] = None
    
    # Failover settings
    is_backup: bool = False
    primary_camera_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CameraState:
    """Runtime state for a camera"""
    config: CameraConfig
    status: CameraStatus = CameraStatus.DISCONNECTED
    capture: Optional[cv2.VideoCapture] = None
    last_frame: Optional[np.ndarray] = None
    last_frame_time: Optional[datetime] = None
    frame_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    reconnect_attempts: int = 0
    connected_at: Optional[datetime] = None
    
    def get_status_dict(self) -> Dict:
        return {
            "camera_id": self.config.id,
            "name": self.config.name,
            "type": self.config.type,
            "status": self.status,
            "enabled": self.config.enabled,
            "priority": self.config.priority,
            "frame_count": self.frame_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_frame_time": self.last_frame_time.isoformat() if self.last_frame_time else None,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "fps": self.config.fps,
            "resolution": f"{self.config.width}x{self.config.height}"
        }


class DroidCamDiscovery:
    """DroidCam device discovery"""
    
    DEFAULT_PORT = 4747
    DISCOVERY_PORTS = [4747, 4748, 4749]
    
    @staticmethod
    async def discover_devices(network_prefix: str = None, timeout: float = 2.0) -> List[Dict]:
        """Scan network for DroidCam devices"""
        devices = []
        
        if not network_prefix:
            # Get local network prefix
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                network_prefix = ".".join(local_ip.split(".")[:3])
            except Exception:
                network_prefix = "192.168.1"
        
        async def check_host(ip: str, port: int) -> Optional[Dict]:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=timeout
                )
                writer.close()
                await writer.wait_closed()
                return {
                    "host": ip,
                    "port": port,
                    "type": "droidcam",
                    "name": f"DroidCam@{ip}"
                }
            except Exception:
                return None
        
        # Scan common IP range
        tasks = []
        for i in range(1, 255):
            ip = f"{network_prefix}.{i}"
            for port in DroidCamDiscovery.DISCOVERY_PORTS:
                tasks.append(check_host(ip, port))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result and isinstance(result, dict):
                devices.append(result)
        
        return devices
    
    @staticmethod
    def get_stream_url(host: str, port: int = 4747, video: bool = True) -> str:
        """Get DroidCam stream URL"""
        if video:
            return f"http://{host}:{port}/video"
        return f"http://{host}:{port}/audio.wav"
    
    @staticmethod
    def get_mjpeg_url(host: str, port: int = 4747) -> str:
        """Get DroidCam MJPEG stream URL"""
        return f"http://{host}:{port}/mjpegfeed?640x480"


class USBCameraDiscovery:
    """USB camera discovery"""
    
    @staticmethod
    def discover_cameras(max_cameras: int = 10) -> List[Dict]:
        """Discover available USB cameras"""
        cameras = []
        
        for i in range(max_cameras):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    # Get camera info
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    cameras.append({
                        "device_index": i,
                        "type": "usb",
                        "name": f"USB Camera {i}",
                        "width": width,
                        "height": height,
                        "fps": fps if fps > 0 else 30
                    })
                cap.release()
        
        return cameras


class CameraStream:
    """Manages a single camera stream with failover support"""
    
    def __init__(
        self, 
        state: CameraState,
        zmq_publisher: zmq.asyncio.Socket,
        redis_client: redis.Redis,
        on_disconnect_callback=None
    ):
        self.state = state
        self.config = state.config
        self.zmq_publisher = zmq_publisher
        self.redis_client = redis_client
        self.on_disconnect = on_disconnect_callback
        self.running = False
        self._reconnect_task = None
        self._stream_task = None
        
    def _build_capture_url(self) -> str:
        """Build capture URL based on camera type"""
        config = self.config
        
        if config.type == CameraType.USB:
            return config.device_index
        
        elif config.type == CameraType.DROIDCAM:
            # DroidCam HTTP stream
            return DroidCamDiscovery.get_stream_url(config.host, config.port or 4747)
        
        elif config.type == CameraType.RTSP:
            url = config.url
            if config.username and config.password:
                # Insert credentials
                if "rtsp://" in url:
                    url = url.replace("rtsp://", f"rtsp://{config.username}:{config.password}@")
            return url
        
        elif config.type == CameraType.HTTP:
            return config.url
        
        elif config.type == CameraType.ONVIF:
            # ONVIF typically uses RTSP
            return config.url
        
        return config.url
    
    async def connect(self) -> bool:
        """Connect to camera"""
        try:
            self.state.status = CameraStatus.CONNECTING
            
            capture_source = self._build_capture_url()
            
            # Create VideoCapture
            if isinstance(capture_source, int):
                self.state.capture = cv2.VideoCapture(capture_source)
            else:
                self.state.capture = cv2.VideoCapture(capture_source)
            
            if not self.state.capture.isOpened():
                self.state.status = CameraStatus.ERROR
                self.state.last_error = "Failed to open camera"
                logger.error(f"Failed to open camera {self.config.id}")
                return False
            
            # Configure capture settings
            self.state.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
            self.state.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
            self.state.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Test read
            ret, frame = self.state.capture.read()
            if not ret:
                self.state.status = CameraStatus.ERROR
                self.state.last_error = "Failed to read initial frame"
                return False
            
            self.state.status = CameraStatus.CONNECTED
            self.state.connected_at = datetime.utcnow()
            self.state.reconnect_attempts = 0
            self.state.error_count = 0
            
            logger.info(f"Connected to camera {self.config.id} ({self.config.name})")
            return True
            
        except Exception as e:
            self.state.status = CameraStatus.ERROR
            self.state.last_error = str(e)
            logger.error(f"Error connecting to camera {self.config.id}: {e}")
            return False
    
    async def start_streaming(self):
        """Start streaming frames"""
        self.running = True
        self.state.status = CameraStatus.STREAMING
        
        frame_interval = 1.0 / self.config.fps
        
        while self.running:
            try:
                if not self.state.capture or not self.state.capture.isOpened():
                    await self._handle_disconnect()
                    continue
                
                ret, frame = self.state.capture.read()
                
                if not ret or frame is None:
                    self.state.error_count += 1
                    if self.state.error_count >= 5:
                        await self._handle_disconnect()
                    await asyncio.sleep(0.1)
                    continue
                
                # Reset error count on successful read
                self.state.error_count = 0
                
                # Apply ROI if configured
                if self.config.roi:
                    roi = self.config.roi
                    frame = frame[
                        roi['y']:roi['y']+roi['height'],
                        roi['x']:roi['x']+roi['width']
                    ]
                
                # Update state
                self.state.last_frame = frame.copy()
                self.state.last_frame_time = datetime.utcnow()
                self.state.frame_count += 1
                
                # Publish frame
                await self._publish_frame(frame)
                
                # Update metrics
                frame_counter.labels(camera_id=self.config.id).inc()
                
                await asyncio.sleep(frame_interval)
                
            except Exception as e:
                logger.error(f"Error in camera {self.config.id} stream: {e}")
                self.state.error_count += 1
                camera_errors.labels(camera_id=self.config.id, error_type="stream").inc()
                await asyncio.sleep(0.1)
    
    async def _publish_frame(self, frame: np.ndarray):
        """Publish frame to preprocessing service"""
        try:
            # Encode frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_bytes = buffer.tobytes()
            
            # Create metadata
            metadata = {
                "camera_id": self.config.id,
                "camera_name": self.config.name,
                "camera_type": self.config.type,
                "timestamp": datetime.utcnow().isoformat(),
                "frame_number": self.state.frame_count,
                "shape": list(frame.shape),
                "priority": self.config.priority
            }
            
            # Publish via ZeroMQ
            await self.zmq_publisher.send_multipart([
                b"frames",
                yaml.dump(metadata).encode('utf-8'),
                frame_bytes
            ])
            
            # Update Redis with latest frame info
            await self.redis_client.setex(
                f"camera:{self.config.id}:last_frame",
                60,
                datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error publishing frame from {self.config.id}: {e}")
    
    async def _handle_disconnect(self):
        """Handle camera disconnection"""
        logger.warning(f"Camera {self.config.id} disconnected")
        self.state.status = CameraStatus.RECONNECTING
        
        if self.on_disconnect:
            await self.on_disconnect(self.config.id)
        
        # Try to reconnect
        await self._reconnect()
    
    async def _reconnect(self, max_attempts: int = 5, base_delay: float = 2.0):
        """Attempt to reconnect with exponential backoff"""
        self.state.reconnect_attempts = 0
        
        while self.running and self.state.reconnect_attempts < max_attempts:
            self.state.reconnect_attempts += 1
            delay = base_delay * (2 ** (self.state.reconnect_attempts - 1))
            
            logger.info(
                f"Reconnecting camera {self.config.id}, "
                f"attempt {self.state.reconnect_attempts}/{max_attempts}"
            )
            
            await asyncio.sleep(delay)
            
            if await self.connect():
                logger.info(f"Camera {self.config.id} reconnected successfully")
                return True
        
        self.state.status = CameraStatus.ERROR
        self.state.last_error = "Max reconnection attempts exceeded"
        camera_errors.labels(camera_id=self.config.id, error_type="reconnect_failed").inc()
        return False
    
    async def stop(self):
        """Stop streaming"""
        self.running = False
        
        if self.state.capture:
            self.state.capture.release()
            self.state.capture = None
        
        self.state.status = CameraStatus.DISCONNECTED
        logger.info(f"Stopped camera {self.config.id}")
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the current frame"""
        return self.state.last_frame


class CameraManager:
    """Main camera management service"""
    
    def __init__(self):
        self.cameras: Dict[str, CameraStream] = {}
        self.states: Dict[str, CameraState] = {}
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
        self.redis_client: Optional[redis.Redis] = None
        self.config_path = os.getenv("CONFIG_PATH", "/app/config/cameras.yaml")
        self.max_cameras = int(os.getenv("MAX_CAMERAS", "10"))
        self._stream_tasks: Dict[str, asyncio.Task] = {}
        
    async def initialize(self):
        """Initialize the camera manager"""
        try:
            # Bind ZeroMQ publisher
            zmq_port = os.getenv("ZMQ_PUB_PORT", "5554")
            self.zmq_publisher.bind(f"tcp://*:{zmq_port}")
            logger.info(f"ZeroMQ publisher bound to port {zmq_port}")
            
            # Connect to Redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = await redis.from_url(redis_url)
            logger.info(f"Connected to Redis: {redis_url}")
            
            # Load camera configurations
            await self.load_config()
            
        except Exception as e:
            logger.error(f"Failed to initialize camera manager: {e}")
            raise
    
    async def load_config(self):
        """Load camera configurations from file"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found: {self.config_path}")
                return
            
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            for cam_data in config.get('cameras', []):
                camera_config = CameraConfig(
                    id=cam_data.get('id') or cam_data.get('camera_id'),
                    name=cam_data.get('name'),
                    type=CameraType(cam_data.get('type', 'usb')),
                    enabled=cam_data.get('enabled', True),
                    priority=cam_data.get('priority', 5),
                    fps=cam_data.get('fps', 15),
                    width=cam_data.get('width', 640),
                    height=cam_data.get('height', 480),
                    device_index=cam_data.get('device_index'),
                    host=cam_data.get('host'),
                    port=cam_data.get('port'),
                    url=cam_data.get('url'),
                    username=cam_data.get('username'),
                    password=cam_data.get('password'),
                    roi=cam_data.get('roi'),
                    is_backup=cam_data.get('is_backup', False),
                    primary_camera_id=cam_data.get('primary_camera_id')
                )
                
                await self.add_camera(camera_config)
            
            camera_count.set(len(self.cameras))
            logger.info(f"Loaded {len(self.cameras)} cameras from config")
            
        except Exception as e:
            logger.error(f"Error loading camera config: {e}")
    
    async def add_camera(self, config: CameraConfig) -> bool:
        """Add a new camera"""
        if len(self.cameras) >= self.max_cameras:
            logger.error(f"Maximum camera limit ({self.max_cameras}) reached")
            return False
        
        if config.id in self.cameras:
            logger.warning(f"Camera {config.id} already exists")
            return False
        
        state = CameraState(config=config)
        self.states[config.id] = state
        
        stream = CameraStream(
            state=state,
            zmq_publisher=self.zmq_publisher,
            redis_client=self.redis_client,
            on_disconnect_callback=self._handle_camera_disconnect
        )
        
        self.cameras[config.id] = stream
        camera_count.set(len(self.cameras))
        
        logger.info(f"Added camera: {config.id} ({config.name})")
        return True
    
    async def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera"""
        if camera_id not in self.cameras:
            return False
        
        # Stop streaming if active
        await self.stop_camera(camera_id)
        
        del self.cameras[camera_id]
        del self.states[camera_id]
        
        camera_count.set(len(self.cameras))
        logger.info(f"Removed camera: {camera_id}")
        return True
    
    async def start_camera(self, camera_id: str) -> bool:
        """Start a camera stream"""
        if camera_id not in self.cameras:
            return False
        
        stream = self.cameras[camera_id]
        
        if not await stream.connect():
            return False
        
        # Start streaming task
        task = asyncio.create_task(stream.start_streaming())
        self._stream_tasks[camera_id] = task
        
        active_camera_count.inc()
        return True
    
    async def stop_camera(self, camera_id: str) -> bool:
        """Stop a camera stream"""
        if camera_id not in self.cameras:
            return False
        
        stream = self.cameras[camera_id]
        await stream.stop()
        
        if camera_id in self._stream_tasks:
            self._stream_tasks[camera_id].cancel()
            del self._stream_tasks[camera_id]
        
        active_camera_count.dec()
        return True
    
    async def start_all_cameras(self):
        """Start all enabled cameras"""
        for camera_id, stream in self.cameras.items():
            if stream.state.config.enabled:
                await self.start_camera(camera_id)
    
    async def stop_all_cameras(self):
        """Stop all cameras"""
        for camera_id in list(self.cameras.keys()):
            await self.stop_camera(camera_id)
    
    async def _handle_camera_disconnect(self, camera_id: str):
        """Handle camera disconnection - trigger failover if configured"""
        logger.warning(f"Handling disconnect for camera {camera_id}")
        
        # Find backup cameras
        for stream in self.cameras.values():
            config = stream.state.config
            if config.is_backup and config.primary_camera_id == camera_id:
                if stream.state.status == CameraStatus.DISCONNECTED:
                    logger.info(f"Activating backup camera {config.id}")
                    await self.start_camera(config.id)
    
    def get_camera_status(self, camera_id: str) -> Optional[Dict]:
        """Get status of a specific camera"""
        if camera_id not in self.states:
            return None
        return self.states[camera_id].get_status_dict()
    
    def get_all_statuses(self) -> List[Dict]:
        """Get status of all cameras"""
        return [state.get_status_dict() for state in self.states.values()]
    
    def get_camera_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Get current frame from a camera"""
        if camera_id not in self.cameras:
            return None
        return self.cameras[camera_id].get_current_frame()
    
    async def discover_cameras(self) -> Dict:
        """Discover available cameras"""
        result = {
            "usb": [],
            "droidcam": []
        }
        
        # Discover USB cameras
        result["usb"] = USBCameraDiscovery.discover_cameras()
        
        # Discover DroidCam devices
        result["droidcam"] = await DroidCamDiscovery.discover_devices()
        
        return result
    
    async def cleanup(self):
        """Clean up resources"""
        await self.stop_all_cameras()
        
        self.zmq_publisher.close()
        self.zmq_context.term()
        
        if self.redis_client:
            await self.redis_client.close()


# Pydantic models for API
class CameraCreateRequest(BaseModel):
    id: str
    name: str
    type: str
    enabled: bool = True
    priority: int = 5
    fps: int = 15
    width: int = 640
    height: int = 480
    device_index: Optional[int] = None
    host: Optional[str] = None
    port: Optional[int] = None
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[int] = None
    fps: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


# FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await manager.initialize()
    await manager.start_all_cameras()
    yield
    # Shutdown
    await manager.cleanup()


app = FastAPI(
    title="Guardia Camera Manager",
    description="Advanced multi-camera management with DroidCam support",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = CameraManager()


# Health and Status Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "camera-manager"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/status")
async def get_status():
    """Get detailed service status"""
    statuses = manager.get_all_statuses()
    return {
        "service": "camera-manager",
        "cameras": statuses,
        "total_cameras": len(statuses),
        "active_cameras": sum(1 for s in statuses if s['status'] == 'streaming'),
        "max_cameras": manager.max_cameras
    }


# Camera Management Endpoints
@app.get("/cameras")
async def list_cameras():
    """List all cameras"""
    return {"cameras": manager.get_all_statuses()}


@app.get("/cameras/{camera_id}")
async def get_camera(camera_id: str):
    """Get specific camera status"""
    status = manager.get_camera_status(camera_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return status


@app.post("/cameras")
async def create_camera(request: CameraCreateRequest):
    """Add a new camera"""
    config = CameraConfig(
        id=request.id,
        name=request.name,
        type=CameraType(request.type),
        enabled=request.enabled,
        priority=request.priority,
        fps=request.fps,
        width=request.width,
        height=request.height,
        device_index=request.device_index,
        host=request.host,
        port=request.port,
        url=request.url,
        username=request.username,
        password=request.password
    )
    
    if not await manager.add_camera(config):
        raise HTTPException(status_code=400, detail="Failed to add camera")
    
    return {"status": "created", "camera_id": request.id}


@app.delete("/cameras/{camera_id}")
async def delete_camera(camera_id: str):
    """Remove a camera"""
    if not await manager.remove_camera(camera_id):
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    return {"status": "deleted", "camera_id": camera_id}


@app.post("/cameras/{camera_id}/start")
async def start_camera(camera_id: str):
    """Start camera stream"""
    if not await manager.start_camera(camera_id):
        raise HTTPException(status_code=400, detail=f"Failed to start camera {camera_id}")
    return {"status": "started", "camera_id": camera_id}


@app.post("/cameras/{camera_id}/stop")
async def stop_camera(camera_id: str):
    """Stop camera stream"""
    if not await manager.stop_camera(camera_id):
        raise HTTPException(status_code=400, detail=f"Failed to stop camera {camera_id}")
    return {"status": "stopped", "camera_id": camera_id}


# Discovery Endpoints
@app.get("/discovery")
async def discover_all():
    """Discover all available cameras"""
    return await manager.discover_cameras()


@app.get("/discovery/usb")
async def discover_usb():
    """Discover USB cameras"""
    return {"cameras": USBCameraDiscovery.discover_cameras()}


@app.get("/discovery/droidcam")
async def discover_droidcam(network_prefix: Optional[str] = None):
    """Discover DroidCam devices"""
    devices = await DroidCamDiscovery.discover_devices(network_prefix)
    return {"devices": devices}


# Streaming Endpoints
@app.get("/snapshot/{camera_id}")
async def get_snapshot(camera_id: str):
    """Get current frame as JPEG"""
    frame = manager.get_camera_frame(camera_id)
    if frame is None:
        raise HTTPException(status_code=404, detail=f"No frame available for camera {camera_id}")
    
    _, buffer = cv2.imencode('.jpg', frame)
    return Response(
        content=buffer.tobytes(),
        media_type="image/jpeg"
    )


async def generate_mjpeg(camera_id: str):
    """Generate MJPEG stream"""
    while True:
        frame = manager.get_camera_frame(camera_id)
        if frame is not None:
            _, buffer = cv2.imencode('.jpg', frame)
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            )
        await asyncio.sleep(0.033)  # ~30 fps


@app.get("/stream/{camera_id}")
async def stream_camera(camera_id: str):
    """MJPEG stream endpoint"""
    if camera_id not in manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    return StreamingResponse(
        generate_mjpeg(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.websocket("/ws/stream/{camera_id}")
async def websocket_stream(websocket: WebSocket, camera_id: str):
    """WebSocket stream endpoint"""
    await websocket.accept()
    
    try:
        while True:
            frame = manager.get_camera_frame(camera_id)
            if frame is not None:
                _, buffer = cv2.imencode('.jpg', frame)
                await websocket.send_bytes(buffer.tobytes())
            await asyncio.sleep(0.033)
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("CAMERA_MANAGER_PORT", "8010"))
    uvicorn.run(app, host="0.0.0.0", port=port)
