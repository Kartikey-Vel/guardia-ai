# 🔐 Guardia AI - Complete Credentials Guide

This document provides a comprehensive guide for configuring all credentials and settings for the Guardia AI Enhanced System.

## 📋 Quick Status Check

**Current Configuration Status: ✅ COMPLETE**

- ✅ **Environment Configuration**: Complete with all settings
- ✅ **MongoDB Atlas**: Configured and connected  
- ✅ **Google Cloud Services**: Credentials and project configured
- ✅ **Security Settings**: JWT and CORS properly set
- ✅ **Storage Paths**: All directories configured
- ✅ **Camera Settings**: Default USB camera configured
- ⚠️ **Notifications**: Available but disabled (configure as needed)

## 🚀 Quick Start Commands

```bash
# Validate current configuration
python validate_config.py

# Reconfigure credentials interactively
./setup_credentials.sh

# Start the system with current settings
python start_server.py
```

## 🔧 Detailed Configuration Guide

### 1. Core Application Settings

```bash
ENVIRONMENT=development              # development, staging, production
SECRET_KEY=your-secret-key-here     # Use: openssl rand -hex 32
DEBUG=true                          # false for production
HOST=0.0.0.0                       # Server host
PORT=8000                           # Server port
```

**🔐 Security Note**: For production, always generate a secure SECRET_KEY:
```bash
openssl rand -hex 32
```

### 2. Database Configuration (MongoDB Atlas)

**Current Configuration**: ✅ **WORKING**
```bash
MONGODB_URL=mongodb+srv://aryanbajpai2411:ESOS5bbK4XLq2mZV@gaurdia-ai-vi-main.drm97zq.mongodb.net/?retryWrites=true&w=majority&appName=gaurdia-ai-vi-main
MONGODB_DATABASE=guardia_ai_db
```

**For Your Own Database**:
```bash
# Replace with your MongoDB Atlas connection string
MONGODB_URL=mongodb+srv://username:password@your-cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=your_database_name
```

**Setup Steps**:
1. Go to [MongoDB Atlas](https://cloud.mongodb.com)
2. Create account/cluster (free tier available)
3. Create database user
4. Get connection string
5. Whitelist your IP address

### 3. Google Cloud Services

**Current Configuration**: ✅ **WORKING**
```bash
GOOGLE_APPLICATION_CREDENTIALS=./guardia/config/google-credentials.json
GCS_BUCKET_NAME=guardia_ai_vi
GOOGLE_CLOUD_PROJECT_ID=gaurdia-ai
ENABLE_VIDEO_INTELLIGENCE=true
```

**For Your Own Google Cloud Project**:

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create new project or select existing
   - Note the Project ID

2. **Enable Required APIs**:
   ```bash
   # Enable these APIs in Google Cloud Console
   - Video Intelligence API
   - Cloud Vision API  
   - Cloud Storage API
   ```

3. **Create Service Account**:
   - Go to IAM & Admin > Service Accounts
   - Create service account with these roles:
     - Storage Admin
     - Video Intelligence API User
     - Vision API User
   - Download JSON key file
   - Place in `./guardia/config/google-credentials.json`

4. **Create Storage Bucket**:
   ```bash
   # Create bucket for video/image storage
   gsutil mb gs://your-bucket-name
   ```

5. **Update Configuration**:
   ```bash
   GOOGLE_CLOUD_PROJECT_ID=your-project-id
   GCS_BUCKET_NAME=your-bucket-name
   ```

### 4. Camera Configuration

```bash
CAMERA_SOURCES=0                     # USB cameras: 0,1,2...
# CAMERA_SOURCES=0,rtsp://camera-ip:554/stream  # Mixed sources
# CAMERA_SOURCES=rtsp://camera1:554,rtsp://camera2:554  # IP cameras only

FACE_DETECTION_CONFIDENCE=0.5        # 0.0-1.0 (higher = stricter)
OBJECT_DETECTION_CONFIDENCE=0.5      # 0.0-1.0 (higher = stricter)
```

**Camera Source Examples**:
- USB Cameras: `0`, `1`, `2`
- IP Cameras: `rtsp://192.168.1.100:554/stream`
- HTTP Streams: `http://192.168.1.100:8080/video`
- Video Files: `/path/to/video.mp4`

### 5. Notification Services (Optional)

#### Email Notifications (SMTP)
```bash
ENABLE_EMAIL_NOTIFICATIONS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password      # Gmail: Use App Password
SMTP_FROM_EMAIL=your-email@gmail.com
```

**Gmail Setup**:
1. Enable 2-factor authentication
2. Generate App Password (not your regular password)
3. Use App Password in SMTP_PASSWORD

#### SMS Notifications (Twilio)
```bash
ENABLE_SMS_NOTIFICATIONS=true
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

**Twilio Setup**:
1. Sign up at [Twilio](https://www.twilio.com)
2. Get Account SID and Auth Token from dashboard
3. Purchase/configure phone number

### 6. Security & CORS Settings

```bash
CORS_ORIGINS=["http://localhost:3000","https://yourdomain.com"]
CORS_CREDENTIALS=true
JWT_EXPIRATION_MINUTES=60           # Session timeout
RATE_LIMIT_REQUESTS=100             # Requests per window
RATE_LIMIT_WINDOW=60                # Window in seconds
```

### 7. Advanced Features

```bash
# Behavior Analysis
ENABLE_BEHAVIOR_ANALYSIS=true
LOITERING_THRESHOLD_SECONDS=30
CROWD_DETECTION_THRESHOLD=5

# Night Mode
ENABLE_NIGHT_MODE=true
NIGHT_MODE_START_HOUR=22
NIGHT_MODE_END_HOUR=6

# Privacy Settings
BLUR_FACES_IN_RECORDINGS=false
ANONYMIZE_UNKNOWN_PERSONS=false
```

### 8. AI/ML Model Settings

```bash
FACE_DETECTION_BACKEND=mediapipe    # mediapipe, face_recognition, opencv
YOLO_MODEL_SIZE=yolov8n.pt         # yolov8n.pt, yolov8s.pt, yolov8m.pt, yolov8l.pt
YOLO_DEVICE=cpu                    # cpu, cuda (for GPU)
AUTO_UPDATE_MODELS=false           # Auto-download model updates
```

**Model Performance vs Speed**:
- `yolov8n.pt`: Fastest, lowest accuracy
- `yolov8s.pt`: Balanced
- `yolov8m.pt`: Better accuracy, slower
- `yolov8l.pt`: Best accuracy, slowest

### 9. Storage Configuration

```bash
MEDIA_STORAGE_PATH=./storage/media
IMAGES_PATH=./storage/images
VIDEOS_PATH=./storage/videos
FACES_PATH=./storage/faces
LOGS_PATH=./storage/logs
MAX_STORAGE_SIZE_MB=5000

# Cleanup Settings
ENABLE_AUTO_CLEANUP=true
CLEANUP_INTERVAL_HOURS=24
RETAIN_MEDIA_DAYS=30
RETAIN_LOGS_DAYS=7
```

### 10. Redis Cache (Optional)

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

**Redis Setup** (optional, for better performance):
```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis

# Docker
docker run -d -p 6379:6379 redis:alpine
```

## 🔧 Configuration Tools

### Interactive Setup
```bash
./setup_credentials.sh
```
- Guides you through all credential setup
- Validates input
- Creates complete .env file

### Configuration Validation
```bash
python validate_config.py
```
- Checks all credentials and settings
- Validates file paths and permissions
- Tests database connectivity
- Provides detailed error reports

### Environment Templates

**Development** (current `.env`):
- Uses existing MongoDB Atlas
- Uses existing Google Cloud project
- Debug mode enabled
- Loose security settings

**Production** (`.env.production`):
- Enhanced security
- Stricter CORS
- Performance optimizations
- Comprehensive logging

**Copy for production**:
```bash
cp .env.production .env
# Edit with your production credentials
```

## 🚨 Security Best Practices

### Production Checklist
- [ ] Generate secure SECRET_KEY (32+ characters)
- [ ] Set DEBUG=false
- [ ] Configure specific CORS_ORIGINS (no wildcards)
- [ ] Use HTTPS with SSL certificates
- [ ] Set up firewall rules
- [ ] Enable monitoring and alerting
- [ ] Regular security updates
- [ ] Backup encryption keys

### Development vs Production

| Setting | Development | Production |
|---------|-------------|------------|
| DEBUG | true | false |
| SECRET_KEY | Simple | 32+ char secure |
| CORS_ORIGINS | ["*"] | Specific domains |
| JWT_EXPIRATION | 1440 min | 60 min |
| LOG_LEVEL | INFO | WARNING |
| Rate Limits | High | Strict |

## 🆘 Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**
   ```bash
   # Check connection string format
   # Verify IP whitelist in MongoDB Atlas
   # Confirm username/password
   ```

2. **Google Cloud Authentication Error**
   ```bash
   # Verify credentials file exists
   # Check service account permissions
   # Confirm project ID is correct
   ```

3. **Camera Not Found**
   ```bash
   # Check camera index (try 0, 1, 2...)
   # Test camera with other applications
   # Verify USB camera permissions
   ```

4. **Permission Denied on Storage**
   ```bash
   # Create directories manually
   mkdir -p storage/{media,images,videos,faces,logs}
   chmod 755 storage/
   ```

### Getting Help

1. **Run Validation**: `python validate_config.py`
2. **Check Logs**: Look in `./storage/logs/`
3. **Test Components**: Use individual test scripts
4. **Reset Config**: `./setup_credentials.sh`

## 📞 Support

- **Documentation**: This file and inline code comments
- **Validation**: Built-in configuration validator
- **Setup Script**: Interactive credential configuration
- **Examples**: Multiple environment templates provided

**Current Status**: ✅ **ALL CREDENTIALS CONFIGURED AND WORKING**

The system is ready to run with the current configuration!
