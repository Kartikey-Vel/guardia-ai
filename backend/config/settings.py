# Configuration settings for Guardia AI
import os
from dotenv import load_dotenv

# Load environment variables from .env.local or .env
# Construct absolute path to .env.local relative to this settings.py file
dotenv_path_local = os.path.join(os.path.dirname(__file__), '..', '.env.local')
load_dotenv(dotenv_path=dotenv_path_local)

# Fallback to .env if .env.local is not found or doesn't contain all vars
dotenv_path_default = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path_default):
    load_dotenv(dotenv_path=dotenv_path_default, override=False) # override=False to not overwrite .env.local vars

# --- Google Cloud Settings ---
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME") 

# --- MongoDB Settings ---
MONGO_DB_URI = os.getenv("MONGO_DB_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "guardia_ai_db") # Default if not in .env

# --- Original Database settings (file-based, can be phased out or kept for fallback) ---
DB_FILE = "data/db.json" # This might be deprecated if fully moving to MongoDB

# Directory paths
ENCODINGS_DIR = "encodings"
FACES_DIR = "faces"
IMAGES_DIR = "images"
DETECTED_KNOWN_DIR = "detected/known"
DETECTED_UNKNOWN_DIR = "detected/unknown"
LOGS_DIR = "logs"

# Camera settings
DEFAULT_CAMERA_INDEX = 0
FACE_RECOGNITION_TOLERANCE = 0.6

# Security settings
MAX_OWNERS = 3
HASH_ALGORITHM = "sha256"
