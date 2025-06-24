"""
Guardia AI Dashboard - Main Interface After Login
"""
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QMessageBox, QGroupBox, QListWidget, QTextEdit, QFrame, QSplitter,
    QProgressBar, QApplication, QListWidgetItem, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QFont
import cv2
import numpy as np
import time
from datetime import datetime

from ..detection.enhanced_detector import EnhancedDetector

# Import our enhanced detector
from ..detection.enhanced_detector import EnhancedDetector

class FaceMatchingThread(QThread):
    """Background thread for real-time face matching with enhanced detection (faces + objects)"""
    enhanced_results = Signal(object)  # enhanced detection results
    error_occurred = Signal(str)  # error message
    
    def __init__(self, face_auth):
        super().__init__()
        self.face_auth = face_auth
        self.running = False
        self.cap = None
        self.enhanced_detector = None
    
    def run(self):
        try:
            # Initialize camera
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.error_occurred.emit("Camera not accessible")
                return
            
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            # Initialize enhanced detector
            self.enhanced_detector = EnhancedDetector(face_auth=self.face_auth)
            
            self.running = True
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                    
                # Run enhanced detection
                results = self.enhanced_detector.enhanced_detection(frame)
                
                # Emit enhanced results
                self.enhanced_results.emit(results)
                    
                time.sleep(0.1)  # Check every 100ms for smoother feed
                
        except Exception as e:
            self.error_occurred.emit(f"Face matching error: {str(e)}")
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.quit()

class GuardiaDashboard(QWidget):
    # Signal emitted when dashboard is closed
    dashboard_closed = Signal()
    
    def __init__(self, face_auth, logged_in_user=None):
        super().__init__()
        self.face_auth = face_auth
        self.logged_in_user = logged_in_user or "User"
        self.setWindowTitle("🛡️ Guardia AI - Enhanced Security Dashboard")
        self.setGeometry(100, 100, 1400, 900)  # Increased size for enhanced features
        self.face_matching_thread = None
        self.live_analysis_active = False
        self.analysis_logs = []
        self.frame_count = 0  # Initialize frame counter
        self._build_ui()
        self._update_stats()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop any running live analysis
        if self.live_analysis_active:
            self._stop_live_analysis()
        
        # Stop any running face matching thread
        if self.face_matching_thread and self.face_matching_thread.running:
            self.face_matching_thread.stop()
            self.face_matching_thread.wait()
        
        # Clean up any temporary files
        self._cleanup_temp_files()
        
        # Emit signal that dashboard is closing
        self.dashboard_closed.emit()
        
        # Accept the close event
        event.accept()
    
    def _cleanup_temp_files(self):
        """Clean up any temporary files created during operation"""
        import os
        import glob
        
        try:
            # Remove any temporary log files that might be created
            temp_files = glob.glob("guardia_ai_analysis_logs_*.txt")
            for temp_file in temp_files:
                # Only remove files older than 1 hour to keep recent ones
                if os.path.getmtime(temp_file) < time.time() - 3600:
                    os.remove(temp_file)
                    self._add_log(f"🗑️ Cleaned up temp file: {temp_file}")
        except Exception as e:
            # Don't fail on cleanup errors
            pass
    
    def _build_ui(self):
        main_layout = QHBoxLayout()
        
        # Left panel - Navigation and controls
        left_panel = self._create_left_panel()
        
        # Right panel - Content area
        right_panel = self._create_right_panel()
        
        # Add panels to main layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 900])  # Adjusted for larger window
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def _create_left_panel(self):
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Welcome section
        welcome_group = QGroupBox(f"👋 Welcome, {self.logged_in_user}")
        welcome_layout = QVBoxLayout()
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_label = QLabel(f"🕒 {current_time}")
        time_label.setStyleSheet("color: #666; font-size: 12px;")
        
        welcome_layout.addWidget(time_label)
        welcome_group.setLayout(welcome_layout)
        
        # System status with enhanced detection info
        status_group = QGroupBox("📊 Enhanced Detection Status")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("🟢 All systems operational")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
        self.users_count_label = QLabel("👥 Loading users...")
        self.face_users_label = QLabel("📷 Loading face data...")
        
        # Detection capabilities
        self.detection_capabilities = QLabel("🔍 MediaPipe + YOLO + InsightFace")
        self.detection_capabilities.setStyleSheet("color: #9C27B0; font-weight: bold; font-size: 11px;")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.users_count_label)
        status_layout.addWidget(self.face_users_label)
        status_layout.addWidget(self.detection_capabilities)
        status_group.setLayout(status_layout)
        
        # Main features
        features_group = QGroupBox("🚀 Enhanced Features")
        features_layout = QVBoxLayout()
        
        # User Management
        self.enroll_btn = QPushButton("👤 Enroll New User")
        self.enroll_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; } QPushButton:hover { background-color: #45a049; }")
        self.enroll_btn.clicked.connect(self._show_enrollment)
        
        self.manage_users_btn = QPushButton("📋 Manage Users")
        self.manage_users_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; background-color: #2196F3; color: white; border: none; border-radius: 5px; } QPushButton:hover { background-color: #1976D2; }")
        self.manage_users_btn.clicked.connect(self._show_user_management)
        
        # Enhanced Analysis - Primary feature
        self.live_analysis_btn = QPushButton("🔍 Enhanced Analysis (Face + Objects)")
        self.live_analysis_btn.setStyleSheet("QPushButton { padding: 12px; font-size: 15px; background-color: #9C27B0; color: white; border: none; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #7B1FA2; }")
        self.live_analysis_btn.clicked.connect(self._toggle_live_analysis)
        
        # Face Recognition Tools
        self.face_test_btn = QPushButton("🧪 Test Face Recognition")
        self.face_test_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; background-color: #FF9800; color: white; border: none; border-radius: 5px; } QPushButton:hover { background-color: #F57C00; }")
        self.face_test_btn.clicked.connect(self._test_face_recognition)
        
        self.real_time_btn = QPushButton("🎥 Real-time Matching (CLI)")
        self.real_time_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; background-color: #795548; color: white; border: none; border-radius: 5px; } QPushButton:hover { background-color: #5D4037; }")
        self.real_time_btn.clicked.connect(self._launch_real_time_cli)
        
        # Simulation Tools
        self.benchmark_btn = QPushButton("⚡ Performance Benchmark")
        self.benchmark_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; background-color: #795548; color: white; border: none; border-radius: 5px; } QPushButton:hover { background-color: #5D4037; }")
        self.benchmark_btn.clicked.connect(self._run_benchmark)
        
        self.export_btn = QPushButton("💾 Export User Data")
        self.export_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; background-color: #607D8B; color: white; border: none; border-radius: 5px; } QPushButton:hover { background-color: #455A64; }")
        self.export_btn.clicked.connect(self._export_data)
        
        # System Controls
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        
        self.logout_btn = QPushButton("🚪 Logout")
        self.logout_btn.setStyleSheet("QPushButton { padding: 10px; font-size: 14px; background-color: #f44336; color: white; border: none; border-radius: 5px; } QPushButton:hover { background-color: #d32f2f; }")
        self.logout_btn.clicked.connect(self._logout)
        
        # Add all buttons
        features_layout.addWidget(self.enroll_btn)
        features_layout.addWidget(self.manage_users_btn)
        features_layout.addWidget(self.live_analysis_btn)  # Primary feature at top
        features_layout.addWidget(self.face_test_btn)
        features_layout.addWidget(self.real_time_btn)
        features_layout.addWidget(self.benchmark_btn)
        features_layout.addWidget(self.export_btn)
        features_layout.addWidget(separator)
        features_layout.addWidget(self.logout_btn)
        features_group.setLayout(features_layout)
        
        # Add all groups to left layout
        left_layout.addWidget(welcome_group)
        left_layout.addWidget(status_group)
        left_layout.addWidget(features_group)
        left_layout.addStretch()  # Push everything to top
        
        left_widget.setLayout(left_layout)
        return left_widget
    
    def _create_right_panel(self):
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Content area header
        self.content_header = QLabel("🛡️ Enhanced Security Monitoring")
        self.content_header.setStyleSheet("font-size: 26px; font-weight: bold; color: #333; padding: 10px;")
        self.content_header.setAlignment(Qt.AlignCenter)
        
        # Create a splitter for video feed and logs
        content_splitter = QSplitter(Qt.Vertical)
        
        # Top section - Video feed with enhanced visualization
        video_widget = QWidget()
        video_layout = QVBoxLayout()
        
        # Video feed label with enhanced size
        self.video_feed = QLabel("📹 Enhanced Live Video Feed")
        self.video_feed.setMinimumSize(800, 600)  # Larger size for better visibility
        self.video_feed.setStyleSheet("border: 3px solid #9C27B0; background-color: #000; color: white; font-size: 18px;")
        self.video_feed.setAlignment(Qt.AlignCenter)
        self.video_feed.setText("🔍 Enhanced Analysis\n\n• Face Recognition (InsightFace)\n• Face Detection (MediaPipe)\n• Object Detection (YOLOv8)\n\nClick 'Enhanced Analysis' to start monitoring")
        
        # Video controls with enhanced information
        video_controls = QHBoxLayout()
        self.video_status = QLabel("📴 Camera Inactive")
        self.video_status.setStyleSheet("font-weight: bold; color: #666; font-size: 14px;")
        
        self.fps_label = QLabel("FPS: --")
        self.fps_label.setStyleSheet("color: #666; font-size: 14px;")
        
        self.detection_stats = QLabel("Detections: --")
        self.detection_stats.setStyleSheet("color: #9C27B0; font-size: 14px; font-weight: bold;")
        
        video_controls.addWidget(self.video_status)
        video_controls.addStretch()
        video_controls.addWidget(self.detection_stats)
        video_controls.addWidget(self.fps_label)
        
        video_layout.addWidget(self.video_feed)
        video_layout.addLayout(video_controls)
        video_widget.setLayout(video_layout)
        
        # Bottom section - Enhanced analysis logs
        logs_widget = QWidget()
        logs_layout = QVBoxLayout()
        
        logs_header = QLabel("📊 Live Analysis Logs & Threat Detection")
        logs_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; padding: 5px;")
        
        self.analysis_logs_display = QTextEdit()
        self.analysis_logs_display.setMaximumHeight(250)
        self.analysis_logs_display.setReadOnly(True)
        self.analysis_logs_display.setStyleSheet("font-family: monospace; font-size: 12px; background-color: #f8f8f8; border: 1px solid #ddd;")
        
        # Logs controls with enhanced features
        logs_controls = QHBoxLayout()
        self.clear_logs_btn = QPushButton("🗑️ Clear Logs")
        self.clear_logs_btn.setStyleSheet("padding: 5px 10px; font-size: 12px; background-color: #ff5722; color: white; border: none; border-radius: 3px;")
        self.clear_logs_btn.clicked.connect(self._clear_logs)
        
        self.save_logs_btn = QPushButton("💾 Save Logs")
        self.save_logs_btn.setStyleSheet("padding: 5px 10px; font-size: 12px; background-color: #2196F3; color: white; border: none; border-radius: 3px;")
        self.save_logs_btn.clicked.connect(self._save_logs)
        
        self.threat_count_label = QLabel("🚨 Threats: 0")
        self.threat_count_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        
        logs_controls.addWidget(self.clear_logs_btn)
        logs_controls.addWidget(self.save_logs_btn)
        logs_controls.addStretch()
        logs_controls.addWidget(self.threat_count_label)
        
        logs_layout.addWidget(logs_header)
        logs_layout.addWidget(self.analysis_logs_display)
        logs_layout.addLayout(logs_controls)
        logs_widget.setLayout(logs_layout)
        
        # Add to splitter
        content_splitter.addWidget(video_widget)
        content_splitter.addWidget(logs_widget)
        content_splitter.setSizes([500, 250])  # Video takes more space
        
        # Progress bar for operations
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        # Initialize with enhanced welcome message in logs
        self.threat_count = 0
        self._add_log("🛡️ Enhanced Guardia AI Security System")
        self._add_log("=" * 60)
        self._add_log("🔍 Advanced Detection Capabilities:")
        self._add_log("  • Face Recognition: InsightFace (ArcFace)")
        self._add_log("  • Face Detection: MediaPipe + OpenCV")
        self._add_log("  • Object Detection: YOLOv8 (80 classes)")
        self._add_log("📹 Click 'Enhanced Analysis' to start comprehensive monitoring")
        self._add_log("🚨 Threat detection and unknown face alerts enabled")
        self._add_log("📊 Real-time analysis with visual feedback")
        self._add_log("✅ System ready for enhanced operation")
        
        right_layout.addWidget(self.content_header)
        right_layout.addWidget(content_splitter)
        right_layout.addWidget(self.progress_bar)
        
        right_widget.setLayout(right_layout)
        return right_widget
    
    def _add_log(self, message):
        """Add a message to the analysis logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.analysis_logs.append(log_entry)
        
        # Keep only last 100 log entries
        if len(self.analysis_logs) > 100:
            self.analysis_logs = self.analysis_logs[-100:]
        
        # Update display
        if hasattr(self, 'analysis_logs_display'):
            self.analysis_logs_display.append(log_entry)
            # Auto-scroll to bottom
            scrollbar = self.analysis_logs_display.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _clear_logs(self):
        """Clear all analysis logs"""
        self.analysis_logs.clear()
        self.analysis_logs_display.clear()
        self.threat_count = 0
        self._update_threat_count()
        self._add_log("📝 Logs cleared by user")
    
    def _save_logs(self):
        """Save analysis logs to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"guardia_ai_enhanced_analysis_logs_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                f.write("🛡️ Guardia AI - Enhanced Analysis Logs\n")
                f.write("=" * 60 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Threats detected: {self.threat_count}\n")
                f.write("=" * 60 + "\n\n")
                
                for log in self.analysis_logs:
                    f.write(log + "\n")
            
            self._add_log(f"💾 Enhanced logs saved to: {filename}")
            QMessageBox.information(self, "Logs Saved", f"Analysis logs saved to:\n{filename}")
            
        except Exception as e:
            self._add_log(f"❌ Failed to save logs: {str(e)}")
            QMessageBox.critical(self, "Save Error", f"Failed to save logs:\n{str(e)}")
    
    def _convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QPixmap.fromImage(p)
    
    def _toggle_live_analysis(self):
        """Toggle enhanced live analysis with video feed"""
        if self.live_analysis_active:
            self._stop_live_analysis()
        else:
            self._start_live_analysis()
    
    def _start_live_analysis(self):
        """Start enhanced live analysis"""
        try:
            self.live_analysis_active = True
            self.live_analysis_btn.setText("🛑 Stop Enhanced Analysis")
            self.live_analysis_btn.setStyleSheet("QPushButton { padding: 12px; font-size: 15px; background-color: #f44336; color: white; border: none; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #d32f2f; }")
            
            self.video_status.setText("🔴 Enhanced Analysis Active (Face + Object Detection)")
            self.video_status.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 14px;")
            
            self._add_log("🚀 Starting enhanced analysis...")
            self._add_log("📹 Camera initializing...")
            self._add_log("🔧 Loading MediaPipe Face Detection...")
            self._add_log("🔧 Loading YOLOv8 Object Detection...")
            self._add_log("🔧 Loading InsightFace Recognition...")
            
            # Create and start enhanced face matching thread
            self.face_matching_thread = FaceMatchingThread(self.face_auth)
            self.face_matching_thread.enhanced_results.connect(self._on_enhanced_results)
            self.face_matching_thread.error_occurred.connect(self._on_analysis_error)
            self.face_matching_thread.start()
            
            # Start FPS timer
            self.fps_timer = QTimer()
            self.fps_timer.timeout.connect(self._update_fps)
            self.fps_timer.start(1000)  # Update every second
            self.frame_count = 0
            self.fps_start_time = time.time()
            
            self._add_log("✅ Enhanced analysis started successfully")
            
        except Exception as e:
            self._add_log(f"❌ Failed to start enhanced analysis: {str(e)}")
            QMessageBox.critical(self, "Camera Error", f"Failed to start enhanced analysis:\n{str(e)}")
    
    def _stop_live_analysis(self):
        """Stop enhanced live analysis"""
        self.live_analysis_active = False
        self.live_analysis_btn.setText("🔍 Enhanced Analysis (Face + Objects)")
        self.live_analysis_btn.setStyleSheet("QPushButton { padding: 12px; font-size: 15px; background-color: #9C27B0; color: white; border: none; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #7B1FA2; }")
        
        self.video_status.setText("📴 Camera Inactive")
        self.video_status.setStyleSheet("font-weight: bold; color: #666; font-size: 14px;")
        self.fps_label.setText("FPS: --")
        self.detection_stats.setText("Detections: --")
        
        if self.face_matching_thread:
            self.face_matching_thread.stop()
            self.face_matching_thread.wait()
            self.face_matching_thread = None
        
        if hasattr(self, 'fps_timer'):
            self.fps_timer.stop()
        
        # Reset video feed
        self.video_feed.clear()
        self.video_feed.setText("🔍 Enhanced Analysis\n\n• Face Recognition (InsightFace)\n• Face Detection (MediaPipe)\n• Object Detection (YOLOv8)\n\nClick 'Enhanced Analysis' to start monitoring")
        
        self._add_log("🛑 Enhanced analysis stopped")
    
    def _on_enhanced_results(self, results):
        """Handle enhanced analysis results with faces and objects"""
        self.frame_count += 1
        
        # Use the annotated frame from the enhanced detector
        annotated_frame = results['frame']
        
        # Update video feed
        pixmap = self._convert_cv_qt(annotated_frame)
        self.video_feed.setPixmap(pixmap)
        
        # Process and log the results
        face_count = results['face_count']
        object_count = results['object_count']
        known_faces = len(results['known_faces'])
        unknown_faces = len(results['unknown_faces'])
        threats = len(results['threats'])
        
        # Update detection stats display
        self.detection_stats.setText(f"Faces: {face_count} | Objects: {object_count}")
        
        # Update threat count
        if threats > 0:
            self.threat_count += threats
            self._update_threat_count()
        
        # Log detections (not every frame to avoid spam)
        if self.frame_count % 30 == 0:  # Log every 30 frames
            summary = f"👁️ Frame {self.frame_count}: {face_count} faces ({known_faces} known, {unknown_faces} unknown), {object_count} objects"
            if threats > 0:
                summary += f", ⚠️ {threats} threats detected!"
            self._add_log(summary)
        
        # Log significant events
        for face in results['known_faces']:
            confidence_percent = face['confidence'] * 100
            if confidence_percent > 70:
                self._add_log(f"✅ RECOGNIZED: {face['identity']} (confidence: {confidence_percent:.1f}%)")
            else:
                self._add_log(f"⚠️ LOW CONFIDENCE: {face['identity']} (confidence: {confidence_percent:.1f}%)")
        
        # Log unknown faces
        if unknown_faces > 0 and self.frame_count % 60 == 0:  # Log unknown faces every 60 frames
            self._add_log(f"👤 UNKNOWN: {unknown_faces} unrecognized face(s) detected")
        
        # Log threats immediately
        for threat in results['threats']:
            if threat['type'] == 'unknown_face':
                self._add_log(f"🚨 THREAT: Unknown face detected (confidence: {threat['confidence']*100:.1f}%)")
            elif threat['type'] == 'suspicious_object':
                self._add_log(f"🚨 THREAT: Suspicious object detected - {threat['class']} (confidence: {threat['confidence']*100:.1f}%)")
        
        # Log interesting objects (occasionally)
        if object_count > 0 and self.frame_count % 90 == 0:  # Log objects every 90 frames
            object_list = [obj['class'] for obj in results['objects']]
            unique_objects = list(set(object_list))
            self._add_log(f"🔍 OBJECTS: {', '.join(unique_objects)}")
    
    def _update_threat_count(self):
        """Update threat count display"""
        self.threat_count_label.setText(f"🚨 Threats: {self.threat_count}")
        if self.threat_count > 0:
            self.threat_count_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px; background-color: #ffebee; padding: 2px 5px; border-radius: 3px;")
        else:
            self.threat_count_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
    
    def _on_analysis_error(self, error_message):
        """Handle analysis errors"""
        self._add_log(f"❌ ERROR: {error_message}")
        self._stop_live_analysis()
        QMessageBox.critical(self, "Analysis Error", error_message)
    
    def _update_fps(self):
        """Update FPS display"""
        if hasattr(self, 'fps_start_time'):
            elapsed = time.time() - self.fps_start_time
            if elapsed > 0:
                fps = self.frame_count / elapsed
                self.fps_label.setText(f"FPS: {fps:.1f}")
                
    def _update_stats(self):
        """Update system statistics"""
        try:
            stats = self.face_auth.get_embedding_stats()
            users = self.face_auth.get_all_users()
            
            self.users_count_label.setText(f"👥 Total Users: {stats['total_users']}")
            self.face_users_label.setText(f"📷 Users with Faces: {stats['users_with_faces']}")
            
        except Exception as e:
            self.status_label.setText(f"🔴 System Error: {str(e)}")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def _show_enrollment(self):
        """Show enrollment interface"""
        self.content_header.setText("👤 User Enrollment")
        self._add_log("🎯 User enrollment feature accessed")
        self._add_log("📝 Launching enrollment interface...")
        self._launch_enrollment_cli()
    
    def _show_user_management(self):
        """Show user management interface"""
        self.content_header.setText("📋 User Management")
        
        try:
            users = self.face_auth.get_all_users()
            stats = self.face_auth.get_embedding_stats()
            
            self._add_log("📋 User Management Dashboard accessed")
            self._add_log(f"📈 Statistics: {stats['total_users']} total users, {stats['users_with_faces']} with faces")
            
            for i, user in enumerate(users, 1):
                face_status = "Face" if user["has_face"] else "PIN-only"
                self._add_log(f"👤 {i}. {user['label']} (ID: {user['id']}) - {face_status}")
            
        except Exception as e:
            self._add_log(f"❌ Error loading user data: {str(e)}")
    
    def _test_face_recognition(self):
        """Test face recognition"""
        self.content_header.setText("🧪 Face Recognition Test")
        self._add_log("🧪 Face recognition test accessed")
        self._add_log("🚀 Launching face recognition test...")
        self._launch_face_test_cli()
    
    def _run_benchmark(self):
        """Run performance benchmark"""
        self.content_header.setText("⚡ Performance Benchmark")
        self._add_log("⚡ Performance benchmark accessed")
        self._add_log("🚀 Launching benchmark suite...")
        self._launch_benchmark_cli()
    
    def _export_data(self):
        """Export user data"""
        self.content_header.setText("💾 Data Export")
        
        try:
            self._add_log("💾 Starting data export...")
            filename = self.face_auth.export_to_json()
            self._add_log(f"✅ Export successful: {filename}")
            
            QMessageBox.information(self, "Export Complete", 
                                   f"User data exported successfully to:\n{filename}")
            
        except Exception as e:
            self._add_log(f"❌ Export failed: {str(e)}")
            QMessageBox.critical(self, "Export Error", f"Failed to export data:\n{str(e)}")
    
    def _logout(self):
        """Logout and return to login screen"""
        reply = QMessageBox.question(self, "Logout", 
                                    "Are you sure you want to logout?",
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Stop any running processes
            if self.live_analysis_active:
                self._stop_live_analysis()
            
            self._add_log("🚪 User logged out")
            
            # Close the dashboard
            self.close()
    
    # CLI launcher methods
    def _launch_enrollment_cli(self):
        """Launch face enrollment CLI"""
        self._add_log("🚀 Launching enrollment CLI tool...")
        
        QMessageBox.information(self, "Launching Enrollment", 
                               "Face enrollment will open in a new window.\n\n"
                               "Follow the on-screen instructions:\n"
                               "1. Enter user name\n"
                               "2. Position face in camera\n"
                               "3. Press SPACE to capture")
        
        import subprocess
        import os
        try:
            # Launch the CLI tool
            cmd = "cd /home/codernotme/Documents/GitHub/guardia-ai && source .venv/bin/activate && python face_enrollment.py"
            subprocess.Popen(cmd, shell=True)
            self._add_log("✅ Enrollment CLI launched successfully")
        except Exception as e:
            self._add_log(f"❌ Failed to launch enrollment CLI: {str(e)}")
            QMessageBox.critical(self, "Launch Error", f"Failed to launch enrollment:\n{str(e)}")
    
    def _launch_face_test_cli(self):
        """Launch face test CLI"""
        self._add_log("🚀 Launching face test CLI tool...")
        
        QMessageBox.information(self, "Launching Face Test", 
                               "Face recognition test will open in a new window.\n\n"
                               "Instructions:\n"
                               "• Position face in camera\n"
                               "• Press 'R' to test recognition\n"
                               "• Press 'Q' to quit")
        
        import subprocess
        try:
            cmd = "cd /home/codernotme/Documents/GitHub/guardia-ai && source .venv/bin/activate && python face_enrollment.py --test"
            subprocess.Popen(cmd, shell=True)
            self._add_log("✅ Face test CLI launched successfully")
        except Exception as e:
            self._add_log(f"❌ Failed to launch face test CLI: {str(e)}")
            QMessageBox.critical(self, "Launch Error", f"Failed to launch face test:\n{str(e)}")
    
    def _launch_real_time_cli(self):
        """Launch real-time matching CLI"""
        self._add_log("🚀 Launching real-time matching CLI tool...")
        
        QMessageBox.information(self, "Launching Real-time Matching", 
                               "Real-time face matching will open in a new window.\n\n"
                               "The system will continuously monitor for faces\n"
                               "and display recognition results in real-time.")
        
        import subprocess
        try:
            cmd = "cd /home/codernotme/Documents/GitHub/guardia-ai && source .venv/bin/activate && echo '1' | python face_match_sim.py"
            subprocess.Popen(cmd, shell=True)
            self._add_log("✅ Real-time matching CLI launched successfully")
        except Exception as e:
            self._add_log(f"❌ Failed to launch real-time matching CLI: {str(e)}")
            QMessageBox.critical(self, "Launch Error", f"Failed to launch real-time matching:\n{str(e)}")
    
    def _launch_benchmark_cli(self):
        """Launch benchmark CLI"""
        self._add_log("🚀 Launching performance benchmark CLI tool...")
        
        QMessageBox.information(self, "Launching Benchmark", 
                               "Performance benchmark will open in a new window.\n\n"
                               "This will test system performance and display\n"
                               "detailed metrics about face recognition speed.")
        
        import subprocess
        try:
            cmd = "cd /home/codernotme/Documents/GitHub/guardia-ai && source .venv/bin/activate && echo '3' | python face_match_sim.py"
            subprocess.Popen(cmd, shell=True)
            self._add_log("✅ Benchmark CLI launched successfully")
        except Exception as e:
            self._add_log(f"❌ Failed to launch benchmark CLI: {str(e)}")
            QMessageBox.critical(self, "Launch Error", f"Failed to launch benchmark:\n{str(e)}")

def main():
    """Test the enhanced dashboard"""
    app = QApplication([])
    
    # Import the face auth
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from guardia_ai.detection.face_auth import FaceAuthenticator
    
    face_auth = FaceAuthenticator()
    dashboard = GuardiaDashboard(face_auth, "Test User")
    dashboard.show()
    
    app.exec()

if __name__ == "__main__":
    main()
