"""
Enhanced Face Detection and Recognition System
Modern implementation using multiple AI frameworks and models
"""
import asyncio
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path
import concurrent.futures
from loguru import logger
import time

# AI/ML Imports
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False

from ..config.settings import settings, MODEL_CONFIGS
from ..models.schemas import DetectionResult, BoundingBox, FaceEncoding, DetectionType

class EnhancedFaceDetector:
    """Enhanced face detection system with multiple AI backends"""
    
    def __init__(self):
        self.models_loaded = False
        self.face_detection_model = None
        self.face_recognition_model = None
        self.mediapipe_face_detector = None
        self.mediapipe_face_mesh = None
        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []
        self.detection_config = MODEL_CONFIGS["face_detection"]
        self.recognition_config = MODEL_CONFIGS["face_recognition"]
        
        # Performance tracking
        self.detection_times = []
        self.recognition_times = []
        
        # Thread pool for parallel processing
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        # Initialize models
        asyncio.create_task(self._initialize_models())
    
    async def _initialize_models(self):
        """Initialize all available face detection models"""
        try:
            logger.info("🔄 Initializing face detection models...")
            
            # Initialize MediaPipe if available
            if MEDIAPIPE_AVAILABLE:
                self.mp_face_detection = mp.solutions.face_detection
                self.mp_face_mesh = mp.solutions.face_mesh
                self.mediapipe_face_detector = self.mp_face_detection.FaceDetection(
                    model_selection=1,  # 0 for short range, 1 for full range
                    min_detection_confidence=self.detection_config["confidence"]
                )
                logger.info("✅ MediaPipe face detection initialized")
            
            # Initialize OpenCV fallback
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.opencv_face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # Initialize TensorFlow GPU if available
            if TENSORFLOW_AVAILABLE and settings.enable_gpu_acceleration:
                gpus = tf.config.experimental.list_physical_devices('GPU')
                if gpus:
                    for gpu in gpus:
                        tf.config.experimental.set_memory_growth(gpu, True)
                    logger.info(f"✅ TensorFlow GPU acceleration enabled ({len(gpus)} GPU(s))")
            
            self.models_loaded = True
            logger.info("✅ Face detection models initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize face detection models: {e}")
            self.models_loaded = False
    
    async def detect_faces(self, frame: np.ndarray, use_async: bool = True) -> List[DetectionResult]:
        """
        Detect faces in frame using the best available method
        
        Args:
            frame: Input image frame
            use_async: Whether to use async processing
            
        Returns:
            List of detection results
        """
        if not self.models_loaded:
            logger.warning("Models not loaded, skipping detection")
            return []
        
        start_time = time.time()
        
        try:
            if use_async:
                # Run detection in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                detections = await loop.run_in_executor(
                    self.executor, self._detect_faces_sync, frame
                )
            else:
                detections = self._detect_faces_sync(frame)
            
            detection_time = time.time() - start_time
            self.detection_times.append(detection_time)
            
            # Keep only last 100 measurements for performance tracking
            if len(self.detection_times) > 100:
                self.detection_times.pop(0)
            
            return detections
            
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []
    
    def _detect_faces_sync(self, frame: np.ndarray) -> List[DetectionResult]:
        """Synchronous face detection implementation"""
        detections = []
        
        # Try MediaPipe first (most accurate)
        if MEDIAPIPE_AVAILABLE and self.mediapipe_face_detector:
            detections = self._detect_with_mediapipe(frame)
        
        # Fallback to face_recognition library
        if not detections and FACE_RECOGNITION_AVAILABLE:
            detections = self._detect_with_face_recognition(frame)
        
        # Final fallback to OpenCV
        if not detections:
            detections = self._detect_with_opencv(frame)
        
        return detections
    
    def _detect_with_mediapipe(self, frame: np.ndarray) -> List[DetectionResult]:
        """Detect faces using MediaPipe"""
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.mediapipe_face_detector.process(rgb_frame)
            
            detections = []
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    h, w = frame.shape[:2]
                    
                    # Convert relative coordinates to absolute
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    # Ensure coordinates are within frame bounds
                    x = max(0, min(x, w - 1))
                    y = max(0, min(y, h - 1))
                    width = max(1, min(width, w - x))
                    height = max(1, min(height, h - y))
                    
                    detection_result = DetectionResult(
                        detection_type=DetectionType.UNKNOWN_PERSON,
                        confidence=detection.score[0] if detection.score else 0.0,
                        bounding_box=BoundingBox(x=x, y=y, width=width, height=height)
                    )
                    detections.append(detection_result)
            
            return detections
            
        except Exception as e:
            logger.error(f"MediaPipe detection error: {e}")
            return []
    
    def _detect_with_face_recognition(self, frame: np.ndarray) -> List[DetectionResult]:
        """Detect faces using face_recognition library"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Detect face locations
            face_locations = face_recognition.face_locations(
                rgb_frame,
                model=self.detection_config["model"]
            )
            
            detections = []
            for (top, right, bottom, left) in face_locations:
                detection_result = DetectionResult(
                    detection_type=DetectionType.UNKNOWN_PERSON,
                    confidence=0.8,  # face_recognition doesn't provide confidence
                    bounding_box=BoundingBox(
                        x=left, 
                        y=top, 
                        width=right-left, 
                        height=bottom-top
                    )
                )
                detections.append(detection_result)
            
            return detections
            
        except Exception as e:
            logger.error(f"Face recognition detection error: {e}")
            return []
    
    def _detect_with_opencv(self, frame: np.ndarray) -> List[DetectionResult]:
        """Detect faces using OpenCV Haar cascades"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.opencv_face_cascade.detectMultiScale(
                gray,
                scaleFactor=self.detection_config["scale_factor"],
                minNeighbors=self.detection_config["min_neighbors"],
                minSize=(30, 30)
            )
            
            detections = []
            for (x, y, w, h) in faces:
                detection_result = DetectionResult(
                    detection_type=DetectionType.UNKNOWN_PERSON,
                    confidence=0.6,  # OpenCV doesn't provide confidence
                    bounding_box=BoundingBox(x=x, y=y, width=w, height=h)
                )
                detections.append(detection_result)
            
            return detections
            
        except Exception as e:
            logger.error(f"OpenCV detection error: {e}")
            return []
    
    async def recognize_faces(self, frame: np.ndarray, face_locations: List[BoundingBox]) -> List[DetectionResult]:
        """
        Recognize faces in the given locations
        
        Args:
            frame: Input image frame
            face_locations: List of face bounding boxes
            
        Returns:
            List of recognition results
        """
        if not FACE_RECOGNITION_AVAILABLE or not self.known_encodings:
            return []
        
        start_time = time.time()
        
        try:
            # Run recognition in thread pool
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor, self._recognize_faces_sync, frame, face_locations
            )
            
            recognition_time = time.time() - start_time
            self.recognition_times.append(recognition_time)
            
            if len(self.recognition_times) > 100:
                self.recognition_times.pop(0)
            
            return results
            
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return []
    
    def _recognize_faces_sync(self, frame: np.ndarray, face_locations: List[BoundingBox]) -> List[DetectionResult]:
        """Synchronous face recognition implementation"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert BoundingBox objects to tuples for face_recognition
            locations = [
                (bbox.y, bbox.x + bbox.width, bbox.y + bbox.height, bbox.x)
                for bbox in face_locations
            ]
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(
                rgb_frame, 
                locations,
                num_jitters=self.recognition_config["num_jitters"],
                model=self.recognition_config["model"]
            )
            
            results = []
            for i, face_encoding in enumerate(face_encodings):
                # Compare with known faces
                matches = face_recognition.compare_faces(
                    self.known_encodings, 
                    face_encoding,
                    tolerance=self.recognition_config["tolerance"]
                )
                
                # Find best match
                face_distances = face_recognition.face_distance(self.known_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index] and face_distances[best_match_index] < self.recognition_config["tolerance"]:
                    name = self.known_names[best_match_index]
                    confidence = 1.0 - face_distances[best_match_index]
                    detection_type = DetectionType.KNOWN_PERSON
                else:
                    name = None
                    confidence = 0.0
                    detection_type = DetectionType.UNKNOWN_PERSON
                
                result = DetectionResult(
                    detection_type=detection_type,
                    confidence=confidence,
                    bounding_box=face_locations[i],
                    person_name=name,
                    face_encoding=FaceEncoding(
                        encoding=face_encoding.tolist(),
                        confidence=confidence
                    )
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Face recognition sync error: {e}")
            return []
    
    async def load_known_faces(self, faces_data: List[Dict[str, Any]]):
        """Load known face encodings for recognition"""
        try:
            self.known_encodings = []
            self.known_names = []
            
            for face_data in faces_data:
                if "encoding" in face_data and "name" in face_data:
                    encoding = np.array(face_data["encoding"])
                    self.known_encodings.append(encoding)
                    self.known_names.append(face_data["name"])
            
            logger.info(f"✅ Loaded {len(self.known_encodings)} known face encodings")
            
        except Exception as e:
            logger.error(f"❌ Failed to load known faces: {e}")
    
    async def extract_face_encoding(self, image_path: str) -> Optional[np.ndarray]:
        """Extract face encoding from image file"""
        try:
            if not FACE_RECOGNITION_AVAILABLE:
                return None
            
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Get face encodings
            encodings = face_recognition.face_encodings(image)
            
            if encodings:
                return encodings[0]  # Return first face found
            else:
                logger.warning(f"No face found in image: {image_path}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract face encoding from {image_path}: {e}")
            return None
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics"""
        stats = {
            "avg_detection_time": 0.0,
            "avg_recognition_time": 0.0,
            "total_detections": len(self.detection_times),
            "total_recognitions": len(self.recognition_times)
        }
        
        if self.detection_times:
            stats["avg_detection_time"] = sum(self.detection_times) / len(self.detection_times)
        
        if self.recognition_times:
            stats["avg_recognition_time"] = sum(self.recognition_times) / len(self.recognition_times)
        
        return stats
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.mediapipe_face_detector:
            self.mediapipe_face_detector.close()
        
        if self.executor:
            self.executor.shutdown(wait=True)
        
        logger.info("🧹 Face detector cleaned up")
