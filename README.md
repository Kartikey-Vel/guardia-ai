# 🔥 Guardia AI - Quick Start Guide

**Production-Ready AI Surveillance System with Google Cloud & MongoDB Atlas**

## ⚡ Super Quick Start (2 Minutes)

```bash
# 1. Clone & Navigate
git clone <your-repo-url>
cd guardia-ai

# 2. Install Dependencies
pip install -r requirements_enhanced.txt

# 3. Start the System
python start_server.py

# 4. Open Browser
# Visit: http://localhost:8000/docs
```

**That's it! Everything is pre-configured and ready to use.**

---

## 🎯 What You Get Out of the Box

- ✅ **Google Cloud Video Intelligence** - Advanced AI detection
- ✅ **MongoDB Atlas** - Cloud database (no local setup needed)
- ✅ **Multi-Camera Support** - USB, IP cameras, video files
- ✅ **Real-time Face Recognition** - Identify family vs strangers
- ✅ **Smart Alerts** - Email, SMS, push notifications
- ✅ **Live Web Interface** - Modern API with documentation
- ✅ **WebSocket Streaming** - Real-time video feeds

---

## 🏃‍♂️ Step-by-Step Setup

### 1. Prerequisites Check
```bash
# Check Python version (3.8+ required)
python --version

# Install pip if missing
# Windows: python -m ensurepip --upgrade
# Mac: brew install python
# Ubuntu: sudo apt install python3-pip
```

### 2. System Dependencies

**Windows:**
```bash
# Install Visual Studio Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

**macOS:**
```bash
brew install cmake opencv
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3-dev python3-pip cmake build-essential
sudo apt install -y libopencv-dev libgtk-3-dev libboost-all-dev
```

### 3. Install & Run

```bash
# Clone the repository
git clone <your-repo-url>
cd guardia-ai

# Install Python dependencies
pip install -r requirements_enhanced.txt

# Start the system (development mode)
python start_server.py

# Or start in production mode
python start_server.py --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access the System

- **Web Interface**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health  
- **API Documentation**: http://localhost:8000/docs
- **Real-time WebSocket**: ws://localhost:8000/ws

---

## 🔧 Configuration (Already Done!)

The system comes pre-configured with working credentials:

### Database
- **MongoDB Atlas**: Cloud database (no local MongoDB needed)
- **Connection**: Automatic, ready to use
- **Database Name**: `guardia_ai_db`

### Google Cloud (Optional)

The system supports Google Cloud Video Intelligence and Storage services for enhanced AI capabilities.

**Configuration Options:**

1. **Service Account Key (Recommended for Production)**:
   ```bash
   # Set the entire service account JSON as an environment variable
   export GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"your-project",...}'
   ```

2. **OAuth Credentials (Alternative)**:
   ```bash
   export GOOGLE_CLIENT_ID=your_client_id
   export GOOGLE_CLIENT_SECRET=your_client_secret
   export GOOGLE_REFRESH_TOKEN=your_refresh_token
   ```

3. **Project Configuration**:
   ```bash
   export GOOGLE_CLOUD_PROJECT_ID=your-project-id
   export GCS_BUCKET_NAME=your-bucket-name
   export ENABLE_VIDEO_INTELLIGENCE=true
   ```

- **Required**: Google Cloud Project with Video Intelligence API enabled
- **Features**: Advanced object detection, person tracking, facial recognition

### Camera Setup
- **Default**: USB camera (index 0)
- **IP Cameras**: Add URLs in environment settings
- **Video Files**: Supported for testing

---

## 📱 Quick API Usage

### 1. Register a User
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
-H "Content-Type: application/json" \
-d '{
  "email": "admin@example.com",
  "password": "admin123",
  "full_name": "Admin User",
  "phone": "+1234567890"
}'
```

### 2. Login & Get Token
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
-H "Content-Type: application/json" \
-d '{
  "email": "admin@example.com", 
  "password": "admin123"
}'
```

### 3. Start Surveillance
```bash
# Use the access_token from login response
curl -X POST "http://localhost:8000/api/surveillance/start" \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{
  "camera_ids": ["0"],
  "detection_types": ["face", "person", "mask"]
}'
```

### 4. Add Family Member
```bash
curl -X POST "http://localhost:8000/api/users/family/register" \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-F "name=John Doe" \
-F "relationship=family" \
-F "image=@path/to/photo.jpg"
```

---

## 🌐 Web Interface Usage

1. **Open Browser**: Go to http://localhost:8000/docs
2. **Try API**: Click "Try it out" on any endpoint
3. **Authenticate**: Use the login endpoint to get a token
4. **Explore**: All endpoints are documented and interactive

---

## 🎥 Camera Configuration

### USB Camera
```bash
# Default camera (index 0) works automatically
# To use a different camera:
export CAMERA_SOURCES=1  # for camera index 1
```

### IP Camera
```bash
# Add IP camera URL to environment
export CAMERA_SOURCES="http://192.168.1.100:8080/video"

# Multiple cameras
export CAMERA_SOURCES="0,http://192.168.1.100:8080/video,rtsp://camera.local/stream"
```

### Video File Testing
```bash
# Use video file for testing
export CAMERA_SOURCES="./test_video.mp4"
```

---

## 🔔 Notification Setup (Optional)

### Email Notifications
```bash
# Edit .env file and add:
ENABLE_EMAIL_NOTIFICATIONS=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

### SMS Notifications (Twilio)
```bash
# Add to .env file:
ENABLE_SMS_NOTIFICATIONS=true
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_FROM_NUMBER=+1234567890
```

---

## 🐳 Docker Deployment (Alternative)

### Quick Docker Start
```bash
# Build and run with Docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production Docker
```bash
# Production deployment
docker-compose -f docker-compose.yml up -d --build

# With SSL and Nginx
docker-compose --profile with-nginx up -d
```

---

## 🧪 Testing Your Setup

### Automated Test Suite
```bash
# Run comprehensive system tests
./test_system.sh

# Expected output: All tests should pass ✅
```

### Manual Testing
```bash
# Check system health
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs

# Test WebSocket (using browser console)
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
```

---

## 🎯 Common Use Cases

### 1. Home Security
```bash
# Start basic home surveillance
python start_server.py

# Register family members via web interface
# Set up email alerts for unknown persons
```

### 2. Business Monitoring
```bash
# Multi-camera setup
export CAMERA_SOURCES="0,1,http://camera1.local,http://camera2.local"
python start_server.py --workers 4

# Configure alerts for business hours
```

### 3. Development & Testing
```bash
# Enable mock cameras for development
export MOCK_CAMERAS=true
export TEST_MODE=true
python start_server.py --dev
```

---

## 🚨 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Solution: Install dependencies
pip install -r requirements_enhanced.txt

# If still failing, try:
pip install --upgrade pip setuptools wheel
pip install -r requirements_enhanced.txt --force-reinstall
```

**2. Camera Not Working**
```bash
# Check camera permissions (Linux/Mac)
sudo chmod 666 /dev/video0

# Test camera manually
python -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print('Camera working:', ret)
cap.release()
"
```

**3. Database Connection Issues**
```bash
# Check internet connection (MongoDB Atlas is cloud-based)
curl -I https://www.google.com

# Verify MongoDB Atlas whitelist includes your IP
# Check MongoDB Atlas dashboard
```

**4. Google Cloud Issues**
```bash
# Check environment variables
echo $GOOGLE_SERVICE_ACCOUNT_KEY
echo $GOOGLE_CLOUD_PROJECT_ID

# Test Google Cloud connection (after installing requirements)
python -c "
from guardia.utils import google_cloud
result = google_cloud.test_connection()
print('Google Cloud services:', result)
"
```

### Performance Optimization

**1. CPU Usage Too High**
```bash
# Reduce detection frequency
export FRAME_SKIP_COUNT=5  # Process every 5th frame

# Lower confidence thresholds
export FACE_DETECTION_CONFIDENCE=0.7
```

**2. Memory Usage High**
```bash
# Reduce buffer size
export MAX_FRAMES_BUFFER=10

# Enable auto-cleanup
export ENABLE_AUTO_CLEANUP=true
```

---

## 📞 Support & Resources

### 📚 Documentation
- **Full Documentation**: [README_ENHANCED.md](README_ENHANCED.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **API Reference**: http://localhost:8000/docs (when running)

### 🔧 Configuration Files
- **Environment Settings**: `.env` (main configuration with all credentials)
- **Application Config**: `guardia/config/settings.py`
- **Docker**: `docker-compose.yml`

### 🎯 Quick Commands
```bash
# Start system
python start_server.py

# Run tests
./test_system.sh

# View logs
tail -f storage/logs/app.log

# Check system status
curl http://localhost:8000/health
```

---

## 🚀 What's Next?

1. **Web Interface**: Build a frontend using the API
2. **Mobile App**: Create mobile alerts and controls
3. **Advanced AI**: Add custom detection models
4. **Integration**: Connect with smart home systems
5. **Scaling**: Deploy on cloud platforms

---

**🎉 You're all set! The Guardia AI system is ready to protect your space with advanced AI surveillance.**

**Need help? Check the troubleshooting section above or refer to the full documentation.**
