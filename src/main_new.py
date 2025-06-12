import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("🛡️ Guardia AI - Cloud Surveillance System")
print("=" * 60)

# Check if MongoDB and Google Cloud modules are available
try:
    from modules.auth import create_owner, login_owner
    from modules.family import add_family_member
    from modules.detector import start_detection, initialize_cloud_detector, check_camera_access, capture_user_face, capture_family_member_face
    from modules.google_cloud_utils import get_video_client, get_storage_client
    CLOUD_MODULES_AVAILABLE = True
    print("✅ Cloud modules loaded successfully")
except ImportError as e:
    print(f"⚠️ Cloud modules not available: {e}")
    print("Running in basic mode")
    CLOUD_MODULES_AVAILABLE = False
    
    # Import basic detection functionality even if cloud modules fail
    try:
        from modules.detector import start_detection, basic_motion_detection, check_camera_access, capture_user_face
        print("✅ Basic detection modules loaded")
    except ImportError as e2:
        print(f"❌ Critical error: Cannot load detection modules: {e2}")
        print("Please ensure all dependencies are installed:")
        print("  pip install opencv-python numpy")
        
        # Define fallback functions
        def start_detection():
            print("❌ Detection modules not available")
            print("Please install required dependencies and try again")
            return False
            
        def check_camera_access():
            print("❌ Camera access not available")
            return False
            
        def capture_user_face(name):
            print("❌ Face capture not available")
            return None
            
        def capture_family_member_face(name, relation):
            print("❌ Face capture not available")
            return None

def main():
    print("=" * 50)
    print("Welcome to Smart Home Surveillance (Cloud Mode)")
    print("=" * 50)
    
    if not CLOUD_MODULES_AVAILABLE:
        print("\n📢 NOTICE: Running in Basic Mode")
        print("Cloud features are not available.")
        print("Only basic motion detection will work.")
        
        response = input("\nContinue with basic surveillance? (y/n): ").strip().lower()
        if response != 'y':
            print("👋 Goodbye!")
            return
        
        print("\n--- Starting Basic Motion Detection ---")
        input("Press Enter to start surveillance...")
        start_detection()
        return
    
    # Test cloud connectivity
    print("\n🔍 Testing cloud connectivity...")
    try:
        video_client = get_video_client()
        storage_client = get_storage_client()
        if video_client and storage_client:
            print("✅ Google Cloud services accessible")
        else:
            print("⚠️ Some Google Cloud services may not be available")
    except Exception as e:
        print(f"⚠️ Cloud connectivity issue: {e}")
    
    while True:
        print("\n1. Create Owner Account")
        print("2. Login")
        print("3. Exit")
        choice = input("Select (1-3): ").strip()

        if choice == '1':
            print("\n--- Create Owner Account ---")
            name = input("Enter Owner Name: ").strip()
            email = input("Enter Email: ").strip()
            password = input("Enter Password: ").strip()
            
            # Face capture option
            print("\n📸 Profile Image Setup")
            print("Choose an option:")
            print("1. Capture face using camera (Recommended)")
            print("2. Provide image file path")
            print("3. Skip image (create account without image)")
            
            image_choice = input("Select (1-3): ").strip()
            image_path = None
            
            if image_choice == '1':
                # Camera face capture
                print("\n📸 Starting camera for face capture...")
                if check_camera_access():
                    captured_path = capture_user_face(name)
                    if captured_path:
                        image_path = captured_path
                        print(f"✅ Face captured and saved: {captured_path}")
                    else:
                        print("❌ Face capture failed. Creating account without image.")
                else:
                    print("❌ Camera not accessible. Creating account without image.")
                    
            elif image_choice == '2':
                # Manual file path
                if os.name == 'nt':  # Windows
                    example_path = "C:\\path\\to\\your\\image.jpg"
                else:  # Linux/Unix
                    example_path = "/app/images/owner.jpg"
                
                print(f"Example path: {example_path}")
                image_path = input("Enter image file path: ").strip()
                image_path = image_path if image_path else None
                
            # else: image_choice == '3' or anything else - skip image
            
            if create_owner(name, email, password, image_path):
                print("✓ Owner account created successfully!")
            else:
                print("✗ Failed to create owner account.")
        elif choice == '2':
            print("\n--- Login ---")
            email = input("Enter Email: ").strip()
            password = input("Enter Password: ").strip()
            owner = login_owner(email, password)
            
            if not owner:
                print("✗ Login failed. Please try again.")
                continue
                
            print(f"✓ Login successful. Welcome {owner['name']}!")
            
            # Family member management with cloud support
            while True:
                print(f"\nCurrent family members: {len(owner.get('family', []))}")
                for member in owner.get('family', []):
                    member_name = member.get('name', 'Unknown')
                    member_relation = member.get('relation', 'Unknown')
                    print(f"  - {member_name} ({member_relation})")
                
                add = input("\nAdd Family Member? (y/n): ").strip().lower()
                if add != 'y':
                    break
                    
                name = input("Family Member Name: ").strip()
                relation = input("Relation (e.g., Father, Mother, Brother): ").strip()
                
                # Face capture option for family member
                print(f"\n📸 Profile Image Setup for {name}")
                print("Choose an option:")
                print("1. Capture face using camera (Recommended)")
                print("2. Provide image file path")
                print("3. Skip image (add without image)")
                
                image_choice = input("Select (1-3): ").strip()
                path = None
                
                if image_choice == '1':
                    # Camera face capture for family member
                    print(f"\n📸 Starting camera for {name}'s face capture...")
                    if check_camera_access():
                        try:
                            captured_path = capture_family_member_face(name, relation)
                            if captured_path:
                                path = captured_path
                                print(f"✅ Face captured and saved: {captured_path}")
                            else:
                                print("❌ Face capture failed. Adding family member without image.")
                        except Exception as e:
                            print(f"❌ Camera capture error: {e}")
                    else:
                        print("❌ Camera not accessible. Adding family member without image.")
                        
                elif image_choice == '2':
                    # Manual file path
                    if os.name == 'nt':  # Windows
                        example_path = "C:\\path\\to\\family\\member.jpg"
                    else:  # Linux/Unix
                        example_path = "/app/images/family_member.jpg"
                    
                    print(f"Example path: {example_path}")
                    path = input("Image path (optional): ").strip()
                    path = path if path else None
                    
                # else: image_choice == '3' or anything else - skip image
                
                if add_family_member(email, name, relation, path):
                    print(f"✓ {name} added successfully!")
                    # Reload owner data to show updated family list
                    owner = login_owner(email, password)
                else:
                    print("✗ Failed to add family member.")

            print("\n--- Starting Cloud Surveillance ---")
            print("This will start camera monitoring with cloud AI analysis.")
            
            # Initialize cloud detector
            if initialize_cloud_detector():
                print("✅ Cloud detector initialized successfully")
            else:
                print("⚠️ Cloud detector initialization failed - using local detection")
            
            input("Press Enter to start surveillance...")
            start_detection()
            break

        elif choice == '3':
            print("👋 Goodbye!")
            break
            
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

if __name__ == "__main__":
    main()