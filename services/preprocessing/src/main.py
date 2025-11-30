"""
Preprocessing Service for Guardia AI
Handles frame preprocessing, normalization, ROI extraction, and feature computation
"""

import asyncio
import logging
import os
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import cv2
import numpy as np
import zmq
import zmq.asyncio
from fastapi import FastAPI
import yaml
import redis.asyncio as redis
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class PreprocessingConfig:
    """Preprocessing configuration"""
    target_width: int = 640
    target_height: int = 480
    face_blur_enabled: bool = True
    normalize: bool = True
    compute_optical_flow: bool = True
    deduplication_threshold: float = 0.95
    frame_buffer_size: int = 10


class FramePreprocessor:
    """Handles frame preprocessing operations"""
    
    def __init__(self, config: PreprocessingConfig):
        self.config = config
        self.face_cascade = None
        self.prev_frames = {}  # Store previous frames for optical flow
        self.frame_hashes = {}  # For deduplication
        
        # Load face detection cascade if face blur is enabled
        if self.config.face_blur_enabled:
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                logger.info("Face detection cascade loaded")
            except Exception as e:
                logger.warning(f"Failed to load face detection cascade: {e}")
    
    def resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Resize frame to target dimensions"""
        return cv2.resize(frame, (self.config.target_width, self.config.target_height))
    
    def blur_faces(self, frame: np.ndarray) -> np.ndarray:
        """Blur detected faces for privacy"""
        if not self.face_cascade:
            return frame
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            for (x, y, w, h) in faces:
                # Apply strong Gaussian blur to face region
                face_region = frame[y:y+h, x:x+w]
                blurred_face = cv2.GaussianBlur(face_region, (99, 99), 30)
                frame[y:y+h, x:x+w] = blurred_face
            
            if len(faces) > 0:
                logger.debug(f"Blurred {len(faces)} faces")
                
        except Exception as e:
            logger.error(f"Error blurring faces: {e}")
        
        return frame
    
    def extract_roi(self, frame: np.ndarray, roi: Optional[Dict]) -> np.ndarray:
        """Extract region of interest if specified"""
        if not roi:
            return frame
        
        x = roi.get('x', 0)
        y = roi.get('y', 0)
        w = roi.get('width', frame.shape[1])
        h = roi.get('height', frame.shape[0])
        
        return frame[y:y+h, x:x+w]
    
    def normalize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Normalize pixel values to [0, 1]"""
        if not self.config.normalize:
            return frame
        
        return frame.astype(np.float32) / 255.0
    
    def compute_optical_flow_features(
        self, 
        frame: np.ndarray, 
        camera_id: str
    ) -> Optional[np.ndarray]:
        """Compute optical flow between current and previous frame"""
        if not self.config.compute_optical_flow:
            return None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Get previous frame
        prev_gray = self.prev_frames.get(camera_id)
        
        if prev_gray is None:
            self.prev_frames[camera_id] = gray
            return None
        
        try:
            # Compute dense optical flow using Farneback method
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray, None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0
            )
            
            # Update previous frame
            self.prev_frames[camera_id] = gray
            
            return flow
            
        except Exception as e:
            logger.error(f"Error computing optical flow: {e}")
            return None
    
    def is_duplicate(self, frame: np.ndarray, camera_id: str) -> bool:
        """Check if frame is duplicate using perceptual hashing"""
        try:
            # Compute simple hash
            small = cv2.resize(frame, (8, 8), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            avg = gray.mean()
            frame_hash = (gray > avg).flatten()
            
            # Check against previous hash
            if camera_id in self.frame_hashes:
                prev_hash = self.frame_hashes[camera_id]
                similarity = np.mean(frame_hash == prev_hash)
                
                if similarity >= self.config.deduplication_threshold:
                    return True
            
            # Update hash
            self.frame_hashes[camera_id] = frame_hash
            return False
            
        except Exception as e:
            logger.error(f"Error in deduplication: {e}")
            return False
    
    def preprocess(
        self, 
        frame: np.ndarray, 
        metadata: Dict
    ) -> Tuple[np.ndarray, Optional[np.ndarray], Dict]:
        """
        Main preprocessing pipeline
        Returns: (preprocessed_frame, optical_flow, updated_metadata)
        """
        camera_id = metadata.get('camera_id')
        
        # Check for duplicate
        if self.is_duplicate(frame, camera_id):
            logger.debug(f"Duplicate frame detected for camera {camera_id}")
            metadata['is_duplicate'] = True
            return None, None, metadata
        
        metadata['is_duplicate'] = False
        
        # Extract ROI if specified
        roi = metadata.get('roi')
        if roi:
            frame = self.extract_roi(frame, roi)
        
        # Blur faces for privacy
        if self.config.face_blur_enabled:
            frame = self.blur_faces(frame)
            metadata['faces_blurred'] = True
        
        # Compute optical flow before resizing
        optical_flow = self.compute_optical_flow_features(frame, camera_id)
        metadata['has_optical_flow'] = optical_flow is not None
        
        # Resize to standard dimensions
        frame = self.resize_frame(frame)
        
        # Normalize
        if self.config.normalize:
            frame = self.normalize_frame(frame)
            metadata['normalized'] = True
        
        metadata['preprocessed_shape'] = frame.shape
        metadata['preprocessing_timestamp'] = datetime.utcnow().isoformat()
        
        return frame, optical_flow, metadata


class PreprocessingService:
    """Main preprocessing service"""
    
    def __init__(self):
        self.config = PreprocessingConfig(
            face_blur_enabled=os.getenv("FACE_BLUR_ENABLED", "true").lower() == "true",
            target_width=int(os.getenv("TARGET_WIDTH", "640")),
            target_height=int(os.getenv("TARGET_HEIGHT", "480")),
        )
        self.preprocessor = FramePreprocessor(self.config)
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_subscriber = None
        self.zmq_publisher = None
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.processed_count = 0
        self.skipped_count = 0
    
    async def initialize(self):
        """Initialize service"""
        try:
            # Connect ZeroMQ subscriber to camera-ingest
            ingest_host = os.getenv("CAMERA_INGEST_HOST", "camera-ingest")
            ingest_port = os.getenv("CAMERA_INGEST_ZMQ_PORT", "5555")
            self.zmq_subscriber = self.zmq_context.socket(zmq.SUB)
            self.zmq_subscriber.connect(f"tcp://{ingest_host}:{ingest_port}")
            self.zmq_subscriber.setsockopt_string(zmq.SUBSCRIBE, "frames")
            logger.info(f"Connected to camera-ingest at {ingest_host}:{ingest_port}")
            
            # Bind ZeroMQ publisher for model services
            pub_port = os.getenv("ZMQ_PUB_PORT", "5556")
            self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
            self.zmq_publisher.bind(f"tcp://*:{pub_port}")
            logger.info(f"ZeroMQ publisher bound to port {pub_port}")
            
            # Connect to Redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = await redis.from_url(redis_url)
            logger.info(f"Connected to Redis: {redis_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    async def process_frames(self):
        """Main frame processing loop"""
        self.running = True
        logger.info("Starting frame processing loop")
        
        while self.running:
            try:
                # Receive frame from camera-ingest
                message = await self.zmq_subscriber.recv_multipart()
                
                if len(message) != 3:
                    logger.warning("Received malformed message")
                    continue
                
                topic, metadata_bytes, frame_bytes = message
                
                # Parse metadata
                metadata = yaml.safe_load(metadata_bytes.decode('utf-8'))
                
                # Decode frame
                frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                
                if frame is None:
                    logger.warning("Failed to decode frame")
                    continue
                
                # Preprocess frame
                processed_frame, optical_flow, updated_metadata = self.preprocessor.preprocess(
                    frame, metadata
                )
                
                # Skip duplicates
                if updated_metadata.get('is_duplicate'):
                    self.skipped_count += 1
                    continue
                
                # Publish to model services
                await self.publish_to_models(processed_frame, optical_flow, updated_metadata)
                
                self.processed_count += 1
                
                # Update stats in Redis
                if self.processed_count % 100 == 0:
                    await self.redis_client.setex(
                        "preprocessing:stats",
                        60,
                        f"processed={self.processed_count},skipped={self.skipped_count}"
                    )
                
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                await asyncio.sleep(0.1)
    
    async def publish_to_models(
        self, 
        frame: np.ndarray, 
        optical_flow: Optional[np.ndarray],
        metadata: Dict
    ):
        """Publish preprocessed data to model services"""
        try:
            # Encode frame
            if metadata.get('normalized'):
                # Convert back to uint8 for encoding
                frame_uint8 = (frame * 255).astype(np.uint8)
            else:
                frame_uint8 = frame
            
            _, buffer = cv2.imencode('.jpg', frame_uint8, [cv2.IMWRITE_JPEG_QUALITY, 90])
            frame_bytes = buffer.tobytes()
            
            # Encode optical flow if available
            flow_bytes = b""
            if optical_flow is not None:
                flow_bytes = optical_flow.tobytes()
                metadata['optical_flow_shape'] = optical_flow.shape
            
            # Publish to different model topics
            for topic in [b"skele_input", b"motion_input", b"mood_input"]:
                await self.zmq_publisher.send_multipart([
                    topic,
                    yaml.dump(metadata).encode('utf-8'),
                    frame_bytes,
                    flow_bytes
                ])
            
        except Exception as e:
            logger.error(f"Error publishing to models: {e}")
    
    async def stop(self):
        """Stop processing"""
        self.running = False
        if self.zmq_subscriber:
            self.zmq_subscriber.close()
        if self.zmq_publisher:
            self.zmq_publisher.close()
        if self.redis_client:
            await self.redis_client.close()
        self.zmq_context.term()
        logger.info("Preprocessing service stopped")


# FastAPI application
app = FastAPI(title="Guardia Preprocessing Service", version="1.0.0")
service = PreprocessingService()


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await service.initialize()
    # Start processing in background
    asyncio.create_task(service.process_frames())


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    await service.stop()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "preprocessing"}


@app.get("/status")
async def get_status():
    """Get service status"""
    return {
        "service": "preprocessing",
        "running": service.running,
        "processed_frames": service.processed_count,
        "skipped_frames": service.skipped_count,
        "config": {
            "face_blur_enabled": service.config.face_blur_enabled,
            "target_resolution": f"{service.config.target_width}x{service.config.target_height}",
            "optical_flow_enabled": service.config.compute_optical_flow,
            "deduplication_enabled": True,
            "deduplication_threshold": service.config.deduplication_threshold
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
