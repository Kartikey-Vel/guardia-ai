"""
Enhanced Object Detection System using YOLO and TensorFlow
Modern implementation for person detection, mask detection, and behavior analysis
"""
import asyncio
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import concurrent.futures
from loguru import logger
import time
from datetime import datetime, timedelta

# AI/ML Imports
try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

from ..config.settings import settings, MODEL_CONFIGS
from ..models.schemas import DetectionResult, BoundingBox, DetectionType

class EnhancedObjectDetector:
    """Enhanced object detection system with YOLO and TensorFlow"""
    
    def __init__(self):
        self.models_loaded = False
        self.yolo_model = None
        self.mask_detection_model = None
        self.person_tracker = {}  # Track persons for loitering detection
        self.detection_history = []  # Store recent detections
        
        # Performance tracking
        self.detection_times = []
        self.frame_count = 0
        
        # Thread pool for parallel processing
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        
        # Configuration
        self.yolo_config = MODEL_CONFIGS["yolo"]
        self.mask_config = MODEL_CONFIGS["mask_detection"]
        
        # Initialize models
        asyncio.create_task(self._initialize_models())
    
    async def _initialize_models(self):
        """Initialize YOLO and other detection models"""
        try:
            logger.info("🔄 Initializing object detection models...")
            
            # Initialize YOLO for person detection
            if ULTRALYTICS_AVAILABLE:
                model_path = self.yolo_config["model_path"]
                self.yolo_model = YOLO(model_path)
                
                # Configure device (auto, cpu, 0, 1, etc.)
                if settings.enable_gpu_acceleration:
                    self.yolo_model.to(self.yolo_config["device"])
                else:
                    self.yolo_model.to("cpu")
                
                logger.info(f"✅ YOLO model loaded: {model_path}")
            
            # Initialize mask detection model if available
            if TENSORFLOW_AVAILABLE and settings.mask_detection_enabled:
                await self._load_mask_detection_model()
            
            self.models_loaded = True
            logger.info("✅ Object detection models initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize object detection models: {e}")
            self.models_loaded = False
    
    async def _load_mask_detection_model(self):
        """Load mask detection TensorFlow model"""
        try:
            mask_model_path = Path(settings.models_dir) / self.mask_config["model_path"]
            
            if mask_model_path.exists():
                self.mask_detection_model = tf.keras.models.load_model(str(mask_model_path))
                logger.info("✅ Mask detection model loaded")
            else:
                logger.warning(f"Mask detection model not found: {mask_model_path}")
                
        except Exception as e:
            logger.error(f"Failed to load mask detection model: {e}")
    
    async def detect_objects(self, frame: np.ndarray, detect_masks: bool = True) -> List[DetectionResult]:
        """
        Detect objects (persons) and analyze behavior
        
        Args:
            frame: Input image frame
            detect_masks: Whether to perform mask detection
            
        Returns:
            List of detection results
        """
        if not self.models_loaded:
            logger.warning("Models not loaded, skipping detection")
            return []
        
        start_time = time.time()
        self.frame_count += 1
        
        try:
            # Run detection in thread pool
            loop = asyncio.get_event_loop()
            detections = await loop.run_in_executor(
                self.executor, self._detect_objects_sync, frame, detect_masks
            )
            
            # Update tracking and behavior analysis
            detections = await self._analyze_behavior(detections, frame)
            
            detection_time = time.time() - start_time
            self.detection_times.append(detection_time)
            
            # Keep only last 100 measurements
            if len(self.detection_times) > 100:
                self.detection_times.pop(0)
            
            # Store detection history for analysis
            self.detection_history.append({
                "timestamp": datetime.utcnow(),
                "detections": detections,
                "frame_count": self.frame_count
            })
            
            # Keep only last hour of history
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            self.detection_history = [
                h for h in self.detection_history 
                if h["timestamp"] > cutoff_time
            ]
            
            return detections
            
        except Exception as e:
            logger.error(f"Object detection error: {e}")
            return []
    
    def _detect_objects_sync(self, frame: np.ndarray, detect_masks: bool) -> List[DetectionResult]:
        """Synchronous object detection implementation"""
        detections = []
        
        # YOLO person detection
        if ULTRALYTICS_AVAILABLE and self.yolo_model:
            detections.extend(self._detect_with_yolo(frame))
        
        # Mask detection for detected persons
        if detect_masks and self.mask_detection_model and detections:
            detections = self._detect_masks(frame, detections)
        
        return detections
    
    def _detect_with_yolo(self, frame: np.ndarray) -> List[DetectionResult]:
        """Detect persons using YOLO"""
        try:
            # Run YOLO inference
            results = self.yolo_model(
                frame,
                conf=self.yolo_config["confidence"],
                iou=self.yolo_config.get("iou_threshold", 0.45),
                classes=self.yolo_config["classes"],  # Only person class (0)
                verbose=False
            )
            
            detections = []
            for result in results:
                for box in result.boxes:
                    # Extract bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    
                    # Only process person detections (class 0)
                    if class_id == 0 and confidence >= self.yolo_config["confidence"]:
                        detection = DetectionResult(
                            detection_type=DetectionType.UNKNOWN_PERSON,
                            confidence=float(confidence),
                            bounding_box=BoundingBox(
                                x=int(x1),
                                y=int(y1),
                                width=int(x2 - x1),
                                height=int(y2 - y1)
                            )
                        )
                        detections.append(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"YOLO detection error: {e}")
            return []
    
    def _detect_masks(self, frame: np.ndarray, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Detect masks on detected persons"""
        try:
            for detection in detections:
                bbox = detection.bounding_box
                
                # Extract face region
                x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height
                
                # Focus on upper part of bounding box (head/face area)
                face_y = y
                face_h = int(h * 0.3)  # Top 30% of person detection
                
                # Ensure coordinates are within frame bounds
                h_frame, w_frame = frame.shape[:2]
                x = max(0, min(x, w_frame - 1))
                y = max(0, min(face_y, h_frame - 1))
                w = max(1, min(w, w_frame - x))
                h = max(1, min(face_h, h_frame - y))
                
                face_region = frame[y:y+h, x:x+w]
                
                if face_region.size > 0:
                    mask_probability = self._predict_mask(face_region)
                    
                    if mask_probability > self.mask_config["confidence"]:
                        detection.detection_type = DetectionType.MASKED_PERSON
                        detection.is_masked = True
            
            return detections
            
        except Exception as e:
            logger.error(f"Mask detection error: {e}")
            return detections
    
    def _predict_mask(self, face_region: np.ndarray) -> float:
        """Predict if person is wearing a mask"""
        try:
            # Resize image to model input size
            img_size = self.mask_config["image_size"]
            resized = cv2.resize(face_region, img_size)
            
            # Normalize pixel values
            normalized = resized.astype(np.float32) / 255.0
            
            # Add batch dimension
            input_data = np.expand_dims(normalized, axis=0)
            
            # Make prediction
            prediction = self.mask_detection_model.predict(input_data, verbose=0)
            
            # Return probability of mask (assuming binary classification)
            return float(prediction[0][1] if prediction.shape[1] > 1 else prediction[0][0])
            
        except Exception as e:
            logger.error(f"Mask prediction error: {e}")
            return 0.0
    
    async def _analyze_behavior(self, detections: List[DetectionResult], frame: np.ndarray) -> List[DetectionResult]:
        """Analyze behavior patterns (loitering, multiple unknown persons, etc.)"""
        try:
            current_time = datetime.utcnow()
            
            # Track persons for loitering detection
            for detection in detections:
                detection_id = self._generate_detection_id(detection.bounding_box, frame.shape)
                
                if detection_id in self.person_tracker:
                    # Update existing tracking
                    self.person_tracker[detection_id]["last_seen"] = current_time
                    self.person_tracker[detection_id]["detections"].append(detection)
                    
                    # Check for loitering (person in same area for extended time)
                    first_seen = self.person_tracker[detection_id]["first_seen"]
                    duration = (current_time - first_seen).total_seconds()
                    
                    if duration > settings.loitering_detection_time:
                        detection.detection_type = DetectionType.LOITERING
                        logger.warning(f"Loitering detected: {duration:.0f} seconds")
                else:
                    # New person detected
                    self.person_tracker[detection_id] = {
                        "first_seen": current_time,
                        "last_seen": current_time,
                        "detections": [detection]
                    }
            
            # Clean up old tracking data
            cutoff_time = current_time - timedelta(seconds=settings.max_unknown_tracking_time)
            self.person_tracker = {
                k: v for k, v in self.person_tracker.items()
                if v["last_seen"] > cutoff_time
            }
            
            # Check for multiple unknown persons (security risk)
            unknown_count = sum(
                1 for d in detections 
                if d.detection_type == DetectionType.UNKNOWN_PERSON
            )
            
            if unknown_count > 1:
                for detection in detections:
                    if detection.detection_type == DetectionType.UNKNOWN_PERSON:
                        detection.detection_type = DetectionType.MULTIPLE_UNKNOWN
            
            # Night intrusion detection (if enabled and it's night time)
            if self._is_night_time():
                for detection in detections:
                    if detection.detection_type in [DetectionType.UNKNOWN_PERSON, DetectionType.MULTIPLE_UNKNOWN]:
                        detection.detection_type = DetectionType.NIGHT_INTRUSION
            
            return detections
            
        except Exception as e:
            logger.error(f"Behavior analysis error: {e}")
            return detections
    
    def _generate_detection_id(self, bbox: BoundingBox, frame_shape: Tuple[int, int]) -> str:
        """Generate a unique ID for tracking based on location"""
        h, w = frame_shape[:2]
        
        # Normalize coordinates to create stable tracking ID
        center_x = (bbox.x + bbox.width // 2) / w
        center_y = (bbox.y + bbox.height // 2) / h
        
        # Round to create zones for stable tracking
        zone_x = round(center_x * 10)  # 10x10 grid
        zone_y = round(center_y * 10)
        
        return f"zone_{zone_x}_{zone_y}"
    
    def _is_night_time(self) -> bool:
        """Check if it's currently night time (simple implementation)"""
        current_hour = datetime.now().hour
        return current_hour < 6 or current_hour > 22  # 10 PM to 6 AM
    
    async def get_detection_statistics(self) -> Dict[str, Any]:
        """Get detection statistics and insights"""
        try:
            current_time = datetime.utcnow()
            
            # Calculate statistics from recent history
            recent_detections = [
                d for h in self.detection_history[-100:]  # Last 100 frames
                for d in h["detections"]
            ]
            
            stats = {
                "total_detections": len(recent_detections),
                "detection_types": {},
                "average_confidence": 0.0,
                "active_tracks": len(self.person_tracker),
                "performance": {
                    "avg_detection_time": sum(self.detection_times[-50:]) / max(len(self.detection_times[-50:]), 1),
                    "frames_processed": self.frame_count,
                    "fps": 0.0
                }
            }
            
            # Count detection types
            for detection in recent_detections:
                det_type = detection.detection_type.value
                stats["detection_types"][det_type] = stats["detection_types"].get(det_type, 0) + 1
            
            # Calculate average confidence
            if recent_detections:
                stats["average_confidence"] = sum(d.confidence for d in recent_detections) / len(recent_detections)
            
            # Calculate FPS from recent performance
            if len(self.detection_times) > 10:
                avg_time = sum(self.detection_times[-10:]) / 10
                stats["performance"]["fps"] = 1.0 / max(avg_time, 0.001)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get detection statistics: {e}")
            return {}
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)
        
        # Clear tracking data
        self.person_tracker.clear()
        self.detection_history.clear()
        
        logger.info("🧹 Object detector cleaned up")
