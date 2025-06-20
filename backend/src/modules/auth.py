import json
import os
import hashlib
from pymongo import MongoClient
from config.settings import MONGO_DB_URI, MONGO_DB_NAME, GOOGLE_APPLICATION_CREDENTIALS # Added GOOGLE_APPLICATION_CREDENTIALS for potential use here

# # Use data directory for database (Old file-based DB)
# DB_FILE = "data/db.json"

# --- MongoDB Connection ---
client = None
db = None
owners_collection = None

def get_mongo_collections():
    global client, db, owners_collection
    if not client and MONGO_DB_URI: # Check if MONGO_DB_URI is set
        try:
            client = MongoClient(MONGO_DB_URI)
            # Test connection before assigning db and collections
            client.admin.command('ping') 
            print("✅ MongoDB connection successful.")
            db = client[MONGO_DB_NAME]
            owners_collection = db["owners"]
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB: {e}")
            print(f"  URI: {MONGO_DB_URI}")
            print(f"  DB Name: {MONGO_DB_NAME}")
            print("  Ensure MongoDB is running and accessible, and MONGO_DB_URI in .env.local is correct.")
            client = None
            db = None
            owners_collection = None
            return False
    elif not MONGO_DB_URI:
        print("⚠️ MONGO_DB_URI not set in environment. Skipping MongoDB initialization.")
        return False
    return True

# Ensure collections are initialized when module is loaded
get_mongo_collections()


def hash_password(password):
    return hashlib.sha256(password.strip().encode('utf-8')).hexdigest()

def create_owner(name, email, password, image_path=None): # image_path is now optional
    if owners_collection is None:
        print("MongoDB owners collection not available. Attempting to reconnect...")
        if not get_mongo_collections(): 
             print("Failed to connect to MongoDB. Cannot create owner.")
             return False
        if owners_collection is None: # Check again after attempting reconnect
            print("Still unable to access MongoDB owners collection after reconnect attempt.")
            return False

    # Limit to 3 owners (This logic might be better handled elsewhere or re-evaluated)
    if owners_collection.count_documents({}) >= 3:
        print("Maximum number of owners (3) already registered.")
        return False

    if owners_collection.find_one({"email": email}):
        print("Owner with this email already exists.")
        return False

    try:
        saved_image_path = None
        if image_path:
            if not os.path.exists(image_path):
                print(f"Image path does not exist: {image_path}")
            
            os.makedirs("faces", exist_ok=True) 
            import shutil
            # Sanitize filename components
            safe_name = "".join(c if c.isalnum() else '_' for c in name)
            base_image_name = os.path.basename(image_path)
            safe_base_image_name = "".join(c if c.isalnum() or c in '.-' else '_' for c in base_image_name)
            saved_image_path = f"faces/{safe_name}_owner_{safe_base_image_name}"
            shutil.copy2(image_path, saved_image_path)
            print(f"Owner {name} created. Image reference: {saved_image_path}")
        else:
            print(f"Owner {name} created without an initial image.")

        owner_data = {
            "name": name,
            "email": email,
            "password": hash_password(password),
            "image_reference": saved_image_path, 
            "family": [],
            "cloud_video_intelligence_enabled": True
        }

        result = owners_collection.insert_one(owner_data)
        print(f"Owner {name} added to MongoDB with ID: {result.inserted_id}")
        return True

    except Exception as e:
        print(f"Error creating owner in MongoDB: {e}")
        return False

def login_owner(email, password):
    if owners_collection is None:
        print("MongoDB owners collection not available. Attempting to reconnect...")
        if not get_mongo_collections():
            print("Failed to connect to MongoDB. Cannot login owner.")
            return None
        if owners_collection is None: # Check again
            print("Still unable to access MongoDB owners collection after reconnect attempt for login.")
            return None

    owner = owners_collection.find_one({"email": email})

    if owner and owner["password"] == hash_password(password):
        print(f"Owner {owner.get('name', 'N/A')} logged in successfully.")
        return owner # Returns the owner document from MongoDB

    print("Invalid email or password.")
    return None
