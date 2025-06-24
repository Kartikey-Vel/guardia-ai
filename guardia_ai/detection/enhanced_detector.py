"""
Enhanced Detection Module - Combines Face Recognition, Face Detection, and Object Detection
"""
import cv2
import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Any

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("⚠️ MediaPipe not available - using basic face detection")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️ YOLO not available - object detection disabled")

class EnhancedDetector:
    """Enhanced detection system combining face recognition, face detection, and object detection"""
    
    def __init__(self, face_auth=None):
        self.face_auth = face_auth
        self.detection_stats = {
            'total_frames': 0,
            'faces_detected': 0,
            'objects_detected': 0,
            'known_faces': 0,
            'unknown_faces': 0,
            'threats_detected': 0,
            'high_risk_objects': 0,
            'medium_risk_objects': 0,
            'processing_time': []
        }
        
        # Initialize MediaPipe Face Detection
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_detection = mp.solutions.face_detection
            self.mp_drawing = mp.solutions.drawing_utils
            self.face_detector = self.mp_face_detection.FaceDetection(
                model_selection=1,  # 0: short-range (2m), 1: full-range (5m)
                min_detection_confidence=0.5
            )
            print("✅ MediaPipe Face Detection initialized")
        else:
            self.face_detector = None
            
        # Initialize YOLO Object Detection
        if YOLO_AVAILABLE:
            try:
                import warnings
                # Suppress specific typing warnings
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=UserWarning, message=".*typing.Self.*")
                    warnings.filterwarnings("ignore", category=FutureWarning, message=".*typing.Self.*")
                    # Download YOLOv8n model if not exists (lightweight version)
                    self.yolo_model = YOLO('yolov8n.pt')
                print("✅ YOLOv8 Object Detection initialized")
            except Exception as e:
                print(f"⚠️ YOLO initialization failed: {e}")
                self.yolo_model = None
        else:
            self.yolo_model = None
            
        # Initialize OpenCV face detector as fallback
        self.cv_face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # COCO class names for object detection (infinite expandable)
        self.coco_classes = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
            'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
            'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        
        # Threat assessment categories
        self.threat_categories = {
            'high_risk': ['knife', 'scissors', 'gun', 'pistol', 'rifle', 'weapon', 'sword', 'axe'],
            'medium_risk': ['baseball bat', 'hammer', 'crowbar', 'brick', 'rock', 'glass bottle'],
            'low_risk': ['bottle', 'wine glass', 'cup', 'fork', 'spoon'],
            'suspicious_behavior': ['mask', 'hood', 'suspicious_bag', 'large_bag'],
            'normal_objects': ['laptop', 'phone', 'book', 'chair', 'table', 'tv'],
            'vehicles': ['car', 'motorcycle', 'truck', 'bus', 'bicycle'],
            'animals': ['dog', 'cat', 'bird', 'horse']
        }
        
        # Object behavior tracking
        self.object_history = {}  # Track objects across frames
        self.detection_confidence_threshold = 0.3  # Lower threshold for infinite detection
        self.tracking_enabled = True
        
    def enhanced_detection(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Perform enhanced detection combining face recognition, face detection, and object detection
        """
        start_time = time.time()
        self.detection_stats['total_frames'] += 1
        
        results = {
            'frame': frame.copy(),
            'faces': [],
            'objects': [],
            'known_faces': [],
            'unknown_faces': [],
            'detection_time': 0,
            'face_count': 0,
            'object_count': 0,
            'threats': []  # For suspicious objects or unknown faces
        }
        
        # 1. Face Detection with MediaPipe (primary)
        if self.face_detector:
            face_locations = self._detect_faces_mediapipe(frame)
        else:
            # Fallback to OpenCV
            face_locations = self._detect_faces_opencv(frame)
            
        results['face_count'] = len(face_locations)
        self.detection_stats['faces_detected'] += len(face_locations)
        
        # 2. Face Recognition for detected faces
        for face_bbox in face_locations:
            face_result = self._process_face(frame, face_bbox)
            results['faces'].append(face_result)
            
            if face_result['is_known']:
                results['known_faces'].append(face_result)
                self.detection_stats['known_faces'] += 1
            else:
                results['unknown_faces'].append(face_result)
                self.detection_stats['unknown_faces'] += 1
                # Unknown faces could be potential threats
                results['threats'].append({
                    'type': 'unknown_face',
                    'confidence': face_result['confidence'],
                    'bbox': face_result['bbox']
                })
        
        # 3. Object Detection with YOLO
        if self.yolo_model:
            objects = self._detect_objects_yolo(frame)
            results['objects'] = objects
            results['object_count'] = len(objects)
            self.detection_stats['objects_detected'] += len(objects)
            
            # Check for suspicious objects and assess threats
            for obj in objects:
                threat_level = self._assess_threat_level(obj['class'])
                obj['threat_level'] = threat_level
                
                # Update threat statistics
                if threat_level == 'high_risk':
                    self.detection_stats['high_risk_objects'] += 1
                elif threat_level == 'medium_risk':
                    self.detection_stats['medium_risk_objects'] += 1
                
                if threat_level in ['high_risk', 'medium_risk']:
                    results['threats'].append({
                        'type': 'suspicious_object',
                        'class': obj['class'],
                        'confidence': obj['confidence'],
                        'bbox': obj['bbox'],
                        'threat_level': threat_level
                    })
        
        # Update threat statistics
        self.detection_stats['threats_detected'] += len(results['threats'])
        
        # 4. Draw all detections on frame
        results['frame'] = self._draw_detections(frame, results)
        
        # Update timing stats
        detection_time = time.time() - start_time
        results['detection_time'] = detection_time
        self.detection_stats['processing_time'].append(detection_time)
        
        return results
    
    def _detect_faces_mediapipe(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using MediaPipe"""
        face_locations = []
        
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_detector.process(rgb_frame)
            
            if results.detections:
                h, w, _ = frame.shape
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    # Convert relative coordinates to absolute
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    face_locations.append((x, y, width, height))
                    
        except Exception as e:
            print(f"MediaPipe face detection error: {e}")
            
        return face_locations
    
    def _detect_faces_opencv(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using OpenCV (fallback)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.cv_face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )
        return [(x, y, w, h) for x, y, w, h in faces]
    
    def _process_face(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Dict[str, Any]:
        """Process individual face for recognition"""
        x, y, w, h = bbox
        
        # Extract face region for recognition
        face_roi = frame[y:y+h, x:x+w]
        
        face_result = {
            'bbox': bbox,
            'is_known': False,
            'identity': 'Unknown',
            'confidence': 0.0,
            'face_roi': face_roi
        }
        
        # Try face recognition if face_auth is available
        if self.face_auth and face_roi.size > 0:
            try:
                user = self.face_auth.match_face(face_roi)
                if user:
                    face_result['is_known'] = True
                    face_result['identity'] = user['label']
                    face_result['confidence'] = user['score']
            except Exception as e:
                print(f"Face recognition error: {e}")
                
        return face_result
    
    def _detect_objects_yolo(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect objects using YOLO"""
        objects = []
        
        try:
            # Run YOLO inference
            results = self.yolo_model(frame, verbose=False)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get box coordinates with defensive programming
                        try:
                            xyxy = box.xyxy[0].cpu().numpy()
                            if len(xyxy) < 4:
                                continue
                            x1, y1, x2, y2 = xyxy[:4]
                            confidence = float(box.conf[0].cpu().numpy())
                            class_id = int(box.cls[0].cpu().numpy())
                        except (IndexError, ValueError, TypeError) as e:
                            continue
                        
                        # Filter by confidence threshold (lower for infinite detection)
                        if confidence > self.detection_confidence_threshold:
                            objects.append({
                                'class': self.coco_classes[class_id],
                                'confidence': float(confidence),
                                'bbox': (int(x1), int(y1), int(x2-x1), int(y2-y1)),
                                'class_id': class_id,
                                'threat_level': 'unknown'  # Will be assessed later
                            })
                            
        except Exception as e:
            # Handle specific typing errors from YOLO
            error_msg = str(e)
            if "typing.Self" in error_msg:
                print(f"⚠️ YOLO typing compatibility warning (non-critical): {e}")
            else:
                print(f"YOLO detection error: {e}")
            
        return objects
    
    def _assess_threat_level(self, object_class: str) -> str:
        """Assess threat level of detected object"""
        for threat_level, classes in self.threat_categories.items():
            if object_class.lower() in [cls.lower() for cls in classes]:
                return threat_level
        return 'unknown'
    
    def _get_threat_color(self, threat_level: str) -> Tuple[int, int, int]:
        """Get color based on threat level"""
        color_map = {
            'high_risk': (0, 0, 255),      # Red
            'medium_risk': (0, 165, 255),  # Orange
            'low_risk': (0, 255, 255),     # Yellow
            'suspicious_behavior': (255, 0, 255),  # Magenta
            'normal_objects': (0, 255, 0), # Green
            'vehicles': (255, 255, 0),     # Cyan
            'animals': (0, 128, 255),      # Orange-red
            'unknown': (128, 128, 128)     # Gray
        }
        return color_map.get(threat_level, (128, 128, 128))
    
    def _draw_detections(self, frame: np.ndarray, results: Dict[str, Any]) -> np.ndarray:
        """Draw all detections on the frame"""
        annotated_frame = frame.copy()
        
        # Draw faces
        for face in results['faces']:
            x, y, w, h = face['bbox']
            
            # Choose color based on recognition status
            if face['is_known']:
                color = (0, 255, 0)  # Green for known faces
                label = f"{face['identity']} ({face['confidence']:.2f})"
            else:
                color = (0, 0, 255)  # Red for unknown faces
                label = "Unknown Face"
            
            # Draw face rectangle
            cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), color, 2)
            
            # Draw label background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            cv2.rectangle(annotated_frame, (x, y-30), (x+label_size[0], y), color, -1)
            
            # Draw label text
            cv2.putText(annotated_frame, label, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw objects with threat-based colors
        for obj in results['objects']:
            x, y, w, h = obj['bbox']
            
            # Get color based on threat level
            threat_level = obj.get('threat_level', 'unknown')
            color = self._get_threat_color(threat_level)
            
            # Create label with threat info
            if threat_level in ['high_risk', 'medium_risk']:
                label = f"⚠️ {obj['class'].upper()} ({obj['confidence']:.2f}) - {threat_level.upper()}"
            else:
                label = f"{obj['class']} ({obj['confidence']:.2f})"
            
            # Draw object rectangle (thicker for threats)
            thickness = 3 if threat_level in ['high_risk', 'medium_risk'] else 2
            cv2.rectangle(annotated_frame, (x, y), (x+w, y+h), color, thickness)
            
            # Draw label with background
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(annotated_frame, (x, y-25), (x+label_size[0], y), color, -1)
            cv2.putText(annotated_frame, label, (x, y-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Draw threat indicators with more detail
        if results['threats']:
            threat_text = f"🚨 THREATS DETECTED: {len(results['threats'])}"
            cv2.putText(annotated_frame, threat_text, 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            
            # List individual threats
            for i, threat in enumerate(results['threats'][:3]):  # Show up to 3 threats
                threat_info = f"• {threat['type']}: {threat.get('class', 'N/A')}"
                cv2.putText(annotated_frame, threat_info, 
                           (10, 60 + i*25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Draw enhanced statistics
        high_risk_objects = sum(1 for obj in results['objects'] if obj.get('threat_level') == 'high_risk')
        medium_risk_objects = sum(1 for obj in results['objects'] if obj.get('threat_level') == 'medium_risk')
        
        stats_text = [
            f"👥 Faces: {results['face_count']} (✅{len(results['known_faces'])}, ❌{len(results['unknown_faces'])})",
            f"🎯 Objects: {results['object_count']} (🚨{high_risk_objects} high, ⚠️{medium_risk_objects} medium)",
            f"⚡ Processing: {results['detection_time']*1000:.1f}ms",
            f"🔍 Infinite Detection: {len([o for o in results['objects'] if o['confidence'] < 0.5])} low-conf"
        ]
        
        for i, text in enumerate(stats_text):
            y_pos = annotated_frame.shape[0] - 80 + i*18  # Adjusted for more stats
            cv2.putText(annotated_frame, text, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return annotated_frame
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection statistics"""
        avg_processing_time = np.mean(self.detection_stats['processing_time']) if self.detection_stats['processing_time'] else 0
        fps = 1.0 / avg_processing_time if avg_processing_time > 0 else 0
        
        return {
            'total_frames': self.detection_stats['total_frames'],
            'faces_detected': self.detection_stats['faces_detected'],
            'objects_detected': self.detection_stats['objects_detected'],
            'known_faces': self.detection_stats['known_faces'],
            'unknown_faces': self.detection_stats['unknown_faces'],
            'threats_detected': self.detection_stats['threats_detected'],
            'high_risk_objects': self.detection_stats['high_risk_objects'],
            'medium_risk_objects': self.detection_stats['medium_risk_objects'],
            'avg_processing_time_ms': avg_processing_time * 1000,
            'estimated_fps': fps,
            'mediapipe_available': MEDIAPIPE_AVAILABLE,
            'yolo_available': YOLO_AVAILABLE,
            'infinite_detection_enabled': self.detection_confidence_threshold < 0.5
        }
    
    def reset_stats(self):
        """Reset detection statistics"""
        self.detection_stats = {
            'total_frames': 0,
            'faces_detected': 0,
            'objects_detected': 0,
            'known_faces': 0,
            'unknown_faces': 0,
            'threats_detected': 0,
            'high_risk_objects': 0,
            'medium_risk_objects': 0,
            'processing_time': []
        }

def test_enhanced_detector():
    """Test the enhanced detector"""
    print("🧪 Testing Enhanced Detector...")
    
    # Test without face_auth first
    detector = EnhancedDetector()
    
    # Test with webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        return
    
    print("📹 Enhanced detection test running...")
    print("📝 Press 'q' to quit, 's' to show stats")
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Run enhanced detection
        results = detector.enhanced_detection(frame)
        
        # Display results
        cv2.imshow('Enhanced Detection Test', results['frame'])
        
        frame_count += 1
        if frame_count % 30 == 0:  # Show stats every 30 frames
            stats = detector.get_detection_stats()
            print(f"📊 Stats: {stats['total_frames']} frames, "
                  f"{stats['faces_detected']} faces, "
                  f"{stats['objects_detected']} objects, "
                  f"{stats['estimated_fps']:.1f} FPS")
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            stats = detector.get_detection_stats()
            print(f"📈 Detailed Stats: {stats}")
    
    cap.release()
    cv2.destroyAllWindows()
    
    final_stats = detector.get_detection_stats()
    print("✅ Enhanced detector test completed!")
    print(f"📊 Final Stats: {final_stats}")

if __name__ == "__main__":
    test_enhanced_detector()
