"""
Edge Computing Service for Guardia AI
Local video processing, bandwidth optimization, and intelligent caching
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import cv2
import numpy as np
import aiofiles
import aiosqlite
from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import yaml
import json
import redis.asyncio as redis
from pydantic import BaseModel
import psutil
from minio import Minio
from minio.error import S3Error
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import zmq
import zmq.asyncio

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
frames_processed = Counter('edge_frames_processed_total', 'Total frames processed', ['camera_id'])
motion_events = Counter('edge_motion_events_total', 'Motion events detected', ['camera_id'])
processing_time = Histogram('edge_processing_time_seconds', 'Frame processing time')
storage_used = Gauge('edge_storage_used_bytes', 'Storage used in bytes')
cpu_usage = Gauge('edge_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('edge_memory_usage_percent', 'Memory usage percentage')


class EventType(str, Enum):
    MOTION = "motion"
    FACE = "face"
    OBJECT = "object"
    SCENE_CHANGE = "scene_change"
    ANOMALY = "anomaly"


@dataclass
class ProcessingConfig:
    """Edge processing configuration"""
    motion_threshold: int = 25
    min_contour_area: int = 500
    frame_skip: int = 2
    compression_quality: int = 75
    max_frame_width: int = 640
    max_frame_height: int = 480
    delta_encoding: bool = True
    face_detection: bool = True
    object_detection: bool = False


@dataclass
class StorageConfig:
    """Local storage configuration"""
    base_path: str = "/app/data"
    clips_path: str = "/app/data/clips"
    snapshots_path: str = "/app/data/snapshots"
    cache_path: str = "/app/data/cache"
    max_storage_gb: float = 50.0
    retention_days: int = 7
    clip_duration: int = 30  # seconds


@dataclass
class DetectionResult:
    """Result from edge detection"""
    event_type: EventType
    confidence: float
    bounding_box: Optional[Tuple[int, int, int, int]] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MotionDetector:
    """Efficient motion detection using frame differencing"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.prev_frame = None
        self.background = None
        self.motion_history = []
        
    def detect(self, frame: np.ndarray) -> Tuple[bool, List[Tuple[int, int, int, int]], float]:
        """
        Detect motion in frame
        Returns: (has_motion, bounding_boxes, motion_score)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Initialize background
        if self.background is None:
            self.background = gray.copy().astype("float")
            self.prev_frame = gray
            return False, [], 0.0
        
        # Update background model
        cv2.accumulateWeighted(gray, self.background, 0.5)
        
        # Compute difference
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.background))
        
        # Threshold
        thresh = cv2.threshold(
            frame_delta, 
            self.config.motion_threshold, 
            255, 
            cv2.THRESH_BINARY
        )[1]
        
        # Dilate to fill gaps
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(
            thresh.copy(), 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filter and extract bounding boxes
        bboxes = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.config.min_contour_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            bboxes.append((x, y, w, h))
            total_area += area
        
        # Calculate motion score
        frame_area = frame.shape[0] * frame.shape[1]
        motion_score = min(total_area / frame_area, 1.0)
        
        has_motion = len(bboxes) > 0
        
        self.prev_frame = gray
        
        return has_motion, bboxes, motion_score
    
    def reset(self):
        """Reset motion detector state"""
        self.prev_frame = None
        self.background = None


class FaceDetector:
    """Lightweight face detection"""
    
    def __init__(self):
        # Use OpenCV's DNN face detector
        self.net = None
        self._load_model()
    
    def _load_model(self):
        """Load face detection model"""
        try:
            # Use Haar cascades as fallback (lightweight)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.cascade = cv2.CascadeClassifier(cascade_path)
            logger.info("Face detector initialized with Haar cascades")
        except Exception as e:
            logger.warning(f"Failed to load face detector: {e}")
            self.cascade = None
    
    def detect(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in frame"""
        if self.cascade is None:
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = self.cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return [tuple(face) for face in faces]


class SceneChangeDetector:
    """Detect significant scene changes"""
    
    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self.prev_hist = None
    
    def detect(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Detect scene change using histogram comparison
        Returns: (is_scene_change, change_score)
        """
        # Calculate histogram
        hist = cv2.calcHist(
            [frame], [0, 1, 2], None, 
            [8, 8, 8], [0, 256, 0, 256, 0, 256]
        )
        hist = cv2.normalize(hist, hist).flatten()
        
        if self.prev_hist is None:
            self.prev_hist = hist
            return False, 0.0
        
        # Compare histograms
        correlation = cv2.compareHist(self.prev_hist, hist, cv2.HISTCMP_CORREL)
        change_score = 1 - correlation
        
        self.prev_hist = hist
        
        is_scene_change = change_score > self.threshold
        
        return is_scene_change, change_score


class LocalStorageManager:
    """Manage local storage for clips and snapshots"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create storage directories"""
        for path in [self.config.clips_path, self.config.snapshots_path, self.config.cache_path]:
            Path(path).mkdir(parents=True, exist_ok=True)
    
    async def save_snapshot(
        self, 
        camera_id: str, 
        frame: np.ndarray, 
        event_type: str = None
    ) -> str:
        """Save a snapshot"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{camera_id}_{timestamp}.jpg"
        filepath = os.path.join(self.config.snapshots_path, filename)
        
        # Encode and save
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(buffer.tobytes())
        
        return filename
    
    async def save_clip(
        self, 
        camera_id: str, 
        frames: List[np.ndarray],
        fps: int = 15
    ) -> str:
        """Save a video clip"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{camera_id}_{timestamp}.mp4"
        filepath = os.path.join(self.config.clips_path, filename)
        
        if not frames:
            return None
        
        # Get frame dimensions
        height, width = frames[0].shape[:2]
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
        
        for frame in frames:
            writer.write(frame)
        
        writer.release()
        
        return filename
    
    async def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        total_size = 0
        file_count = 0
        
        for root, dirs, files in os.walk(self.config.base_path):
            for file in files:
                filepath = os.path.join(root, file)
                total_size += os.path.getsize(filepath)
                file_count += 1
        
        return {
            "total_size_bytes": total_size,
            "total_size_gb": total_size / (1024 ** 3),
            "file_count": file_count,
            "max_storage_gb": self.config.max_storage_gb,
            "usage_percent": (total_size / (self.config.max_storage_gb * 1024 ** 3)) * 100
        }
    
    async def cleanup_old_files(self):
        """Remove files older than retention period"""
        cutoff = datetime.utcnow() - timedelta(days=self.config.retention_days)
        removed_count = 0
        
        for path in [self.config.clips_path, self.config.snapshots_path]:
            for filename in os.listdir(path):
                filepath = os.path.join(path, filename)
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                if file_time < cutoff:
                    os.remove(filepath)
                    removed_count += 1
        
        logger.info(f"Cleaned up {removed_count} old files")
        return removed_count
    
    async def list_clips(self, camera_id: str = None) -> List[Dict]:
        """List stored clips"""
        clips = []
        
        for filename in os.listdir(self.config.clips_path):
            if camera_id and not filename.startswith(camera_id):
                continue
            
            filepath = os.path.join(self.config.clips_path, filename)
            stat = os.stat(filepath)
            
            clips.append({
                "filename": filename,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "camera_id": filename.split("_")[0]
            })
        
        return sorted(clips, key=lambda x: x["created_at"], reverse=True)
    
    async def list_snapshots(self, camera_id: str = None, limit: int = 100) -> List[Dict]:
        """List stored snapshots"""
        snapshots = []
        
        for filename in os.listdir(self.config.snapshots_path):
            if camera_id and not filename.startswith(camera_id):
                continue
            
            filepath = os.path.join(self.config.snapshots_path, filename)
            stat = os.stat(filepath)
            
            snapshots.append({
                "filename": filename,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "camera_id": filename.split("_")[0]
            })
        
        # Sort by creation time, newest first
        snapshots.sort(key=lambda x: x["created_at"], reverse=True)
        
        return snapshots[:limit]


class BandwidthOptimizer:
    """Optimize bandwidth usage"""
    
    def __init__(self, config: ProcessingConfig):
        self.config = config
        self.prev_frame = None
    
    def resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Resize frame to max dimensions"""
        height, width = frame.shape[:2]
        
        if width <= self.config.max_frame_width and height <= self.config.max_frame_height:
            return frame
        
        # Calculate scaling factor
        scale = min(
            self.config.max_frame_width / width,
            self.config.max_frame_height / height
        )
        
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        return cv2.resize(frame, (new_width, new_height))
    
    def compress_frame(
        self, 
        frame: np.ndarray, 
        quality: int = None,
        adaptive: bool = True
    ) -> bytes:
        """Compress frame with adaptive quality"""
        if quality is None:
            quality = self.config.compression_quality
        
        if adaptive:
            # Lower quality for high motion scenes
            motion_score = self._estimate_motion(frame)
            if motion_score > 0.5:
                quality = max(quality - 20, 30)
        
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buffer.tobytes()
    
    def _estimate_motion(self, frame: np.ndarray) -> float:
        """Quick motion estimation"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return 0.0
        
        diff = cv2.absdiff(self.prev_frame, gray)
        motion_score = np.mean(diff) / 255.0
        
        self.prev_frame = gray
        
        return motion_score
    
    def compute_delta(self, frame: np.ndarray) -> Optional[bytes]:
        """Compute frame delta for efficient transmission"""
        if not self.config.delta_encoding:
            return None
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_frame is None:
            self.prev_frame = gray
            return None
        
        delta = cv2.absdiff(self.prev_frame, gray)
        self.prev_frame = gray
        
        _, buffer = cv2.imencode('.jpg', delta, [cv2.IMWRITE_JPEG_QUALITY, 50])
        return buffer.tobytes()


class EventDatabase:
    """Local SQLite database for event storage"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize database schema"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    camera_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    confidence REAL,
                    timestamp TEXT NOT NULL,
                    snapshot_path TEXT,
                    clip_path TEXT,
                    metadata TEXT,
                    synced INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_camera 
                ON events(camera_id)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp)
            """)
            
            await db.commit()
    
    async def insert_event(
        self,
        camera_id: str,
        event_type: str,
        confidence: float,
        snapshot_path: str = None,
        clip_path: str = None,
        metadata: Dict = None
    ) -> int:
        """Insert a new event"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO events (camera_id, event_type, confidence, timestamp, 
                                   snapshot_path, clip_path, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    camera_id,
                    event_type,
                    confidence,
                    datetime.utcnow().isoformat(),
                    snapshot_path,
                    clip_path,
                    json.dumps(metadata) if metadata else None
                )
            )
            await db.commit()
            return cursor.lastrowid
    
    async def get_events(
        self,
        camera_id: str = None,
        event_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[Dict]:
        """Query events"""
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if camera_id:
            query += " AND camera_id = ?"
            params.append(camera_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_unsynced_events(self, limit: int = 100) -> List[Dict]:
        """Get events not yet synced to cloud"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM events WHERE synced = 0 ORDER BY timestamp LIMIT ?",
                (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def mark_synced(self, event_ids: List[int]):
        """Mark events as synced"""
        async with aiosqlite.connect(self.db_path) as db:
            placeholders = ",".join("?" * len(event_ids))
            await db.execute(
                f"UPDATE events SET synced = 1 WHERE id IN ({placeholders})",
                event_ids
            )
            await db.commit()


class EdgeProcessor:
    """Main edge processing engine"""
    
    def __init__(
        self,
        processing_config: ProcessingConfig,
        storage_config: StorageConfig
    ):
        self.processing_config = processing_config
        self.storage_config = storage_config
        
        # Initialize detectors
        self.motion_detectors: Dict[str, MotionDetector] = {}
        self.face_detector = FaceDetector()
        self.scene_detector = SceneChangeDetector()
        
        # Initialize managers
        self.storage = LocalStorageManager(storage_config)
        self.optimizer = BandwidthOptimizer(processing_config)
        
        # Frame buffers for clip recording
        self.frame_buffers: Dict[str, List[np.ndarray]] = {}
        self.buffer_max_frames = storage_config.clip_duration * 15  # 15 fps
        
        # Statistics
        self.stats = {
            "frames_processed": 0,
            "motion_events": 0,
            "face_detections": 0,
            "snapshots_saved": 0,
            "clips_saved": 0
        }
    
    def get_motion_detector(self, camera_id: str) -> MotionDetector:
        """Get or create motion detector for camera"""
        if camera_id not in self.motion_detectors:
            self.motion_detectors[camera_id] = MotionDetector(self.processing_config)
        return self.motion_detectors[camera_id]
    
    async def process_frame(
        self,
        camera_id: str,
        frame: np.ndarray,
        save_on_event: bool = True
    ) -> List[DetectionResult]:
        """Process a single frame"""
        start_time = time.time()
        results = []
        
        # Resize for processing
        processed_frame = self.optimizer.resize_frame(frame)
        
        # Motion detection
        motion_detector = self.get_motion_detector(camera_id)
        has_motion, motion_bboxes, motion_score = motion_detector.detect(processed_frame)
        
        if has_motion:
            results.append(DetectionResult(
                event_type=EventType.MOTION,
                confidence=motion_score,
                metadata={"bounding_boxes": motion_bboxes}
            ))
            self.stats["motion_events"] += 1
            motion_events.labels(camera_id=camera_id).inc()
        
        # Face detection (if enabled and motion detected)
        if self.processing_config.face_detection and has_motion:
            faces = self.face_detector.detect(processed_frame)
            if faces:
                results.append(DetectionResult(
                    event_type=EventType.FACE,
                    confidence=0.9,
                    metadata={"faces": faces, "count": len(faces)}
                ))
                self.stats["face_detections"] += len(faces)
        
        # Scene change detection
        is_scene_change, change_score = self.scene_detector.detect(processed_frame)
        if is_scene_change:
            results.append(DetectionResult(
                event_type=EventType.SCENE_CHANGE,
                confidence=change_score,
                metadata={}
            ))
        
        # Update frame buffer
        if camera_id not in self.frame_buffers:
            self.frame_buffers[camera_id] = []
        
        self.frame_buffers[camera_id].append(frame.copy())
        if len(self.frame_buffers[camera_id]) > self.buffer_max_frames:
            self.frame_buffers[camera_id].pop(0)
        
        # Save snapshot on significant event
        if save_on_event and results and any(r.confidence > 0.5 for r in results):
            await self.storage.save_snapshot(camera_id, frame, results[0].event_type)
            self.stats["snapshots_saved"] += 1
        
        # Update statistics
        self.stats["frames_processed"] += 1
        frames_processed.labels(camera_id=camera_id).inc()
        
        processing_time.observe(time.time() - start_time)
        
        return results
    
    async def save_event_clip(self, camera_id: str) -> Optional[str]:
        """Save buffered frames as clip"""
        if camera_id not in self.frame_buffers:
            return None
        
        frames = self.frame_buffers[camera_id].copy()
        if not frames:
            return None
        
        filename = await self.storage.save_clip(camera_id, frames)
        self.stats["clips_saved"] += 1
        
        return filename
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        return {
            **self.stats,
            "active_cameras": len(self.motion_detectors),
            "buffer_sizes": {k: len(v) for k, v in self.frame_buffers.items()}
        }


class CloudSyncManager:
    """Sync local data to cloud storage"""
    
    def __init__(
        self,
        minio_endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str = "guardia-edge"
    ):
        self.client = Minio(
            minio_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )
        self.bucket = bucket
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as e:
            logger.error(f"Failed to create bucket: {e}")
    
    async def sync_file(self, local_path: str, remote_path: str) -> bool:
        """Sync a file to cloud"""
        try:
            self.client.fput_object(self.bucket, remote_path, local_path)
            return True
        except S3Error as e:
            logger.error(f"Failed to sync file: {e}")
            return False
    
    async def sync_events(
        self,
        event_db: EventDatabase,
        storage: LocalStorageManager
    ) -> int:
        """Sync unsynced events to cloud"""
        events = await event_db.get_unsynced_events()
        synced_count = 0
        synced_ids = []
        
        for event in events:
            try:
                # Sync snapshot
                if event.get("snapshot_path"):
                    local_path = os.path.join(
                        storage.config.snapshots_path,
                        event["snapshot_path"]
                    )
                    if os.path.exists(local_path):
                        remote_path = f"snapshots/{event['snapshot_path']}"
                        await self.sync_file(local_path, remote_path)
                
                # Sync clip
                if event.get("clip_path"):
                    local_path = os.path.join(
                        storage.config.clips_path,
                        event["clip_path"]
                    )
                    if os.path.exists(local_path):
                        remote_path = f"clips/{event['clip_path']}"
                        await self.sync_file(local_path, remote_path)
                
                synced_ids.append(event["id"])
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Failed to sync event {event['id']}: {e}")
        
        if synced_ids:
            await event_db.mark_synced(synced_ids)
        
        return synced_count


# FastAPI Application
processing_config = ProcessingConfig(
    motion_threshold=int(os.getenv("MOTION_THRESHOLD", "25")),
    min_contour_area=int(os.getenv("MIN_CONTOUR_AREA", "500")),
    frame_skip=int(os.getenv("FRAME_SKIP", "2")),
    compression_quality=int(os.getenv("COMPRESSION_QUALITY", "75"))
)

storage_config = StorageConfig(
    base_path=os.getenv("LOCAL_STORAGE_PATH", "/app/data"),
    clips_path=os.getenv("CLIPS_PATH", "/app/data/clips"),
    snapshots_path=os.getenv("SNAPSHOTS_PATH", "/app/data/snapshots"),
    cache_path=os.getenv("CACHE_PATH", "/app/data/cache"),
    max_storage_gb=float(os.getenv("MAX_STORAGE_GB", "50")),
    retention_days=int(os.getenv("RETENTION_DAYS", "7"))
)

processor = EdgeProcessor(processing_config, storage_config)
event_db = EventDatabase(os.path.join(storage_config.base_path, "events.db"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await event_db.initialize()
    logger.info("Edge computing service started")
    
    # Start background tasks
    asyncio.create_task(update_metrics_loop())
    asyncio.create_task(cleanup_loop())
    
    yield
    
    # Shutdown
    logger.info("Edge computing service stopped")


async def update_metrics_loop():
    """Periodically update system metrics"""
    while True:
        try:
            cpu_usage.set(psutil.cpu_percent())
            memory_usage.set(psutil.virtual_memory().percent)
            
            stats = await processor.storage.get_storage_stats()
            storage_used.set(stats["total_size_bytes"])
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
        
        await asyncio.sleep(10)


async def cleanup_loop():
    """Periodically clean up old files"""
    while True:
        try:
            await processor.storage.cleanup_old_files()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        await asyncio.sleep(3600)  # Every hour


app = FastAPI(
    title="Guardia Edge Computing",
    description="Local video processing and storage",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health and Status Endpoints
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "edge-compute"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/status")
async def get_status():
    stats = processor.get_stats()
    storage_stats = await processor.storage.get_storage_stats()
    
    return {
        "service": "edge-compute",
        "processing": stats,
        "storage": storage_stats,
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent
        }
    }


# Processing Endpoints
class ProcessFrameRequest(BaseModel):
    camera_id: str
    save_on_event: bool = True


@app.post("/process/frame")
async def process_frame(
    camera_id: str,
    file: UploadFile = File(...)
):
    """Process a single frame"""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image")
    
    results = await processor.process_frame(camera_id, frame)
    
    # Store event if significant
    for result in results:
        if result.confidence > 0.5:
            await event_db.insert_event(
                camera_id=camera_id,
                event_type=result.event_type.value,
                confidence=result.confidence,
                metadata=result.metadata
            )
    
    return {
        "camera_id": camera_id,
        "events": [
            {
                "type": r.event_type.value,
                "confidence": r.confidence,
                "metadata": r.metadata
            }
            for r in results
        ]
    }


@app.get("/process/stats")
async def get_processing_stats():
    """Get processing statistics"""
    return processor.get_stats()


# Storage Endpoints
@app.get("/storage/clips")
async def list_clips(camera_id: Optional[str] = None):
    """List stored clips"""
    clips = await processor.storage.list_clips(camera_id)
    return {"clips": clips}


@app.get("/storage/clips/{filename}")
async def get_clip(filename: str):
    """Get a specific clip"""
    filepath = os.path.join(processor.storage.config.clips_path, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(filepath, media_type="video/mp4")


@app.delete("/storage/clips/{filename}")
async def delete_clip(filename: str):
    """Delete a clip"""
    filepath = os.path.join(processor.storage.config.clips_path, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Clip not found")
    os.remove(filepath)
    return {"status": "deleted", "filename": filename}


@app.get("/storage/snapshots")
async def list_snapshots(camera_id: Optional[str] = None, limit: int = 100):
    """List stored snapshots"""
    snapshots = await processor.storage.list_snapshots(camera_id, limit)
    return {"snapshots": snapshots}


@app.get("/storage/snapshots/{filename}")
async def get_snapshot(filename: str):
    """Get a specific snapshot"""
    filepath = os.path.join(processor.storage.config.snapshots_path, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return FileResponse(filepath, media_type="image/jpeg")


@app.get("/storage/stats")
async def get_storage_stats():
    """Get storage statistics"""
    return await processor.storage.get_storage_stats()


@app.post("/storage/cleanup")
async def trigger_cleanup():
    """Manually trigger cleanup"""
    removed = await processor.storage.cleanup_old_files()
    return {"removed_files": removed}


# Events Endpoints
@app.get("/events")
async def get_events(
    camera_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100
):
    """Get local events"""
    events = await event_db.get_events(camera_id, event_type, limit=limit)
    return {"events": events}


@app.post("/events/{camera_id}/clip")
async def save_event_clip(camera_id: str):
    """Save current buffer as clip"""
    filename = await processor.save_event_clip(camera_id)
    if not filename:
        raise HTTPException(status_code=404, detail="No frames buffered")
    return {"filename": filename, "camera_id": camera_id}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("EDGE_COMPUTE_PORT", "8011"))
    uvicorn.run(app, host="0.0.0.0", port=port)
