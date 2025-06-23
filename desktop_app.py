#!/usr/bin/env python3
"""
Guardia AI Desktop Application
Modern GUI application using CustomTkinter for advanced surveillance monitoring
"""
import sys
import os
import asyncio
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

# GUI Imports
try:
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import messagebox, filedialog
    from PIL import Image, ImageTk
    CTK_AVAILABLE = True
except ImportError:
    print("❌ CustomTkinter not available. Installing...")
    os.system("pip install customtkinter pillow")
    try:
        import customtkinter as ctk
        import tkinter as tk
        from tkinter import messagebox, filedialog
        from PIL import Image, ImageTk
        CTK_AVAILABLE = True
    except ImportError:
        CTK_AVAILABLE = False

# Computer Vision
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import authentication system
try:
    from face_auth_system import FaceAuthSystem, UserProfile
    from user_dialogs import UserRegistrationDialog, UserManagementDialog
    FACE_AUTH_AVAILABLE = True
except ImportError:
    FACE_AUTH_AVAILABLE = False
    print("⚠️ Face authentication system not available")

# Guardia AI imports
try:
    from guardia.core.camera_manager import EnhancedCameraManager
    from guardia.core.face_detector import EnhancedFaceDetector
    from guardia.core.object_detector import EnhancedObjectDetector
    from guardia.config.settings import get_settings
    from guardia.utils.logger import setup_logging
    from guardia.models.schemas import DetectionResult, DetectionType
    GUARDIA_AVAILABLE = True
except ImportError as e:
    print(f"❌ Guardia AI modules not available: {e}")
    GUARDIA_AVAILABLE = False
    
    # Create placeholder classes for limited mode
    class DetectionResult:
        def __init__(self, detection_type=None, confidence=0.0, bounding_box=None, person_name=None):
            self.detection_type = detection_type
            self.confidence = confidence
            self.bounding_box = bounding_box
            self.person_name = person_name
    
    class DetectionType:
        KNOWN_PERSON = "known_person"
        UNKNOWN_PERSON = "unknown_person"
        MASKED_PERSON = "masked_person"
        MULTIPLE_UNKNOWN = "multiple_unknown"
    
    class BoundingBox:
        def __init__(self, x=0, y=0, width=0, height=0):
            self.x = x
            self.y = y
            self.width = width
            self.height = height

class BasicCameraManager:
    """Basic camera manager using OpenCV for limited mode"""
    
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.is_recording = False
        self.video_writer = None
        
    async def initialize(self):
        """Initialize camera"""
        self.cap = cv2.VideoCapture(self.camera_index)
        return self.cap.isOpened()
    
    async def start_capture(self):
        """Start capture (placeholder)"""
        pass
    
    async def get_frame(self):
        """Get current frame"""
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
    
    async def start_recording(self, output_path):
        """Start recording"""
        if self.cap and self.cap.isOpened():
            # Get frame properties
            width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = 30.0
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            self.is_recording = True
            return True
        return False
    
    async def stop_recording(self):
        """Stop recording"""
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            self.is_recording = False
            return True
        return False
    
    async def release(self):
        """Release camera"""
        if self.is_recording:
            await self.stop_recording()
        if self.cap:
            self.cap.release()
            self.cap = None

class BasicFaceDetector:
    """Basic face detection using OpenCV for limited mode"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    async def detect_faces(self, frame):
        """Simple face detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        detections = []
        for (x, y, w, h) in faces:
            detection = DetectionResult(
                detection_type=DetectionType.UNKNOWN_PERSON,
                confidence=0.8,
                bounding_box=BoundingBox(x=x, y=y, width=w, height=h),
                person_name=None
            )
            detections.append(detection)
        
        return detections

class BasicObjectDetector:
    """Basic object detection for limited mode"""
    
    async def detect_objects(self, frame):
        """Placeholder object detection"""
        return []  # No object detection in limited mode

# Configure CustomTkinter appearance
if CTK_AVAILABLE:
    ctk.set_appearance_mode("dark")  # "dark" or "light"
    ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

class GuardiaDesktopApp:
    """Modern desktop application for Guardia AI surveillance system"""
    
    def __init__(self):
        # Initialize main window
        self.root = ctk.CTk()
        self.root.title("🔥 Guardia AI - Advanced Surveillance System")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)
        
        # App state
        self.camera_manager: Optional[EnhancedCameraManager] = None
        self.face_detector: Optional[EnhancedFaceDetector] = None
        self.object_detector: Optional[EnhancedObjectDetector] = None
        self.auth_system: Optional[FaceAuthSystem] = None
        self.current_user: Optional[UserProfile] = None
        self.is_monitoring = False
        self.is_recording = False
        self.detection_enabled = True
        self.current_frame = None
        self.detection_count = 0
        self.fps = 0
        self.settings = None
        
        # Threading
        self.camera_thread = None
        self.detection_thread = None
        self.update_thread = None
        self.stop_event = threading.Event()
        
        # Detection storage for real-time display
        self.latest_face_detections = []
        self.latest_object_detections = []
        
        # Statistics tracking
        self.stats = {
            "session_start": None,
            "frames_processed": 0,
            "detections_made": 0,
            "alerts_generated": 0,
            "known_persons": 0,
            "unknown_persons": 0
        }
        
        # Initialize UI and services
        self._setup_ui()
        self._initialize_services()
    
    def _setup_ui(self):
        """Setup the modern UI interface"""
        # Configure grid weights
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self._create_sidebar()
        
        # Create main content area
        self._create_main_content()
        
        # Create status bar
        self._create_status_bar()
        
        # Setup keybindings
        self._setup_keybindings()
    
    def _create_sidebar(self):
        """Create the left sidebar with controls"""
        self.sidebar_frame = ctk.CTkFrame(self.root, width=300, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=3, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)  # Empty space
        
        # Logo and title
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="🔥 Guardia AI", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.subtitle_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Advanced AI Surveillance", 
            font=ctk.CTkFont(size=14)
        )
        self.subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Camera controls
        self.camera_frame = ctk.CTkFrame(self.sidebar_frame)
        self.camera_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.camera_label = ctk.CTkLabel(self.camera_frame, text="📹 Camera Control", font=ctk.CTkFont(weight="bold"))
        self.camera_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.start_button = ctk.CTkButton(
            self.camera_frame, 
            text="▶️ Start Monitoring",
            command=self._toggle_monitoring,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        self.record_button = ctk.CTkButton(
            self.camera_frame, 
            text="⏺️ Start Recording",
            command=self._toggle_recording,
            height=35
        )
        self.record_button.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        # Detection controls
        self.detection_frame = ctk.CTkFrame(self.sidebar_frame)
        self.detection_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.detection_label = ctk.CTkLabel(self.detection_frame, text="🧠 AI Detection", font=ctk.CTkFont(weight="bold"))
        self.detection_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.detection_switch = ctk.CTkSwitch(
            self.detection_frame, 
            text="Enable Detection",
            command=self._toggle_detection
        )
        self.detection_switch.grid(row=1, column=0, padx=10, pady=5)
        self.detection_switch.select()  # Enable by default
        
        self.face_recognition_switch = ctk.CTkSwitch(
            self.detection_frame, 
            text="Face Recognition"
        )
        self.face_recognition_switch.grid(row=2, column=0, padx=10, pady=5)
        self.face_recognition_switch.select()
        
        self.object_detection_switch = ctk.CTkSwitch(
            self.detection_frame, 
            text="Object Detection"
        )
        self.object_detection_switch.grid(row=3, column=0, padx=10, pady=5)
        self.object_detection_switch.select()
        
        # Statistics
        self.stats_frame = ctk.CTkFrame(self.sidebar_frame)
        self.stats_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        self.stats_label = ctk.CTkLabel(self.stats_frame, text="📊 Statistics", font=ctk.CTkFont(weight="bold"))
        self.stats_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.fps_label = ctk.CTkLabel(self.stats_frame, text="FPS: 0")
        self.fps_label.grid(row=1, column=0, padx=10, pady=2, sticky="w")
        
        self.detections_label = ctk.CTkLabel(self.stats_frame, text="Detections: 0")
        self.detections_label.grid(row=2, column=0, padx=10, pady=2, sticky="w")
        
        self.frames_label = ctk.CTkLabel(self.stats_frame, text="Frames: 0")
        self.frames_label.grid(row=3, column=0, padx=10, pady=2, sticky="w")
        
        self.uptime_label = ctk.CTkLabel(self.stats_frame, text="Uptime: 00:00:00")
        self.uptime_label.grid(row=4, column=0, padx=10, pady=2, sticky="w")
        
        # User Management
        self.user_frame = ctk.CTkFrame(self.sidebar_frame)
        self.user_frame.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        self.user_label = ctk.CTkLabel(self.user_frame, text="👤 User Management", font=ctk.CTkFont(weight="bold"))
        self.user_label.grid(row=0, column=0, padx=10, pady=10, columnspan=2)
        
        self.current_user_label = ctk.CTkLabel(self.user_frame, text="Current User: None")
        self.current_user_label.grid(row=1, column=0, padx=10, pady=2, sticky="w", columnspan=2)
        
        self.register_user_button = ctk.CTkButton(
            self.user_frame, 
            text="➕ Register User",
            command=self._open_user_registration,
            height=30,
            width=120
        )
        self.register_user_button.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        self.manage_users_button = ctk.CTkButton(
            self.user_frame, 
            text="👥 Manage Users",
            command=self._open_user_management,
            height=30,
            width=120
        )
        self.manage_users_button.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        self.user_frame.grid_columnconfigure(0, weight=1)
        self.user_frame.grid_columnconfigure(1, weight=1)
        
        # Settings
        self.settings_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="⚙️ Settings",
            command=self._open_settings,
            height=35
        )
        self.settings_button.grid(row=12, column=0, padx=20, pady=10, sticky="ew")
        
        # About
        self.about_button = ctk.CTkButton(
            self.sidebar_frame, 
            text="ℹ️ About",
            command=self._show_about,
            height=35
        )
        self.about_button.grid(row=13, column=0, padx=20, pady=(0, 20), sticky="ew")
    
    def _create_main_content(self):
        """Create the main content area with video display"""
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Top toolbar
        self.toolbar_frame = ctk.CTkFrame(self.main_frame, height=60)
        self.toolbar_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.toolbar_frame.grid_columnconfigure(2, weight=1)
        
        self.camera_selector = ctk.CTkOptionMenu(
            self.toolbar_frame,
            values=["USB Camera (0)", "USB Camera (1)", "IP Camera", "Video File"],
            command=self._on_camera_selected
        )
        self.camera_selector.grid(row=0, column=0, padx=20, pady=15)
        
        self.resolution_selector = ctk.CTkOptionMenu(
            self.toolbar_frame,
            values=["640x480", "1280x720", "1920x1080"],
            command=self._on_resolution_selected
        )
        self.resolution_selector.grid(row=0, column=1, padx=10, pady=15)
        
        # Status indicator
        self.status_indicator = ctk.CTkLabel(
            self.toolbar_frame, 
            text="🔴 OFFLINE", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.status_indicator.grid(row=0, column=3, padx=20, pady=15)
        
        # Video display area
        self.video_frame = ctk.CTkFrame(self.main_frame)
        self.video_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.video_frame.grid_columnconfigure(0, weight=1)
        self.video_frame.grid_rowconfigure(0, weight=1)
        
        # Top video toolbar
        self.video_toolbar_frame = ctk.CTkFrame(self.video_frame, height=40)
        self.video_toolbar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        self.snapshot_button = ctk.CTkButton(
            self.video_toolbar_frame, 
            text="📸 Snapshot",
            command=self._take_snapshot,
            height=30
        )
        self.snapshot_button.grid(row=0, column=0, padx=10, pady=5)
        
        # Video canvas
        self.video_canvas = tk.Canvas(
            self.video_frame, 
            bg="#2b2b2b", 
            highlightthickness=0
        )
        self.video_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        # Placeholder text
        self.placeholder_text = self.video_canvas.create_text(
            400, 300, 
            text="📹 Camera feed will appear here\nClick 'Start Monitoring' to begin",
            font=("Arial", 20),
            fill="#ffffff",
            justify="center"
        )
    
    def _create_status_bar(self):
        """Create the bottom status bar"""
        self.status_frame = ctk.CTkFrame(self.root, height=40)
        self.status_frame.grid(row=2, column=1, sticky="ew", padx=(0, 20), pady=(0, 20))
        self.status_frame.grid_columnconfigure(1, weight=1)
        
        self.connection_status = ctk.CTkLabel(
            self.status_frame, 
            text="🔌 Not Connected"
        )
        self.connection_status.grid(row=0, column=0, padx=20, pady=10)
        
        self.current_time = ctk.CTkLabel(
            self.status_frame, 
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.current_time.grid(row=0, column=2, padx=20, pady=10)
        
        # Start time updates
        self._update_time()
    
    def _setup_keybindings(self):
        """Setup keyboard shortcuts"""
        self.root.bind("<space>", lambda e: self._toggle_monitoring())
        self.root.bind("<r>", lambda e: self._toggle_recording())
        self.root.bind("<d>", lambda e: self._toggle_detection())
        self.root.bind("<s>", lambda e: self._take_snapshot())
        self.root.bind("<Escape>", lambda e: self._stop_all())
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
    
    def _initialize_services(self):
        """Initialize AI services"""
        try:
            if GUARDIA_AVAILABLE:
                # Initialize settings
                self.settings = get_settings()
                
                # Setup logging
                setup_logging()
                
                # Initialize face authentication system
                if FACE_AUTH_AVAILABLE:
                    self.auth_system = FaceAuthSystem()
                    print("✅ Face authentication system initialized")
                
                # Initialize AI components without async initialization
                # We'll defer their async setup until first use
                try:
                    # Create detectors but don't await their initialization
                    self.face_detector = EnhancedFaceDetector()
                    self.object_detector = EnhancedObjectDetector()
                    
                    # Update connection status
                    self.connection_status.configure(text="🟢 AI Services Ready")
                    print("✅ Guardia AI services initialized")
                    
                except Exception as async_error:
                    print(f"⚠️ Async initialization deferred: {async_error}")
                    # Fall back to basic mode
                    self.face_detector = BasicFaceDetector()
                    self.object_detector = BasicObjectDetector()
                    self.connection_status.configure(text="🟡 Basic Mode - Async Deferred")
                    print("✅ Basic detection services initialized (async deferred)")
                
            else:
                # Use basic detection in limited mode
                if CV2_AVAILABLE:
                    self.face_detector = BasicFaceDetector()
                    self.object_detector = BasicObjectDetector()
                    self.connection_status.configure(text="🟡 Basic Mode - OpenCV Only")
                    print("✅ Basic detection services initialized")
                else:
                    self.connection_status.configure(text="⚠️ Limited Mode - Camera Only")
                    print("⚠️ Running in camera-only mode")
                
        except Exception as e:
            print(f"❌ Failed to initialize services: {e}")
            self.connection_status.configure(text="🔴 Services Failed")
    
    def _toggle_monitoring(self):
        """Toggle camera monitoring on/off"""
        if not self.is_monitoring:
            self._start_monitoring()
        else:
            self._stop_monitoring()
    
    def _start_monitoring(self):
        """Start camera monitoring"""
        try:
            if not CV2_AVAILABLE:
                messagebox.showerror("Error", "OpenCV not available. Please install: pip install opencv-python")
                return
            
            # Initialize camera
            camera_index = 0  # Default to first camera
            
            if GUARDIA_AVAILABLE:
                self.camera_manager = EnhancedCameraManager("desktop_app", camera_index)
            else:
                # Use basic OpenCV camera in limited mode
                self.camera_manager = BasicCameraManager(camera_index)
            
            # Start camera in a separate thread
            self.stop_event.clear()
            self.camera_thread = threading.Thread(target=self._camera_loop, daemon=True)
            self.camera_thread.start()
            
            # Start detection if enabled
            if self.detection_enabled and (self.face_detector or self.object_detector):
                self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
                self.detection_thread.start()
            elif not GUARDIA_AVAILABLE:
                # Limited mode - use basic detectors
                self.face_detector = BasicFaceDetector()
                self.object_detector = BasicObjectDetector()
                
                self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
                self.detection_thread.start()
            
            # Start real-time video display updates
            self.root.after(100, self._update_video_display)
            
            # Update status and statistics
            self.is_monitoring = True
            self.stats["session_start"] = time.time()
            self.start_button.configure(text="⏹️ Stop Monitoring")
            self.status_indicator.configure(text="🟢 LIVE")
            self.connection_status.configure(text="🟢 Camera Active")
            
            # Remove placeholder
            self.video_canvas.delete(self.placeholder_text)
            
            print("✅ Monitoring started")
            
        except Exception as e:
            print(f"❌ Failed to start monitoring: {e}")
            messagebox.showerror("Error", f"Failed to start camera monitoring:\n{e}")
    
    def _stop_monitoring(self):
        """Stop camera monitoring"""
        try:
            self.is_monitoring = False
            self.stop_event.set()
            
            # Stop recording if active
            if self.is_recording:
                self._stop_recording()
            
            # Wait for threads to finish
            if self.camera_thread and self.camera_thread.is_alive():
                self.camera_thread.join(timeout=2)
            
            if self.detection_thread and self.detection_thread.is_alive():
                self.detection_thread.join(timeout=2)
            
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=2)
            
            # Release camera
            if self.camera_manager:
                asyncio.run(self.camera_manager.release())
                self.camera_manager = None
            
            # Update UI
            self.start_button.configure(text="▶️ Start Monitoring")
            self.status_indicator.configure(text="🔴 OFFLINE")
            self.connection_status.configure(text="🔌 Camera Disconnected")
            
            # Clear video display
            self.video_canvas.delete("all")
            self.placeholder_text = self.video_canvas.create_text(
                400, 300,
                text="📹 Camera feed will appear here\nClick 'Start Monitoring' to begin",
                font=("Arial", 20),
                fill="#ffffff",
                justify="center"
            )
            
            print("✅ Monitoring stopped")
            
        except Exception as e:
            print(f"❌ Error stopping monitoring: {e}")
    
    def _toggle_recording(self):
        """Toggle video recording"""
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()
    
    def _start_recording(self):
        """Start video recording"""
        if not self.is_monitoring:
            messagebox.showwarning("Warning", "Please start monitoring first")
            return
        
        try:
            if self.camera_manager:
                # Create recordings directory
                recordings_dir = Path("recordings")
                recordings_dir.mkdir(exist_ok=True)
                
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                recording_path = recordings_dir / f"guardia_recording_{timestamp}.mp4"
                
                # Start recording
                asyncio.run(self.camera_manager.start_recording(recording_path))
                
                self.is_recording = True
                self.record_button.configure(text="⏹️ Stop Recording")
                
                print(f"✅ Recording started: {recording_path}")
                
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            messagebox.showerror("Error", f"Failed to start recording:\n{e}")
    
    def _stop_recording(self):
        """Stop video recording"""
        try:
            if self.camera_manager:
                recording_path = asyncio.run(self.camera_manager.stop_recording())
                
                self.is_recording = False
                self.record_button.configure(text="⏺️ Start Recording")
                
                if recording_path:
                    print(f"✅ Recording saved: {recording_path}")
                    messagebox.showinfo("Recording Saved", f"Recording saved to:\n{recording_path}")
                
        except Exception as e:
            print(f"❌ Error stopping recording: {e}")
            # Force reset recording state
            self.is_recording = False
            self.record_button.configure(text="⏺️ Start Recording")
    
    def _toggle_detection(self):
        """Toggle AI detection on/off"""
        self.detection_enabled = self.detection_switch.get()
        print(f"🧠 Detection {'enabled' if self.detection_enabled else 'disabled'}")
    
    def _camera_loop(self):
        """Main camera capture loop"""
        last_fps_time = time.time()
        frame_count = 0
        
        try:
            # Initialize camera
            asyncio.run(self.camera_manager.initialize())
            if GUARDIA_AVAILABLE:
                asyncio.run(self.camera_manager.start_capture())
            
            while not self.stop_event.is_set() and self.is_monitoring:
                try:
                    # Get frame
                    frame = asyncio.run(self.camera_manager.get_frame())
                    
                    if frame is not None:
                        # Write to video if recording
                        if self.is_recording and hasattr(self.camera_manager, 'video_writer') and self.camera_manager.video_writer:
                            self.camera_manager.video_writer.write(frame)
                        
                        self.current_frame = frame.copy()
                        self.stats["frames_processed"] += 1
                        frame_count += 1
                        
                        # Calculate FPS
                        current_time = time.time()
                        if current_time - last_fps_time >= 1.0:
                            self.fps = frame_count / (current_time - last_fps_time)
                            frame_count = 0
                            last_fps_time = current_time
                    
                    time.sleep(0.033)  # ~30 FPS
                    
                except Exception as e:
                    print(f"❌ Camera loop error: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"❌ Camera initialization failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Camera Error", f"Camera failed:\n{e}"))
    
    def _detection_loop(self):
        """AI detection processing loop"""
        while not self.stop_event.is_set() and self.is_monitoring:
            try:
                if self.current_frame is not None and self.detection_enabled:
                    frame = self.current_frame.copy()
                    
                    # Perform face detection
                    if self.face_recognition_switch.get():
                        face_detections = asyncio.run(self.face_detector.detect_faces(frame))
                        
                        # Store latest detections for overlay
                        self.latest_face_detections = face_detections
                        
                        for detection in face_detections:
                            self.stats["detections_made"] += 1
                    
                    # Perform object detection
                    if self.object_detection_switch.get():
                        object_detections = asyncio.run(self.object_detector.detect_objects(frame))
                        
                        # Store latest object detections
                        self.latest_object_detections = object_detections
                        
                        for detection in object_detections:
                            self.stats["detections_made"] += 1
                
                time.sleep(0.1)  # Detection rate limiting
                
            except Exception as e:
                print(f"❌ Detection loop error: {e}")
                time.sleep(0.5)
    
    def _draw_detection(self, frame, detection: DetectionResult):
        """Draw detection bounding box and label on frame"""
        try:
            bbox = detection.bounding_box
            x, y, w, h = bbox.x, bbox.y, bbox.width, bbox.height
            
            # Choose color based on detection type
            color_map = {
                DetectionType.KNOWN_PERSON: (0, 255, 0),      # Green
                DetectionType.UNKNOWN_PERSON: (0, 0, 255),    # Red
                DetectionType.MASKED_PERSON: (255, 255, 0),   # Yellow
                DetectionType.MULTIPLE_UNKNOWN: (255, 0, 255) # Magenta
            }
            
            color = color_map.get(detection.detection_type, (0, 255, 255))  # Default cyan
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw label
            label = f"{detection.detection_type.value}"
            if detection.person_name:
                label = f"{detection.person_name}"
            
            confidence = f" ({detection.confidence:.2f})"
            label += confidence
            
            # Background for text
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
            )
            cv2.rectangle(frame, (x, y - text_height - 10), 
                         (x + text_width, y), color, -1)
            
            # Text
            cv2.putText(frame, label, (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
        except Exception as e:
            print(f"❌ Error drawing detection: {e}")
    
    def _update_ui_loop(self):
        """UI update loop"""
        while not self.stop_event.is_set() and self.is_monitoring:
            try:
                self.root.after(0, self._update_video_display)
                self.root.after(0, self._update_statistics)
                time.sleep(0.033)  # ~30 FPS UI updates
                
            except Exception as e:
                print(f"❌ UI update error: {e}")
    
    def _update_video_display(self):
        """Update the video display with enhanced real-time rendering"""
        try:
            if self.current_frame is not None:
                # Get canvas dimensions
                canvas_width = self.video_canvas.winfo_width()
                canvas_height = self.video_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    # Calculate scaling to maintain aspect ratio
                    frame_height, frame_width = self.current_frame.shape[:2]
                    scale = min((canvas_width - 20) / frame_width, (canvas_height - 20) / frame_height)
                    
                    new_width = int(frame_width * scale)
                    new_height = int(frame_height * scale)
                    
                    # Resize frame with proper scaling
                    frame = cv2.resize(self.current_frame, (new_width, new_height))
                    
                    # Add detection overlays if enabled
                    if self.detection_enabled:
                        frame = self._add_detection_overlays(frame)
                    
                    # Add info overlays
                    frame = self._add_info_overlays(frame)
                    
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to PIL Image
                    image = Image.fromarray(frame_rgb)
                    photo = ImageTk.PhotoImage(image)
                    
                    # Update canvas
                    self.video_canvas.delete("video")
                    self.video_canvas.create_image(
                        canvas_width // 2, canvas_height // 2, 
                        image=photo, tags="video"
                    )
                    
                    # Keep reference to prevent garbage collection
                    self.video_canvas.image = photo
                    
            # Schedule next update for smooth real-time display
            self.root.after(33, self._update_video_display)  # ~30 FPS
                    
        except Exception as e:
            print(f"❌ Video display error: {e}")
            # Continue updating even on error
            self.root.after(100, self._update_video_display)
    
    def _add_detection_overlays(self, frame):
        """Add detection overlays to the frame"""
        try:
            # Face recognition using authentication system
            if self.auth_system and hasattr(self, 'latest_face_detections'):
                recognized_user, confidence, face_location = self.auth_system.recognize_face(frame)
                
                if recognized_user and len(face_location) > 0:
                    # Draw bounding box for recognized user
                    top, right, bottom, left = face_location
                    
                    # Choose color based on user role
                    if recognized_user.role == "admin":
                        color = (255, 0, 0)  # Blue for admin
                        role_text = "👑 ADMIN"
                    elif recognized_user.role == "family":
                        color = (0, 255, 0)  # Green for family
                        role_text = "👨‍👩‍👧‍👦 FAMILY"
                    else:
                        color = (0, 255, 255)  # Yellow for regular user
                        role_text = "👤 USER"
                    
                    # Draw main bounding box
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
                    
                    # Prepare label text
                    main_label = f"{recognized_user.name}"
                    conf_label = f"Confidence: {confidence:.2f}"
                    
                    # Draw label background
                    label_height = 60
                    cv2.rectangle(frame, (left, top - label_height), (right, top), color, -1)
                    
                    # Draw user name
                    cv2.putText(frame, main_label, (left + 5, top - 35), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    # Draw role
                    cv2.putText(frame, role_text, (left + 5, top - 15), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    
                    # Draw confidence
                    cv2.putText(frame, conf_label, (left + 5, top - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
                    
                    # Update current user
                    if self.current_user != recognized_user:
                        self.current_user = recognized_user
                        # Update UI on main thread
                        self.root.after(0, self._update_current_user_display)
                        print(f"👋 User recognized: {recognized_user.name} ({recognized_user.role})")
            
            # Add traditional face detection boxes if no user recognized
            if hasattr(self, 'latest_face_detections') and self.latest_face_detections:
                for detection in self.latest_face_detections:
                    if hasattr(detection, 'bounding_box') and detection.bounding_box:
                        x, y = int(detection.bounding_box.x), int(detection.bounding_box.y)
                        w, h = int(detection.bounding_box.width), int(detection.bounding_box.height)
                        
                        # Only show if not already shown by face recognition
                        if not (self.current_user and len(face_location) > 0):
                            color = (0, 0, 255)  # Red for unrecognized
                            label = "Unknown Person"
                            
                            # Draw bounding box
                            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                            
                            # Draw label
                            cv2.rectangle(frame, (x, y - 25), (x + len(label) * 10, y), color, -1)
                            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            return frame
        except Exception as e:
            print(f"❌ Detection overlay error: {e}")
            return frame
    
    def _add_info_overlays(self, frame):
        """Add information overlays to the frame"""
        try:
            height, width = frame.shape[:2]
            
            # Add timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, timestamp, (10, height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Add FPS counter
            fps_text = f"FPS: {self.fps:.1f}"
            cv2.putText(frame, fps_text, (width - 100, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Add recording indicator
            if self.is_recording:
                cv2.circle(frame, (width - 25, 50), 8, (0, 0, 255), -1)
                cv2.putText(frame, "REC", (width - 50, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            
            # Add detection status
            if self.detection_enabled:
                status_text = "AI Detection: ON"
                cv2.putText(frame, status_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            return frame
        except Exception as e:
            print(f"❌ Info overlay error: {e}")
            return frame
    
    def _update_statistics(self):
        """Update statistics display"""
        try:
            # Update FPS
            self.fps_label.configure(text=f"FPS: {self.fps:.1f}")
            
            # Update detections
            self.detections_label.configure(text=f"Detections: {self.stats['detections_made']}")
            
            # Update frames
            self.frames_label.configure(text=f"Frames: {self.stats['frames_processed']}")
            
            # Update uptime
            if self.stats["session_start"]:
                uptime = time.time() - self.stats["session_start"]
                hours = int(uptime // 3600)
                minutes = int((uptime % 3600) // 60)
                seconds = int(uptime % 60)
                self.uptime_label.configure(text=f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
                
        except Exception as e:
            print(f"❌ Statistics update error: {e}")
    
    def _update_time(self):
        """Update current time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.current_time.configure(text=current_time)
        self.root.after(1000, self._update_time)
    
    def _on_camera_selected(self, selection):
        """Handle camera selection change"""
        print(f"📹 Camera selected: {selection}")
        # TODO: Implement camera switching
    
    def _on_resolution_selected(self, selection):
        """Handle resolution change"""
        print(f"🖥️ Resolution selected: {selection}")
        # TODO: Implement resolution changing
    
    def _take_snapshot(self):
        """Take a snapshot of current frame"""
        try:
            if self.current_frame is not None:
                # Create snapshots directory
                snapshots_dir = Path("snapshots")
                snapshots_dir.mkdir(exist_ok=True)
                
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_path = snapshots_dir / f"guardia_snapshot_{timestamp}.jpg"
                
                # Save image
                cv2.imwrite(str(snapshot_path), self.current_frame)
                
                print(f"📸 Snapshot saved: {snapshot_path}")
                messagebox.showinfo("Snapshot Saved", f"Snapshot saved to:\n{snapshot_path}")
            else:
                messagebox.showwarning("Warning", "No frame available to capture")
                
        except Exception as e:
            print(f"❌ Snapshot error: {e}")
            messagebox.showerror("Error", f"Failed to save snapshot:\n{e}")
    
    def _stop_all(self):
        """Stop all operations"""
        if self.is_monitoring:
            self._stop_monitoring()
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.root.attributes('-fullscreen'):
            self.root.attributes('-fullscreen', False)
        else:
            self.root.attributes('-fullscreen', True)
    
    def _open_settings(self):
        """Open settings dialog"""
        # TODO: Implement settings dialog
        messagebox.showinfo("Settings", "Settings dialog will be implemented soon!")
    
    def _show_about(self):
        """Show about dialog"""
        about_text = """
🔥 Guardia AI Desktop Application
Version 2.0.0

Advanced AI-powered surveillance system with:
• Real-time face recognition
• Object detection and tracking
• Multi-camera support
• Smart alerts and notifications
• Modern desktop interface

Built with CustomTkinter and powered by:
• OpenCV for computer vision
• TensorFlow/PyTorch for AI
• Google Cloud AI services
• MongoDB for data storage

© 2025 Guardia AI
        """
        messagebox.showinfo("About Guardia AI", about_text)
    
    def _update_current_user_display(self):
        """Update the current user display in the UI"""
        try:
            if self.current_user:
                user_text = f"Current User: {self.current_user.name} ({self.current_user.role.title()})"
                self.current_user_label.configure(text=user_text)
            else:
                self.current_user_label.configure(text="Current User: None")
        except Exception as e:
            print(f"❌ Error updating user display: {e}")
    
    def _open_user_registration(self):
        """Open user registration dialog"""
        UserRegistrationDialog(self.root, self.auth_system, self._update_current_user_display)
    
    def _open_user_management(self):
        """Open user management dialog"""
        UserManagementDialog(self.root, self.auth_system, self._update_current_user_display)
    
    def run(self):
        """Start the application"""
        print("🚀 Starting Guardia AI Desktop Application...")
        
        # Show startup message
        if not GUARDIA_AVAILABLE:
            startup_msg = "⚠️ Running in LIMITED MODE\n\nAI features are disabled.\nTo enable full functionality:\n\n1. Install dependencies: pip install -r requirements_enhanced.txt\n2. Configure Google Cloud credentials\n3. Restart the application"
            messagebox.showwarning("Limited Mode", startup_msg)
        
        # Start main loop
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n👋 Shutting down gracefully...")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup resources"""
        try:
            if self.is_monitoring:
                self._stop_all()
            print("✅ Cleanup completed")
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

def main():
    """Main entry point"""
    print("🔥 Guardia AI Desktop Application")
    print("=" * 50)
    
    # Check dependencies
    if not CTK_AVAILABLE:
        print("❌ CustomTkinter not available")
        print("Please install: pip install customtkinter pillow")
        return
    
    if not CV2_AVAILABLE:
        print("❌ OpenCV not available")
        print("Please install: pip install opencv-python")
        return
    
    # Create and run application
    try:
        app = GuardiaDesktopApp()
        app.run()
    except Exception as e:
        print(f"❌ Application error: {e}")
        if CTK_AVAILABLE:
            messagebox.showerror("Application Error", f"Failed to start application:\n{e}")

if __name__ == "__main__":
    main()
