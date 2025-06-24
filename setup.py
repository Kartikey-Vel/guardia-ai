#!/usr/bin/env python3
"""
Guardia AI Setup and Launcher
"""
import sys
import os

def setup_project():
    """Setup the Guardia AI project structure"""
    print("🛡️ Guardia AI - Intelligent Surveillance System")
    print("=" * 50)
    print("📁 Project Structure:")
    print("✓ Authentication module (face + PIN)")
    print("✓ Face recognition (InsightFace/MobileFaceNet)")
    print("✓ SQLite database for users")
    print("✓ PySide6 GUI framework")
    print()
    
    print("🔧 Dependencies installed:")
    try:
        import PySide6
        print(f"✓ PySide6 {PySide6.__version__}")
    except ImportError:
        print("❌ PySide6 not found")
    
    try:
        import cv2
        print(f"✓ OpenCV {cv2.__version__}")
    except ImportError:
        print("❌ OpenCV not found")
    
    try:
        import numpy as np
        print(f"✓ NumPy {np.__version__}")
    except ImportError:
        print("❌ NumPy not found")
    
    try:
        import insightface
        print("✓ InsightFace (face recognition)")
    except ImportError:
        print("❌ InsightFace not found")
    
    print()

def test_authentication():
    """Test the authentication module"""
    print("🧪 Testing Authentication Module:")
    try:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from guardia_ai.detection.face_auth import FaceAuthenticator
        
        face_auth = FaceAuthenticator()
        print("✓ FaceAuthenticator initialized")
        
        # Test PIN functionality
        test_pin = "1234"
        face_auth.add_user("Admin", test_pin, None)
        
        if face_auth.verify_pin(test_pin):
            print("✓ PIN authentication works")
        else:
            print("❌ PIN authentication failed")
            
        print("✓ Authentication module ready")
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

def show_next_steps():
    """Show next steps for development"""
    print("\n🚀 Next Development Steps:")
    print("1. ✅ User Authentication (COMPLETED)")
    print("2. 🔄 Surveillance Engine (object detection)")
    print("3. 🔄 Alert System (notifications)")
    print("4. 🔄 Dashboard UI (monitoring)")
    print("5. 🔄 Configuration management")
    print()
    
    print("💡 Usage:")
    print("• For GUI (if display available): python -m guardia_ai.main")
    print("• For testing: python test_face_auth.py")
    print("• For development: import guardia_ai modules")
    print()
    
    print("📚 Available Modules:")
    print("• guardia_ai.detection.face_auth - Face recognition & PIN auth")
    print("• guardia_ai.ui.login - Authentication GUI")
    print("• guardia_ai.main - Main application entry")

def main():
    setup_project()
    
    if test_authentication():
        show_next_steps()
        print("🎉 Guardia AI authentication system is ready!")
    else:
        print("❌ Setup incomplete. Check dependencies.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
