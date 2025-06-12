#!/usr/bin/env python3
"""
Configuration setup script for Guardia AI
Helps with setting up environment variables, credentials, and configuration
"""

import os
import json
from pathlib import Path

def create_env_template():
    """Create a template .env.local file with placeholder values"""
    env_template = """# Guardia AI Environment Configuration
# Copy this file to .env.local and fill in your actual values

# Google Cloud Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
GCS_BUCKET_NAME=your-gcs-bucket-name

# MongoDB Configuration
MONGO_DB_URI=mongodb://localhost:27017/
MONGO_DB_NAME=guardia_ai_db

# Optional: Logging Configuration
LOG_LEVEL=INFO
DEBUG_MODE=false

# Optional: Alert Configuration
ENABLE_EMAIL_ALERTS=false
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
ALERT_RECIPIENTS=alert1@email.com,alert2@email.com

# Optional: Camera Configuration
DEFAULT_CAMERA_INDEX=0
VIDEO_QUALITY=HIGH
MAX_VIDEO_DURATION=30
"""
    
    env_file = Path(".env.example")
    with open(env_file, 'w') as f:
        f.write(env_template)
    
    print(f"✅ Created environment template: {env_file}")
    print("📝 Copy this to .env.local and fill in your values")

def check_dependencies():
    """Check if all required dependencies are available"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'cv2',
        'numpy', 
        'google.cloud.videointelligence',
        'google.cloud.storage',
        'pymongo',
        'dotenv'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("📦 Install missing packages with:")
        if 'cv2' in missing_packages:
            print("   pip install opencv-python")
        if 'google.cloud.videointelligence' in missing_packages:
            print("   pip install google-cloud-videointelligence")
        if 'google.cloud.storage' in missing_packages:
            print("   pip install google-cloud-storage")
        if 'pymongo' in missing_packages:
            print("   pip install pymongo")
        if 'dotenv' in missing_packages:
            print("   pip install python-dotenv")
        return False
    else:
        print("✅ All dependencies available")
        return True

def setup_directories():
    """Create necessary directories for the application"""
    directories = [
        'data',
        'logs', 
        'faces',
        'encodings',
        'detected/known',
        'detected/unknown',
        'config'
    ]
    
    print("📁 Setting up directories...")
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ {dir_path}")

def check_camera_access():
    """Test camera access"""
    try:
        import cv2
        print("📹 Testing camera access...")
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                print("✅ Camera accessible")
                return True
            else:
                print("⚠️ Camera opened but failed to capture")
                return False
        else:
            print("❌ Camera not accessible")
            return False
    except Exception as e:
        print(f"❌ Camera test error: {e}")
        return False

def check_google_cloud_config():
    """Check Google Cloud configuration"""
    print("☁️ Checking Google Cloud configuration...")
    
    # Check for credentials file
    cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not cred_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS not set")
        return False
    
    if not os.path.exists(cred_path):
        print(f"❌ Credentials file not found: {cred_path}")
        return False
    
    print(f"✅ Credentials file found: {cred_path}")
    
    # Check bucket name
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    if not bucket_name:
        print("❌ GCS_BUCKET_NAME not set")
        return False
    
    print(f"✅ GCS bucket configured: {bucket_name}")
    
    # Test connection
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        if bucket.exists():
            print("✅ GCS bucket accessible")
        else:
            print("⚠️ GCS bucket may not exist or not accessible")
        return True
    except Exception as e:
        print(f"❌ GCS connection error: {e}")
        return False

def check_mongodb_config():
    """Check MongoDB configuration"""
    print("🍃 Checking MongoDB configuration...")
    
    mongo_uri = os.getenv('MONGO_DB_URI')
    if not mongo_uri:
        print("❌ MONGO_DB_URI not set")
        return False
    
    try:
        import pymongo
        client = pymongo.MongoClient(mongo_uri)
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection error: {e}")
        return False

def main():
    print("🛡️ Guardia AI - Configuration Setup")
    print("=" * 50)
    
    # Load environment if exists
    try:
        from dotenv import load_dotenv
        if os.path.exists('.env.local'):
            load_dotenv('.env.local')
            print("📝 Loaded .env.local")
        elif os.path.exists('.env'):
            load_dotenv('.env')
            print("📝 Loaded .env")
    except ImportError:
        print("⚠️ python-dotenv not available")
    
    # Run all checks
    print("\n1. Creating environment template...")
    create_env_template()
    
    print("\n2. Setting up directories...")
    setup_directories()
    
    print("\n3. Checking dependencies...")
    deps_ok = check_dependencies()
    
    print("\n4. Testing camera access...")
    camera_ok = check_camera_access()
    
    print("\n5. Checking Google Cloud configuration...")
    gcp_ok = check_google_cloud_config()
    
    print("\n6. Checking MongoDB configuration...")
    mongo_ok = check_mongodb_config()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 CONFIGURATION SUMMARY")
    print("=" * 50)
    print(f"Dependencies: {'✅' if deps_ok else '❌'}")
    print(f"Camera Access: {'✅' if camera_ok else '❌'}")
    print(f"Google Cloud: {'✅' if gcp_ok else '❌'}")
    print(f"MongoDB: {'✅' if mongo_ok else '❌'}")
    
    all_good = deps_ok and camera_ok and gcp_ok and mongo_ok
    
    if all_good:
        print("\n🎉 All systems ready! You can now run Guardia AI.")
        print("\nNext steps:")
        print("  python src/main.py              # Run main application")
        print("  python demo_cloud_surveillance.py  # Run demo")
        print("  python test_camera.py           # Test camera only")
    else:
        print("\n⚠️ Some issues found. Please fix the above errors before running Guardia AI.")
        print("\nConfiguration help:")
        print("  1. Copy .env.example to .env.local")
        print("  2. Fill in your Google Cloud credentials")
        print("  3. Set up MongoDB connection")
        print("  4. Test camera permissions")

if __name__ == "__main__":
    main()
