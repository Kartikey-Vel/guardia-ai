"""
Guardia AI Dashboard - Main Interface After Login
"""
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QMessageBox, QGroupBox, QListWidget, QTextEdit, QFrame, QSplitter,
    QProgressBar, QApplication, QListWidgetItem, QScrollArea, QDialog,
    QComboBox, QLineEdit, QDialogButtonBox, QFormLayout, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QPainter, QPen, QFont
import cv2
import numpy as np
import time
import json
from datetime import datetime

from ..detection.enhanced_detector import EnhancedDetector
from ..detection.camera_manager import camera_manager
from ..detection.camera_web_server import CameraWebServer
import traceback

class FaceMatchingThread(QThread):
    """Background thread for real-time face matching with enhanced detection (faces + objects)"""
    enhanced_results = Signal(object)  # enhanced detection results
    error_occurred = Signal(str)  # error message
    
    def __init__(self, face_auth):
        super().__init__()
        self.face_auth = face_auth
        self.running = False
        self.enhanced_detector = None
    
    def run(self):
        try:
            # Initialize enhanced detector
            self.enhanced_detector = EnhancedDetector(face_auth=self.face_auth)
            
            self.running = True
            while self.running:
                # Get frame from camera manager instead of direct camera access
                frame = camera_manager.get_active_frame()
                if frame is None:
                    time.sleep(0.1)
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
        self.quit()

class GuardiaDashboard(QWidget):
    # Signal emitted when dashboard is closed
    dashboard_closed = Signal()
    
    def __init__(self, face_auth, logged_in_user=None):
        super().__init__()
        self.face_auth = face_auth
        self.logged_in_user = logged_in_user or "User"
        self.setWindowTitle("🛡️ Guardia AI - Security Dashboard")
        self.setGeometry(100, 100, 1200, 800)
        self.face_matching_thread = None
        self.live_analysis_active = False
        self.analysis_logs = []
        self.frame_count = 0
        
        # Initialize camera manager with default webcam if no cameras are configured
        self._initialize_cameras()
        
        self._build_ui()
        self._update_stats()
        
        # Start detection automatically
        self._start_live_analysis()
    
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
        # Apply enhanced modern dark theme with better visibility
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                font-family: 'Segoe UI', 'Roboto', 'Ubuntu', sans-serif;
                font-size: 13px;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                color: #ffffff;
                border: 2px solid #00d4ff;
                border-radius: 12px;
                margin: 8px;
                padding-top: 18px;
                background-color: #2d2d2d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #00d4ff;
                font-weight: bold;
                font-size: 15px;
            }
            QLabel {
                color: #ffffff;
                padding: 4px;
            }
            QTextEdit {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 8px;
                padding: 10px;
                color: #ffffff;
                selection-background-color: #0078d4;
                font-family: 'Consolas', 'Monaco', monospace;
            }
            QListWidget {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 8px;
                color: #ffffff;
                selection-background-color: #0078d4;
                alternate-background-color: #333333;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #404040;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #404040;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                color: #ffffff;
                padding: 12px 16px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        
        main_layout = QHBoxLayout()
        
        # Left panel - Navigation and controls
        left_panel = self._create_left_panel()
        
        # Right panel - Content area
        right_panel = self._create_right_panel()
        
        # Add panels to main layout with enhanced splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([380, 920])  # Optimized for better visibility
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #00d4ff;
                width: 4px;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #00a8cc;
            }
        """)
        
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
        features_group = QGroupBox("🚀 Security Features")
        features_layout = QVBoxLayout()
        
        # User Management
        self.enroll_btn = QPushButton("👤 Enroll New User")
        self.enroll_btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4CAF50, stop:1 #45a049);
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 14px; 
                font-size: 14px; 
                font-weight: bold;
                min-height: 20px;
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5CBF60, stop:1 #4CAF50);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d8b40, stop:1 #357a38);
            }
        """)
        self.enroll_btn.clicked.connect(self._show_enrollment)
        
        self.manage_users_btn = QPushButton("📋 Manage Users")
        self.manage_users_btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2);
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 14px; 
                font-size: 14px; 
                font-weight: bold;
                min-height: 20px;
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #42A5F5, stop:1 #2196F3);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1565C0, stop:1 #0D47A1);
            }
        """)
        self.manage_users_btn.clicked.connect(self._show_user_management)
        
        # Camera Management buttons
        self.camera_management_btn = QPushButton("📹 Camera Management")
        self.camera_management_btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FF9800, stop:1 #F57C00);
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 14px; 
                font-size: 14px; 
                font-weight: bold;
                min-height: 20px;
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFB74D, stop:1 #FF9800);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E65100, stop:1 #BF360C);
            }
        """)
        self.camera_management_btn.clicked.connect(self._show_camera_management)
        
        self.qr_connection_btn = QPushButton("📱 Smart Camera Setup")
        self.qr_connection_btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #9C27B0, stop:1 #7B1FA2);
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 14px; 
                font-size: 14px; 
                font-weight: bold;
                min-height: 20px;
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #BA68C8, stop:1 #9C27B0);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6A1B9A, stop:1 #4A148C);
            }
        """)
        self.qr_connection_btn.clicked.connect(self._show_qr_connection)
        
        # Detection Control
        self.live_analysis_btn = QPushButton("⏹ Stop Detection")
        self.live_analysis_btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f44336, stop:1 #d32f2f);
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 16px; 
                font-size: 15px; 
                font-weight: bold;
                min-height: 24px;
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F57C7C, stop:1 #f44336);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #C62828, stop:1 #B71C1C);
            }
        """)
        self.live_analysis_btn.clicked.connect(self._toggle_live_analysis)
        
        # Export
        self.export_btn = QPushButton("💾 Export User Data")
        self.export_btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #607D8B, stop:1 #455A64);
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 14px; 
                font-size: 14px; 
                font-weight: bold;
                min-height: 20px;
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #78909C, stop:1 #607D8B);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #37474F, stop:1 #263238);
            }
        """)
        self.export_btn.clicked.connect(self._export_data)
        
        # System Controls
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("QFrame { color: #404040; background-color: #404040; margin: 10px 0; }")
        
        self.logout_btn = QPushButton("🚪 Logout")
        self.logout_btn.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f44336, stop:1 #d32f2f);
                color: white; 
                border: none; 
                border-radius: 10px; 
                padding: 14px; 
                font-size: 14px; 
                font-weight: bold;
                min-height: 20px;
            } 
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #F57C7C, stop:1 #f44336);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #C62828, stop:1 #B71C1C);
            }
        """)
        self.logout_btn.clicked.connect(self._logout)
        
        # Add essential buttons only
        features_layout.addWidget(self.enroll_btn)
        features_layout.addWidget(self.manage_users_btn)
        features_layout.addWidget(self.camera_management_btn)  # New camera management
        features_layout.addWidget(self.qr_connection_btn)      # New QR setup
        features_layout.addWidget(self.live_analysis_btn)      # Detection control
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
        self.content_header = QLabel("🛡️ Live Security Monitoring")
        self.content_header.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; padding: 10px;")
        self.content_header.setAlignment(Qt.AlignCenter)
        
        # Create a splitter for video feed and logs
        content_splitter = QSplitter(Qt.Vertical)
        
        # Top section - Video feed
        video_widget = QWidget()
        video_layout = QVBoxLayout()
        
        # Video feed label
        self.video_feed = QLabel("📹 Live Camera Feed")
        self.video_feed.setMinimumSize(700, 500)
        self.video_feed.setStyleSheet("""
            border: 3px solid #00d4ff; 
            background-color: #1a1a1a; 
            color: #e0e0e0; 
            font-size: 16px;
            border-radius: 12px;
            padding: 20px;
        """)
        self.video_feed.setAlignment(Qt.AlignCenter)
        self.video_feed.setText("🔍 AI Detection Active\n\n• Face Recognition\n• Object Detection\n• Threat Analysis\n\nCamera initializing...")
        
        # Video controls
        video_controls = QHBoxLayout()
        self.video_status = QLabel("� Detection Active")
        self.video_status.setStyleSheet("""
            font-weight: bold; 
            color: #4CAF50; 
            font-size: 14px;
            background-color: #2d2d2d;
            padding: 6px 10px;
            border-radius: 6px;
            border: 2px solid #404040;
        """)
        
        self.fps_label = QLabel("FPS: --")
        self.fps_label.setStyleSheet("""
            color: #e0e0e0; 
            font-size: 14px;
            background-color: #2d2d2d;
            padding: 6px 10px;
            border-radius: 6px;
            border: 2px solid #404040;
        """)
        
        self.detection_stats = QLabel("Detections: --")
        self.detection_stats.setStyleSheet("""
            color: #9C27B0; 
            font-size: 14px; 
            font-weight: bold;
            background-color: #2d2d2d;
            padding: 6px 10px;
            border-radius: 6px;
            border: 2px solid #404040;
        """)
        
        video_controls.addWidget(self.video_status)
        video_controls.addStretch()
        video_controls.addWidget(self.detection_stats)
        video_controls.addWidget(self.fps_label)
        
        video_layout.addWidget(self.video_feed)
        video_layout.addLayout(video_controls)
        video_widget.setLayout(video_layout)
        
        # Bottom section - Detection logs
        logs_widget = QWidget()
        logs_layout = QVBoxLayout()
        
        logs_header = QLabel("📊 Detection & Alert Logs")
        logs_header.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            color: #00d4ff; 
            padding: 8px;
            background-color: #2d2d2d;
            border-radius: 6px;
            margin-bottom: 5px;
        """)
        
        self.analysis_logs_display = QTextEdit()
        self.analysis_logs_display.setMaximumHeight(200)
        self.analysis_logs_display.setReadOnly(True)
        self.analysis_logs_display.setStyleSheet("""
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
            font-size: 13px; 
            background-color: #1e1e1e; 
            color: #e0e0e0; 
            border: 2px solid #404040;
            border-radius: 8px;
            padding: 10px;
            selection-background-color: #0078d4;
            selection-color: #ffffff;
        """)
        
        # Logs controls with enhanced features
        logs_controls = QHBoxLayout()
        self.clear_logs_btn = QPushButton("🗑️ Clear Logs")
        self.clear_logs_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f44336, stop:1 #d32f2f);
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 10px 16px; 
                font-size: 13px; 
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f66356, stop:1 #e53935);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #c62828, stop:1 #b71c1c);
            }
        """)
        self.clear_logs_btn.clicked.connect(self._clear_logs)
        
        self.save_logs_btn = QPushButton("💾 Save Logs")
        self.save_logs_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2196F3, stop:1 #1976D2);
                color: white; 
                border: none; 
                border-radius: 8px; 
                padding: 10px 16px; 
                font-size: 13px; 
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #42A5F5, stop:1 #1E88E5);
            }
            QPushButton:pressed { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1565C0, stop:1 #0D47A1);
            }
        """)
        self.save_logs_btn.clicked.connect(self._save_logs)
        
        self.threat_count_label = QLabel("🚨 Threats: 0")
        self.threat_count_label.setStyleSheet("""
            color: #4CAF50; 
            font-weight: bold; 
            font-size: 14px;
            background-color: #2d2d2d;
            padding: 8px 12px;
            border-radius: 6px;
            border: 2px solid #404040;
        """)
        
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
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #404040;
                border-radius: 8px;
                text-align: center;
                background-color: #2d2d2d;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4ff, stop:1 #0078d4);
                border-radius: 6px;
                margin: 2px;
            }
        """)
        
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
        """Start live analysis"""
        try:
            self.live_analysis_active = True
            self.live_analysis_btn.setText("🛑 Stop Detection")
            self.live_analysis_btn.setStyleSheet("QPushButton { padding: 12px; font-size: 15px; background-color: #f44336; color: white; border: none; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #d32f2f; }")
            
            self.video_status.setText("� Detection Active")
            self.video_status.setStyleSheet("""
                font-weight: bold; 
                color: #4CAF50; 
                font-size: 14px;
                background-color: #2d2d2d;
                padding: 6px 10px;
                border-radius: 6px;
                border: 2px solid #404040;
            """)
            
            self._add_log("🚀 Starting AI detection system...")
            self._add_log("📹 Camera initializing...")
            self._add_log("🔧 Loading face detection models...")
            self._add_log("🔧 Loading object detection models...")
            
            # Create and start face matching thread
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
        """Stop live analysis"""
        self.live_analysis_active = False
        self.live_analysis_btn.setText("🔍 Start Detection")
        self.live_analysis_btn.setStyleSheet("QPushButton { padding: 12px; font-size: 15px; background-color: #4CAF50; color: white; border: none; border-radius: 5px; font-weight: bold; } QPushButton:hover { background-color: #45a049; }")
        
        self.video_status.setText("� Detection Stopped")
        self.video_status.setStyleSheet("""
            font-weight: bold; 
            color: #ff9800; 
            font-size: 14px;
            background-color: #2d2d2d;
            padding: 6px 10px;
            border-radius: 6px;
            border: 2px solid #404040;
        """)
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
        self.video_feed.setText("🔍 AI Detection Stopped\n\n• Face Recognition\n• Object Detection\n• Threat Analysis\n\nClick 'Start Detection' to resume monitoring")
        
        self._add_log("🛑 Detection system stopped")
    
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
            
            # Update camera status
            camera_status = camera_manager.get_camera_status()
            active_camera = camera_manager.get_active_camera()
            
            if active_camera:
                camera_info = f"📹 Active: {active_camera.name} ({camera_status['total_cameras']} total)"
            else:
                camera_info = f"📹 No active camera ({camera_status['total_cameras']} total)"
            
            # Update status based on camera availability
            if active_camera and active_camera.is_active:
                self.status_label.setText("🟢 All systems operational")
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                self.status_label.setText("🟡 Camera not available")
                self.status_label.setStyleSheet("color: orange; font-weight: bold;")
            
            # Update detection capabilities with camera info
            self.detection_capabilities.setText(f"🔍 MediaPipe + YOLO + InsightFace | {camera_info}")
            
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
    
    def _show_camera_management(self):
        """Show camera management interface"""
        dialog = CameraManagementDialog(self)
        dialog.exec()
    
    def _show_qr_connection(self):
        """Show QR camera setup interface"""
        self.content_header.setText("📱 QR Camera Setup")
        self._add_log("📱 QR camera setup feature accessed")
        
        try:
            dialog = QRConnectionDialog(self)
            dialog.exec()
        except Exception as e:
            self._add_log(f"❌ Error launching QR setup: {str(e)}")
    
    def _export_data(self):
        """Export user data to JSON file"""
        try:
            from PySide6.QtWidgets import QFileDialog
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"guardia_ai_export_{timestamp}.json"
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export User Data",
                default_filename,
                "JSON Files (*.json);;All Files (*)"
            )
            
            if filename:
                success = self.face_auth.export_to_json(filename)
                if success:
                    self._add_log(f"✅ User data exported successfully to: {filename}")
                    QMessageBox.information(self, "Export Success", f"Data exported to:\n{filename}")
                else:
                    self._add_log(f"❌ Failed to export user data")
                    QMessageBox.critical(self, "Export Failed", "Failed to export user data")
            else:
                self._add_log("📝 Export cancelled by user")
                
        except Exception as e:
            error_msg = f"❌ Export error: {str(e)}"
            self._add_log(error_msg)
            QMessageBox.critical(self, "Export Error", error_msg)
    
    def _logout(self):
        """Handle logout action"""
        reply = QMessageBox.question(
            self,
            "Logout Confirmation",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._add_log("🚪 User logged out")
            
            # Stop live analysis if running
            if self.live_analysis_active:
                self._stop_live_analysis()
            
            # Close dashboard and return to login
            self.close()
    
    def _launch_enrollment_cli(self):
        """Launch enrollment CLI in a separate process"""
        import subprocess
        import sys
        import os
        
        try:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            script_path = os.path.join(project_root, "face_enrollment.py")
            
            if os.path.exists(script_path):
                # Launch the enrollment script
                subprocess.Popen([sys.executable, script_path], cwd=project_root)
                self._add_log("✅ Enrollment interface launched successfully")
            else:
                self._add_log(f"❌ Enrollment script not found at: {script_path}")
                
        except Exception as e:
            self._add_log(f"❌ Failed to launch enrollment interface: {str(e)}")

    def _initialize_cameras(self):
        """Initialize camera manager with default cameras if none exist"""
        try:
            # Check if there are any cameras already configured
            if not camera_manager.get_all_cameras():
                # Scan for local webcams and add the first one found
                available_cameras = camera_manager.scan_local_cameras()
                if available_cameras:
                    # Add the first available webcam as default
                    first_cam = available_cameras[0]
                    camera_manager.add_camera(
                        first_cam['source_type'],
                        first_cam['source_path'],
                        first_cam['name'],
                        first_cam['description']
                    )
            
            # Connect to all available cameras
            camera_manager.connect_all_cameras()
            
        except Exception as e:
            print(f"Error initializing cameras: {e}")

class QRConnectionDialog(QDialog):
    """Dialog for QR-based camera setup and connection - CareCam style"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📱 Guardia AI - Smart Camera Setup")
        self.setFixedSize(800, 900)
        self.web_server = None
        self.setup_ui()
        self.start_web_server()

    def setup_ui(self):
        self.setStyleSheet(self.style_sheet())

        layout = QVBoxLayout()

        layout.addWidget(self.build_header())
        layout.addWidget(self.build_instructions())
        layout.addWidget(self.build_qr_frame())
        layout.addWidget(self.build_status_frame())
        layout.addLayout(self.build_buttons())
        layout.addLayout(self.build_close_button())

        self.setLayout(layout)
        self.generate_qr_code()

    def style_sheet(self):
        return """..."""  # Truncated for clarity; use your full QSS

    def build_header(self):
        header = QLabel("📱 Guardia AI Smart Camera Setup")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""...""")  # Full CSS here
        return header

    def build_instructions(self):
        label = QLabel("🔗 <b>Connect Your Smart Camera in 3 Easy Steps:</b><br>..."
                       "<span style='color: #4CAF50;'>✅ Connection is stored permanently...</span>")
        label.setWordWrap(True)
        label.setStyleSheet("""...""")
        return label

    def build_qr_frame(self):
        frame = QWidget()
        layout = QVBoxLayout()

        title = QLabel("📱 Scan This QR Code")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00d4ff; padding: 10px;")
        layout.addWidget(title)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setFixedSize(420, 420)
        self.qr_label.setStyleSheet("border: 3px solid #00d4ff; background-color: white; ...")
        layout.addWidget(self.qr_label)

        frame.setStyleSheet("...")
        frame.setLayout(layout)
        return frame

    def build_status_frame(self):
        frame = QWidget()
        layout = QVBoxLayout()

        title = QLabel("🔗 Connection Status")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00d4ff; padding: 10px;")
        layout.addWidget(title)

        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(120)
        self.info_text.setReadOnly(True)
        layout.addWidget(self.info_text)

        self.connection_progress = QProgressBar()
        self.connection_progress.setRange(0, 100)
        self.connection_progress.setValue(0)
        self.connection_progress.setFormat("Ready to connect cameras")
        layout.addWidget(self.connection_progress)

        frame.setStyleSheet("...")
        frame.setLayout(layout)
        return frame

    def build_buttons(self):
        layout = QHBoxLayout()
        self.regenerate_btn = QPushButton("🔄 New QR Code")
        self.test_server_btn = QPushButton("🧪 Test Connection")
        self.view_cameras_btn = QPushButton("📹 View Connected")

        self.regenerate_btn.clicked.connect(self.generate_qr_code)
        self.test_server_btn.clicked.connect(self.test_web_server)
        self.view_cameras_btn.clicked.connect(self.view_connected_cameras)

        for btn in [self.regenerate_btn, self.test_server_btn, self.view_cameras_btn]:
            btn.setMinimumHeight(40)

        layout.addWidget(self.regenerate_btn)
        layout.addWidget(self.test_server_btn)
        layout.addWidget(self.view_cameras_btn)
        return layout

    def build_close_button(self):
        layout = QHBoxLayout()
        close_btn = QPushButton("✅ Done")
        close_btn.setMinimumHeight(45)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""...""")
        layout.addWidget(close_btn)
        return layout

    def start_web_server(self):
        try:
            self.web_server = CameraWebServer(camera_manager, port=8080)
            if self.web_server.start_server():
                self.log("✅ Smart camera server started on port 8080")
                self.update_progress(25, "Server ready - waiting for cameras")
            else:
                self.log("⚠️ Server already running - ready to accept connections")
                self.update_progress(25)
        except Exception as e:
            self.log(f"❌ Failed to start server:\n{traceback.format_exc()}")
            self.update_progress(0, "Server error")

    def generate_qr_code(self):
        try:
            self.log("🔄 Generating new QR code...")
            self.update_progress(50, "Generating QR code...")

            qr_result = camera_manager.generate_connection_qr("GuardiaAI_Smart_Camera")
            if qr_result and len(qr_result) == 2:
                qr_image, conn_info = qr_result
                pixmap = self.cv_image_to_pixmap(qr_image)
                self.qr_label.setPixmap(pixmap)

                self.info_text.clear()
                self.log(f"📱 Server URL: {conn_info['http_url']}")
                self.log(f"🌐 Network IP: {conn_info['server_ip']}")
                self.log(f"🏷️ Device Name: {conn_info['camera_name']}")
                self.log("📋 QR contains auto-setup information")
                self.log("✅ Ready for camera connection!")

                self.update_progress(75, "Scan QR code with your camera")
            else:
                self.log("❌ Failed to generate QR code")
                self.update_progress(0, "QR generation failed")
        except Exception as e:
            self.log(f"❌ QR generation error:\n{traceback.format_exc()}")
            self.update_progress(0, "Error generating QR")

    def cv_image_to_pixmap(self, image):
        try:
            height, width, channel = image.shape
            bytes_per_line = 3 * width
            qt_image = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
            return QPixmap.fromImage(qt_image).scaled(380, 380, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            self.log("❌ Image conversion failed")
            return QPixmap()

    def test_web_server(self):
        try:
            import requests
            local_ip = camera_manager.get_local_ip()
            test_url = f"http://{local_ip}:8080"

            self.log(f"🧪 Testing server at {test_url}...")
            self.update_progress(None, "Testing connection...")

            response = requests.get(test_url, timeout=5)
            if response.status_code == 200:
                self.log("✅ Web server is accessible and ready!")
                self.update_progress(100, "Server online - ready for connections")
            else:
                self.log(f"⚠️ Server responded with status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            self.log("❌ Cannot connect to web server")
            self.update_progress(0, "Connection failed")
        except requests.exceptions.Timeout:
            self.log("❌ Connection timeout")
            self.update_progress(0, "Connection timeout")
        except Exception:
            self.log(f"❌ Test error:\n{traceback.format_exc()}")

    def view_connected_cameras(self):
        cameras = camera_manager.get_all_cameras()
        self.log("\n📹 Connected Cameras:")
        if cameras:
            for i, cam in enumerate(cameras, 1):
                status = "🟢 Active" if cam.is_active else "🔴 Inactive"
                self.log(f"{i}. {cam.name} - {status}")
        else:
            self.log("📹 No cameras connected yet")
            self.log("👆 Scan the QR code to add your first camera!")

    def log(self, msg):
        self.info_text.append(msg)

    def update_progress(self, value=None, message=None):
        if value is not None:
            self.connection_progress.setValue(value)
        if message:
            self.connection_progress.setFormat(message)

    def closeEvent(self, event):
        # Server remains running intentionally
        event.accept()
class CameraManagementDialog(QDialog):
    """Dialog for managing camera sources"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📹 Camera Management")
        self.setFixedSize(600, 500)
        self.setup_ui()
        self.refresh_camera_list()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("📹 Camera Management")
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Camera list
        self.camera_list = QListWidget()
        self.camera_list.setMinimumHeight(200)
        layout.addWidget(QLabel("Connected Cameras:"))
        layout.addWidget(self.camera_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("🔍 Scan Local")
        self.scan_btn.clicked.connect(self.scan_local_cameras)
        
        self.add_ip_btn = QPushButton("📷 Add IP Camera")
        self.add_ip_btn.clicked.connect(self.add_ip_camera)
        
        self.remove_btn = QPushButton("🗑️ Remove")
        self.remove_btn.clicked.connect(self.remove_camera)
        
        self.set_active_btn = QPushButton("🎯 Set Active")
        self.set_active_btn.clicked.connect(self.set_active_camera)
        
        button_layout.addWidget(self.scan_btn)
        button_layout.addWidget(self.add_ip_btn)
        button_layout.addWidget(self.remove_btn)
        button_layout.addWidget(self.set_active_btn)
        layout.addLayout(button_layout)
        
        # Status area
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.status_text)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def refresh_camera_list(self):
        """Refresh the camera list display"""
        self.camera_list.clear()
        
        cameras = camera_manager.get_all_cameras()
        active_id = camera_manager.active_camera_id
        
        for camera in cameras:
            status_icon = "🟢" if camera.is_active else "🔴"
            active_marker = " (ACTIVE)" if camera.source_id == active_id else ""
            camera_type = {
                'webcam': '💻',
                'ip': '📷',
                'rtsp': '📡'
            }.get(camera.source_type, '📹')
            
            item_text = f"{status_icon} {camera_type} {camera.name}{active_marker}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, camera.source_id)
            self.camera_list.addItem(item)
    
    def scan_local_cameras(self):
        """Scan for local webcams"""
        self.status_text.append("🔍 Scanning for local cameras...")
        
        available = camera_manager.scan_local_cameras()
        added_count = 0
        
        for cam_info in available:
            # Check if camera already exists
            existing = False
            for existing_cam in camera_manager.get_all_cameras():
                if (existing_cam.source_type == cam_info['source_type'] and 
                    existing_cam.source_path == cam_info['source_path']):
                    existing = True
                    break
            
            if not existing:
                source_id, success, message = camera_manager.add_camera(
                    cam_info['source_type'],
                    cam_info['source_path'],
                    cam_info['name'],
                    cam_info['description']
                )
                if success:
                    added_count += 1
                    self.status_text.append(f"✅ Added: {cam_info['name']}")
        
        self.status_text.append(f"📊 Scan complete. Added {added_count} new cameras.")
        self.refresh_camera_list()
    
    def add_ip_camera(self):
        """Add IP camera dialog"""
        dialog = AddIPCameraDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.refresh_camera_list()
    
    def remove_camera(self):
        """Remove selected camera"""
        current_item = self.camera_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a camera to remove.")
            return
        
        camera_id = current_item.data(Qt.UserRole)
        camera_name = current_item.text()
        
        reply = QMessageBox.question(
            self, "Remove Camera",
            f"Are you sure you want to remove {camera_name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if camera_manager.remove_camera(camera_id):
                self.status_text.append(f"🗑️ Removed camera: {camera_name}")
                self.refresh_camera_list()
            else:
                self.status_text.append(f"❌ Failed to remove camera: {camera_name}")
    
    def set_active_camera(self):
        """Set selected camera as active"""
        current_item = self.camera_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a camera to activate.")
            return
        
        camera_id = current_item.data(Qt.UserRole)
        success, message = camera_manager.set_active_camera(camera_id)
        
        if success:
            self.status_text.append(f"🎯 {message}")
            self.refresh_camera_list()
        else:
            self.status_text.append(f"❌ {message}")

class AddIPCameraDialog(QDialog):
    """Dialog for adding IP cameras"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📷 Add IP Camera")
        self.setFixedSize(400, 300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Living Room Camera")
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["IP Camera (HTTP)", "RTSP Stream"])
        
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("http://192.168.1.100:8080/video")
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description")
        
        layout.addRow("Camera Name:", self.name_edit)
        layout.addRow("Camera Type:", self.type_combo)
        layout.addRow("Camera URL:", self.url_edit)
        layout.addRow("Description:", self.description_edit)
        
        # Test button
        test_btn = QPushButton("🧪 Test Connection")
        test_btn.clicked.connect(self.test_connection)
        layout.addRow(test_btn)
        
        # Status
        self.status_label = QLabel("")
        layout.addRow("Status:", self.status_label)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_camera)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)
        
        self.setLayout(layout)
    
    def test_connection(self):
        """Test the camera connection"""
        url = self.url_edit.text().strip()
        if not url:
            self.status_label.setText("❌ Please enter a URL")
            return
        
        self.status_label.setText("🔄 Testing connection...")
        QApplication.processEvents()
        
        success, message = camera_manager.test_ip_camera_url(url)
        
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: red;")
    
    def accept_camera(self):
        """Accept and add the camera"""
        name = self.name_edit.text().strip()
        url = self.url_edit.text().strip()
        description = self.description_edit.text().strip()
        
        if not name or not url:
            QMessageBox.warning(self, "Missing Information", "Please fill in camera name and URL.")
            return
        
        # Determine camera type
        camera_type = "ip" if self.type_combo.currentIndex() == 0 else "rtsp"
        
        # Add camera
        source_id, success, message = camera_manager.add_camera(
            camera_type, url, name, description
        )
        
        if success:
            QMessageBox.information(self, "Success", f"Camera '{name}' added successfully!")
            self.accept()
        else:
            QMessageBox.critical(self, "Error", f"Failed to add camera: {message}")
