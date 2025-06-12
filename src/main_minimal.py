import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("🛡️ Guardia AI - Minimal Mode")
print("=" * 60)

from modules.detector import start_detection

def main():
    print("\nWelcome to Smart Home Surveillance (Minimal Mode)")
    print("=" * 50)
    
    print("\n📢 NOTICE: Running in Minimal Mode")
    print("This mode provides basic local functionalities (if implemented).")
    print("For full features, including cloud-based AI detection and database integration,")
    print("please run the main application: python src/main.py")
    print("-" * 50)
    
    print("\n--- Starting Minimal Mode Surveillance ---")
    
    input("Press Enter to start surveillance...")
    
    try:
        start_detection() # This will call the placeholder function in detector.py
    except KeyboardInterrupt:
        print("\n🛑 Surveillance stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("This may be due to camera access issues in Docker.")
        print("Try running with camera permissions or in native mode.")

if __name__ == "__main__":
    main()
