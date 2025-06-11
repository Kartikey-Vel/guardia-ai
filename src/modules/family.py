import json
import os
import cv2

# Try to import face_recognition, fallback gracefully if not available
try:
    import face_recognition
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
    print("✅ Face recognition available in family module")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠️ Face recognition not available in family module - using basic mode")

DB_FILE = "data/db.json"

def add_family_member(owner_email, name, relation, image_path):
    if not os.path.exists(DB_FILE):
        print("Database not found. Please create an owner account first.")
        return False

    with open(DB_FILE, "r") as f:
        data = json.load(f)

    owner = next((o for o in data["owners"] if o["email"] == owner_email), None)
    if not owner:
        print("Owner not found.")
        return False

    try:
        if not os.path.exists(image_path):
            print(f"Image path does not exist: {image_path}")
            return False

        if FACE_RECOGNITION_AVAILABLE:
            # Full face recognition mode
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if not encodings:
                print("No face found in image.")
                return False
            encoding = encodings[0]

            os.makedirs("encodings", exist_ok=True)
            os.makedirs("faces", exist_ok=True)

            np.save(f"encodings/{name}.npy", encoding)
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(f"faces/{name}.jpg", img_bgr)
            
            print(f"Family member {name} added successfully with encoding saved.")
        else:
            # Basic mode - just save the image without face recognition
            os.makedirs("faces", exist_ok=True)
            
            # Just copy the image file
            import shutil
            shutil.copy2(image_path, f"faces/{name}.jpg")
            print(f"Family member {name} added successfully (basic mode - no face encoding).")

        owner["family"].append({
            "name": name, 
            "relation": relation,
            "face_recognition_enabled": FACE_RECOGNITION_AVAILABLE
        })

        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)

        return True

    except Exception as e:
        print(f"Error processing family member's image: {e}")
        return False
