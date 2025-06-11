import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if face recognition is available before importing modules
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    print("✅ Full face recognition mode available")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠️ Face recognition not available - limited functionality")

from modules.auth import create_owner, login_owner
from modules.family import add_family_member
from modules.detector import start_detection

def main():
    print("=" * 50)
    print("Welcome to Smart Home Surveillance Prototype")
    print("=" * 50)
    
    if not FACE_RECOGNITION_AVAILABLE:
        print("\n📢 NOTICE: Running in Basic Mode")
        print("Face recognition features are not available.")
        print("Only motion detection will work.")
        
        response = input("\nContinue with basic surveillance? (y/n): ").strip().lower()
        if response != 'y':
            print("👋 Goodbye!")
            return
        
        print("\n--- Starting Basic Motion Detection ---")
        input("Press Enter to start surveillance...")
        start_detection()
        return
    
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
            
            # Show example path based on OS
            if os.name == 'nt':  # Windows
                example_path = "C:\\path\\to\\your\\image.jpg"
            else:  # Linux/Unix
                example_path = "/app/images/owner.jpg"
            
            print(f"Example path: {example_path}")
            image_path = input("Enter Owner Image Path: ").strip()
            
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
            
            # Family member management (only if face recognition is available)
            if FACE_RECOGNITION_AVAILABLE:
                while True:
                    print(f"\nCurrent family members: {len(owner.get('family', []))}")
                    for member in owner.get('family', []):
                        print(f"  - {member['name']} ({member['relation']})")
                    
                    add = input("\nAdd Family Member? (y/n): ").strip().lower()
                    if add != 'y':
                        break
                        
                    name = input("Family Member Name: ").strip()
                    relation = input("Relation (e.g., Father, Mother, Brother): ").strip()
                    
                    if os.name == 'nt':  # Windows
                        example_path = "C:\\path\\to\\family\\member.jpg"
                    else:  # Linux/Unix
                        example_path = "/app/images/family_member.jpg"
                    
                    print(f"Example path: {example_path}")
                    path = input("Image path: ").strip()
                    
                    if add_family_member(email, name, relation, path):
                        print(f"✓ {name} added successfully!")
                        # Reload owner data to show updated family list
                        owner = login_owner(email, password)
                    else:
                        print("✗ Failed to add family member.")
            else:
                print("\n⚠️ Family member management not available in basic mode")

            print("\n--- Starting Real-time Detection ---")
            print("Make sure your camera is connected and working.")
            input("Press Enter to start surveillance...")
            start_detection()
            break

        elif choice == '3':
            print("Goodbye!")
            break
            
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

if __name__ == "__main__":
    main()
