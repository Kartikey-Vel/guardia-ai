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
        self.stats = {}
        self.face_cascade = None
        if not MEDIAPIPE_AVAILABLE:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.yolo_model = YOLO('yolov8n.pt') if YOLO_AVAILABLE else None
        self.detection_confidence_threshold = 0.3
        
    def enhanced_detection(self, frame):
        import cv2
        h, w = frame.shape[:2]
        if max(h, w) > 640:
            scale = 640.0 / max(h, w)
            frame = cv2.resize(frame, (int(w*scale), int(h*scale)))
        faces = self._detect_faces(frame)
        objects = self._detect_objects(frame)
        self.stats = {'faces': len(faces), 'objects': len(objects)}
        return {'faces': faces, 'objects': objects}
    
    def _detect_faces(self, frame):
        if MEDIAPIPE_AVAILABLE:
            mp_face = mp.solutions.face_detection
            with mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
                results = face_detection.process(frame[:,:,::-1])
                faces = []
                if results.detections:
                    for det in results.detections:
                        bboxC = det.location_data.relative_bounding_box
                        ih, iw = frame.shape[:2]
                        x = int(bboxC.xmin * iw)
                        y = int(bboxC.ymin * ih)
                        w = int(bboxC.width * iw)
                        h = int(bboxC.height * ih)
                        faces.append((x, y, w, h))
                return faces
        else:
            if self.face_cascade is None:
                import cv2
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = frame if len(frame.shape) == 2 else cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            return faces
    
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
    
    def _detect_objects(self, frame):
        if YOLO_AVAILABLE:
            model = YOLO('yolov8n.pt')  # Use nano model for speed
            results = model(frame, verbose=False)
            objects = []
            for r in results:
                for box in r.boxes:
                    objects.append({'class': int(box.cls[0]), 'conf': float(box.conf[0])})
            return objects
        return []
    
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
    
    def get_detection_stats(self):
        return self.stats

    def reset_stats(self):
        self.stats = {}

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
