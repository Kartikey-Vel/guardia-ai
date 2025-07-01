#!/usr/bin/env python3
"""
Camera Manager for Guardia AI
Handles multiple camera sources including webcams, IP cameras, and RTSP streams
"""

import cv2
import json
import os
import socket
import threading
import time
import qrcode
import netifaces
from datetime import datetime
from urllib.parse import urlparse
import requests
from io import BytesIO
import numpy as np

class CameraSource:
    """Represents a single camera source"""
    
    def __init__(self, source_id, source_type, source_path, name="Camera", description=""):
        self.source_id = source_id
        self.source_type = source_type  # 'webcam', 'ip', 'rtsp'
        self.source_path = source_path  # 0, 1, 2 for webcam; URL for IP/RTSP
        self.name = name
        self.description = description
        self.is_active = False
        self.cap = None
        self.last_frame = None
        self.connection_status = "disconnected"
        self.error_message = ""
        
    def connect(self):
        """Connect to the camera source"""
        try:
            if self.source_type == 'webcam':
                self.cap = cv2.VideoCapture(int(self.source_path))
            else:  # IP camera or RTSP
                self.cap = cv2.VideoCapture(self.source_path)
            
            if self.cap and self.cap.isOpened():
                # Set camera properties for better performance
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Test frame capture
                ret, frame = self.cap.read()
                if ret:
                    self.is_active = True
                    self.connection_status = "connected"
                    self.error_message = ""
                    self.last_frame = frame
                    return True
                else:
                    self.connection_status = "failed"
                    self.error_message = "Failed to capture frame"
                    return False
            else:
                self.connection_status = "failed"
                self.error_message = "Failed to open camera"
                return False
                
        except Exception as e:
            self.connection_status = "error"
            self.error_message = str(e)
            return False
    
    def disconnect(self):
        """Disconnect from the camera source"""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_active = False
        self.connection_status = "disconnected"
        self.last_frame = None
    
    def get_frame(self):
        """Get the latest frame from the camera"""
        if not self.cap or not self.is_active:
            # Try to reconnect if not active
            if not self.connect():
                return self.last_frame
        
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                self.last_frame = frame
                self.connection_status = "connected"
                self.error_message = ""
                return frame
            else:
                self.connection_status = "error"
                self.error_message = "Failed to read frame"
                # Try to reconnect
                self.disconnect()
                time.sleep(0.1)
                if self.connect():
                    ret, frame = self.cap.read()
                    if ret and frame is not None:
                        self.last_frame = frame
                        return frame
        except Exception as e:
            self.connection_status = "error"
            self.error_message = str(e)
            
        return self.last_frame
    
    def to_dict(self):
        """Convert to dictionary for persistence"""
        return {
            'source_id': self.source_id,
            'source_type': self.source_type,
            'source_path': self.source_path,
            'name': self.name,
            'description': self.description
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create instance from dictionary"""
        return cls(
            data['source_id'],
            data['source_type'],
            data['source_path'],
            data.get('name', 'Camera'),
            data.get('description', '')
        )

class CameraManager:
    """Manages multiple camera sources and QR code generation"""
    
    def __init__(self, config_file="guardia_ai/storage/camera_config.json"):
        self.config_file = config_file
        self.cameras = {}
        self.active_camera_id = None
        self.web_server_port = 8080
        self.web_server_running = False
        self._load_config()
        
    def _load_config(self):
        """Load camera configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    
                for camera_data in config.get('cameras', []):
                    camera = CameraSource.from_dict(camera_data)
                    self.cameras[camera.source_id] = camera
                    
                self.active_camera_id = config.get('active_camera_id')
                self.web_server_port = config.get('web_server_port', 8080)
                    
        except Exception as e:
            print(f"Error loading camera config: {e}")
    
    def _save_config(self):
        """Save camera configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config = {
                'cameras': [camera.to_dict() for camera in self.cameras.values()],
                'active_camera_id': self.active_camera_id,
                'web_server_port': self.web_server_port,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            print(f"Error saving camera config: {e}")
    
    def get_local_ip(self):
        """Get the local IP address for QR code generation"""
        try:
            # Get all network interfaces
            interfaces = netifaces.interfaces()
            
            for interface in interfaces:
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    for addr in addresses[netifaces.AF_INET]:
                        ip = addr['addr']
                        # Skip localhost and check if it's a private IP
                        if ip != '127.0.0.1' and (
                            ip.startswith('192.168.') or 
                            ip.startswith('10.') or 
                            ip.startswith('172.')
                        ):
                            return ip
            
            # Fallback method
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
            
        except Exception:
            return "192.168.1.100"  # Default fallback
    
    def generate_connection_qr(self, camera_name="GuardiaAI_Camera"):
        """Generate QR code for IP camera connection"""
        local_ip = self.get_local_ip()
        
        # Create connection info for the camera
        connection_info = {
            "server_name": "Guardia AI Security System",
            "server_ip": local_ip,
            "server_port": self.web_server_port,
            "camera_name": camera_name,
            "rtsp_url": f"rtsp://{local_ip}:{self.web_server_port}/live",
            "http_url": f"http://{local_ip}:{self.web_server_port}/connect",
            "setup_url": f"http://{local_ip}:{self.web_server_port}/setup?name={camera_name}",
            "timestamp": datetime.now().isoformat()
        }
        
        # Convert to JSON string for QR code
        qr_data = json.dumps(connection_info)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to numpy array for OpenCV
        qr_array = np.array(qr_img.convert('RGB'))
        qr_cv2 = cv2.cvtColor(qr_array, cv2.COLOR_RGB2BGR)
        
        return qr_cv2, connection_info
    
    def scan_local_cameras(self):
        """Scan for available local cameras (webcams)"""
        available_cameras = []
        
        # Check up to 10 possible camera indices
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    available_cameras.append({
                        'source_id': f"webcam_{i}",
                        'source_type': 'webcam',
                        'source_path': str(i),
                        'name': f"Webcam {i}",
                        'description': f"Local webcam at index {i}"
                    })
                cap.release()
        
        return available_cameras
    
    def add_camera(self, source_type, source_path, name, description=""):
        """Add a new camera source"""
        source_id = f"{source_type}_{len(self.cameras)}"
        camera = CameraSource(source_id, source_type, source_path, name, description)
        
        # Try to connect to verify it works
        if camera.connect():
            self.cameras[source_id] = camera
            if not self.active_camera_id:
                self.active_camera_id = source_id
            self._save_config()
            return source_id, True, "Camera added successfully"
        else:
            return None, False, camera.error_message
    
    def remove_camera(self, source_id):
        """Remove a camera source"""
        if source_id in self.cameras:
            self.cameras[source_id].disconnect()
            del self.cameras[source_id]
            
            if self.active_camera_id == source_id:
                # Set new active camera if available
                if self.cameras:
                    self.active_camera_id = list(self.cameras.keys())[0]
                else:
                    self.active_camera_id = None
                    
            self._save_config()
            return True
        return False
    
    def set_active_camera(self, source_id):
        """Set the active camera for surveillance"""
        if source_id in self.cameras:
            # Disconnect current active camera
            if self.active_camera_id and self.active_camera_id in self.cameras:
                self.cameras[self.active_camera_id].disconnect()
            
            # Connect to new active camera
            if self.cameras[source_id].connect():
                self.active_camera_id = source_id
                self._save_config()
                return True, "Camera activated successfully"
            else:
                return False, self.cameras[source_id].error_message
        return False, "Camera not found"
    
    def get_active_camera(self):
        """Get the currently active camera"""
        if self.active_camera_id and self.active_camera_id in self.cameras:
            return self.cameras[self.active_camera_id]
        return None
    
    def get_active_frame(self):
        """Get frame from the active camera"""
        active_camera = self.get_active_camera()
        if active_camera:
            frame = active_camera.get_frame()
            if frame is not None:
                return frame
            else:
                # If frame is None, try to reconnect camera
                print(f"⚠️ Camera {active_camera.name} returned None frame, attempting reconnect...")
                if active_camera.connect():
                    frame = active_camera.get_frame()
                    if frame is not None:
                        print(f"✅ Camera {active_camera.name} reconnected successfully")
                        return frame
                    else:
                        print(f"❌ Camera {active_camera.name} still not providing frames after reconnect")
                else:
                    print(f"❌ Failed to reconnect camera {active_camera.name}")
        return None
    
    def get_all_cameras(self):
        """Get list of all cameras"""
        return list(self.cameras.values())
    
    def get_camera_status(self):
        """Get status of all cameras"""
        status = {
            'total_cameras': len(self.cameras),
            'active_camera': self.active_camera_id,
            'cameras': []
        }
        
        for camera in self.cameras.values():
            camera_status = {
                'id': camera.source_id,
                'name': camera.name,
                'type': camera.source_type,
                'path': camera.source_path,
                'status': camera.connection_status,
                'is_active': camera.is_active,
                'error': camera.error_message
            }
            status['cameras'].append(camera_status)
            
        return status
    
    def connect_all_cameras(self):
        """Connect to all configured cameras"""
        results = {}
        for source_id, camera in self.cameras.items():
            success = camera.connect()
            results[source_id] = {
                'success': success,
                'error': camera.error_message if not success else None
            }
        return results
    
    def disconnect_all_cameras(self):
        """Disconnect from all cameras"""
        for camera in self.cameras.values():
            camera.disconnect()
    
    def test_ip_camera_url(self, url):
        """Test if an IP camera URL is accessible"""
        try:
            # First try to access as HTTP stream
            if url.startswith('http'):
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return True, "HTTP stream accessible"
            
            # Try to open with OpenCV
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    return True, "RTSP/Video stream accessible"
                else:
                    return False, "Stream opened but no frames received"
            else:
                return False, "Failed to open stream"
                
        except Exception as e:
            return False, str(e)

# Global camera manager instance
camera_manager = CameraManager()
