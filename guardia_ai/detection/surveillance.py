#!/usr/bin/env python3
"""
Guardia AI - Advanced Video Surveillance & Behavior Detection Module
Developed by Tackle Studioz

Main AI surveillance loop that orchestrates:
- Real-time video processing
- Multi-model object detection
- Behavior analysis
- Threat assessment
- Alert generation
"""

import cv2
import numpy as np
import time
import json
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from queue import Queue, Empty

# Deep learning imports
try:
    from ultralytics import YOLO
    import torch
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️ YOLO not available")

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("⚠️ MediaPipe not available")

# Import existing modules
from .enhanced_detector import EnhancedDetector
from .camera_manager import camera_manager
from .behavior import BehaviorAnalyzer
from .zone_manager import ZoneManager
from .tracker import EnhancedTracker

@dataclass
class DetectionResult:
    """Standardized detection result structure"""
    timestamp: datetime
    frame_id: int
    frame: np.ndarray
    objects: List[Dict[str, Any]]
    faces: List[Dict[str, Any]]
    behaviors: List[Dict[str, Any]]
    threats: List[Dict[str, Any]]
    zones_violated: List[str]
    confidence_score: float
    processing_time_ms: float
    tracks: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AlertEvent:
    """Alert event structure"""
    alert_id: str
    timestamp: datetime
    alert_type: str  # 'intrusion', 'loitering', 'aggression', 'threat_object', etc.
    priority: str    # 'critical', 'high', 'medium', 'low'
    zone_name: str
    description: str
    confidence: float
    frame_snapshot: np.ndarray
    metadata: Dict[str, Any]

class SurveillanceEngine:
    """
    Advanced surveillance engine combining multiple AI models for comprehensive security monitoring
    """
    
    def __init__(self, face_auth=None, config_path: str = "guardia_ai/storage/surveillance_config.json"):
        self.face_auth = face_auth
        self.config_path = config_path
        self.config = self._load_config()
        
        # Core components
        self.enhanced_detector = None
        self.behavior_analyzer = None
        self.zone_manager = None
        
        # Threading and processing
        self.running = False
        self.processing_thread = None
        self.alert_queue = Queue()
        self.detection_history = []
        self.frame_buffer = Queue(maxsize=30)  # Keep last 30 frames
        
        # Performance tracking
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        self.frame_id = 0
        
        # Alert callbacks
        self.alert_callbacks: List[Callable[[AlertEvent], None]] = []
        
        # Result callbacks for real-time streaming
        self.result_callbacks: List[Callable[[DetectionResult], None]] = []
        
        # Initialize logging
        self._setup_logging()
        
        # Initialize AI models
        self._initialize_models()
        
        self.logger.info("🛡️ Surveillance Engine initialized successfully")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load surveillance configuration"""
        default_config = {
            "detection": {
                "face_confidence_threshold": 0.7,
                "object_confidence_threshold": 0.5,
                "enable_tracking": True,
                "max_tracking_age": 30,
                "infinite_detection": True
            },
            "behavior": {
                "loitering_time_threshold": 10.0,  # seconds
                "intrusion_sensitivity": 0.8,
                "crowd_density_threshold": 5,
                "aggression_detection": True,
                "pose_analysis": True
            },
            "zones": {
                "default_zones": [
                    {
                        "name": "entrance",
                        "type": "intrusion_detection",
                        "points": [[100, 100], [300, 100], [300, 200], [100, 200]],
                        "sensitivity": 0.8
                    }
                ]
            },
            "alerts": {
                "enable_email": False,
                "enable_sms": False,
                "enable_gui": True,
                "alert_cooldown": 5.0,  # seconds between same alerts
                "auto_save_snapshots": True
            },
            "performance": {
                "target_fps": 15,
                "max_processing_threads": 2,
                "frame_skip_ratio": 0,  # Skip every N frames (0 = no skip)
                "memory_optimization": True
            }
        }
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            self._save_config(default_config)
            return default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        try:
            import os
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving surveillance config: {e}")
    
    def _setup_logging(self):
        """Setup logging for surveillance events"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('guardia_ai/storage/surveillance.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('GuardiaSurveillance')
    
    def _initialize_models(self):
        """Initialize AI models and components"""
        try:
            # Initialize enhanced detector with face authenticator
            if self.face_auth:
                self.enhanced_detector = EnhancedDetector(self.face_auth)
            else:
                self.enhanced_detector = EnhancedDetector()
            self.logger.info("✅ Enhanced Detector initialized")
            
            # Initialize enhanced tracker
            tracking_config = self.config.get('detection', {})
            self.tracker = EnhancedTracker(
                max_age=tracking_config.get('max_tracking_age', 30),
                min_hits=tracking_config.get('min_hits', 3),
                iou_threshold=tracking_config.get('iou_threshold', 0.3)
            )
            self.logger.info("✅ Enhanced Tracker initialized")
            
            # Initialize behavior analyzer
            self.behavior_analyzer = BehaviorAnalyzer(self.config['behavior'])
            self.logger.info("✅ Behavior Analyzer initialized")
            
            # Initialize zone manager
            self.zone_manager = ZoneManager(self.config['zones'])
            self.logger.info("✅ Zone Manager initialized")
            
        except Exception as e:
            self.logger.error(f"❌ Error initializing models: {e}")
            raise
    
    def add_alert_callback(self, callback: Callable[[AlertEvent], None]):
        """Add callback function for alert notifications"""
        self.alert_callbacks.append(callback)

    def remove_alert_callback(self, callback: Callable[[AlertEvent], None]):
        """Remove alert callback"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    def add_result_callback(self, callback: Callable[[DetectionResult], None]):
        """Add callback function for detection result notifications"""
        self.result_callbacks.append(callback)

    def remove_result_callback(self, callback: Callable[[DetectionResult], None]):
        """Remove result callback"""
        if callback in self.result_callbacks:
            self.result_callbacks.remove(callback)
    
    def start_surveillance(self):
        """Start the surveillance loop"""
        if self.running:
            self.logger.warning("Surveillance already running")
            return
        
        # Check if camera is available
        from .camera_manager import camera_manager
        active_camera = camera_manager.get_active_camera()
        if not active_camera or not active_camera.is_active:
            error_msg = "No active camera available for surveillance"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._surveillance_loop, daemon=True)
        self.processing_thread.start()
        self.logger.info("🚀 Surveillance started")
    
    def stop_surveillance(self):
        """Stop the surveillance loop"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)
        self.logger.info("⏹️ Surveillance stopped")
    
    def _surveillance_loop(self):
        """Main surveillance processing loop"""
        self.logger.info("🔄 Starting surveillance loop")
        last_frame_time = time.time()
        target_frame_time = 1.0 / self.config['performance']['target_fps']
        no_frame_count = 0
        max_no_frame_count = 50  # Stop after 50 consecutive failed frame reads (5 seconds at 10fps)
        
        while self.running:
            try:
                start_time = time.time()
                
                # Get frame from active camera
                frame = camera_manager.get_active_frame()
                if frame is None:
                    no_frame_count += 1
                    if no_frame_count >= max_no_frame_count:
                        self.logger.error("❌ Camera disconnected - no frames for extended period")
                        break
                    time.sleep(0.1)
                    continue
                else:
                    no_frame_count = 0  # Reset counter on successful frame
                
                # Process frame
                detection_result = self._process_frame(frame)
                
                # Call result callbacks
                for callback in self.result_callbacks:
                    try:
                        callback(detection_result)
                    except Exception as e:
                        self.logger.error(f"Error in result callback: {e}")
                
                # Generate alerts
                self._generate_alerts(detection_result)
                
                # Update performance metrics
                self._update_performance_metrics()
                
                # Frame rate control
                processing_time = time.time() - start_time
                if processing_time < target_frame_time:
                    time.sleep(target_frame_time - processing_time)
                
            except Exception as e:
                self.logger.error(f"Error in surveillance loop: {e}")
                time.sleep(0.1)
    
    def _process_frame(self, frame: np.ndarray) -> DetectionResult:
        """Process a single frame through all detection models"""
        start_time = time.time()
        self.frame_id += 1
        
        # Run enhanced detection
        enhanced_results = self.enhanced_detector.enhanced_detection(frame)
        
        # Update object tracking
        tracks = []
        if self.config['detection'].get('enable_tracking', True):
            try:
                tracks = self.tracker.update(enhanced_results.get('objects', []), frame)
            except Exception as e:
                self.logger.warning(f"Tracking update failed: {e}")
        
        # Run behavior analysis
        behaviors = self.behavior_analyzer.analyze_frame(
            frame, 
            enhanced_results.get('objects', []), 
            enhanced_results.get('faces', [])
        )
        
        # Check zone violations
        zones_violated = self.zone_manager.check_violations(enhanced_results.get('objects', []))
        
        # Create detection result
        result = DetectionResult(
            timestamp=datetime.now(),
            frame_id=self.frame_id,
            frame=enhanced_results.get('frame', frame.copy()),  # Use annotated frame if available
            objects=enhanced_results.get('objects', []),
            faces=enhanced_results.get('faces', []),
            behaviors=behaviors,
            threats=enhanced_results.get('threats', []),
            zones_violated=zones_violated,
            confidence_score=self._calculate_overall_confidence(enhanced_results),
            processing_time_ms=(time.time() - start_time) * 1000,
            tracks=[{
                'track_id': track.track_id,
                'object_class': track.object_class,
                'bbox': track.current_bbox,
                'confidence': track.confidence,
                'age': track.age
            } for track in tracks]
        )
        
        # Generate alerts
        self._generate_alerts(result)
        
        # Add to history (keep last 100 frames)
        self.detection_history.append(result)
        if len(self.detection_history) > 100:
            self.detection_history.pop(0)
        
        # Add frame to buffer
        if not self.frame_buffer.full():
            self.frame_buffer.put((self.frame_id, frame.copy()))
        
        return result
    
    def _calculate_overall_confidence(self, enhanced_results: Dict[str, Any]) -> float:
        """Calculate overall confidence score for the detection"""
        total_confidence = 0.0
        total_detections = 0
        
        # Face confidences
        for face in enhanced_results.get('faces', []):
            total_confidence += face.get('confidence', 0.0)
            total_detections += 1
        
        # Object confidences
        for obj in enhanced_results.get('objects', []):
            total_confidence += obj.get('confidence', 0.0)
            total_detections += 1
        
        return total_confidence / total_detections if total_detections > 0 else 0.0
    
    def _generate_alerts(self, detection_result: DetectionResult):
        """Generate alerts based on detection results"""
        alerts = []
        
        # High-priority threat objects
        for threat in detection_result.threats:
            if threat.get('threat_level') == 'high_risk':
                alert = AlertEvent(
                    alert_id=f"threat_{detection_result.frame_id}_{time.time()}",
                    timestamp=detection_result.timestamp,
                    alert_type="threat_object",
                    priority="critical",
                    zone_name="general",
                    description=f"High-risk object detected: {threat.get('class', 'unknown')}",
                    confidence=threat.get('confidence', 0.0),
                    frame_snapshot=self._get_frame_snapshot(detection_result.frame_id),
                    metadata=threat
                )
                alerts.append(alert)
        
        # Unknown faces
        for face in detection_result.faces:
            if not face.get('is_known', False):
                alert = AlertEvent(
                    alert_id=f"unknown_face_{detection_result.frame_id}_{time.time()}",
                    timestamp=detection_result.timestamp,
                    alert_type="unknown_person",
                    priority="high",
                    zone_name="general",
                    description="Unknown person detected",
                    confidence=face.get('confidence', 0.0),
                    frame_snapshot=self._get_frame_snapshot(detection_result.frame_id),
                    metadata=face
                )
                alerts.append(alert)
        
        # Zone violations
        for zone_name in detection_result.zones_violated:
            alert = AlertEvent(
                alert_id=f"zone_violation_{zone_name}_{detection_result.frame_id}",
                timestamp=detection_result.timestamp,
                alert_type="intrusion",
                priority="high",
                zone_name=zone_name,
                description=f"Zone violation detected in {zone_name}",
                confidence=0.9,
                frame_snapshot=self._get_frame_snapshot(detection_result.frame_id),
                metadata={"zone": zone_name}
            )
            alerts.append(alert)
        
        # Behavioral alerts
        for behavior in detection_result.behaviors:
            if behavior.get('alert_level', 'none') != 'none':
                priority_map = {'critical': 'critical', 'high': 'high', 'medium': 'medium', 'low': 'low'}
                alert = AlertEvent(
                    alert_id=f"behavior_{behavior['type']}_{detection_result.frame_id}",
                    timestamp=detection_result.timestamp,
                    alert_type=behavior['type'],
                    priority=priority_map.get(behavior['alert_level'], 'medium'),
                    zone_name=behavior.get('zone', 'general'),
                    description=behavior.get('description', f"{behavior['type']} detected"),
                    confidence=behavior.get('confidence', 0.0),
                    frame_snapshot=self._get_frame_snapshot(detection_result.frame_id),
                    metadata=behavior
                )
                alerts.append(alert)
        
        # Process and send alerts
        for alert in alerts:
            self._send_alert(alert)
    
    def _get_frame_snapshot(self, frame_id: int) -> Optional[np.ndarray]:
        """Get frame snapshot for alerts"""
        try:
            # Try to get from frame buffer
            temp_frames = []
            while not self.frame_buffer.empty():
                try:
                    fid, frame = self.frame_buffer.get_nowait()
                    temp_frames.append((fid, frame))
                    if fid == frame_id:
                        # Return frames to buffer
                        for temp_frame in temp_frames:
                            if not self.frame_buffer.full():
                                self.frame_buffer.put(temp_frame)
                        return frame
                except Empty:
                    break
            
            # Return frames to buffer
            for temp_frame in temp_frames:
                if not self.frame_buffer.full():
                    self.frame_buffer.put(temp_frame)
            
            # If not found, get current frame
            return camera_manager.get_active_frame()
            
        except Exception as e:
            self.logger.error(f"Error getting frame snapshot: {e}")
            return None
    
    def _send_alert(self, alert: AlertEvent):
        """Send alert through all configured channels"""
        try:
            # Add to alert queue
            self.alert_queue.put(alert)
            
            # Call registered callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Error in alert callback: {e}")
            
            # Log alert
            self.logger.warning(f"🚨 ALERT: {alert.alert_type} - {alert.description} "
                              f"(Priority: {alert.priority}, Confidence: {alert.confidence:.2f})")
            
            # Save snapshot if configured
            if self.config['alerts']['auto_save_snapshots'] and alert.frame_snapshot is not None:
                self._save_alert_snapshot(alert)
                
        except Exception as e:
            self.logger.error(f"Error sending alert: {e}")
    
    def _save_alert_snapshot(self, alert: AlertEvent):
        """Save alert frame snapshot to disk"""
        try:
            import os
            snapshot_dir = "guardia_ai/storage/alert_snapshots"
            os.makedirs(snapshot_dir, exist_ok=True)
            
            timestamp_str = alert.timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"{alert.alert_type}_{timestamp_str}_{alert.alert_id[:8]}.jpg"
            filepath = os.path.join(snapshot_dir, filename)
            
            cv2.imwrite(filepath, alert.frame_snapshot)
            self.logger.info(f"📸 Alert snapshot saved: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Error saving alert snapshot: {e}")
    
    def _update_performance_metrics(self):
        """Update FPS and performance metrics"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_start_time >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.fps_start_time)
            self.fps_counter = 0
            self.fps_start_time = current_time
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics"""
        return {
            'current_fps': self.current_fps,
            'target_fps': self.config['performance']['target_fps'],
            'frames_processed': self.frame_id,
            'detection_history_size': len(self.detection_history),
            'alert_queue_size': self.alert_queue.qsize(),
            'models_loaded': {
                'enhanced_detector': self.enhanced_detector is not None,
                'behavior_analyzer': self.behavior_analyzer is not None,
                'zone_manager': self.zone_manager is not None
            }
        }
    
    def get_recent_alerts(self, count: int = 10) -> List[AlertEvent]:
        """Get recent alerts from the queue"""
        alerts = []
        temp_alerts = []
        
        # Get alerts from queue
        while not self.alert_queue.empty() and len(alerts) < count:
            try:
                alert = self.alert_queue.get_nowait()
                alerts.append(alert)
                temp_alerts.append(alert)
            except Empty:
                break
        
        # Put alerts back in queue
        for alert in temp_alerts:
            if not self.alert_queue.full():
                self.alert_queue.put(alert)
        
        return alerts[-count:]  # Return most recent
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update surveillance configuration"""
        self.config.update(new_config)
        self._save_config(self.config)
        
        # Reinitialize components if needed
        if self.behavior_analyzer:
            self.behavior_analyzer.update_config(self.config['behavior'])
        if self.zone_manager:
            self.zone_manager.update_config(self.config['zones'])
        
        self.logger.info("📝 Surveillance configuration updated")
    
    def add_zone(self, zone_config: Dict[str, Any]):
        """Add a new detection zone"""
        if self.zone_manager:
            self.zone_manager.add_zone(zone_config)
            # Update config
            if 'zones' not in self.config:
                self.config['zones'] = {'zones': []}
            self.config['zones']['zones'].append(zone_config)
            self._save_config(self.config)
    
    def remove_zone(self, zone_name: str):
        """Remove a detection zone"""
        if self.zone_manager:
            self.zone_manager.remove_zone(zone_name)
            # Update config
            if 'zones' in self.config and 'zones' in self.config['zones']:
                self.config['zones']['zones'] = [
                    z for z in self.config['zones']['zones'] 
                    if z.get('name') != zone_name
                ]
                self._save_config(self.config)
    
    def is_running(self) -> bool:
        """Check if surveillance is currently running"""
        return self.running


def test_surveillance_engine():
    """Test the surveillance engine"""
    print("🧪 Testing Surveillance Engine...")
    
    # Create surveillance engine
    engine = SurveillanceEngine()
    
    # Add alert callback for testing
    def test_alert_callback(alert: AlertEvent):
        print(f"🚨 Test Alert: {alert.alert_type} - {alert.description}")
    
    engine.add_alert_callback(test_alert_callback)
    
    # Start surveillance
    engine.start_surveillance()
    
    print("🔄 Surveillance running... Press Ctrl+C to stop")
    try:
        while True:
            # Print performance stats every 5 seconds
            time.sleep(5)
            stats = engine.get_performance_stats()
            print(f"📊 FPS: {stats['current_fps']:.1f}, "
                  f"Frames: {stats['frames_processed']}, "
                  f"Alerts: {stats['alert_queue_size']}")
            
            # Show recent alerts
            alerts = engine.get_recent_alerts(3)
            if alerts:
                print(f"🚨 Recent alerts: {len(alerts)}")
                for alert in alerts:
                    print(f"   - {alert.alert_type}: {alert.description}")
    
    except KeyboardInterrupt:
        print("\n⏹️ Stopping surveillance...")
        engine.stop_surveillance()
        print("✅ Surveillance stopped")


if __name__ == "__main__":
    test_surveillance_engine()
