#!/usr/bin/env python3
"""
Guardia AI - DeepSORT Object Tracking Integration
Developed by Tackle Studioz

Implements advanced object tracking using DeepSORT algorithm:
- Consistent object ID assignment across frames
- Track lifecycle management
- Object trajectory analysis
- Track-based behavior detection
- Multi-object tracking optimization
"""

import cv2
import numpy as np
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
import math

# Import DeepSORT
try:
    from deep_sort_realtime import DeepSort
    DEEPSORT_AVAILABLE = True
    print("✅ DeepSORT Real-time tracker available")
except ImportError:
    DEEPSORT_AVAILABLE = False
    print("⚠️ DeepSORT Real-time tracker not available")

@dataclass
class Track:
    """Represents a tracked object with complete trajectory"""
    track_id: int
    object_class: str
    confidence: float
    
    # Position and movement
    current_bbox: List[int] = field(default_factory=list)
    current_center: Tuple[int, int] = (0, 0)
    position_history: deque = field(default_factory=lambda: deque(maxlen=100))
    bbox_history: deque = field(default_factory=lambda: deque(maxlen=30))
    
    # Temporal tracking
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    age: int = 0
    time_since_update: int = 0
    
    # Movement analysis
    velocity: Tuple[float, float] = (0.0, 0.0)
    acceleration: Tuple[float, float] = (0.0, 0.0)
    total_distance: float = 0.0
    avg_speed: float = 0.0
    max_speed: float = 0.0
    direction_angle: float = 0.0
    direction_changes: int = 0
    
    # Behavioral tracking
    is_stationary: bool = False
    stationary_time: float = 0.0
    zone_entries: List[str] = field(default_factory=list)
    zone_exits: List[str] = field(default_factory=list)
    current_zones: List[str] = field(default_factory=list)
    
    # Track state
    state: str = "tentative"  # tentative, confirmed, deleted
    hits: int = 0
    hit_streak: int = 0
    
    # Feature embedding for re-identification
    feature_embedding: Optional[np.ndarray] = None
    appearance_features: deque = field(default_factory=lambda: deque(maxlen=10))

class EnhancedTracker:
    """
    Enhanced tracking system that uses DeepSORT when available, simplified tracker as fallback
    """
    
    def __init__(self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        
        # Initialize DeepSORT if available
        if DEEPSORT_AVAILABLE:
            try:
                self.deep_sort = DeepSort(
                    max_age=max_age,
                    n_init=min_hits,
                    max_iou_distance=iou_threshold,
                    max_cosine_distance=0.4,
                    nn_budget=None,
                    override_track_class=None
                )
                self.use_deepsort = True
                print("✅ Using DeepSORT real-time tracker")
            except Exception as e:
                print(f"⚠️ DeepSORT initialization failed: {e}")
                self.use_deepsort = False
        else:
            self.use_deepsort = False
        
        # Fallback to simplified tracker
        if not self.use_deepsort:
            self.simplified_tracker = SimplifiedDeepSORT(max_age, min_hits, iou_threshold)
            print("🎯 Using simplified DeepSORT tracker")
        
        # Track analytics
        self.track_analytics = TrackingAnalyzer()
        self.trajectory_analyzer = TrajectoryAnalyzer()
    
    def update(self, detections: List[Dict[str, Any]], frame: Optional[np.ndarray] = None) -> List[Track]:
        """Update tracker with new detections"""
        if self.use_deepsort and DEEPSORT_AVAILABLE:
            return self._update_with_deepsort(detections, frame)
        else:
            return self._update_with_simplified(detections)
    
    def _update_with_deepsort(self, detections: List[Dict[str, Any]], frame: Optional[np.ndarray] = None) -> List[Track]:
        """Update using real DeepSORT tracker"""
        try:
            # Convert detections to DeepSORT format
            bbs = []
            confidences = []
            
            for detection in detections:
                bbox = detection.get('bbox', [0, 0, 0, 0])
                confidence = detection.get('confidence', 0.0)
                
                # Convert [x, y, w, h] to [x1, y1, x2, y2]
                x, y, w, h = bbox
                x1, y1, x2, y2 = x, y, x + w, y + h
                bbs.append([x1, y1, x2, y2])
                confidences.append(confidence)
            
            # Update DeepSORT
            tracks = self.deep_sort.update_tracks(bbs, confidences, frame)
            
            # Convert DeepSORT tracks to our Track format
            track_results = []
            for track in tracks:
                if not track.is_confirmed():
                    continue
                
                # Get track data
                track_id = track.track_id
                bbox = track.to_ltrb()  # [x1, y1, x2, y2]
                
                # Convert to our format [x, y, w, h]
                x1, y1, x2, y2 = bbox
                converted_bbox = [int(x1), int(y1), int(x2-x1), int(y2-y1)]
                center = (int((x1+x2)/2), int((y1+y2)/2))
                
                # Find matching detection for class info
                object_class = "unknown"
                confidence = 0.0
                for detection in detections:
                    det_bbox = detection.get('bbox', [0, 0, 0, 0])
                    if self._calculate_iou(converted_bbox, det_bbox) > 0.3:
                        object_class = detection.get('class', 'unknown')
                        confidence = detection.get('confidence', 0.0)
                        break
                
                # Create Track object
                track_obj = Track(
                    track_id=track_id,
                    object_class=object_class,
                    confidence=confidence,
                    current_bbox=converted_bbox,
                    current_center=center,
                    state="confirmed",
                    age=track.age if hasattr(track, 'age') else 1
                )
                
                track_results.append(track_obj)
            
            return track_results
            
        except Exception as e:
            print(f"⚠️ DeepSORT update error: {e}")
            # Fallback to simplified tracker
            return self._update_with_simplified(detections)
    
    def _update_with_simplified(self, detections: List[Dict[str, Any]]) -> List[Track]:
        """Update using simplified tracker"""
        return self.simplified_tracker.update(detections)
    
    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """Calculate Intersection over Union of two bounding boxes"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        left = max(x1, x2)
        top = max(y1, y2)
        right = min(x1 + w1, x2 + w2)
        bottom = min(y1 + h1, y2 + h2)
        
        if right < left or bottom < top:
            return 0.0
        
        intersection = (right - left) * (bottom - top)
        union = w1 * h1 + w2 * h2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def get_tracking_analytics(self) -> Dict[str, Any]:
        """Get tracking analytics and insights"""
        if self.use_deepsort:
            # Get basic stats from DeepSORT
            return {
                'tracker_type': 'DeepSORT',
                'active_tracks': len(getattr(self.deep_sort, 'tracks', [])),
                'tracking_confidence': 'high'
            }
        else:
            return self.track_analytics.get_loitering_detections(list(self.simplified_tracker.tracks.values()))


class SimplifiedDeepSORT:
    """
    Simplified DeepSORT implementation for object tracking
    """
    
    def __init__(self, max_age: int = 30, min_hits: int = 3, iou_threshold: float = 0.3):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.next_id = 1
        self.tracks: Dict[int, Track] = {}
        
        # Kalman filter parameters (simplified)
        self.motion_predictor = MotionPredictor()
        
        print("🎯 Simplified DeepSORT tracker initialized")
    
    def update(self, detections: List[Dict[str, Any]]) -> List[Track]:
        """Update tracker with new detections"""
        current_time = datetime.now()
        
        # Predict new locations of existing tracks
        for track in self.tracks.values():
            self._predict_track_motion(track)
        
        # Match detections to existing tracks
        matched_tracks, unmatched_detections, unmatched_tracks = self._associate_detections_to_tracks(
            detections
        )
        
        # Update matched tracks
        for track_id, detection in matched_tracks:
            self._update_track(self.tracks[track_id], detection, current_time)
        
        # Mark unmatched tracks
        for track_id in unmatched_tracks:
            track = self.tracks[track_id]
            track.time_since_update += 1
            if track.time_since_update > self.max_age:
                track.state = "deleted"
        
        # Create new tracks for unmatched detections
        for detection in unmatched_detections:
            self._create_new_track(detection, current_time)
        
        # Remove deleted tracks
        self.tracks = {tid: track for tid, track in self.tracks.items() 
                      if track.state != "deleted"}
        
        # Return confirmed tracks
        confirmed_tracks = [track for track in self.tracks.values() 
                           if track.state == "confirmed"]
        
        return confirmed_tracks
    
    def _predict_track_motion(self, track: Track):
        """Predict next position of track using motion model"""
        if len(track.position_history) >= 2:
            # Simple linear prediction based on velocity
            last_pos = track.position_history[-1]
            predicted_pos = (
                last_pos[0] + track.velocity[0],
                last_pos[1] + track.velocity[1]
            )
            
            # Update predicted bbox
            if track.current_bbox:
                w, h = track.current_bbox[2], track.current_bbox[3]
                track.current_bbox = [
                    int(predicted_pos[0] - w/2),
                    int(predicted_pos[1] - h/2),
                    w, h
                ]
                track.current_center = predicted_pos
    
    def _associate_detections_to_tracks(self, detections: List[Dict[str, Any]]) -> Tuple[List[Tuple[int, Dict]], List[Dict], List[int]]:
        """Associate detections with existing tracks using IoU"""
        if not self.tracks:
            return [], detections, []
        
        # Calculate IoU matrix
        iou_matrix = np.zeros((len(self.tracks), len(detections)))
        track_ids = list(self.tracks.keys())
        
        for i, track_id in enumerate(track_ids):
            track = self.tracks[track_id]
            for j, detection in enumerate(detections):
                det_bbox = detection.get('bbox', [0, 0, 0, 0])
                iou = self._calculate_iou(track.current_bbox, det_bbox)
                iou_matrix[i, j] = iou
        
        # Hungarian algorithm (simplified greedy approach)
        matched_tracks = []
        unmatched_detections = list(range(len(detections)))
        unmatched_tracks = list(range(len(track_ids)))
        
        # Greedy matching
        while True:
            # Find best match
            best_iou = 0
            best_track_idx = -1
            best_det_idx = -1
            
            for i in unmatched_tracks:
                for j in unmatched_detections:
                    if iou_matrix[i, j] > best_iou and iou_matrix[i, j] > self.iou_threshold:
                        best_iou = iou_matrix[i, j]
                        best_track_idx = i
                        best_det_idx = j
            
            if best_track_idx == -1:
                break
            
            # Add match
            track_id = track_ids[best_track_idx]
            detection = detections[best_det_idx]
            matched_tracks.append((track_id, detection))
            
            # Remove from unmatched
            unmatched_tracks.remove(best_track_idx)
            unmatched_detections.remove(best_det_idx)
        
        # Convert indices back to actual objects
        unmatched_detections = [detections[i] for i in unmatched_detections]
        unmatched_tracks = [track_ids[i] for i in unmatched_tracks]
        
        return matched_tracks, unmatched_detections, unmatched_tracks
    
    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        """Calculate Intersection over Union of two bounding boxes"""
        if not bbox1 or not bbox2:
            return 0.0
        
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
        
        intersection = (xi2 - xi1) * (yi2 - yi1)
        union = w1 * h1 + w2 * h2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _update_track(self, track: Track, detection: Dict[str, Any], current_time: datetime):
        """Update track with new detection"""
        bbox = detection.get('bbox', [0, 0, 0, 0])
        confidence = detection.get('confidence', 0.0)
        
        # Update basic properties
        track.current_bbox = bbox
        track.current_center = self._get_bbox_center(bbox)
        track.confidence = confidence
        track.last_seen = current_time
        track.time_since_update = 0
        track.hits += 1
        track.hit_streak += 1
        track.age += 1
        
        # Update position history
        track.position_history.append(track.current_center)
        track.bbox_history.append(bbox)
        
        # Calculate movement statistics
        self._update_movement_stats(track)
        
        # Update track state
        if track.hit_streak >= self.min_hits:
            track.state = "confirmed"
        
        # Extract appearance features (simplified)
        if 'feature' in detection:
            track.appearance_features.append(detection['feature'])
    
    def _create_new_track(self, detection: Dict[str, Any], current_time: datetime):
        """Create new track from detection"""
        bbox = detection.get('bbox', [0, 0, 0, 0])
        object_class = detection.get('class', 'unknown')
        confidence = detection.get('confidence', 0.0)
        
        track = Track(
            track_id=self.next_id,
            object_class=object_class,
            confidence=confidence,
            current_bbox=bbox,
            current_center=self._get_bbox_center(bbox),
            first_seen=current_time,
            last_seen=current_time,
            hits=1,
            hit_streak=1,
            age=1
        )
        
        track.position_history.append(track.current_center)
        track.bbox_history.append(bbox)
        
        self.tracks[self.next_id] = track
        self.next_id += 1
    
    def _get_bbox_center(self, bbox: List[int]) -> Tuple[int, int]:
        """Get center point of bounding box"""
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)
    
    def _update_movement_stats(self, track: Track):
        """Update movement statistics for track"""
        if len(track.position_history) < 2:
            return
        
        current_pos = track.position_history[-1]
        previous_pos = track.position_history[-2]
        
        # Calculate distance
        distance = math.sqrt(
            (current_pos[0] - previous_pos[0])**2 + 
            (current_pos[1] - previous_pos[1])**2
        )
        track.total_distance += distance
        
        # Calculate velocity (assume ~30 FPS)
        dt = 1.0 / 30.0  # Time delta
        velocity_x = (current_pos[0] - previous_pos[0]) / dt
        velocity_y = (current_pos[1] - previous_pos[1]) / dt
        
        prev_velocity = track.velocity
        track.velocity = (velocity_x, velocity_y)
        
        # Calculate acceleration
        track.acceleration = (
            (velocity_x - prev_velocity[0]) / dt,
            (velocity_y - prev_velocity[1]) / dt
        )
        
        # Calculate speed and direction
        speed = math.sqrt(velocity_x**2 + velocity_y**2)
        track.avg_speed = track.total_distance / len(track.position_history) if track.position_history else 0
        track.max_speed = max(track.max_speed, speed)
        
        # Calculate direction angle
        if velocity_x != 0 or velocity_y != 0:
            new_angle = math.atan2(velocity_y, velocity_x)
            if abs(new_angle - track.direction_angle) > math.pi / 4:  # 45 degree change
                track.direction_changes += 1
            track.direction_angle = new_angle
        
        # Check if stationary
        if speed < 5.0:  # pixels per second
            track.stationary_time += dt
            track.is_stationary = track.stationary_time > 2.0  # 2 seconds
        else:
            track.stationary_time = 0.0
            track.is_stationary = False
    
    def get_track_by_id(self, track_id: int) -> Optional[Track]:
        """Get track by ID"""
        return self.tracks.get(track_id)
    
    def get_all_tracks(self) -> List[Track]:
        """Get all active tracks"""
        return list(self.tracks.values())
    
    def get_confirmed_tracks(self) -> List[Track]:
        """Get only confirmed tracks"""
        return [track for track in self.tracks.values() if track.state == "confirmed"]


class MotionPredictor:
    """Simple motion prediction using Kalman filter concepts"""
    
    def __init__(self):
        self.state_transition = np.array([
            [1, 0, 1, 0],  # x' = x + vx
            [0, 1, 0, 1],  # y' = y + vy
            [0, 0, 1, 0],  # vx' = vx
            [0, 0, 0, 1]   # vy' = vy
        ])
        
        self.process_noise = 0.1
        self.measurement_noise = 1.0
    
    def predict(self, state: np.ndarray) -> np.ndarray:
        """Predict next state"""
        return self.state_transition @ state
    
    def update(self, predicted_state: np.ndarray, measurement: np.ndarray) -> np.ndarray:
        """Update state with measurement"""
        # Simplified Kalman update
        innovation = measurement - predicted_state[:2]
        updated_state = predicted_state.copy()
        updated_state[:2] += 0.5 * innovation  # Simple gain
        return updated_state


class TrackingAnalyzer:
    """Analyzes tracking data for behavioral insights"""
    
    def __init__(self):
        self.track_history: Dict[int, List[Track]] = defaultdict(list)
        self.trajectory_analyzer = TrajectoryAnalyzer()
    
    def analyze_tracks(self, tracks: List[Track]) -> List[Dict[str, Any]]:
        """Analyze tracks for behavioral patterns"""
        behaviors = []
        
        for track in tracks:
            # Store track history
            self.track_history[track.track_id].append(track)
            
            # Analyze trajectory
            trajectory_behavior = self.trajectory_analyzer.analyze_trajectory(track)
            if trajectory_behavior:
                behaviors.extend(trajectory_behavior)
            
            # Check for loitering
            if track.is_stationary and track.stationary_time > 10.0:
                behaviors.append({
                    'type': 'loitering_tracked',
                    'track_id': track.track_id,
                    'object_class': track.object_class,
                    'confidence': 0.9,
                    'duration': track.stationary_time,
                    'position': track.current_center,
                    'alert_level': 'medium'
                })
            
            # Check for erratic movement
            if (track.direction_changes > 5 and 
                track.max_speed > 50 and 
                len(track.position_history) > 20):
                behaviors.append({
                    'type': 'erratic_movement',
                    'track_id': track.track_id,
                    'object_class': track.object_class,
                    'confidence': 0.8,
                    'direction_changes': track.direction_changes,
                    'max_speed': track.max_speed,
                    'alert_level': 'high'
                })
            
            # Check for high-speed movement
            if track.max_speed > 100:  # pixels per second
                behaviors.append({
                    'type': 'high_speed_movement',
                    'track_id': track.track_id,
                    'object_class': track.object_class,
                    'confidence': 0.7,
                    'speed': track.max_speed,
                    'alert_level': 'medium'
                })
        
        return behaviors
    
    def get_track_statistics(self) -> Dict[str, Any]:
        """Get tracking statistics"""
        total_tracks = len(self.track_history)
        
        if total_tracks == 0:
            return {'total_tracks': 0}
        
        # Calculate average track duration
        durations = []
        for track_list in self.track_history.values():
            if track_list:
                duration = (track_list[-1].last_seen - track_list[0].first_seen).total_seconds()
                durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_tracks': total_tracks,
            'average_duration': avg_duration,
            'active_tracks': len([t for t in self.track_history.values() if t]),
            'longest_track': max(durations) if durations else 0
        }


class TrajectoryAnalyzer:
    """Analyzes object trajectories for pattern detection"""
    
    def __init__(self):
        self.pattern_templates = self._load_pattern_templates()
    
    def _load_pattern_templates(self) -> Dict[str, Any]:
        """Load pre-defined trajectory patterns"""
        return {
            'circular': {'min_points': 20, 'circularity_threshold': 0.8},
            'zigzag': {'min_direction_changes': 5, 'regularity_threshold': 0.6},
            'linear': {'direction_variance_threshold': 0.2},
            'random': {'entropy_threshold': 0.8}
        }
    
    def analyze_trajectory(self, track: Track) -> List[Dict[str, Any]]:
        """Analyze trajectory pattern of a track"""
        behaviors = []
        
        if len(track.position_history) < 10:
            return behaviors
        
        positions = list(track.position_history)
        
        # Check for circular motion
        circularity = self._calculate_circularity(positions)
        if circularity > 0.7:
            behaviors.append({
                'type': 'circular_motion',
                'track_id': track.track_id,
                'confidence': circularity,
                'description': 'Object moving in circular pattern',
                'alert_level': 'low'
            })
        
        # Check for back-and-forth motion
        if self._detect_oscillation(positions):
            behaviors.append({
                'type': 'oscillating_motion',
                'track_id': track.track_id,
                'confidence': 0.8,
                'description': 'Object moving back and forth',
                'alert_level': 'medium'
            })
        
        # Check for sudden stops
        if self._detect_sudden_stop(track):
            behaviors.append({
                'type': 'sudden_stop',
                'track_id': track.track_id,
                'confidence': 0.9,
                'description': 'Object stopped suddenly',
                'alert_level': 'medium'
            })
        
        return behaviors
    
    def _calculate_circularity(self, positions: List[Tuple[int, int]]) -> float:
        """Calculate how circular a trajectory is"""
        if len(positions) < 4:
            return 0.0
        
        # Calculate center of mass
        center_x = sum(p[0] for p in positions) / len(positions)
        center_y = sum(p[1] for p in positions) / len(positions)
        center = (center_x, center_y)
        
        # Calculate distances from center
        distances = [
            math.sqrt((p[0] - center[0])**2 + (p[1] - center[1])**2)
            for p in positions
        ]
        
        # Calculate variance in distances (low variance = more circular)
        mean_distance = sum(distances) / len(distances)
        variance = sum((d - mean_distance)**2 for d in distances) / len(distances)
        
        # Normalize to 0-1 scale (lower variance = higher circularity)
        circularity = 1.0 / (1.0 + variance / (mean_distance + 1))
        
        return circularity
    
    def _detect_oscillation(self, positions: List[Tuple[int, int]]) -> bool:
        """Detect back-and-forth oscillating motion"""
        if len(positions) < 6:
            return False
        
        # Calculate direction changes
        direction_changes = 0
        prev_direction = None
        
        for i in range(1, len(positions)):
            current_dir = (
                positions[i][0] - positions[i-1][0],
                positions[i][1] - positions[i-1][1]
            )
            
            if prev_direction is not None:
                # Check if direction changed significantly
                dot_product = (current_dir[0] * prev_direction[0] + 
                              current_dir[1] * prev_direction[1])
                if dot_product < 0:  # Opposite directions
                    direction_changes += 1
            
            prev_direction = current_dir
        
        # Oscillation if many direction changes relative to path length
        oscillation_ratio = direction_changes / len(positions)
        return oscillation_ratio > 0.3
    
    def _detect_sudden_stop(self, track: Track) -> bool:
        """Detect sudden stopping behavior"""
        if len(track.position_history) < 5:
            return False
        
        # Check if object was moving fast and then stopped
        recent_speeds = []
        positions = list(track.position_history)
        
        for i in range(len(positions) - 4, len(positions) - 1):
            if i < 1:
                continue
            
            distance = math.sqrt(
                (positions[i][0] - positions[i-1][0])**2 + 
                (positions[i][1] - positions[i-1][1])**2
            )
            recent_speeds.append(distance)
        
        if not recent_speeds:
            return False
        
        # Check if there was high speed followed by low speed
        early_speed = sum(recent_speeds[:2]) / 2 if len(recent_speeds) >= 2 else 0
        late_speed = sum(recent_speeds[-2:]) / 2 if len(recent_speeds) >= 2 else 0
        
        return early_speed > 20 and late_speed < 5  # Significant speed drop


def test_tracking_system():
    """Test the tracking system"""
    print("🧪 Testing DeepSORT Tracking System...")
    
    tracker = SimplifiedDeepSORT()
    analyzer = TrackingAnalyzer()
    
    # Test with webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera for testing")
        return
    
    print("📹 Tracking test running... Press 'q' to quit, 's' for stats")
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Simulate detections (in real use, this would come from YOLO)
        simulated_detections = []
        
        # Add some moving objects for testing
        if frame_count % 30 < 15:  # Moving object
            x = 100 + (frame_count % 30) * 10
            y = 200
            simulated_detections.append({
                'bbox': [x, y, 50, 80],
                'class': 'person',
                'confidence': 0.9
            })
        
        # Update tracker
        tracks = tracker.update(simulated_detections)
        
        # Analyze behaviors
        behaviors = analyzer.analyze_tracks(tracks)
        
        # Draw results
        result_frame = frame.copy()
        
        # Draw tracks
        for track in tracks:
            if track.state == "confirmed":
                bbox = track.current_bbox
                color = (0, 255, 0) if not track.is_stationary else (0, 255, 255)
                
                # Draw bounding box
                cv2.rectangle(result_frame, (bbox[0], bbox[1]), 
                             (bbox[0] + bbox[2], bbox[1] + bbox[3]), color, 2)
                
                # Draw track ID and info
                label = f"ID:{track.track_id} {track.object_class} Age:{track.age}"
                cv2.putText(result_frame, label, (bbox[0], bbox[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # Draw trajectory
                if len(track.position_history) > 1:
                    points = list(track.position_history)
                    for i in range(1, len(points)):
                        cv2.line(result_frame, points[i-1], points[i], color, 1)
                
                # Show speed
                speed_text = f"Speed: {track.avg_speed:.1f}"
                cv2.putText(result_frame, speed_text, (bbox[0], bbox[1] + bbox[3] + 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Display behaviors
        y_offset = 30
        for behavior in behaviors:
            text = f"Track {behavior.get('track_id', 'N/A')}: {behavior['type']}"
            cv2.putText(result_frame, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            y_offset += 25
        
        # Show statistics
        cv2.putText(result_frame, f"Active tracks: {len(tracks)}", 
                   (10, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(result_frame, f"Frame: {frame_count}", 
                   (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow('DeepSORT Tracking Test', result_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            stats = analyzer.get_track_statistics()
            print(f"📊 Tracking Statistics: {stats}")
    
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Tracking system test completed")


if __name__ == "__main__":
    test_tracking_system()
