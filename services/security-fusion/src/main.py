"""
Security Fusion Model Service for Guardia AI
Multi-modal fusion for owner protection with facial recognition, 
anomaly detection, and multi-person tracking
"""

import asyncio
import logging
import os
import time
import pickle
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import uuid
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import yaml
import json
import redis.asyncio as redis
from pydantic import BaseModel
import aiofiles
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import zmq
import zmq.asyncio
from scipy.spatial.distance import cosine
from collections import defaultdict
import hashlib
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
face_recognitions = Counter('security_face_recognitions_total', 'Total face recognitions', ['result'])
tracking_active = Gauge('security_tracking_active_persons', 'Active tracked persons')
alerts_generated = Counter('security_alerts_generated_total', 'Alerts generated', ['severity'])
processing_time = Histogram('security_processing_time_seconds', 'Processing time')


class PersonType(str, Enum):
    OWNER = "owner"
    FAMILY = "family"
    GUEST = "guest"
    UNKNOWN = "unknown"
    INTRUDER = "intruder"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    UNKNOWN_PERSON = "unknown_person"
    INTRUSION = "intrusion"
    LOITERING = "loitering"
    ANOMALY = "anomaly"
    FACE_MATCH = "face_match"
    MULTIPLE_PERSONS = "multiple_persons"


@dataclass
class EnrolledFace:
    """Enrolled face data"""
    id: str
    name: str
    person_type: PersonType
    embeddings: List[np.ndarray]  # Multiple embeddings for robustness
    created_at: datetime
    last_seen: Optional[datetime] = None
    access_level: int = 1  # 1-10, 10 being highest
    notes: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "person_type": self.person_type.value,
            "created_at": self.created_at.isoformat(),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "access_level": self.access_level,
            "notes": self.notes
        }


@dataclass
class TrackedPerson:
    """Tracked person state"""
    id: str
    camera_id: str
    bounding_box: Tuple[int, int, int, int]
    first_seen: datetime
    last_seen: datetime
    trajectory: List[Tuple[int, int]]
    face_id: Optional[str] = None
    person_type: PersonType = PersonType.UNKNOWN
    confidence: float = 0.0
    velocity: Tuple[float, float] = (0.0, 0.0)
    is_loitering: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "bounding_box": self.bounding_box,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "person_type": self.person_type.value,
            "confidence": self.confidence,
            "is_loitering": self.is_loitering,
            "face_id": self.face_id
        }


@dataclass
class SecurityAlert:
    """Security alert"""
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    camera_id: str
    timestamp: datetime
    person_id: Optional[str] = None
    face_id: Optional[str] = None
    description: str = ""
    metadata: Dict = field(default_factory=dict)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp.isoformat(),
            "person_id": self.person_id,
            "face_id": self.face_id,
            "description": self.description,
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }


class FaceRecognitionEngine:
    """Face recognition with embedding-based matching"""
    
    def __init__(
        self,
        embeddings_path: str,
        tolerance: float = 0.6,
        model: str = "hog"
    ):
        self.embeddings_path = embeddings_path
        self.tolerance = tolerance
        self.model = model
        self.enrolled_faces: Dict[str, EnrolledFace] = {}
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self._encryption_key = os.getenv("FACE_ENCRYPTION_KEY", Fernet.generate_key())
        self._fernet = Fernet(self._encryption_key if isinstance(self._encryption_key, bytes) 
                              else self._encryption_key.encode())
        
        Path(embeddings_path).mkdir(parents=True, exist_ok=True)
        self._load_enrolled_faces()
    
    def _load_enrolled_faces(self):
        """Load enrolled faces from disk"""
        faces_file = os.path.join(self.embeddings_path, "faces.pkl")
        if os.path.exists(faces_file):
            try:
                with open(faces_file, "rb") as f:
                    encrypted_data = f.read()
                    decrypted_data = self._fernet.decrypt(encrypted_data)
                    self.enrolled_faces = pickle.loads(decrypted_data)
                logger.info(f"Loaded {len(self.enrolled_faces)} enrolled faces")
            except Exception as e:
                logger.error(f"Failed to load faces: {e}")
                self.enrolled_faces = {}
    
    def _save_enrolled_faces(self):
        """Save enrolled faces to disk (encrypted)"""
        faces_file = os.path.join(self.embeddings_path, "faces.pkl")
        try:
            data = pickle.dumps(self.enrolled_faces)
            encrypted_data = self._fernet.encrypt(data)
            with open(faces_file, "wb") as f:
                f.write(encrypted_data)
            logger.info(f"Saved {len(self.enrolled_faces)} enrolled faces")
        except Exception as e:
            logger.error(f"Failed to save faces: {e}")
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(50, 50)
        )
        
        return [tuple(face) for face in faces]
    
    def extract_embedding(self, image: np.ndarray, face_rect: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """Extract face embedding"""
        x, y, w, h = face_rect
        face_image = image[y:y+h, x:x+w]
        
        if face_image.size == 0:
            return None
        
        # Resize to standard size
        face_image = cv2.resize(face_image, (128, 128))
        
        # Simple embedding: flatten normalized histogram
        # In production, use a proper face embedding model
        hsv = cv2.cvtColor(face_image, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        return hist
    
    def enroll_face(
        self,
        name: str,
        person_type: PersonType,
        images: List[np.ndarray],
        access_level: int = 1,
        notes: str = None
    ) -> EnrolledFace:
        """Enroll a new face"""
        face_id = str(uuid.uuid4())
        embeddings = []
        
        for image in images:
            faces = self.detect_faces(image)
            if faces:
                embedding = self.extract_embedding(image, faces[0])
                if embedding is not None:
                    embeddings.append(embedding)
        
        if not embeddings:
            raise ValueError("No valid face found in provided images")
        
        enrolled = EnrolledFace(
            id=face_id,
            name=name,
            person_type=person_type,
            embeddings=embeddings,
            created_at=datetime.utcnow(),
            access_level=access_level,
            notes=notes
        )
        
        self.enrolled_faces[face_id] = enrolled
        self._save_enrolled_faces()
        
        logger.info(f"Enrolled face: {name} ({face_id})")
        return enrolled
    
    def recognize_face(
        self,
        image: np.ndarray,
        face_rect: Tuple[int, int, int, int]
    ) -> Tuple[Optional[EnrolledFace], float]:
        """Recognize a face"""
        embedding = self.extract_embedding(image, face_rect)
        
        if embedding is None:
            return None, 0.0
        
        best_match = None
        best_distance = float('inf')
        
        for face in self.enrolled_faces.values():
            for enrolled_emb in face.embeddings:
                distance = cosine(embedding, enrolled_emb)
                if distance < best_distance:
                    best_distance = distance
                    best_match = face
        
        if best_match and best_distance < self.tolerance:
            # Update last seen
            best_match.last_seen = datetime.utcnow()
            confidence = 1 - best_distance
            return best_match, confidence
        
        return None, 0.0
    
    def delete_face(self, face_id: str) -> bool:
        """Delete enrolled face"""
        if face_id in self.enrolled_faces:
            del self.enrolled_faces[face_id]
            self._save_enrolled_faces()
            return True
        return False
    
    def get_all_faces(self) -> List[Dict]:
        """Get all enrolled faces"""
        return [face.to_dict() for face in self.enrolled_faces.values()]


class PersonTracker:
    """Multi-person tracking using simple IoU-based tracking"""
    
    def __init__(
        self,
        max_age: int = 30,
        min_hits: int = 3,
        iou_threshold: float = 0.3
    ):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracks: Dict[str, TrackedPerson] = {}
        self.track_history: List[TrackedPerson] = []
        self.next_id = 0
    
    def _iou(self, box1: Tuple, box2: Tuple) -> float:
        """Calculate Intersection over Union"""
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        
        box1_area = w1 * h1
        box2_area = w2 * h2
        
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0
    
    def update(
        self,
        camera_id: str,
        detections: List[Tuple[int, int, int, int]],
        face_matches: Dict[int, Tuple[Optional[EnrolledFace], float]] = None
    ) -> List[TrackedPerson]:
        """Update tracks with new detections"""
        current_time = datetime.utcnow()
        
        if face_matches is None:
            face_matches = {}
        
        # Match detections to existing tracks
        matched_tracks = set()
        matched_detections = set()
        
        for det_idx, detection in enumerate(detections):
            best_track_id = None
            best_iou = self.iou_threshold
            
            for track_id, track in self.tracks.items():
                if track.camera_id != camera_id:
                    continue
                
                iou = self._iou(detection, track.bounding_box)
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id
            
            if best_track_id:
                # Update existing track
                track = self.tracks[best_track_id]
                old_center = (
                    track.bounding_box[0] + track.bounding_box[2] // 2,
                    track.bounding_box[1] + track.bounding_box[3] // 2
                )
                new_center = (
                    detection[0] + detection[2] // 2,
                    detection[1] + detection[3] // 2
                )
                
                track.bounding_box = detection
                track.last_seen = current_time
                track.trajectory.append(new_center)
                if len(track.trajectory) > 100:
                    track.trajectory.pop(0)
                
                # Calculate velocity
                dt = 1.0 / 15.0  # Assume 15 fps
                track.velocity = (
                    (new_center[0] - old_center[0]) / dt,
                    (new_center[1] - old_center[1]) / dt
                )
                
                # Update face info
                if det_idx in face_matches:
                    face, conf = face_matches[det_idx]
                    if face:
                        track.face_id = face.id
                        track.person_type = face.person_type
                        track.confidence = conf
                
                matched_tracks.add(best_track_id)
                matched_detections.add(det_idx)
        
        # Create new tracks for unmatched detections
        for det_idx, detection in enumerate(detections):
            if det_idx in matched_detections:
                continue
            
            track_id = f"track_{self.next_id}"
            self.next_id += 1
            
            center = (
                detection[0] + detection[2] // 2,
                detection[1] + detection[3] // 2
            )
            
            person_type = PersonType.UNKNOWN
            face_id = None
            confidence = 0.0
            
            if det_idx in face_matches:
                face, conf = face_matches[det_idx]
                if face:
                    face_id = face.id
                    person_type = face.person_type
                    confidence = conf
            
            self.tracks[track_id] = TrackedPerson(
                id=track_id,
                camera_id=camera_id,
                bounding_box=detection,
                first_seen=current_time,
                last_seen=current_time,
                trajectory=[center],
                face_id=face_id,
                person_type=person_type,
                confidence=confidence
            )
        
        # Remove stale tracks
        stale_tracks = []
        for track_id, track in self.tracks.items():
            age = (current_time - track.last_seen).total_seconds()
            if age > self.max_age / 15:  # Convert frames to seconds
                stale_tracks.append(track_id)
                self.track_history.append(track)
        
        for track_id in stale_tracks:
            del self.tracks[track_id]
        
        # Keep history manageable
        if len(self.track_history) > 1000:
            self.track_history = self.track_history[-500:]
        
        tracking_active.set(len(self.tracks))
        
        return list(self.tracks.values())
    
    def get_active_tracks(self, camera_id: str = None) -> List[TrackedPerson]:
        """Get active tracks"""
        if camera_id:
            return [t for t in self.tracks.values() if t.camera_id == camera_id]
        return list(self.tracks.values())
    
    def get_track_history(self, limit: int = 100) -> List[Dict]:
        """Get tracking history"""
        return [t.to_dict() for t in self.track_history[-limit:]]
    
    def reset(self):
        """Reset all tracks"""
        self.tracks.clear()
        self.next_id = 0


class AnomalyDetector:
    """Detect security anomalies"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.loitering_threshold = self.config.get("loitering_threshold", 60)  # seconds
        self.night_mode_start = self.config.get("night_mode_start", 22)
        self.night_mode_end = self.config.get("night_mode_end", 6)
        self.intrusion_zones: List[Tuple[int, int, int, int]] = self.config.get("intrusion_zones", [])
        
    def is_night_mode(self) -> bool:
        """Check if currently in night mode"""
        hour = datetime.now().hour
        if self.night_mode_start > self.night_mode_end:
            return hour >= self.night_mode_start or hour < self.night_mode_end
        return self.night_mode_start <= hour < self.night_mode_end
    
    def check_loitering(self, track: TrackedPerson) -> bool:
        """Check if person is loitering"""
        duration = (track.last_seen - track.first_seen).total_seconds()
        
        if duration < self.loitering_threshold:
            return False
        
        # Check movement - loitering if not moving much
        if len(track.trajectory) < 10:
            return False
        
        # Calculate total displacement
        start = track.trajectory[0]
        end = track.trajectory[-1]
        displacement = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        
        # If displacement is small relative to time, consider it loitering
        threshold = duration * 2  # Should move at least 2 pixels/second
        
        return displacement < threshold
    
    def check_intrusion(self, track: TrackedPerson) -> bool:
        """Check if person is in intrusion zone"""
        if not self.intrusion_zones:
            return False
        
        x, y, w, h = track.bounding_box
        center = (x + w // 2, y + h // 2)
        
        for zone in self.intrusion_zones:
            zx, zy, zw, zh = zone
            if zx <= center[0] <= zx + zw and zy <= center[1] <= zy + zh:
                return True
        
        return False
    
    def analyze(
        self,
        tracks: List[TrackedPerson],
        camera_id: str
    ) -> List[Dict]:
        """Analyze tracks for anomalies"""
        anomalies = []
        is_night = self.is_night_mode()
        
        for track in tracks:
            # Check for unknown person (more concerning at night)
            if track.person_type == PersonType.UNKNOWN:
                severity = AlertSeverity.HIGH if is_night else AlertSeverity.MEDIUM
                anomalies.append({
                    "type": AlertType.UNKNOWN_PERSON,
                    "severity": severity,
                    "track": track,
                    "description": f"Unknown person detected in camera {camera_id}"
                })
            
            # Check loitering
            if self.check_loitering(track):
                track.is_loitering = True
                anomalies.append({
                    "type": AlertType.LOITERING,
                    "severity": AlertSeverity.MEDIUM,
                    "track": track,
                    "description": f"Loitering detected: {track.id}"
                })
            
            # Check intrusion zones
            if self.check_intrusion(track):
                anomalies.append({
                    "type": AlertType.INTRUSION,
                    "severity": AlertSeverity.CRITICAL,
                    "track": track,
                    "description": f"Intrusion detected in restricted zone"
                })
        
        # Check for multiple unknown persons
        unknown_tracks = [t for t in tracks if t.person_type == PersonType.UNKNOWN]
        if len(unknown_tracks) > 2:
            anomalies.append({
                "type": AlertType.MULTIPLE_PERSONS,
                "severity": AlertSeverity.HIGH,
                "description": f"Multiple unknown persons ({len(unknown_tracks)}) detected"
            })
        
        return anomalies


class SecurityFusionService:
    """Main security fusion service"""
    
    def __init__(self):
        self.face_engine = FaceRecognitionEngine(
            embeddings_path=os.getenv("EMBEDDINGS_PATH", "/app/data/embeddings"),
            tolerance=float(os.getenv("FACE_TOLERANCE", "0.6")),
            model=os.getenv("FACE_MODEL", "hog")
        )
        self.tracker = PersonTracker()
        self.anomaly_detector = AnomalyDetector()
        self.alerts: List[SecurityAlert] = []
        self.redis_client: Optional[redis.Redis] = None
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
        
    async def initialize(self):
        """Initialize service"""
        try:
            # Connect to Redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = await redis.from_url(redis_url)
            
            # Bind ZeroMQ publisher
            zmq_port = os.getenv("ZMQ_PUB_PORT", "5561")
            self.zmq_publisher.bind(f"tcp://*:{zmq_port}")
            
            logger.info("Security fusion service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    async def process_frame(
        self,
        camera_id: str,
        frame: np.ndarray
    ) -> Dict:
        """Process a frame for security analysis"""
        start_time = time.time()
        
        # Detect faces
        faces = self.face_engine.detect_faces(frame)
        
        # Recognize faces
        face_matches = {}
        for i, face_rect in enumerate(faces):
            enrolled_face, confidence = self.face_engine.recognize_face(frame, face_rect)
            face_matches[i] = (enrolled_face, confidence)
            
            if enrolled_face:
                face_recognitions.labels(result="known").inc()
            else:
                face_recognitions.labels(result="unknown").inc()
        
        # Update tracking
        tracks = self.tracker.update(camera_id, faces, face_matches)
        
        # Analyze for anomalies
        anomalies = self.anomaly_detector.analyze(tracks, camera_id)
        
        # Generate alerts
        new_alerts = []
        for anomaly in anomalies:
            alert = SecurityAlert(
                id=str(uuid.uuid4()),
                alert_type=anomaly["type"],
                severity=anomaly["severity"],
                camera_id=camera_id,
                timestamp=datetime.utcnow(),
                person_id=anomaly.get("track", {}).id if anomaly.get("track") else None,
                description=anomaly["description"],
                metadata={"track_id": anomaly.get("track", {}).id if anomaly.get("track") else None}
            )
            self.alerts.append(alert)
            new_alerts.append(alert)
            
            alerts_generated.labels(severity=anomaly["severity"].value).inc()
            
            # Publish alert
            await self._publish_alert(alert)
        
        # Keep alerts manageable
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-500:]
        
        processing_time.observe(time.time() - start_time)
        
        return {
            "camera_id": camera_id,
            "faces_detected": len(faces),
            "tracks_active": len(tracks),
            "alerts": [a.to_dict() for a in new_alerts],
            "tracks": [t.to_dict() for t in tracks]
        }
    
    async def _publish_alert(self, alert: SecurityAlert):
        """Publish alert via ZeroMQ"""
        try:
            await self.zmq_publisher.send_multipart([
                b"security_alert",
                json.dumps(alert.to_dict()).encode('utf-8')
            ])
            
            # Also publish to Redis for real-time subscribers
            if self.redis_client:
                await self.redis_client.publish(
                    "security:alerts",
                    json.dumps(alert.to_dict())
                )
                
        except Exception as e:
            logger.error(f"Failed to publish alert: {e}")
    
    def get_alerts(
        self,
        severity: AlertSeverity = None,
        acknowledged: bool = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get alerts"""
        alerts = self.alerts.copy()
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [a.to_dict() for a in alerts[:limit]]
    
    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = user
                alert.acknowledged_at = datetime.utcnow()
                return True
        return False
    
    async def cleanup(self):
        """Cleanup resources"""
        self.zmq_publisher.close()
        self.zmq_context.term()
        if self.redis_client:
            await self.redis_client.close()


# FastAPI Application
service = SecurityFusionService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await service.initialize()
    yield
    await service.cleanup()


app = FastAPI(
    title="Guardia Security Fusion",
    description="Multi-modal security with facial recognition",
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


# Health and Status
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "security-fusion"}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/status")
async def get_status():
    return {
        "service": "security-fusion",
        "enrolled_faces": len(service.face_engine.enrolled_faces),
        "active_tracks": len(service.tracker.tracks),
        "total_alerts": len(service.alerts),
        "unacknowledged_alerts": sum(1 for a in service.alerts if not a.acknowledged)
    }


# Face Management
class FaceEnrollRequest(BaseModel):
    name: str
    person_type: str
    access_level: int = 1
    notes: Optional[str] = None


@app.post("/faces/enroll")
async def enroll_face(
    name: str = Form(...),
    person_type: str = Form(...),
    access_level: int = Form(1),
    notes: Optional[str] = Form(None),
    images: List[UploadFile] = File(...)
):
    """Enroll a new face"""
    try:
        image_arrays = []
        for img in images:
            contents = await img.read()
            nparr = np.frombuffer(contents, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is not None:
                image_arrays.append(image)
        
        if not image_arrays:
            raise HTTPException(status_code=400, detail="No valid images provided")
        
        enrolled = service.face_engine.enroll_face(
            name=name,
            person_type=PersonType(person_type),
            images=image_arrays,
            access_level=access_level,
            notes=notes
        )
        
        return enrolled.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/faces")
async def list_faces():
    """List all enrolled faces"""
    return {"faces": service.face_engine.get_all_faces()}


@app.delete("/faces/{face_id}")
async def delete_face(face_id: str):
    """Delete enrolled face"""
    if not service.face_engine.delete_face(face_id):
        raise HTTPException(status_code=404, detail="Face not found")
    return {"status": "deleted", "face_id": face_id}


@app.post("/faces/recognize")
async def recognize_face(file: UploadFile = File(...)):
    """Recognize face in image"""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image")
    
    faces = service.face_engine.detect_faces(image)
    
    results = []
    for face_rect in faces:
        enrolled, confidence = service.face_engine.recognize_face(image, face_rect)
        results.append({
            "bounding_box": face_rect,
            "recognized": enrolled.to_dict() if enrolled else None,
            "confidence": confidence
        })
    
    return {"faces": results}


# Tracking
@app.get("/tracking/active")
async def get_active_tracks(camera_id: Optional[str] = None):
    """Get active tracked persons"""
    tracks = service.tracker.get_active_tracks(camera_id)
    return {"tracks": [t.to_dict() for t in tracks]}


@app.get("/tracking/history")
async def get_track_history(limit: int = 100):
    """Get tracking history"""
    return {"history": service.tracker.get_track_history(limit)}


@app.post("/tracking/reset")
async def reset_tracking():
    """Reset tracking state"""
    service.tracker.reset()
    return {"status": "reset"}


# Alerts
@app.get("/alerts")
async def get_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 100
):
    """Get security alerts"""
    sev = AlertSeverity(severity) if severity else None
    return {"alerts": service.get_alerts(sev, acknowledged, limit)}


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user: str = "operator"):
    """Acknowledge an alert"""
    if not service.acknowledge_alert(alert_id, user):
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "acknowledged", "alert_id": alert_id}


# Processing
@app.post("/process")
async def process_frame(
    camera_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Process frame for security analysis"""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid image")
    
    return await service.process_frame(camera_id, frame)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SECURITY_FUSION_PORT", "8012"))
    uvicorn.run(app, host="0.0.0.0", port=port)
