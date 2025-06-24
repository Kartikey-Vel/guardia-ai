"""
Guardia AI Enhanced Main Entry Point
Includes face recognition, object detection, and threat assessment
"""
import sys
import os

# Fix Qt plugin conflicts before importing any Qt-related modules
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = ''
os.environ['QT_PLUGIN_PATH'] = ''

# Prefer system Qt over OpenCV's bundled Qt
if 'QT_QPA_PLATFORM' not in os.environ:
    os.environ['QT_QPA_PLATFORM'] = 'xcb'  # or 'wayland' depending on your system

from PySide6.QtWidgets import QApplication
from guardia_ai.detection.face_auth import FaceAuthenticator
from guardia_ai.ui.login import AuthMainWindow

def main():
    print("🛡️ Guardia AI Enhanced Security System")
    print("=" * 50)
    print("✨ Features: Face Recognition + Object Detection + Threat Assessment")
    print("🔍 Technologies: InsightFace, MediaPipe, YOLOv8, OpenCV")
    print("⚡ Capabilities: Infinite Detection, Real-time Analysis")
    print("=" * 50)
    
    try:
        app = QApplication(sys.argv)
        
        print("🔐 Initializing face authentication...")
        face_auth = FaceAuthenticator()
        
        print("🚀 Starting enhanced security interface...")
        main_window = AuthMainWindow(face_auth)
        main_window.show()
        
        print("✅ Guardia AI launched successfully!")
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"❌ GUI Error: {e}")
        print("⚠️ Running in headless mode...")
        # Fallback to test mode
        face_auth = FaceAuthenticator()
        print("✅ Face authentication module loaded successfully")
        print("💡 Use test_dashboard.py for GUI testing")
        print("💡 Use setup.py for system verification")

if __name__ == "__main__":
    main()
