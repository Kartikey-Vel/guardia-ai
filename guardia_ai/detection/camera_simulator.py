#!/usr/bin/env python3
"""
Guardia AI - Camera Simulation Script
Developed by Tackle Studioz

Provides various camera simulation modes for testing the surveillance system:
- Video file playback
- Static image sequence
- Synthetic scene generation
- Multi-camera simulation
- Network camera emulation
- Test pattern generation
"""

import cv2
import numpy as np
import time
import json
import threading
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import math
import random

class SimulationMode(Enum):
    """Camera simulation modes"""
    VIDEO_FILE = "video_file"
    IMAGE_SEQUENCE = "image_sequence"
    SYNTHETIC = "synthetic"
    WEBCAM_PLAYBACK = "webcam_playback"
    MULTI_CAMERA = "multi_camera"
    NETWORK_STREAM = "network_stream"
    TEST_PATTERNS = "test_patterns"

@dataclass
class SimulatedObject:
    """Represents a simulated object in the scene"""
    object_id: str
    object_type: str
    position: Tuple[float, float]
    velocity: Tuple[float, float]
    size: Tuple[int, int]
    color: Tuple[int, int, int]
    confidence: float
    trajectory_type: str = "linear"  # linear, circular, random, stationary
    
    # Behavior simulation
    stationary_time: float = 0.0
    direction_change_interval: float = 5.0
    last_direction_change: float = 0.0
    
    # Visual properties
    shape: str = "rectangle"  # rectangle, circle, ellipse
    opacity: float = 1.0

class CameraSimulator:
    """
    Advanced camera simulator for testing surveillance systems
    """
    
    def __init__(self, config_path: str = "guardia_ai/storage/simulation_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        
        # Simulation state
        self.running = False
        self.current_mode = SimulationMode.SYNTHETIC
        self.frame_width = self.config.get('frame_width', 640)
        self.frame_height = self.config.get('frame_height', 480)
        self.fps = self.config.get('fps', 30)
        
        # Video sources
        self.video_capture = None
        self.current_frame = None
        self.frame_count = 0
        
        # Synthetic scene
        self.simulated_objects: List[SimulatedObject] = []
        self.background_image = None
        self.scene_complexity = self.config.get('scene_complexity', 'medium')
        
        # Multi-camera simulation
        self.camera_views: Dict[str, Dict[str, Any]] = {}
        
        # Performance tracking
        self.start_time = time.time()
        self.frames_generated = 0
        
        print("📹 Camera Simulator initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load simulation configuration"""
        default_config = {
            "frame_width": 640,
            "frame_height": 480,
            "fps": 30,
            "scene_complexity": "medium",
            "background_color": [50, 50, 50],
            "simulation_duration": 300,  # seconds
            "synthetic_objects": {
                "people_count": 3,
                "vehicle_count": 1,
                "random_objects": 2
            },
            "scenarios": {
                "normal_activity": {
                    "people_moving": True,
                    "vehicles_present": True,
                    "crowd_formation": False,
                    "intrusion_events": False
                },
                "security_test": {
                    "intrusion_events": True,
                    "loitering_behavior": True,
                    "crowd_formation": True,
                    "aggressive_movement": True
                }
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
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving simulation config: {e}")
    
    def start_simulation(self, mode: SimulationMode, source: Optional[str] = None):
        """Start camera simulation"""
        self.current_mode = mode
        self.running = True
        self.start_time = time.time()
        self.frames_generated = 0
        
        # Initialize based on mode
        if mode == SimulationMode.VIDEO_FILE:
            if source and os.path.exists(source):
                self.video_capture = cv2.VideoCapture(source)
                print(f"📹 Playing video file: {source}")
            else:
                print("❌ Video file not found, switching to synthetic mode")
                self.current_mode = SimulationMode.SYNTHETIC
        
        elif mode == SimulationMode.WEBCAM_PLAYBACK:
            self.video_capture = cv2.VideoCapture(0)
            print("📹 Using webcam input")
        
        elif mode == SimulationMode.SYNTHETIC:
            self._initialize_synthetic_scene()
            print("🎨 Generating synthetic scene")
        
        elif mode == SimulationMode.MULTI_CAMERA:
            self._initialize_multi_camera()
            print("📹 Multi-camera simulation active")
        
        elif mode == SimulationMode.TEST_PATTERNS:
            print("🔧 Generating test patterns")
        
        print(f"🚀 Camera simulation started ({mode.value})")
    
    def stop_simulation(self):
        """Stop camera simulation"""
        self.running = False
        if self.video_capture:
            self.video_capture.release()
        print("⏹️ Camera simulation stopped")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get next simulated frame"""
        if not self.running:
            return None
        
        frame = None
        
        if self.current_mode == SimulationMode.VIDEO_FILE:
            frame = self._get_video_frame()
        
        elif self.current_mode == SimulationMode.WEBCAM_PLAYBACK:
            frame = self._get_webcam_frame()
        
        elif self.current_mode == SimulationMode.SYNTHETIC:
            frame = self._generate_synthetic_frame()
        
        elif self.current_mode == SimulationMode.MULTI_CAMERA:
            frame = self._get_multi_camera_frame()
        
        elif self.current_mode == SimulationMode.TEST_PATTERNS:
            frame = self._generate_test_pattern()
        
        if frame is not None:
            self.current_frame = frame
            self.frame_count += 1
            self.frames_generated += 1
        
        return frame
    
    def _get_video_frame(self) -> Optional[np.ndarray]:
        """Get frame from video file"""
        if not self.video_capture:
            return None
        
        ret, frame = self.video_capture.read()
        if not ret:
            # Loop video
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.video_capture.read()
        
        if ret:
            # Resize to target dimensions
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
        
        return frame if ret else None
    
    def _get_webcam_frame(self) -> Optional[np.ndarray]:
        """Get frame from webcam"""
        if not self.video_capture:
            return None
        
        ret, frame = self.video_capture.read()
        if ret:
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
        
        return frame if ret else None
    
    def _initialize_synthetic_scene(self):
        """Initialize synthetic scene with objects"""
        self.simulated_objects.clear()
        
        # Create background
        self._create_background()
        
        # Add people
        people_count = self.config['synthetic_objects']['people_count']
        for i in range(people_count):
            person = self._create_simulated_person(f"person_{i}")
            self.simulated_objects.append(person)
        
        # Add vehicles
        vehicle_count = self.config['synthetic_objects']['vehicle_count']
        for i in range(vehicle_count):
            vehicle = self._create_simulated_vehicle(f"vehicle_{i}")
            self.simulated_objects.append(vehicle)
        
        # Add random objects
        random_count = self.config['synthetic_objects']['random_objects']
        for i in range(random_count):
            obj = self._create_random_object(f"object_{i}")
            self.simulated_objects.append(obj)
        
        print(f"🎭 Created synthetic scene with {len(self.simulated_objects)} objects")
    
    def _create_background(self):
        """Create scene background"""
        bg_color = tuple(self.config['background_color'])
        self.background_image = np.full(
            (self.frame_height, self.frame_width, 3), 
            bg_color, 
            dtype=np.uint8
        )
        
        # Add some basic scene elements
        # Floor
        cv2.rectangle(self.background_image, 
                     (0, int(self.frame_height * 0.7)), 
                     (self.frame_width, self.frame_height), 
                     (40, 40, 40), -1)
        
        # Walls/boundaries
        cv2.rectangle(self.background_image, 
                     (0, 0), (50, self.frame_height), 
                     (80, 80, 80), -1)
        cv2.rectangle(self.background_image, 
                     (self.frame_width - 50, 0), 
                     (self.frame_width, self.frame_height), 
                     (80, 80, 80), -1)
        
        # Add some texture/noise for realism
        noise = np.random.randint(-10, 11, self.background_image.shape, dtype=np.int16)
        self.background_image = np.clip(self.background_image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    def _create_simulated_person(self, object_id: str) -> SimulatedObject:
        """Create a simulated person"""
        x = random.randint(60, self.frame_width - 100)
        y = random.randint(60, self.frame_height - 150)
        
        # Random movement parameters
        vx = random.uniform(-2, 2)
        vy = random.uniform(-2, 2)
        
        # Random trajectory type
        trajectory_types = ["linear", "circular", "random", "stationary"]
        trajectory = random.choice(trajectory_types)
        
        return SimulatedObject(
            object_id=object_id,
            object_type="person",
            position=(float(x), float(y)),
            velocity=(vx, vy),
            size=(40, 80),  # width, height
            color=(0, 255, 0),  # Green
            confidence=random.uniform(0.8, 0.95),
            trajectory_type=trajectory,
            shape="rectangle"
        )
    
    def _create_simulated_vehicle(self, object_id: str) -> SimulatedObject:
        """Create a simulated vehicle"""
        x = random.randint(80, self.frame_width - 120)
        y = random.randint(int(self.frame_height * 0.6), self.frame_height - 80)
        
        vx = random.uniform(-3, 3)
        vy = random.uniform(-1, 1)
        
        return SimulatedObject(
            object_id=object_id,
            object_type="car",
            position=(float(x), float(y)),
            velocity=(vx, vy),
            size=(80, 40),
            color=(255, 0, 0),  # Red
            confidence=random.uniform(0.85, 0.98),
            trajectory_type="linear",
            shape="rectangle"
        )
    
    def _create_random_object(self, object_id: str) -> SimulatedObject:
        """Create a random object"""
        x = random.randint(30, self.frame_width - 50)
        y = random.randint(30, self.frame_height - 50)
        
        object_types = ["backpack", "bottle", "handbag", "suitcase"]
        obj_type = random.choice(object_types)
        
        return SimulatedObject(
            object_id=object_id,
            object_type=obj_type,
            position=(float(x), float(y)),
            velocity=(0.0, 0.0),  # Stationary
            size=(20, 20),
            color=(0, 255, 255),  # Yellow
            confidence=random.uniform(0.7, 0.9),
            trajectory_type="stationary",
            shape="circle"
        )
    
    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generate synthetic frame with simulated objects"""
        # Start with background
        frame = self.background_image.copy()
        
        # Update and draw objects
        current_time = time.time() - self.start_time
        
        for obj in self.simulated_objects:
            # Update object position based on trajectory
            self._update_object_position(obj, current_time)
            
            # Draw object on frame
            self._draw_object(frame, obj)
        
        # Add some random noise for realism
        if random.random() < 0.1:  # 10% chance
            self._add_noise(frame)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"SIM: {timestamp}", (10, 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def _update_object_position(self, obj: SimulatedObject, current_time: float):
        """Update object position based on its trajectory type"""
        x, y = obj.position
        vx, vy = obj.velocity
        
        if obj.trajectory_type == "linear":
            # Simple linear movement
            x += vx
            y += vy
            
            # Bounce off walls
            if x <= 60 or x >= self.frame_width - 60:
                obj.velocity = (-vx, vy)
                vx = -vx
            if y <= 60 or y >= self.frame_height - 60:
                obj.velocity = (vx, -vy)
                vy = -vy
        
        elif obj.trajectory_type == "circular":
            # Circular movement
            center_x = self.frame_width // 2
            center_y = self.frame_height // 2
            radius = 100
            angle = current_time * 0.5  # Slow rotation
            
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
        
        elif obj.trajectory_type == "random":
            # Random walk with direction changes
            if current_time - obj.last_direction_change > obj.direction_change_interval:
                obj.velocity = (
                    random.uniform(-3, 3),
                    random.uniform(-3, 3)
                )
                obj.last_direction_change = current_time
                obj.direction_change_interval = random.uniform(2, 8)
            
            x += vx
            y += vy
            
            # Keep in bounds
            x = max(60, min(x, self.frame_width - 60))
            y = max(60, min(y, self.frame_height - 60))
        
        elif obj.trajectory_type == "stationary":
            # Stationary with small random movement
            x += random.uniform(-0.5, 0.5)
            y += random.uniform(-0.5, 0.5)
            obj.stationary_time += 1.0 / self.fps
        
        # Update position
        obj.position = (x, y)
    
    def _draw_object(self, frame: np.ndarray, obj: SimulatedObject):
        """Draw object on frame"""
        x, y = obj.position
        w, h = obj.size
        
        # Convert to integer coordinates
        x, y = int(x), int(y)
        
        if obj.shape == "rectangle":
            cv2.rectangle(frame, (x - w//2, y - h//2), 
                         (x + w//2, y + h//2), obj.color, -1)
            # Add border
            cv2.rectangle(frame, (x - w//2, y - h//2), 
                         (x + w//2, y + h//2), (255, 255, 255), 1)
        
        elif obj.shape == "circle":
            cv2.circle(frame, (x, y), w//2, obj.color, -1)
            cv2.circle(frame, (x, y), w//2, (255, 255, 255), 1)
        
        # Add object label
        label = f"{obj.object_type} ({obj.confidence:.2f})"
        cv2.putText(frame, label, (x - w//2, y - h//2 - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def _add_noise(self, frame: np.ndarray):
        """Add random noise to frame for realism"""
        # Salt and pepper noise
        noise = np.random.randint(0, 2, (frame.shape[0], frame.shape[1]), dtype=np.uint8)
        noise = noise * 255
        
        # Apply noise to random pixels
        noise_mask = np.random.random((frame.shape[0], frame.shape[1])) < 0.01
        frame[noise_mask] = noise[noise_mask, np.newaxis]
    
    def _initialize_multi_camera(self):
        """Initialize multi-camera simulation"""
        self.camera_views = {
            'camera_1': {
                'name': 'Main Entrance',
                'position': (0, 0),
                'view_angle': 0,
                'objects': []
            },
            'camera_2': {
                'name': 'Parking Area',
                'position': (100, 100),
                'view_angle': 45,
                'objects': []
            },
            'camera_3': {
                'name': 'Side Gate',
                'position': (200, 50),
                'view_angle': 90,
                'objects': []
            }
        }
    
    def _get_multi_camera_frame(self) -> np.ndarray:
        """Get frame from multi-camera simulation"""
        # Create composite view showing multiple camera feeds
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        
        # Divide frame into sections for each camera
        cam_width = self.frame_width // 2
        cam_height = self.frame_height // 2
        
        camera_positions = [
            (0, 0),  # Top-left
            (cam_width, 0),  # Top-right
            (0, cam_height),  # Bottom-left
            (cam_width, cam_height)  # Bottom-right
        ]
        
        for i, (cam_id, cam_info) in enumerate(self.camera_views.items()):
            if i >= len(camera_positions):
                break
            
            x_offset, y_offset = camera_positions[i]
            
            # Generate mini synthetic scene for this camera
            cam_frame = self._generate_camera_view(cam_info, cam_width, cam_height)
            
            # Place in composite frame
            frame[y_offset:y_offset+cam_height, x_offset:x_offset+cam_width] = cam_frame
            
            # Add camera label
            cv2.putText(frame, cam_info['name'], (x_offset + 5, y_offset + 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def _generate_camera_view(self, cam_info: Dict[str, Any], width: int, height: int) -> np.ndarray:
        """Generate individual camera view"""
        # Create simple scene for this camera
        view_frame = np.full((height, width, 3), (30, 30, 30), dtype=np.uint8)
        
        # Add some objects based on camera position/angle
        num_objects = random.randint(1, 3)
        for i in range(num_objects):
            x = random.randint(20, width - 20)
            y = random.randint(20, height - 20)
            size = random.randint(10, 30)
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            
            cv2.circle(view_frame, (x, y), size, color, -1)
        
        return view_frame
    
    def _generate_test_pattern(self) -> np.ndarray:
        """Generate test pattern for calibration"""
        frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        
        # Color bars
        bar_width = self.frame_width // 8
        colors = [
            (255, 255, 255),  # White
            (255, 255, 0),    # Yellow
            (0, 255, 255),    # Cyan
            (0, 255, 0),      # Green
            (255, 0, 255),    # Magenta
            (255, 0, 0),      # Red
            (0, 0, 255),      # Blue
            (0, 0, 0)         # Black
        ]
        
        for i, color in enumerate(colors):
            x_start = i * bar_width
            x_end = min((i + 1) * bar_width, self.frame_width)
            frame[:, x_start:x_end] = color
        
        # Add grid pattern
        grid_size = 50
        for i in range(0, self.frame_width, grid_size):
            cv2.line(frame, (i, 0), (i, self.frame_height), (128, 128, 128), 1)
        for i in range(0, self.frame_height, grid_size):
            cv2.line(frame, (0, i), (self.frame_width, i), (128, 128, 128), 1)
        
        # Add frame counter
        cv2.putText(frame, f"Frame: {self.frame_count}", 
                   (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    def add_scenario_event(self, event_type: str, duration: float = 5.0):
        """Add a scenario event to the simulation"""
        if event_type == "intrusion":
            # Add fast-moving object entering from edge
            intruder = SimulatedObject(
                object_id="intruder",
                object_type="person",
                position=(10.0, float(self.frame_height // 2)),
                velocity=(5.0, 0.0),
                size=(35, 70),
                color=(255, 0, 0),  # Red
                confidence=0.9,
                trajectory_type="linear"
            )
            self.simulated_objects.append(intruder)
        
        elif event_type == "loitering":
            # Make an existing person stationary
            for obj in self.simulated_objects:
                if obj.object_type == "person":
                    obj.trajectory_type = "stationary"
                    obj.velocity = (0.0, 0.0)
                    break
        
        elif event_type == "crowd":
            # Add multiple people in same area
            center_x = self.frame_width // 2
            center_y = self.frame_height // 2
            
            for i in range(5):
                person = SimulatedObject(
                    object_id=f"crowd_person_{i}",
                    object_type="person",
                    position=(
                        center_x + random.uniform(-50, 50),
                        center_y + random.uniform(-50, 50)
                    ),
                    velocity=(random.uniform(-1, 1), random.uniform(-1, 1)),
                    size=(35, 70),
                    color=(0, 255, 255),  # Yellow
                    confidence=0.85,
                    trajectory_type="random"
                )
                self.simulated_objects.append(person)
        
        print(f"🎬 Added scenario event: {event_type}")
    
    def get_simulation_stats(self) -> Dict[str, Any]:
        """Get simulation statistics"""
        elapsed_time = time.time() - self.start_time
        fps_actual = self.frames_generated / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'mode': self.current_mode.value,
            'frames_generated': self.frames_generated,
            'elapsed_time': elapsed_time,
            'actual_fps': fps_actual,
            'target_fps': self.fps,
            'simulated_objects': len(self.simulated_objects),
            'frame_dimensions': (self.frame_width, self.frame_height)
        }
    
    def export_detection_annotations(self, output_file: str):
        """Export object annotations for testing detection algorithms"""
        annotations = {
            'frame_info': {
                'width': self.frame_width,
                'height': self.frame_height,
                'fps': self.fps
            },
            'objects': []
        }
        
        for obj in self.simulated_objects:
            x, y = obj.position
            w, h = obj.size
            
            # Convert to standard bbox format
            bbox = [
                int(x - w//2),  # x
                int(y - h//2),  # y
                w,              # width
                h               # height
            ]
            
            annotations['objects'].append({
                'id': obj.object_id,
                'class': obj.object_type,
                'bbox': bbox,
                'confidence': obj.confidence,
                'trajectory_type': obj.trajectory_type
            })
        
        try:
            with open(output_file, 'w') as f:
                json.dump(annotations, f, indent=2)
            print(f"📄 Exported annotations to: {output_file}")
        except Exception as e:
            print(f"❌ Error exporting annotations: {e}")


def test_camera_simulator():
    """Test the camera simulator"""
    print("🧪 Testing Camera Simulator...")
    
    simulator = CameraSimulator()
    
    # Test different simulation modes
    modes_to_test = [
        SimulationMode.SYNTHETIC,
        SimulationMode.TEST_PATTERNS,
        SimulationMode.MULTI_CAMERA
    ]
    
    for mode in modes_to_test:
        print(f"\n📹 Testing {mode.value} mode...")
        simulator.start_simulation(mode)
        
        # Generate and display frames
        for i in range(30):  # Test 30 frames
            frame = simulator.get_frame()
            if frame is not None:
                # Show frame
                cv2.imshow(f'Camera Simulator - {mode.value}', frame)
                
                # Add scenario events for testing
                if mode == SimulationMode.SYNTHETIC and i == 15:
                    simulator.add_scenario_event("intrusion")
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        # Show statistics
        stats = simulator.get_simulation_stats()
        print(f"📊 Stats: {stats}")
        
        simulator.stop_simulation()
        cv2.destroyAllWindows()
        time.sleep(1)
    
    print("✅ Camera simulator test completed")


def main():
    """Main function for camera simulator"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Guardia AI Camera Simulator')
    parser.add_argument('--mode', choices=['synthetic', 'video', 'webcam', 'multi', 'test'], 
                       default='synthetic', help='Simulation mode')
    parser.add_argument('--source', type=str, help='Video file path (for video mode)')
    parser.add_argument('--duration', type=int, default=60, help='Simulation duration in seconds')
    parser.add_argument('--scenario', type=str, help='Scenario to simulate')
    parser.add_argument('--export', type=str, help='Export annotations to file')
    
    args = parser.parse_args()
    
    # Create simulator
    simulator = CameraSimulator()
    
    # Map command line mode to enum
    mode_map = {
        'synthetic': SimulationMode.SYNTHETIC,
        'video': SimulationMode.VIDEO_FILE,
        'webcam': SimulationMode.WEBCAM_PLAYBACK,
        'multi': SimulationMode.MULTI_CAMERA,
        'test': SimulationMode.TEST_PATTERNS
    }
    
    mode = mode_map.get(args.mode, SimulationMode.SYNTHETIC)
    
    # Start simulation
    simulator.start_simulation(mode, args.source)
    
    print(f"🚀 Camera simulation started ({mode.value})")
    print("Press 'q' to quit, 's' for stats, 'e' for events")
    
    start_time = time.time()
    
    try:
        while True:
            # Check duration
            if time.time() - start_time > args.duration:
                break
            
            # Get frame
            frame = simulator.get_frame()
            if frame is None:
                break
            
            # Display frame
            cv2.imshow('Guardia AI Camera Simulator', frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                stats = simulator.get_simulation_stats()
                print(f"📊 Simulation Stats: {stats}")
            elif key == ord('e'):
                # Add random event
                events = ['intrusion', 'loitering', 'crowd']
                event = random.choice(events)
                simulator.add_scenario_event(event)
                print(f"🎬 Added event: {event}")
            
            # Maintain target FPS
            time.sleep(1.0 / simulator.fps)
    
    except KeyboardInterrupt:
        print("\n⏹️ Simulation interrupted")
    
    finally:
        simulator.stop_simulation()
        cv2.destroyAllWindows()
        
        # Export annotations if requested
        if args.export:
            simulator.export_detection_annotations(args.export)
        
        # Final stats
        final_stats = simulator.get_simulation_stats()
        print(f"📈 Final Statistics: {final_stats}")
        print("✅ Camera simulator finished")


if __name__ == "__main__":
    if len(os.sys.argv) > 1:
        main()
    else:
        test_camera_simulator()
