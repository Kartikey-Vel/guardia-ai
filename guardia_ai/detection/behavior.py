#!/usr/bin/env python3
"""
Guardia AI - Advanced Behavior Detection & Analysis Module
Developed by Tackle Studioz

Implements sophisticated behavior detection including:
- Loitering detection
- Intrusion analysis  
- Crowd formation monitoring
- Aggression detection
- Line crossing detection
- Abnormal motion patterns
- Pose-based behavior analysis
"""

import cv2
import numpy as np
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque

# Deep learning imports
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

try:
    from ultralytics import YOLO
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Anomaly detection imports
try:
    from pyod.models.auto_encoder import AutoEncoder
    from pyod.models.lof import LOF
    from sklearn.preprocessing import StandardScaler
    ANOMALY_DETECTION_AVAILABLE = True
except ImportError:
    ANOMALY_DETECTION_AVAILABLE = False

# Import for optical flow and motion analysis
try:
    from scipy.spatial.distance import euclidean
    from scipy.signal import find_peaks
    import numpy.linalg as la
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

@dataclass
class TrackedObject:
    """Represents a tracked object across frames"""
    object_id: str
    object_type: str  # 'person', 'vehicle', etc.
    positions: deque = field(default_factory=lambda: deque(maxlen=50))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=50))
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    bounding_boxes: deque = field(default_factory=lambda: deque(maxlen=50))
    confidence_scores: deque = field(default_factory=lambda: deque(maxlen=50))
    
    # Behavior tracking
    stationary_time: float = 0.0
    total_distance: float = 0.0
    average_velocity: float = 0.0
    max_velocity: float = 0.0
    direction_changes: int = 0
    zone_violations: List[str] = field(default_factory=list)
    behavior_flags: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BehaviorEvent:
    """Represents a detected behavior event"""
    event_id: str
    behavior_type: str
    object_id: str
    start_time: datetime
    end_time: Optional[datetime]
    confidence: float
    alert_level: str  # 'critical', 'high', 'medium', 'low', 'none'
    description: str
    zone: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class BehaviorAnalyzer:
    """
    Advanced behavior analysis system using multiple detection techniques
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tracked_objects: Dict[str, TrackedObject] = {}
        self.behavior_events: Dict[str, BehaviorEvent] = {}
        self.frame_history: deque = deque(maxlen=30)
        
        # Initialize pose detection
        if MEDIAPIPE_AVAILABLE:
            self.mp_pose = mp.solutions.pose
            self.mp_drawing = mp.solutions.drawing_utils
            self.pose_detector = self.mp_pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                smooth_landmarks=True,
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5
            )
            print("✅ MediaPipe Pose Detection initialized")
        else:
            self.pose_detector = None
            print("⚠️ MediaPipe not available - pose analysis disabled")
        
        # Behavior detection thresholds
        self.loitering_threshold = config.get('loitering_time_threshold', 10.0)
        self.intrusion_sensitivity = config.get('intrusion_sensitivity', 0.8)
        self.crowd_threshold = config.get('crowd_density_threshold', 5)
        self.aggression_enabled = config.get('aggression_detection', True)
        self.pose_analysis_enabled = config.get('pose_analysis', True)
        
        # Motion analysis
        self.motion_analyzer = MotionAnalyzer()
        self.optical_flow = OpticalFlowAnalyzer()
        
        # Line crossing detection
        self.virtual_lines: List[Dict[str, Any]] = []
        
        # Advanced anomaly detection
        self.anomaly_detector = AdvancedAnomalyDetector(sequence_length=10)
        
        print("🧠 Behavior Analyzer initialized")
    
    def analyze_frame(self, frame: np.ndarray, objects: List[Dict[str, Any]], 
                     faces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze a frame for behavioral patterns
        """
        behaviors = []
        current_time = datetime.now()
        
        # Update tracked objects
        self._update_tracked_objects(objects, faces, current_time)
        
        # Analyze behaviors for each tracked object
        for obj_id, tracked_obj in self.tracked_objects.items():
            # Skip if object is too new (need history)
            if len(tracked_obj.positions) < 3:
                continue
            
            # 1. Loitering detection
            loitering_behavior = self._detect_loitering(tracked_obj, current_time)
            if loitering_behavior:
                behaviors.append(loitering_behavior)
            
            # 2. Intrusion detection (handled by zone manager, but can add velocity-based)
            intrusion_behavior = self._detect_intrusion_behavior(tracked_obj)
            if intrusion_behavior:
                behaviors.append(intrusion_behavior)
            
            # 3. Erratic movement / aggression
            if self.aggression_enabled:
                aggression_behavior = self._detect_aggression(tracked_obj, frame)
                if aggression_behavior:
                    behaviors.append(aggression_behavior)
            
            # 4. Line crossing
            line_crossing = self._detect_line_crossing(tracked_obj)
            if line_crossing:
                behaviors.append(line_crossing)
        
        # 5. Crowd formation analysis
        crowd_behavior = self._detect_crowd_formation(objects, faces)
        if crowd_behavior:
            behaviors.append(crowd_behavior)
        
        # 6. Global motion analysis
        motion_behaviors = self._analyze_global_motion(frame)
        behaviors.extend(motion_behaviors)
        
        # 7. Pose-based behavior analysis
        if self.pose_analysis_enabled and self.pose_detector:
            pose_behaviors = self._analyze_pose_behaviors(frame, objects)
            behaviors.extend(pose_behaviors)
        
        # 8. Anomaly detection
        anomaly_behaviors = self._detect_anomalies(frame, objects)
        behaviors.extend(anomaly_behaviors)
        
        # Update frame history
        self.frame_history.append({
            'timestamp': current_time,
            'frame': frame.copy(),
            'objects': objects,
            'faces': faces,
            'behaviors': behaviors
        })
        
        return behaviors
    
    def _update_tracked_objects(self, objects: List[Dict[str, Any]], 
                               faces: List[Dict[str, Any]], current_time: datetime):
        """Update tracked objects with new detections"""
        # Combine objects and faces for tracking
        all_detections = []
        
        # Add objects
        for obj in objects:
            bbox = obj.get('bbox', [0, 0, 0, 0])
            all_detections.append({
                'id': f"obj_{obj.get('class', 'unknown')}_{bbox[0]}_{bbox[1]}",
                'type': obj.get('class', 'unknown'),
                'bbox': bbox,
                'confidence': obj.get('confidence', 0.0),
                'center': self._get_bbox_center(bbox)
            })
        
        # Add faces
        for face in faces:
            bbox = face.get('bbox', [0, 0, 0, 0])
            all_detections.append({
                'id': f"face_{face.get('identity', 'unknown')}_{bbox[0]}_{bbox[1]}",
                'type': 'person',
                'bbox': bbox,
                'confidence': face.get('confidence', 0.0),
                'center': self._get_bbox_center(bbox),
                'is_known': face.get('is_known', False),
                'identity': face.get('identity', 'unknown')
            })
        
        # Update existing tracks or create new ones
        matched_ids = set()
        
        for detection in all_detections:
            best_match_id = None
            best_distance = float('inf')
            
            # Find best matching existing track
            for obj_id, tracked_obj in self.tracked_objects.items():
                if tracked_obj.object_type == detection['type'] and len(tracked_obj.positions) > 0:
                    last_pos = tracked_obj.positions[-1]
                    distance = self._calculate_distance(last_pos, detection['center'])
                    
                    # Match if within reasonable distance (adaptive threshold)
                    max_distance = 100 if tracked_obj.object_type == 'person' else 150
                    if distance < max_distance and distance < best_distance:
                        best_distance = distance
                        best_match_id = obj_id
            
            if best_match_id:
                # Update existing track
                tracked_obj = self.tracked_objects[best_match_id]
                tracked_obj.positions.append(detection['center'])
                tracked_obj.timestamps.append(current_time)
                tracked_obj.bounding_boxes.append(detection['bbox'])
                tracked_obj.confidence_scores.append(detection['confidence'])
                tracked_obj.last_seen = current_time
                
                # Update movement statistics
                self._update_movement_stats(tracked_obj)
                matched_ids.add(best_match_id)
            else:
                # Create new track
                new_id = f"{detection['type']}_{int(time.time() * 1000)}"
                new_tracked_obj = TrackedObject(
                    object_id=new_id,
                    object_type=detection['type'],
                    first_seen=current_time,
                    last_seen=current_time
                )
                new_tracked_obj.positions.append(detection['center'])
                new_tracked_obj.timestamps.append(current_time)
                new_tracked_obj.bounding_boxes.append(detection['bbox'])
                new_tracked_obj.confidence_scores.append(detection['confidence'])
                
                # Add face-specific metadata
                if 'is_known' in detection:
                    new_tracked_obj.behavior_flags['is_known_face'] = detection['is_known']
                    new_tracked_obj.behavior_flags['identity'] = detection['identity']
                
                self.tracked_objects[new_id] = new_tracked_obj
                matched_ids.add(new_id)
        
        # Remove old tracks (not seen for 5 seconds)
        cutoff_time = current_time - timedelta(seconds=5)
        expired_ids = [
            obj_id for obj_id, tracked_obj in self.tracked_objects.items()
            if tracked_obj.last_seen < cutoff_time
        ]
        for obj_id in expired_ids:
            del self.tracked_objects[obj_id]
    
    def _get_bbox_center(self, bbox: List[int]) -> Tuple[int, int]:
        """Get center point of bounding box"""
        if len(bbox) < 4:
            return (0, 0)
        
        try:
            x, y, w, h = [int(val) for val in bbox[:4]]
            return (x + w // 2, y + h // 2)
        except (ValueError, TypeError):
            return (0, 0)
    
    def _calculate_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _update_movement_stats(self, tracked_obj: TrackedObject):
        """Update movement statistics for tracked object"""
        if len(tracked_obj.positions) < 2:
            return
        
        # Calculate distance from previous position
        current_pos = tracked_obj.positions[-1]
        previous_pos = tracked_obj.positions[-2]
        distance = self._calculate_distance(current_pos, previous_pos)
        tracked_obj.total_distance += distance
        
        # Calculate velocity (pixels per second)
        if len(tracked_obj.timestamps) >= 2:
            time_diff = (tracked_obj.timestamps[-1] - tracked_obj.timestamps[-2]).total_seconds()
            if time_diff > 0:
                velocity = distance / time_diff
                tracked_obj.average_velocity = tracked_obj.total_distance / (
                    tracked_obj.timestamps[-1] - tracked_obj.timestamps[0]
                ).total_seconds()
                tracked_obj.max_velocity = max(tracked_obj.max_velocity, velocity)
        
        # Check if stationary (very low movement)
        if distance < 10:  # 10 pixel threshold
            if len(tracked_obj.timestamps) >= 2:
                time_diff = (tracked_obj.timestamps[-1] - tracked_obj.timestamps[-2]).total_seconds()
                tracked_obj.stationary_time += time_diff
        else:
            tracked_obj.stationary_time = 0.0
        
        # Count direction changes
        if len(tracked_obj.positions) >= 3:
            p1, p2, p3 = tracked_obj.positions[-3:]
            angle1 = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            angle2 = math.atan2(p3[1] - p2[1], p3[0] - p2[0])
            angle_diff = abs(angle2 - angle1)
            if angle_diff > math.pi / 2:  # 90 degree change
                tracked_obj.direction_changes += 1
    
    def _detect_loitering(self, tracked_obj: TrackedObject, current_time: datetime) -> Optional[Dict[str, Any]]:
        """Detect loitering behavior"""
        if tracked_obj.stationary_time > self.loitering_threshold:
            return {
                'type': 'loitering',
                'object_id': tracked_obj.object_id,
                'confidence': min(tracked_obj.stationary_time / self.loitering_threshold, 1.0),
                'alert_level': 'medium' if tracked_obj.stationary_time < 30 else 'high',
                'description': f"Object loitering for {tracked_obj.stationary_time:.1f} seconds",
                'zone': 'general',
                'duration': tracked_obj.stationary_time,
                'position': tracked_obj.positions[-1] if tracked_obj.positions else None
            }
        return None
    
    def _detect_intrusion_behavior(self, tracked_obj: TrackedObject) -> Optional[Dict[str, Any]]:
        """Detect intrusion-like behavior patterns"""
        if len(tracked_obj.positions) < 5:
            return None
        
        # Check for rapid approach to sensitive areas (edges of frame)
        frame_edges = self._check_frame_edge_approach(tracked_obj)
        if frame_edges:
            return frame_edges
        
        # Check for suspicious movement patterns
        if tracked_obj.average_velocity > 50 and tracked_obj.direction_changes > 3:
            return {
                'type': 'suspicious_movement',
                'object_id': tracked_obj.object_id,
                'confidence': 0.7,
                'alert_level': 'medium',
                'description': "Erratic high-speed movement detected",
                'zone': 'general',
                'velocity': tracked_obj.average_velocity,
                'direction_changes': tracked_obj.direction_changes
            }
        
        return None
    
    def _check_frame_edge_approach(self, tracked_obj: TrackedObject) -> Optional[Dict[str, Any]]:
        """Check if object is rapidly approaching frame edges"""
        if len(tracked_obj.positions) < 3:
            return None
        
        # Assume frame dimensions (can be updated with actual frame size)
        frame_width, frame_height = 640, 480
        edge_threshold = 50  # pixels from edge
        
        current_pos = tracked_obj.positions[-1]
        x, y = current_pos
        
        # Check if near edges and moving towards them
        near_edge = (x < edge_threshold or x > frame_width - edge_threshold or
                    y < edge_threshold or y > frame_height - edge_threshold)
        
        if near_edge and tracked_obj.average_velocity > 30:
            return {
                'type': 'edge_approach',
                'object_id': tracked_obj.object_id,
                'confidence': 0.8,
                'alert_level': 'high',
                'description': "Rapid approach to restricted boundary",
                'zone': 'boundary',
                'position': current_pos,
                'velocity': tracked_obj.average_velocity
            }
        
        return None
    
    def _detect_aggression(self, tracked_obj: TrackedObject, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """Detect aggressive behavior using movement patterns and pose analysis"""
        if tracked_obj.object_type != 'person':
            return None
        
        # Movement-based aggression indicators
        is_erratic = (tracked_obj.direction_changes > 5 and 
                     tracked_obj.max_velocity > 80 and 
                     len(tracked_obj.positions) > 10)
        
        # Pose-based aggression (if pose detection available)
        pose_aggression_score = 0.0
        if self.pose_detector and len(tracked_obj.bounding_boxes) > 0:
            bbox = tracked_obj.bounding_boxes[-1]
            pose_aggression_score = self._analyze_aggressive_pose(frame, bbox)
        
        # Combined score
        total_score = 0.0
        if is_erratic:
            total_score += 0.6
        total_score += pose_aggression_score * 0.4
        
        if total_score > 0.5:
            alert_level = 'critical' if total_score > 0.8 else 'high'
            return {
                'type': 'aggression',
                'object_id': tracked_obj.object_id,
                'confidence': total_score,
                'alert_level': alert_level,
                'description': f"Aggressive behavior detected (score: {total_score:.2f})",
                'zone': 'general',
                'movement_score': 0.6 if is_erratic else 0.0,
                'pose_score': pose_aggression_score,
                'velocity': tracked_obj.max_velocity,
                'direction_changes': tracked_obj.direction_changes
            }
        
        return None
    
    def _analyze_aggressive_pose(self, frame: np.ndarray, bbox: List[int]) -> float:
        """Analyze pose for aggressive indicators"""
        if not self.pose_detector:
            return 0.0
        
        try:
            # Ensure bbox values are integers
            if len(bbox) < 4:
                return 0.0
            
            x, y, w, h = [int(val) for val in bbox[:4]]
            
            # Validate bbox coordinates
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                return 0.0
            
            # Ensure we don't go out of frame bounds
            frame_h, frame_w = frame.shape[:2]
            x = max(0, min(x, frame_w - 1))
            y = max(0, min(y, frame_h - 1))
            w = min(w, frame_w - x)
            h = min(h, frame_h - y)
            
            if w <= 0 or h <= 0:
                return 0.0
            
            person_roi = frame[y:y+h, x:x+w]
            
            if person_roi.size == 0:
                return 0.0
            
            # Convert to RGB for MediaPipe
            rgb_roi = cv2.cvtColor(person_roi, cv2.COLOR_BGR2RGB)
            results = self.pose_detector.process(rgb_roi)
            
            if not results.pose_landmarks:
                return 0.0
            
            landmarks = results.pose_landmarks.landmark
            aggression_score = 0.0
            
            # Check for raised arms (fighting stance)
            left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
            right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
            
            # Arms raised above shoulders
            if (left_wrist.y < left_shoulder.y and right_wrist.y < right_shoulder.y):
                aggression_score += 0.4
            
            # Wide stance (legs apart)
            left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
            right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
            left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE]
            right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE]
            
            hip_width = abs(right_hip.x - left_hip.x)
            ankle_width = abs(right_ankle.x - left_ankle.x)
            
            if ankle_width > hip_width * 1.5:  # Wide stance
                aggression_score += 0.3
            
            # Forward lean (aggressive posture)
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE]
            mid_hip = (left_hip.x + right_hip.x) / 2
            
            if nose.x > mid_hip:  # Leaning forward
                aggression_score += 0.2
            
            return min(aggression_score, 1.0)
            
        except Exception as e:
            print(f"Error in pose analysis: {e}")
            return 0.0
    
    def _detect_line_crossing(self, tracked_obj: TrackedObject) -> Optional[Dict[str, Any]]:
        """Detect virtual line crossing"""
        if len(tracked_obj.positions) < 2:
            return None
        
        current_pos = tracked_obj.positions[-1]
        previous_pos = tracked_obj.positions[-2]
        
        for line in self.virtual_lines:
            if self._line_intersection(previous_pos, current_pos, line['start'], line['end']):
                return {
                    'type': 'line_crossing',
                    'object_id': tracked_obj.object_id,
                    'confidence': 0.9,
                    'alert_level': line.get('alert_level', 'medium'),
                    'description': f"Virtual line '{line['name']}' crossed",
                    'zone': line.get('zone', 'general'),
                    'line_name': line['name'],
                    'crossing_point': current_pos,
                    'direction': self._get_crossing_direction(previous_pos, current_pos, line)
                }
        
        return None
    
    def _line_intersection(self, p1: Tuple[int, int], p2: Tuple[int, int], 
                          p3: Tuple[int, int], p4: Tuple[int, int]) -> bool:
        """Check if two line segments intersect"""
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
        
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
    
    def _get_crossing_direction(self, p1: Tuple[int, int], p2: Tuple[int, int], 
                               line: Dict[str, Any]) -> str:
        """Determine crossing direction"""
        # Simple implementation - can be enhanced
        line_vector = (line['end'][0] - line['start'][0], line['end'][1] - line['start'][1])
        movement_vector = (p2[0] - p1[0], p2[1] - p1[1])
        
        # Cross product to determine direction
        cross = line_vector[0] * movement_vector[1] - line_vector[1] * movement_vector[0]
        return "left_to_right" if cross > 0 else "right_to_left"
    
    def _detect_crowd_formation(self, objects: List[Dict[str, Any]], 
                               faces: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Detect crowd formation and density"""
        people_count = len([obj for obj in objects if obj.get('class') == 'person']) + len(faces)
        
        if people_count >= self.crowd_threshold:
            # Calculate crowd density
            all_positions = []
            for obj in objects:
                if obj.get('class') == 'person':
                    bbox = obj.get('bbox', [0, 0, 0, 0])
                    all_positions.append(self._get_bbox_center(bbox))
            
            for face in faces:
                bbox = face.get('bbox', [0, 0, 0, 0])
                all_positions.append(self._get_bbox_center(bbox))
            
            if len(all_positions) >= self.crowd_threshold:
                density = self._calculate_crowd_density(all_positions)
                
                return {
                    'type': 'crowd_formation',
                    'object_id': 'crowd',
                    'confidence': min(people_count / (self.crowd_threshold * 2), 1.0),
                    'alert_level': 'high' if people_count > self.crowd_threshold * 2 else 'medium',
                    'description': f"Crowd of {people_count} people detected",
                    'zone': 'general',
                    'people_count': people_count,
                    'density': density,
                    'positions': all_positions
                }
        
        return None
    
    def _calculate_crowd_density(self, positions: List[Tuple[int, int]]) -> float:
        """Calculate crowd density metric"""
        if len(positions) < 2:
            return 0.0
        
        total_distance = 0.0
        pair_count = 0
        
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                distance = self._calculate_distance(positions[i], positions[j])
                total_distance += distance
                pair_count += 1
        
        average_distance = total_distance / pair_count if pair_count > 0 else 0.0
        # Higher density = lower average distance
        density = 1000.0 / (average_distance + 1.0)  # Normalize
        return min(density, 100.0)
    
    def _analyze_global_motion(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Analyze global motion patterns in the frame"""
        behaviors = []
        
        # Use optical flow analysis
        motion_data = self.optical_flow.analyze_frame(frame)
        
        if motion_data:
            # Check for unusual motion patterns
            if motion_data.get('average_magnitude', 0) > 50:
                behaviors.append({
                    'type': 'high_motion_activity',
                    'object_id': 'global',
                    'confidence': min(motion_data['average_magnitude'] / 100.0, 1.0),
                    'alert_level': 'low',
                    'description': "High motion activity detected in scene",
                    'zone': 'general',
                    'motion_magnitude': motion_data['average_magnitude'],
                    'motion_direction': motion_data.get('dominant_direction', 'unknown')
                })
        
        return behaviors
    
    def _analyze_pose_behaviors(self, frame: np.ndarray, objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze pose-specific behaviors"""
        behaviors = []
        
        if not self.pose_detector:
            return behaviors
        
        for obj in objects:
            if obj.get('class') == 'person':
                bbox = obj.get('bbox', [0, 0, 0, 0])
                pose_behavior = self._analyze_person_pose(frame, bbox)
                if pose_behavior:
                    behaviors.append(pose_behavior)
        
        return behaviors
    
    def _analyze_person_pose(self, frame: np.ndarray, bbox: List[int]) -> Optional[Dict[str, Any]]:
        """Analyze individual person's pose for behavioral indicators"""
        try:
            # Ensure bbox values are integers
            if len(bbox) < 4:
                return None
            
            x, y, w, h = [int(val) for val in bbox[:4]]
            
            # Validate bbox coordinates
            if x < 0 or y < 0 or w <= 0 or h <= 0:
                return None
            
            # Ensure we don't go out of frame bounds
            frame_h, frame_w = frame.shape[:2]
            x = max(0, min(x, frame_w - 1))
            y = max(0, min(y, frame_h - 1))
            w = min(w, frame_w - x)
            h = min(h, frame_h - y)
            
            if w <= 0 or h <= 0:
                return None
            
            person_roi = frame[y:y+h, x:x+w]
            
            if person_roi.size == 0:
                return None
            
            rgb_roi = cv2.cvtColor(person_roi, cv2.COLOR_BGR2RGB)
            results = self.pose_detector.process(rgb_roi)
            
            if not results.pose_landmarks:
                return None
            
            landmarks = results.pose_landmarks.landmark
            
            # Check for specific poses
            pose_type = self._classify_pose(landmarks)
            
            if pose_type and pose_type != 'normal':
                return {
                    'type': f'pose_{pose_type}',
                    'object_id': f'person_{x}_{y}',
                    'confidence': 0.7,
                    'alert_level': 'low' if pose_type in ['sitting', 'lying'] else 'medium',
                    'description': f"Person in {pose_type} pose detected",
                    'zone': 'general',
                    'pose_type': pose_type,
                    'bbox': bbox
                }
        
        except Exception as e:
            print(f"Error in pose analysis: {e}")
        
        return None
    
    def _classify_pose(self, landmarks) -> Optional[str]:
        """Classify the person's pose"""
        try:
            # Get key landmarks
            nose = landmarks[self.mp_pose.PoseLandmark.NOSE]
            left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
            right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
            right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
            left_knee = landmarks[self.mp_pose.PoseLandmark.LEFT_KNEE]
            right_knee = landmarks[self.mp_pose.PoseLandmark.RIGHT_KNEE]
            
            # Check if person is lying down
            shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
            hip_y = (left_hip.y + right_hip.y) / 2
            knee_y = (left_knee.y + right_knee.y) / 2
            
            if abs(shoulder_y - hip_y) < 0.1 and abs(hip_y - knee_y) < 0.1:
                return 'lying'
            
            # Check if person is sitting (knees above hips)
            if knee_y < hip_y - 0.1:
                return 'sitting'
            
            # Check for raised arms (possibly surrendering or celebrating)
            left_wrist = landmarks[self.mp_pose.PoseLandmark.LEFT_WRIST]
            right_wrist = landmarks[self.mp_pose.PoseLandmark.RIGHT_WRIST]
            
            if (left_wrist.y < left_shoulder.y - 0.1 and 
                right_wrist.y < right_shoulder.y - 0.1):
                return 'arms_raised'
            
            return 'normal'
            
        except Exception:
            return None
    
    def add_virtual_line(self, name: str, start: Tuple[int, int], end: Tuple[int, int], 
                        alert_level: str = 'medium', zone: str = 'general'):
        """Add a virtual line for crossing detection"""
        self.virtual_lines.append({
            'name': name,
            'start': start,
            'end': end,
            'alert_level': alert_level,
            'zone': zone
        })
    
    def remove_virtual_line(self, name: str):
        """Remove a virtual line"""
        self.virtual_lines = [line for line in self.virtual_lines if line['name'] != name]
    
    def get_tracked_objects(self) -> Dict[str, TrackedObject]:
        """Get all currently tracked objects"""
        return self.tracked_objects
    
    def get_behavior_events(self) -> Dict[str, BehaviorEvent]:
        """Get all behavior events"""
        return self.behavior_events
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update behavior analysis configuration"""
        self.config.update(new_config)
        self.loitering_threshold = self.config.get('loitering_time_threshold', 10.0)
        self.intrusion_sensitivity = self.config.get('intrusion_sensitivity', 0.8)
        self.crowd_threshold = self.config.get('crowd_density_threshold', 5)
        self.aggression_enabled = self.config.get('aggression_detection', True)
        self.pose_analysis_enabled = self.config.get('pose_analysis', True)
    

    def _detect_anomalies(self, frame: np.ndarray, objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in the frame using advanced methods"""
        return self.anomaly_detector.analyze_motion_anomaly(frame, objects)


class MotionAnalyzer:
    """Analyzes motion patterns for anomaly detection"""
    
    def __init__(self):
        self.prev_frame = None
        self.motion_history = deque(maxlen=10)
    
    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze motion in the current frame"""
        if self.prev_frame is None:
            self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return {}
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate frame difference
        diff = cv2.absdiff(gray, self.prev_frame)
        
        # Threshold the difference
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        
        # Calculate motion metrics
        motion_pixels = cv2.countNonZero(thresh)
        total_pixels = frame.shape[0] * frame.shape[1]
        motion_percentage = (motion_pixels / total_pixels) * 100
        
        self.motion_history.append(motion_percentage)
        self.prev_frame = gray
        
        return {
            'motion_percentage': motion_percentage,
            'motion_trend': self._analyze_motion_trend(),
            'is_anomalous': motion_percentage > 20  # Threshold for anomalous motion
        }
    
    def _analyze_motion_trend(self) -> str:
        """Analyze motion trend over recent frames"""
        if len(self.motion_history) < 3:
            return 'stable'
        
        recent = list(self.motion_history)[-3:]
        if all(recent[i] > recent[i-1] for i in range(1, len(recent))):
            return 'increasing'
        elif all(recent[i] < recent[i-1] for i in range(1, len(recent))):
            return 'decreasing'
        else:
            return 'stable'


class OpticalFlowAnalyzer:
    """Analyzes optical flow for motion direction and magnitude"""
    
    def __init__(self):
        self.prev_gray = None
        
        # Parameters for Lucas-Kanade optical flow
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        # Parameters for Shi-Tomasi corner detection
        self.feature_params = dict(
            maxCorners=100,
            qualityLevel=0.3,
            minDistance=7,
            blockSize=7
        )
    
    def analyze_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Analyze optical flow in the frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            return {}
        
        # Detect feature points in previous frame
        prev_pts = cv2.goodFeaturesToTrack(self.prev_gray, mask=None, **self.feature_params)
        
        if prev_pts is None:
            self.prev_gray = gray
            return {}
        
        # Calculate optical flow
        next_pts, status, error = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, gray, prev_pts, None, **self.lk_params
        )
        
        # Select good points
        good_new = next_pts[status == 1]
        good_old = prev_pts[status == 1]
        
        if len(good_new) == 0:
            self.prev_gray = gray
            return {}
        
        # Calculate motion vectors
        motion_vectors = good_new - good_old
        magnitudes = np.sqrt(motion_vectors[:, 0]**2 + motion_vectors[:, 1]**2)
        angles = np.arctan2(motion_vectors[:, 1], motion_vectors[:, 0])
        
        # Calculate statistics
        avg_magnitude = np.mean(magnitudes)
        avg_angle = np.mean(angles)
        
        # Determine dominant direction
        dominant_direction = self._angle_to_direction(avg_angle)
        
        self.prev_gray = gray
        
        return {
            'average_magnitude': avg_magnitude,
            'dominant_direction': dominant_direction,
            'motion_vectors': motion_vectors,
            'num_tracked_points': len(good_new)
        }
    
    def _angle_to_direction(self, angle: float) -> str:
        """Convert angle to direction string"""
        # Convert angle to degrees
        angle_deg = np.degrees(angle)
        
        # Normalize to 0-360
        if angle_deg < 0:
            angle_deg += 360
        
        # Determine direction
        if 0 <= angle_deg < 45 or 315 <= angle_deg < 360:
            return 'right'
        elif 45 <= angle_deg < 135:
            return 'down'
        elif 135 <= angle_deg < 225:
            return 'left'
        elif 225 <= angle_deg < 315:
            return 'up'
        else:
            return 'unknown'


class ConvLSTMCell(nn.Module):
    """ConvLSTM Cell implementation"""
    def __init__(self, input_channels, hidden_channels, kernel_size):
        super(ConvLSTMCell, self).__init__()
        
        self.input_channels = input_channels
        self.hidden_channels = hidden_channels
        self.kernel_size = kernel_size
        self.padding = kernel_size // 2
        
        self.conv = nn.Conv2d(
            input_channels + hidden_channels,
            4 * hidden_channels,
            kernel_size,
            padding=self.padding
        )
    
    def forward(self, x, state):
        h, c = state
        
        combined = torch.cat([x, h], dim=1)
        gates = self.conv(combined)
        
        i, f, o, g = torch.chunk(gates, 4, dim=1)
        
        i = torch.sigmoid(i)
        f = torch.sigmoid(f)
        o = torch.sigmoid(o)
        g = torch.tanh(g)
        
        c_new = f * c + i * g
        h_new = o * torch.tanh(c_new)
        
        return h_new, c_new


class ConvLSTMAnomalyDetector(nn.Module):
    """
    ConvLSTM-based anomaly detection for motion patterns
    """
    def __init__(self, input_channels=3, hidden_channels=64, kernel_size=3, sequence_length=10):
        super(ConvLSTMAnomalyDetector, self).__init__()
        
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch not available for ConvLSTM")
        
        self.sequence_length = sequence_length
        self.hidden_channels = hidden_channels
        
        # ConvLSTM layers
        self.conv_lstm1 = ConvLSTMCell(input_channels, hidden_channels, kernel_size)
        self.conv_lstm2 = ConvLSTMCell(hidden_channels, hidden_channels, kernel_size)
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Conv2d(hidden_channels, hidden_channels // 2, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(hidden_channels // 2, input_channels, 3, padding=1),
            nn.Sigmoid()
        )
        
        self.criterion = nn.MSELoss()
        
    def forward(self, x):
        batch_size, seq_len, channels, height, width = x.size()
        
        h1, c1 = self.init_hidden(batch_size, height, width)
        h2, c2 = self.init_hidden(batch_size, height, width)
        
        # Encode sequence
        for t in range(seq_len):
            h1, c1 = self.conv_lstm1(x[:, t], (h1, c1))
            h2, c2 = self.conv_lstm2(h1, (h2, c2))
        
        # Decode
        reconstructed = self.decoder(h2)
        return reconstructed
    
    def init_hidden(self, batch_size, height, width):
        h = torch.zeros(batch_size, self.hidden_channels, height, width)
        c = torch.zeros(batch_size, self.hidden_channels, height, width)
        return h, c
    
    def detect_anomaly(self, sequence, threshold=0.1):
        """Detect anomalies in motion sequence"""
        with torch.no_grad():
            if len(sequence) < self.sequence_length:
                return False, 0.0
            
            # Prepare input
            input_seq = torch.stack(sequence[-self.sequence_length:]).unsqueeze(0)
            
            # Forward pass
            reconstruction = self.forward(input_seq)
            
            # Calculate reconstruction error
            error = F.mse_loss(reconstruction, input_seq[:, -1:]).item()
            
            return error > threshold, error


class MotionAutoencoder(nn.Module):
    """
    Autoencoder for anomaly detection in motion patterns
    """
    def __init__(self, input_size=128, hidden_sizes=[64, 32, 16]):
        super(MotionAutoencoder, self).__init__()
        
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch not available for Autoencoder")
        
        # Encoder
        encoder_layers = []
        prev_size = input_size
        for hidden_size in hidden_sizes:
            encoder_layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_size = hidden_size
        
        # Decoder
        decoder_layers = []
        for i in range(len(hidden_sizes) - 1, -1, -1):
            if i == len(hidden_sizes) - 1:
                continue
            decoder_layers.extend([
                nn.Linear(prev_size, hidden_sizes[i]),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_size = hidden_sizes[i]
        
        decoder_layers.append(nn.Linear(prev_size, input_size))
        
        self.encoder = nn.Sequential(*encoder_layers)
        self.decoder = nn.Sequential(*decoder_layers)
    
    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded
    
    def detect_anomaly(self, motion_features, threshold=0.5):
        """Detect anomalies in motion features"""
        with torch.no_grad():
            if isinstance(motion_features, np.ndarray):
                motion_features = torch.FloatTensor(motion_features)
            
            reconstruction = self.forward(motion_features)
            error = F.mse_loss(reconstruction, motion_features).item()
            
            return error > threshold, error


class AdvancedAnomalyDetector:
    """
    Advanced anomaly detection combining multiple methods
    """
    def __init__(self, frame_size=(64, 64), sequence_length=10):
        self.frame_size = frame_size
        self.sequence_length = sequence_length
        self.motion_history = deque(maxlen=sequence_length)
        self.feature_history = deque(maxlen=100)
        
        # Initialize models if available
        self.conv_lstm = None
        self.motion_autoencoder = None
        self.statistical_detector = None
        
        if TORCH_AVAILABLE:
            try:
                self.conv_lstm = ConvLSTMAnomalyDetector(
                    input_channels=3,
                    sequence_length=sequence_length
                )
                self.motion_autoencoder = MotionAutoencoder(input_size=128)
                print("✅ Deep learning anomaly detectors initialized")
            except Exception as e:
                print(f"⚠️ Deep learning anomaly detection failed: {e}")
        
        if ANOMALY_DETECTION_AVAILABLE:
            try:
                self.statistical_detector = LOF(n_neighbors=20, contamination=0.1)
                self.scaler = StandardScaler()
                print("✅ Statistical anomaly detector initialized")
            except Exception as e:
                print(f"⚠️ Statistical anomaly detection failed: {e}")
    
    def analyze_motion_anomaly(self, frame: np.ndarray, objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze frame for motion anomalies"""
        anomalies = []
        
        # Resize frame for processing
        resized_frame = cv2.resize(frame, self.frame_size)
        self.motion_history.append(resized_frame)
        
        # Extract motion features
        motion_features = self._extract_motion_features(objects)
        if motion_features is not None:
            self.feature_history.append(motion_features)
        
        # Deep learning based detection
        if self.conv_lstm and len(self.motion_history) == self.sequence_length:
            try:
                motion_sequence = [torch.FloatTensor(frame / 255.0).permute(2, 0, 1) 
                                 for frame in self.motion_history]
                is_anomaly, error = self.conv_lstm.detect_anomaly(motion_sequence)
                
                if is_anomaly:
                    anomalies.append({
                        'type': 'motion_anomaly',
                        'method': 'conv_lstm',
                        'confidence': min(error * 2, 1.0),
                        'alert_level': 'high' if error > 0.3 else 'medium',
                        'description': f"Abnormal motion pattern detected (error: {error:.3f})",
                        'error_score': error
                    })
            except Exception as e:
                print(f"ConvLSTM anomaly detection error: {e}")
        
        # Statistical anomaly detection
        if (self.statistical_detector and len(self.feature_history) >= 20 and 
            motion_features is not None):
            try:
                # Fit detector on historical features
                feature_array = np.array(list(self.feature_history))
                scaled_features = self.scaler.fit_transform(feature_array)
                
                # Detect outliers
                outlier_labels = self.statistical_detector.fit_predict(scaled_features)
                if outlier_labels[-1] == -1:  # Latest sample is outlier
                    anomaly_score = self.statistical_detector.decision_function(
                        scaled_features[-1:].reshape(1, -1)
                    )[0]
                    
                    anomalies.append({
                        'type': 'statistical_anomaly',
                        'method': 'lof',
                        'confidence': abs(anomaly_score),
                        'alert_level': 'medium',
                        'description': f"Statistical motion anomaly detected (LOF score: {anomaly_score:.3f})",
                        'anomaly_score': anomaly_score
                    })
            except Exception as e:
                print(f"Statistical anomaly detection error: {e}")
        
        return anomalies
    
    def _extract_motion_features(self, objects: List[Dict[str, Any]]) -> Optional[np.ndarray]:
        """Extract motion features from detected objects"""
        if not objects:
            return None
        
        features = []
        
        for obj in objects:
            bbox = obj.get('bbox', [0, 0, 0, 0])
            confidence = obj.get('confidence', 0.0)
            obj_class = obj.get('class', 'unknown')
            
            # Basic features
            x, y, w, h = bbox
            center_x = x + w / 2
            center_y = y + h / 2
            area = w * h
            aspect_ratio = w / h if h > 0 else 0
            
            features.extend([
                center_x / 640,  # Normalized coordinates
                center_y / 480,
                area / (640 * 480),  # Normalized area
                aspect_ratio,
                confidence
            ])
        
        # Pad or truncate to fixed size
        target_size = 25  # 5 objects * 5 features each
        while len(features) < target_size:
            features.append(0.0)
        features = features[:target_size]
        
        return np.array(features, dtype=np.float32)
    
    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Get summary of anomaly detection status"""
        return {
            'conv_lstm_available': self.conv_lstm is not None,
            'autoencoder_available': self.motion_autoencoder is not None,
            'statistical_available': self.statistical_detector is not None,
            'motion_history_length': len(self.motion_history),
            'feature_history_length': len(self.feature_history),
            'ready_for_detection': len(self.motion_history) >= self.sequence_length // 2
        }
    


def test_behavior_analyzer():
    """Test the behavior analyzer"""
    print("🧪 Testing Behavior Analyzer...")
    
    config = {
        'loitering_time_threshold': 5.0,
        'intrusion_sensitivity': 0.8,
        'crowd_density_threshold': 3,
        'aggression_detection': True,
        'pose_analysis': True
    }
    
    analyzer = BehaviorAnalyzer(config)
    
    # Add test virtual line
    analyzer.add_virtual_line('test_line', (100, 200), (400, 200), 'high', 'entrance')
    
    # Test with webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera for testing")
        return
    
    print("📹 Behavior analysis test running... Press 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Simulate some objects and faces for testing
        test_objects = [
            {
                'class': 'person',
                'bbox': [100, 100, 80, 160],
                'confidence': 0.9
            }
        ]
        
        test_faces = [
            {
                'bbox': [110, 110, 60, 60],
                'confidence': 0.8,
                'is_known': False,
                'identity': 'unknown'
            }
        ]
        
        # Analyze behaviors
        behaviors = analyzer.analyze_frame(frame, test_objects, test_faces)
        
        # Display results
        result_frame = frame.copy()
        
        # Draw virtual lines
        for line in analyzer.virtual_lines:
            cv2.line(result_frame, line['start'], line['end'], (0, 255, 255), 2)
            cv2.putText(result_frame, line['name'], line['start'], 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # Display behaviors
        y_offset = 30
        for behavior in behaviors:
            text = f"{behavior['type']}: {behavior['description']}"
            cv2.putText(result_frame, text, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_offset += 25
        
        # Display tracked objects count
        cv2.putText(result_frame, f"Tracked objects: {len(analyzer.tracked_objects)}", 
                   (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow('Behavior Analysis Test', result_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Behavior analyzer test completed")


if __name__ == "__main__":
    test_behavior_analyzer()
