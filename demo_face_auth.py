#!/usr/bin/env python3
"""
Guardia AI - Face Authentication Demo
Interactive demonstration of all features
"""

from real_time_face_auth import FaceAuthSystem, RealTimeFaceAuthApp
import time

class FaceAuthDemo:
    def __init__(self):
        self.face_auth = FaceAuthSystem()
        
    def show_welcome(self):
        print("🔥" * 25)
        print("🔥 GUARDIA AI FACE AUTHENTICATION DEMO")
        print("🔥" * 25)
        print()
        print("This demo showcases the advanced face authentication system with:")
        print("✅ Real-time video feed with face detection")
        print("✅ User registration and management")
        print("✅ Family vs Guest role system")
        print("✅ Training mode for improved accuracy")
        print("✅ Statistics and analytics")
        print("✅ Confidence scoring and optimization")
        print()
        
    def show_menu(self):
        print("📋 DEMO MENU")
        print("=" * 30)
        print("1. 🎥 Start Real-Time Face Authentication")
        print("2. 👥 Show User Statistics")
        print("3. 📊 System Information")
        print("4. 🧪 Quick Camera Test")
        print("5. 📖 View Documentation")
        print("6. 🚪 Exit Demo")
        print()
        
    def run_real_time_system(self):
        print("🎥 Starting Real-Time Face Authentication System...")
        print()
        print("🎮 CONTROLS:")
        print("   'r' - Register new user (family/guest)")
        print("   't' - Training mode (add photos to existing user)")
        print("   's' - Show statistics")
        print("   'c' - Capture photo (during registration/training)")
        print("   'f' - Finish registration/training")
        print("   'q' - Quit to menu")
        print()
        print("💡 TIP: Register yourself first by pressing 'r'!")
        print()
        
        input("Press Enter to start the camera...")
        
        try:
            app = RealTimeFaceAuthApp()
            app.run()
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("🔙 Returning to demo menu...")
        
    def show_statistics(self):
        print("📊 SYSTEM STATISTICS")
        print("=" * 30)
        
        stats = self.face_auth.get_recognition_stats()
        
        print(f"👥 Total Users: {stats['total_users']}")
        print(f"👨‍👩‍👧‍👦 Family Members: {stats['family_members']}")
        print(f"👤 Guests: {stats['guests']}")
        print(f"🧠 Face Encodings: {stats['total_encodings']}")
        print(f"🎯 Recognition Events: {stats['total_recognitions']}")
        print()
        
        if stats['total_users'] > 0:
            print("👥 REGISTERED USERS:")
            print("-" * 20)
            for user in self.face_auth.get_users_list():
                role_emoji = "👨‍👩‍👧‍👦" if user.role == "family" else "👤"
                status = "🟢" if user.is_active else "🔴"
                last_seen = user.last_seen[:19] if user.last_seen else "Never"
                print(f"{role_emoji} {user.name} ({user.role}) {status}")
                print(f"   📸 Photos: {user.photo_count}")
                print(f"   👁️ Last seen: {last_seen}")
                print(f"   🎯 Confidence: {user.confidence_threshold}")
                print()
        else:
            print("ℹ️ No users registered yet.")
            print("💡 Use the real-time system to register users!")
        
    def show_system_info(self):
        print("🔧 SYSTEM INFORMATION")
        print("=" * 30)
        print("🐍 Python Libraries:")
        print("   • OpenCV - Camera capture and image processing")
        print("   • face_recognition - Face detection and recognition")
        print("   • NumPy - Numerical computations")
        print("   • JSON - Data persistence")
        print()
        print("📁 Data Storage:")
        print(f"   • User data: {self.face_auth.data_dir}")
        print(f"   • Face photos: {self.face_auth.data_dir}/[username]/")
        print(f"   • User profiles: {self.face_auth.users_file}")
        print(f"   • Training data: {self.face_auth.training_file}")
        print()
        print("🎯 Recognition Features:")
        print("   • Real-time face detection")
        print("   • Multi-face recognition")
        print("   • Confidence scoring")
        print("   • Role-based identification")
        print("   • Training mode for accuracy improvement")
        print()
        print("🔒 Privacy & Security:")
        print("   • All data stored locally")
        print("   • No cloud upload")
        print("   • User role management")
        print("   • Confidence thresholds")
        
    def test_camera(self):
        print("🧪 CAMERA TEST")
        print("=" * 20)
        
        import cv2
        
        print("🔍 Testing camera availability...")
        
        # Test multiple camera indices
        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    height, width = frame.shape[:2]
                    print(f"✅ Camera {i}: Working - Resolution: {width}x{height}")
                else:
                    print(f"⚠️ Camera {i}: Found but cannot capture")
                cap.release()
            else:
                print(f"❌ Camera {i}: Not available")
        
        print()
        print("💡 The system will use Camera 0 by default.")
        print("📝 If your camera isn't working, check:")
        print("   • Camera permissions")
        print("   • Other apps using the camera")
        print("   • USB connection (for external cameras)")
        
    def show_documentation(self):
        print("📖 DOCUMENTATION")
        print("=" * 20)
        print("📄 Available documentation files:")
        print("   • README_FACE_AUTH.md - Complete face authentication guide")
        print("   • README.md - Main Guardia AI documentation")
        print("   • CREDENTIALS_GUIDE.md - Setup and configuration")
        print()
        print("🎓 Learning Resources:")
        print("   • Face Recognition Library: https://github.com/ageitgey/face_recognition")
        print("   • OpenCV Documentation: https://docs.opencv.org/")
        print("   • Python Computer Vision: https://opencv-python-tutroals.readthedocs.io/")
        print()
        print("🔧 Advanced Topics:")
        print("   • Integration with main Guardia AI system")
        print("   • API development for remote access")
        print("   • Performance optimization")
        print("   • Multi-camera setups")
        
    def run(self):
        self.show_welcome()
        
        while True:
            self.show_menu()
            
            try:
                choice = input("Select option (1-6): ").strip()
                print()
                
                if choice == "1":
                    self.run_real_time_system()
                elif choice == "2":
                    self.show_statistics()
                elif choice == "3":
                    self.show_system_info()
                elif choice == "4":
                    self.test_camera()
                elif choice == "5":
                    self.show_documentation()
                elif choice == "6":
                    print("👋 Thank you for using Guardia AI Face Authentication!")
                    print("🚀 Visit the full system for more features!")
                    break
                else:
                    print("❌ Invalid option. Please select 1-6.")
                
                if choice != "6":
                    input("\nPress Enter to continue...")
                    print()
                    
            except KeyboardInterrupt:
                print("\n\n👋 Demo interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                input("Press Enter to continue...")

if __name__ == "__main__":
    demo = FaceAuthDemo()
    demo.run()
