#!/usr/bin/env python3
"""
Test script for Real-Time Face Authentication System
"""

import cv2
import time
from real_time_face_auth import FaceAuthSystem, RealTimeFaceAuthApp

def test_camera():
    """Test camera availability"""
    print("🔍 Testing camera...")
    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print("✅ Camera is working!")
            height, width = frame.shape[:2]
            print(f"📹 Resolution: {width}x{height}")
        else:
            print("❌ Camera cannot capture frames")
    else:
        print("❌ Camera not available")
    cap.release()

def test_face_auth_system():
    """Test face authentication system initialization"""
    print("\n🧠 Testing Face Authentication System...")
    try:
        face_auth = FaceAuthSystem()
        stats = face_auth.get_recognition_stats()
        print(f"✅ Face Auth System initialized")
        print(f"👥 Current users: {stats['total_users']}")
        print(f"🧠 Face encodings: {stats['total_encodings']}")
        return True
    except Exception as e:
        print(f"❌ Face Auth System failed: {e}")
        return False

def demo_mode():
    """Run a quick demo"""
    print("\n🎬 Starting demo mode...")
    print("This will start the real-time face authentication system.")
    print("Controls available:")
    print("  'r' - Start registration mode")
    print("  't' - Start training mode")
    print("  's' - Show statistics")
    print("  'c' - Capture photo (during registration/training)")
    print("  'f' - Finish registration/training")
    print("  'q' - Quit")
    
    input("\nPress Enter to continue or Ctrl+C to cancel...")
    
    try:
        app = RealTimeFaceAuthApp()
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 Demo cancelled")

if __name__ == "__main__":
    print("🔥 Guardia AI - Face Authentication Test")
    print("=" * 40)
    
    # Run tests
    test_camera()
    
    if test_face_auth_system():
        print("\n✅ All tests passed!")
        
        choice = input("\n🎬 Run demo? (y/n): ").lower()
        if choice == 'y':
            demo_mode()
        else:
            print("👋 Test completed. Use 'python3 real_time_face_auth.py' to run the full system.")
    else:
        print("\n❌ Tests failed!")
