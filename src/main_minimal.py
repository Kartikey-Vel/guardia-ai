import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("🛡️ Guardia AI - Minimal Mode (Motion Detection Only)")
print("=" * 60)

# Check if face recognition is available
try:
    import face_recognition
    print("✅ Face recognition available")
    USE_FULL_MODE = True
except ImportError:
    print("⚠️ Face recognition not available - running in motion detection mode")
    USE_FULL_MODE = False

from modules.detector import start_detection

def main():
    print("\nWelcome to Smart Home Surveillance (Minimal Mode)")
    print("=" * 50)
    
    if not USE_FULL_MODE:
        print("\n📢 NOTICE: Running in Motion Detection Mode")
        print("Features available:")
        print("  ✅ Motion detection")
        print("  ✅ Basic surveillance")
        print("  ❌ Face recognition (requires full installation)")
        print("  ❌ Owner/family management")
        print("\nTo enable full features:")
        print("  1. Use the full Docker image")
        print("  2. Install face_recognition manually")
        print("  3. Run: pip install face-recognition dlib")
    
    print("\n--- Starting Motion Detection Surveillance ---")
    print("Make sure your camera is connected and working.")
    
    # Skip user management in minimal mode
    input("Press Enter to start surveillance...")
    
    try:
        start_detection()
    except KeyboardInterrupt:
        print("\n🛑 Surveillance stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("This may be due to camera access issues in Docker.")
        print("Try running with camera permissions or in native mode.")

if __name__ == "__main__":
    main()
