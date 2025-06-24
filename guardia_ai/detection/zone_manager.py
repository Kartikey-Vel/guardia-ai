#!/usr/bin/env python3
"""
Guardia AI - Zone Management & ROI Detection Module
Developed by Tackle Studioz

Implements sophisticated zone-based detection including:
- Region of Interest (ROI) definition
- Intrusion detection zones
- Restricted area monitoring
- Custom zone shapes (polygons, circles, lines)
- Zone-specific sensitivity settings
- Multi-zone violation tracking
"""

import cv2
import numpy as np
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum

class ZoneType(Enum):
    """Types of detection zones"""
    INTRUSION = "intrusion_detection"
    RESTRICTED = "restricted_area"
    COUNTING = "counting_zone"
    TRIPWIRE = "tripwire_line"
    LOITERING = "loitering_detection"
    CROWD = "crowd_monitoring"
    PARKING = "parking_zone"
    CUSTOM = "custom_zone"

class ZoneShape(Enum):
    """Zone shapes"""
    POLYGON = "polygon"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    LINE = "line"

@dataclass
class Zone:
    """Represents a detection zone with properties"""
    zone_id: str
    name: str
    zone_type: ZoneType
    shape: ZoneShape
    points: List[Tuple[int, int]]
    sensitivity: float = 0.8
    enabled: bool = True
    
    # Zone-specific settings
    alert_level: str = "medium"
    cooldown_seconds: float = 5.0
    min_object_size: int = 20
    max_object_size: int = 500
    
    # Counting and tracking
    object_count: int = 0
    entry_count: int = 0
    exit_count: int = 0
    
    # Violation tracking
    current_violations: List[str] = field(default_factory=list)
    violation_history: List[Dict[str, Any]] = field(default_factory=list)
    last_violation_time: Optional[datetime] = None
    
    # Visual properties
    color: Tuple[int, int, int] = (0, 255, 255)  # Yellow
    thickness: int = 2
    fill_alpha: float = 0.2

@dataclass
class ZoneViolation:
    """Represents a zone violation event"""
    violation_id: str
    zone_id: str
    zone_name: str
    object_id: str
    object_type: str
    timestamp: datetime
    violation_type: str
    confidence: float
    object_bbox: List[int]
    object_center: Tuple[int, int]
    metadata: Dict[str, Any] = field(default_factory=dict)

class ZoneManager:
    """
    Advanced zone management system for ROI-based detection
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.zones: Dict[str, Zone] = {}
        self.zone_masks: Dict[str, np.ndarray] = {}
        self.frame_dimensions: Optional[Tuple[int, int]] = None
        
        # Violation tracking
        self.active_violations: Dict[str, ZoneViolation] = {}
        self.violation_cooldowns: Dict[str, float] = {}
        
        # Load zones from config
        self._load_zones_from_config()
        
        print("🎯 Zone Manager initialized")
    
    def _load_zones_from_config(self):
        """Load zones from configuration"""
        default_zones = self.config.get('default_zones', [])
        
        for zone_config in default_zones:
            try:
                zone = Zone(
                    zone_id=zone_config.get('id', f"zone_{len(self.zones)}"),
                    name=zone_config.get('name', 'Unnamed Zone'),
                    zone_type=ZoneType(zone_config.get('type', 'intrusion_detection')),
                    shape=ZoneShape(zone_config.get('shape', 'polygon')),
                    points=zone_config.get('points', []),
                    sensitivity=zone_config.get('sensitivity', 0.8),
                    enabled=zone_config.get('enabled', True),
                    alert_level=zone_config.get('alert_level', 'medium'),
                    color=tuple(zone_config.get('color', [0, 255, 255])),
                    thickness=zone_config.get('thickness', 2)
                )
                self.zones[zone.zone_id] = zone
                
            except Exception as e:
                print(f"Error loading zone {zone_config.get('name', 'unknown')}: {e}")
    
    def add_zone(self, zone_config: Dict[str, Any]) -> str:
        """Add a new detection zone"""
        zone_id = zone_config.get('id', f"zone_{int(time.time())}")
        
        zone = Zone(
            zone_id=zone_id,
            name=zone_config.get('name', 'New Zone'),
            zone_type=ZoneType(zone_config.get('type', 'intrusion_detection')),
            shape=ZoneShape(zone_config.get('shape', 'polygon')),
            points=zone_config.get('points', []),
            sensitivity=zone_config.get('sensitivity', 0.8),
            enabled=zone_config.get('enabled', True),
            alert_level=zone_config.get('alert_level', 'medium'),
            color=tuple(zone_config.get('color', [0, 255, 255])),
            thickness=zone_config.get('thickness', 2)
        )
        
        self.zones[zone_id] = zone
        
        # Generate mask if frame dimensions are known
        if self.frame_dimensions:
            self._generate_zone_mask(zone)
        
        print(f"✅ Zone '{zone.name}' added with ID: {zone_id}")
        return zone_id
    
    def remove_zone(self, zone_id: str) -> bool:
        """Remove a detection zone"""
        if zone_id in self.zones:
            del self.zones[zone_id]
            if zone_id in self.zone_masks:
                del self.zone_masks[zone_id]
            print(f"🗑️ Zone {zone_id} removed")
            return True
        return False
    
    def update_zone(self, zone_id: str, updates: Dict[str, Any]) -> bool:
        """Update zone properties"""
        if zone_id not in self.zones:
            return False
        
        zone = self.zones[zone_id]
        
        # Update properties
        for key, value in updates.items():
            if hasattr(zone, key):
                if key == 'zone_type':
                    zone.zone_type = ZoneType(value)
                elif key == 'shape':
                    zone.shape = ZoneShape(value)
                else:
                    setattr(zone, key, value)
        
        # Regenerate mask if points changed
        if 'points' in updates and self.frame_dimensions:
            self._generate_zone_mask(zone)
        
        return True
    
    def set_frame_dimensions(self, width: int, height: int):
        """Set frame dimensions and generate masks"""
        self.frame_dimensions = (width, height)
        
        # Generate masks for all zones
        for zone in self.zones.values():
            self._generate_zone_mask(zone)
    
    def _generate_zone_mask(self, zone: Zone):
        """Generate binary mask for a zone"""
        if not self.frame_dimensions:
            return
        
        width, height = self.frame_dimensions
        mask = np.zeros((height, width), dtype=np.uint8)
        
        if zone.shape == ZoneShape.POLYGON:
            if len(zone.points) >= 3:
                points = np.array(zone.points, dtype=np.int32)
                cv2.fillPoly(mask, [points], 255)
        
        elif zone.shape == ZoneShape.RECTANGLE:
            if len(zone.points) >= 2:
                p1, p2 = zone.points[0], zone.points[1]
                cv2.rectangle(mask, p1, p2, 255, -1)
        
        elif zone.shape == ZoneShape.CIRCLE:
            if len(zone.points) >= 1:
                center = zone.points[0]
                radius = zone.points[1][0] if len(zone.points) > 1 else 50
                cv2.circle(mask, center, radius, 255, -1)
        
        elif zone.shape == ZoneShape.LINE:
            if len(zone.points) >= 2:
                # For line zones, create a thick line
                p1, p2 = zone.points[0], zone.points[1]
                thickness = max(10, zone.thickness * 5)
                cv2.line(mask, p1, p2, 255, thickness)
        
        self.zone_masks[zone.zone_id] = mask
    
    def check_violations(self, detections: List[Dict[str, Any]]) -> List[str]:
        """Check for zone violations with current detections"""
        violations = []
        current_time = datetime.now()
        
        # Update frame dimensions if first detection
        if detections and not self.frame_dimensions:
            # Estimate frame dimensions from detection bounding boxes
            max_x = max_y = 0
            for detection in detections:
                bbox = detection.get('bbox', [0, 0, 0, 0])
                max_x = max(max_x, bbox[0] + bbox[2])
                max_y = max(max_y, bbox[1] + bbox[3])
            if max_x > 0 and max_y > 0:
                self.set_frame_dimensions(max_x + 100, max_y + 100)
        
        for zone_id, zone in self.zones.items():
            if not zone.enabled:
                continue
            
            # Check cooldown
            if zone_id in self.violation_cooldowns:
                if time.time() - self.violation_cooldowns[zone_id] < zone.cooldown_seconds:
                    continue
            
            zone_violations = self._check_zone_violations(zone, detections, current_time)
            violations.extend(zone_violations)
            
            if zone_violations:
                self.violation_cooldowns[zone_id] = time.time()
        
        return violations
    
    def _check_zone_violations(self, zone: Zone, detections: List[Dict[str, Any]], 
                              current_time: datetime) -> List[str]:
        """Check violations for a specific zone"""
        violations = []
        
        # Get zone mask
        mask = self.zone_masks.get(zone.zone_id)
        if mask is None:
            return violations
        
        zone.current_violations.clear()
        
        for detection in detections:
            bbox = detection.get('bbox', [0, 0, 0, 0])
            object_type = detection.get('class', 'unknown')
            confidence = detection.get('confidence', 0.0)
            
            # Skip if confidence is too low
            if confidence < zone.sensitivity:
                continue
            
            # Check object size constraints
            object_area = bbox[2] * bbox[3]
            if (object_area < zone.min_object_size or 
                object_area > zone.max_object_size):
                continue
            
            # Check if object intersects with zone
            intersection_ratio = self._calculate_intersection(bbox, mask)
            
            if intersection_ratio > 0.1:  # 10% overlap threshold
                violation_detected = self._process_zone_violation(
                    zone, detection, intersection_ratio, current_time
                )
                
                if violation_detected:
                    violations.append(zone.name)
                    zone.current_violations.append(detection.get('id', 'unknown'))
        
        return violations
    
    def _calculate_intersection(self, bbox: List[int], mask: np.ndarray) -> float:
        """Calculate intersection ratio between bounding box and zone mask"""
        if len(bbox) < 4:
            return 0.0
        
        try:
            x, y, w, h = [int(val) for val in bbox[:4]]
        except (ValueError, TypeError):
            return 0.0
        
        # Validate bbox coordinates
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            return 0.0
        
        # Ensure coordinates are within mask bounds
        x = max(0, min(x, mask.shape[1] - 1))
        y = max(0, min(y, mask.shape[0] - 1))
        x2 = max(0, min(x + w, mask.shape[1]))
        y2 = max(0, min(y + h, mask.shape[0]))
        
        if x2 <= x or y2 <= y:
            return 0.0
        
        # Extract region of interest
        roi_mask = mask[y:y2, x:x2]
        
        # Calculate intersection
        intersection_pixels = np.sum(roi_mask > 0)
        total_pixels = roi_mask.size
        
        return intersection_pixels / total_pixels if total_pixels > 0 else 0.0
    
    def _process_zone_violation(self, zone: Zone, detection: Dict[str, Any], 
                               intersection_ratio: float, current_time: datetime) -> bool:
        """Process a zone violation and determine if it should trigger an alert"""
        object_id = detection.get('id', f"obj_{int(time.time())}")
        object_type = detection.get('class', 'unknown')
        bbox = detection.get('bbox', [0, 0, 0, 0])
        
        # Create violation record
        violation = ZoneViolation(
            violation_id=f"{zone.zone_id}_{object_id}_{int(time.time())}",
            zone_id=zone.zone_id,
            zone_name=zone.name,
            object_id=object_id,
            object_type=object_type,
            timestamp=current_time,
            violation_type=zone.zone_type.value,
            confidence=detection.get('confidence', 0.0) * intersection_ratio,
            object_bbox=bbox,
            object_center=self._get_bbox_center(bbox),
            metadata={
                'intersection_ratio': intersection_ratio,
                'zone_sensitivity': zone.sensitivity,
                'alert_level': zone.alert_level
            }
        )
        
        # Zone-specific processing
        should_alert = False
        
        if zone.zone_type == ZoneType.INTRUSION:
            # Intrusion detection - always alert
            should_alert = True
            zone.entry_count += 1
        
        elif zone.zone_type == ZoneType.RESTRICTED:
            # Restricted area - alert based on object type
            restricted_objects = ['person', 'vehicle', 'car', 'truck', 'motorcycle']
            should_alert = object_type in restricted_objects
        
        elif zone.zone_type == ZoneType.COUNTING:
            # Counting zone - update counts
            zone.object_count += 1
            should_alert = False  # Don't alert for counting zones
        
        elif zone.zone_type == ZoneType.TRIPWIRE:
            # Tripwire - check for line crossing
            should_alert = self._check_tripwire_crossing(zone, violation)
        
        elif zone.zone_type == ZoneType.LOITERING:
            # Loitering detection - check duration
            should_alert = self._check_loitering_violation(zone, violation)
        
        elif zone.zone_type == ZoneType.CROWD:
            # Crowd monitoring - check density
            should_alert = self._check_crowd_density(zone)
        
        elif zone.zone_type == ZoneType.PARKING:
            # Parking zone - check for unauthorized vehicles
            vehicle_types = ['car', 'truck', 'motorcycle', 'bus']
            should_alert = object_type in vehicle_types
        
        else:  # CUSTOM or unknown
            should_alert = True
        
        # Add to violation history
        zone.violation_history.append(violation.__dict__)
        if len(zone.violation_history) > 100:  # Keep last 100 violations
            zone.violation_history.pop(0)
        
        zone.last_violation_time = current_time
        
        return should_alert
    
    def _get_bbox_center(self, bbox: List[int]) -> Tuple[int, int]:
        """Get center point of bounding box"""
        x, y, w, h = bbox
        return (x + w // 2, y + h // 2)
    
    def _check_tripwire_crossing(self, zone: Zone, violation: ZoneViolation) -> bool:
        """Check if object crossed tripwire line"""
        # This would need object tracking history to determine crossing
        # For now, return True if object is detected on line
        return True
    
    def _check_loitering_violation(self, zone: Zone, violation: ZoneViolation) -> bool:
        """Check if loitering duration threshold is exceeded"""
        # Count recent violations from same object
        recent_violations = [
            v for v in zone.violation_history[-10:]  # Last 10 violations
            if v['object_id'] == violation.object_id
        ]
        
        # If same object detected multiple times recently, it's loitering
        return len(recent_violations) >= 3
    
    def _check_crowd_density(self, zone: Zone) -> bool:
        """Check if crowd density exceeds threshold"""
        # Count current objects in zone
        current_object_count = len(zone.current_violations)
        return current_object_count >= 3  # Threshold for crowd
    
    def draw_zones(self, frame: np.ndarray, show_violations: bool = True) -> np.ndarray:
        """Draw all zones on the frame"""
        result_frame = frame.copy()
        
        for zone in self.zones.values():
            if not zone.enabled:
                continue
            
            # Choose color based on violations
            color = zone.color
            if show_violations and zone.current_violations:
                color = (0, 0, 255)  # Red for violations
            
            # Draw zone based on shape
            if zone.shape == ZoneShape.POLYGON and len(zone.points) >= 3:
                points = np.array(zone.points, dtype=np.int32)
                
                # Draw filled polygon with transparency
                overlay = result_frame.copy()
                cv2.fillPoly(overlay, [points], color)
                cv2.addWeighted(result_frame, 1 - zone.fill_alpha, overlay, zone.fill_alpha, 0, result_frame)
                
                # Draw outline
                cv2.polylines(result_frame, [points], True, color, zone.thickness)
            
            elif zone.shape == ZoneShape.RECTANGLE and len(zone.points) >= 2:
                p1, p2 = zone.points[0], zone.points[1]
                
                # Draw filled rectangle with transparency
                overlay = result_frame.copy()
                cv2.rectangle(overlay, p1, p2, color, -1)
                cv2.addWeighted(result_frame, 1 - zone.fill_alpha, overlay, zone.fill_alpha, 0, result_frame)
                
                # Draw outline
                cv2.rectangle(result_frame, p1, p2, color, zone.thickness)
            
            elif zone.shape == ZoneShape.CIRCLE and len(zone.points) >= 1:
                center = zone.points[0]
                radius = zone.points[1][0] if len(zone.points) > 1 else 50
                
                # Draw filled circle with transparency
                overlay = result_frame.copy()
                cv2.circle(overlay, center, radius, color, -1)
                cv2.addWeighted(result_frame, 1 - zone.fill_alpha, overlay, zone.fill_alpha, 0, result_frame)
                
                # Draw outline
                cv2.circle(result_frame, center, radius, color, zone.thickness)
            
            elif zone.shape == ZoneShape.LINE and len(zone.points) >= 2:
                p1, p2 = zone.points[0], zone.points[1]
                cv2.line(result_frame, p1, p2, color, zone.thickness)
            
            # Draw zone label
            if zone.points:
                label_pos = zone.points[0]
                cv2.putText(result_frame, zone.name, 
                           (label_pos[0], label_pos[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                # Show violation count if any
                if show_violations and zone.current_violations:
                    violation_text = f"VIOLATION: {len(zone.current_violations)} objects"
                    cv2.putText(result_frame, violation_text,
                               (label_pos[0], label_pos[1] + 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        return result_frame
    
    def get_zone_statistics(self) -> Dict[str, Any]:
        """Get statistics for all zones"""
        stats = {
            'total_zones': len(self.zones),
            'enabled_zones': len([z for z in self.zones.values() if z.enabled]),
            'zones': {}
        }
        
        for zone_id, zone in self.zones.items():
            stats['zones'][zone_id] = {
                'name': zone.name,
                'type': zone.zone_type.value,
                'enabled': zone.enabled,
                'current_violations': len(zone.current_violations),
                'entry_count': zone.entry_count,
                'exit_count': zone.exit_count,
                'object_count': zone.object_count,
                'last_violation': zone.last_violation_time.isoformat() if zone.last_violation_time else None,
                'total_violations': len(zone.violation_history)
            }
        
        return stats
    
    def export_zones_config(self) -> Dict[str, Any]:
        """Export zones configuration"""
        config = {
            'zones': [],
            'exported_at': datetime.now().isoformat()
        }
        
        for zone in self.zones.values():
            zone_config = {
                'id': zone.zone_id,
                'name': zone.name,
                'type': zone.zone_type.value,
                'shape': zone.shape.value,
                'points': zone.points,
                'sensitivity': zone.sensitivity,
                'enabled': zone.enabled,
                'alert_level': zone.alert_level,
                'color': list(zone.color),
                'thickness': zone.thickness,
                'min_object_size': zone.min_object_size,
                'max_object_size': zone.max_object_size,
                'cooldown_seconds': zone.cooldown_seconds
            }
            config['zones'].append(zone_config)
        
        return config
    
    def import_zones_config(self, config: Dict[str, Any]) -> bool:
        """Import zones configuration"""
        try:
            self.zones.clear()
            self.zone_masks.clear()
            
            for zone_config in config.get('zones', []):
                zone = Zone(
                    zone_id=zone_config['id'],
                    name=zone_config['name'],
                    zone_type=ZoneType(zone_config['type']),
                    shape=ZoneShape(zone_config['shape']),
                    points=zone_config['points'],
                    sensitivity=zone_config.get('sensitivity', 0.8),
                    enabled=zone_config.get('enabled', True),
                    alert_level=zone_config.get('alert_level', 'medium'),
                    color=tuple(zone_config.get('color', [0, 255, 255])),
                    thickness=zone_config.get('thickness', 2),
                    min_object_size=zone_config.get('min_object_size', 20),
                    max_object_size=zone_config.get('max_object_size', 500),
                    cooldown_seconds=zone_config.get('cooldown_seconds', 5.0)
                )
                self.zones[zone.zone_id] = zone
            
            # Regenerate masks if frame dimensions are known
            if self.frame_dimensions:
                for zone in self.zones.values():
                    self._generate_zone_mask(zone)
            
            print(f"✅ Imported {len(self.zones)} zones")
            return True
            
        except Exception as e:
            print(f"❌ Error importing zones config: {e}")
            return False
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update zone manager configuration"""
        self.config.update(new_config)
        
        # Reload zones if needed
        if 'default_zones' in new_config:
            self._load_zones_from_config()


class ZoneEditor:
    """Interactive zone editor for creating and modifying detection zones"""
    
    def __init__(self, zone_manager: ZoneManager):
        self.zone_manager = zone_manager
        self.current_points = []
        self.editing_zone_id = None
        self.current_shape = ZoneShape.POLYGON
        self.mouse_callback_active = False
    
    def start_zone_creation(self, shape: ZoneShape = ZoneShape.POLYGON):
        """Start creating a new zone"""
        self.current_points = []
        self.editing_zone_id = None
        self.current_shape = shape
        print(f"🎨 Starting zone creation ({shape.value})")
        print("Click to add points, press 'c' to complete, 'r' to reset")
    
    def start_zone_editing(self, zone_id: str):
        """Start editing an existing zone"""
        if zone_id not in self.zone_manager.zones:
            print(f"❌ Zone {zone_id} not found")
            return False
        
        zone = self.zone_manager.zones[zone_id]
        self.editing_zone_id = zone_id
        self.current_points = zone.points.copy()
        self.current_shape = zone.shape
        print(f"✏️ Editing zone '{zone.name}'")
        return True
    
    def mouse_callback(self, event, x, y, flags, param):
        """Handle mouse events for zone editing"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.current_points.append((x, y))
            print(f"Added point: ({x}, {y})")
        
        elif event == cv2.EVENT_RBUTTONDOWN:
            # Remove last point
            if self.current_points:
                removed = self.current_points.pop()
                print(f"Removed point: {removed}")
    
    def complete_zone(self, name: str, zone_type: ZoneType = ZoneType.INTRUSION) -> Optional[str]:
        """Complete zone creation/editing"""
        if len(self.current_points) < 2:
            print("❌ Need at least 2 points for a zone")
            return None
        
        zone_config = {
            'name': name,
            'type': zone_type.value,
            'shape': self.current_shape.value,
            'points': self.current_points,
            'sensitivity': 0.8,
            'enabled': True,
            'alert_level': 'medium'
        }
        
        if self.editing_zone_id:
            # Update existing zone
            self.zone_manager.update_zone(self.editing_zone_id, zone_config)
            print(f"✅ Zone '{name}' updated")
            return self.editing_zone_id
        else:
            # Create new zone
            zone_id = self.zone_manager.add_zone(zone_config)
            print(f"✅ Zone '{name}' created with ID: {zone_id}")
            return zone_id
    
    def reset_current_zone(self):
        """Reset current zone being edited"""
        self.current_points = []
        print("🔄 Zone reset")
    
    def draw_current_zone(self, frame: np.ndarray) -> np.ndarray:
        """Draw the zone currently being created/edited"""
        result_frame = frame.copy()
        
        if not self.current_points:
            return result_frame
        
        color = (0, 255, 0)  # Green for current zone
        
        # Draw points
        for point in self.current_points:
            cv2.circle(result_frame, point, 5, color, -1)
        
        # Draw lines between points
        if len(self.current_points) > 1:
            if self.current_shape == ZoneShape.POLYGON:
                for i in range(len(self.current_points) - 1):
                    cv2.line(result_frame, self.current_points[i], 
                            self.current_points[i + 1], color, 2)
                
                # Close polygon if more than 2 points
                if len(self.current_points) > 2:
                    cv2.line(result_frame, self.current_points[-1], 
                            self.current_points[0], (255, 255, 0), 1)
            
            elif self.current_shape == ZoneShape.RECTANGLE:
                if len(self.current_points) >= 2:
                    cv2.rectangle(result_frame, self.current_points[0], 
                                 self.current_points[1], color, 2)
            
            elif self.current_shape == ZoneShape.CIRCLE:
                if len(self.current_points) >= 2:
                    center = self.current_points[0]
                    radius = int(np.linalg.norm(np.array(self.current_points[1]) - np.array(center)))
                    cv2.circle(result_frame, center, radius, color, 2)
            
            elif self.current_shape == ZoneShape.LINE:
                cv2.line(result_frame, self.current_points[0], 
                        self.current_points[-1], color, 3)
        
        # Draw instructions
        cv2.putText(result_frame, f"Creating {self.current_shape.value} zone", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(result_frame, f"Points: {len(self.current_points)}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        return result_frame


def test_zone_manager():
    """Test the zone manager"""
    print("🧪 Testing Zone Manager...")
    
    # Create test configuration
    config = {
        'default_zones': [
            {
                'id': 'entrance',
                'name': 'Main Entrance',
                'type': 'intrusion_detection',
                'shape': 'polygon',
                'points': [[100, 100], [300, 100], [300, 200], [100, 200]],
                'sensitivity': 0.8,
                'alert_level': 'high'
            },
            {
                'id': 'parking',
                'name': 'Parking Area',
                'type': 'parking_zone',
                'shape': 'rectangle',
                'points': [[400, 300], [600, 450]],
                'sensitivity': 0.7,
                'alert_level': 'medium'
            }
        ]
    }
    
    zone_manager = ZoneManager(config)
    
    # Test with webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera for testing")
        return
    
    # Set frame dimensions
    ret, frame = cap.read()
    if ret:
        h, w = frame.shape[:2]
        zone_manager.set_frame_dimensions(w, h)
    
    print("📹 Zone manager test running... Press 'q' to quit, 's' for stats")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Simulate detections
        test_detections = [
            {
                'id': 'person_1',
                'class': 'person',
                'bbox': [150, 150, 50, 100],
                'confidence': 0.9
            },
            {
                'id': 'car_1',
                'class': 'car',
                'bbox': [450, 350, 100, 80],
                'confidence': 0.8
            }
        ]
        
        # Check violations
        violations = zone_manager.check_violations(test_detections)
        
        # Draw zones and detections
        result_frame = zone_manager.draw_zones(frame, show_violations=True)
        
        # Draw detections
        for detection in test_detections:
            bbox = detection['bbox']
            cv2.rectangle(result_frame, (bbox[0], bbox[1]), 
                         (bbox[0] + bbox[2], bbox[1] + bbox[3]), (255, 0, 0), 2)
            cv2.putText(result_frame, detection['class'], 
                       (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # Show violations
        if violations:
            cv2.putText(result_frame, f"VIOLATIONS: {', '.join(violations)}", 
                       (10, frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow('Zone Manager Test', result_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            stats = zone_manager.get_zone_statistics()
            print(f"📊 Zone Statistics: {stats}")
    
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Zone manager test completed")


if __name__ == "__main__":
    test_zone_manager()
