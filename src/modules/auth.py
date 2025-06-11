import json
import os
import hashlib
import cv2

# Try to import face_recognition, fallback gracefully if not available
try:
    import face_recognition
    import numpy as np
    FACE_RECOGNITION_AVAILABLE = True
    print("✅ Face recognition available in auth module")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠️ Face recognition not available in auth module - using basic mode")

# Use data directory for database
DB_FILE = "data/db.json"

def hash_password(password):
    return hashlib.sha256(password.strip().encode('utf-8')).hexdigest()

def create_owner(name, email, password, image_path):
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    if not os.path.exists(DB_FILE):
        data = {"owners": []}
    else:
        with open(DB_FILE, "r") as f:
            data = json.load(f)

    # Limit to 3 owners
    if len(data["owners"]) >= 3:
        print("Maximum number of owners (3) already registered.")
        return False

    for owner in data["owners"]:
        if owner["email"] == email:
            print("Owner with this email already exists.")
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
                print("No face detected in owner's image.")
                return False

            encoding = encodings[0]
            os.makedirs("encodings", exist_ok=True)
            os.makedirs("faces", exist_ok=True)

            enc_file = f"encodings/{name}_owner.npy"
            img_file = f"faces/{name}_owner.jpg"

            np.save(enc_file, encoding)
            img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(img_file, img_bgr)
            
            print(f"Owner {name} created successfully with face encoding saved.")
        else:
            # Basic mode - just save the image without face recognition
            os.makedirs("faces", exist_ok=True)
            img_file = f"faces/{name}_owner.jpg"
            
            # Just copy the image file
            import shutil
            shutil.copy2(image_path, img_file)
            print(f"Owner {name} created successfully (basic mode - no face encoding).")

        owner = {
            "name": name,
            "email": email,
            "password": hash_password(password),
            "image": img_file,
            "family": [],
            "face_recognition_enabled": FACE_RECOGNITION_AVAILABLE
        }

        data["owners"].append(owner)

        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=4)

        return True

    except Exception as e:
        print(f"Error processing owner's image: {e}")
        return False

def login_owner(email, password):
    if not os.path.exists(DB_FILE):
        print("Database not found.")
        return None

    with open(DB_FILE, "r") as f:
        data = json.load(f)

    for owner in data["owners"]:
        if owner["email"] == email and owner["password"] == hash_password(password):
            return owner

    print("Invalid email or password.")
    return None
