"""
Guardia AI Configuration Settings
Centralized configuration for the entire surveillance system
"""
import os
from pathlib import Path

# Project Paths
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
IMAGES_DIR = PROJECT_ROOT / "images"
RECORDINGS_DIR = PROJECT_ROOT / "recordings"
FACES_DIR = PROJECT_ROOT / "faces"

# Create directories if they don't exist
for directory in [DATA_DIR, LOGS_DIR, IMAGES_DIR, RECORDINGS_DIR, FACES_DIR]:
    directory.mkdir(exist_ok=True)

# Camera Settings
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30

# Face Recognition Settings
FACE_RECOGNITION_TOLERANCE = 0.6
FACE_DETECTION_MODEL = "hog"  # or "cnn" for better accuracy but slower
UNKNOWN_FACE_ENCODING_SAMPLES = 5

# Alert Settings
ALERT_COOLDOWN_SECONDS = 60
INTRUDER_ALERT_DELAY = 30  # seconds before alerting unknown person
NOTIFICATION_ENABLED = True

# Security Settings
MAX_UNKNOWN_TRACKING_TIME = 300  # 5 minutes
MOTION_THRESHOLD = 1000
CONFIDENCE_THRESHOLD = 0.7

# Database Settings (MongoDB)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "guardia_ai"
USERS_COLLECTION = "users"
FACES_COLLECTION = "faces"
ALERTS_COLLECTION = "alerts"

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# System Settings
DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"
ENABLE_CLOUD_AI = os.getenv("ENABLE_CLOUD_AI", "False").lower() == "true"
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Performance Settings
PROCESSING_INTERVAL = 0.5  # seconds
CLEANUP_INTERVAL = 3600  # 1 hour
MAX_MEMORY_USAGE = 80  # percentage
