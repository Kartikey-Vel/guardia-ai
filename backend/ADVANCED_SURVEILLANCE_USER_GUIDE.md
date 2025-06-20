# 🛡️ Guardia AI Advanced Surveillance System - User Guide

## 🚀 Quick Start

### Windows Users
1. **Double-click** `start_guardia_ai_surveillance.bat`
2. **Login** with your credentials
3. **Select option 2**: Advanced Live Surveillance
4. **Press 'q'** in the camera window to quit

### Command Line Users
```bash
cd guardia-ai/src
python main.py
# Select option 2: Advanced Live Surveillance
```

---

## 🎯 Features Overview

### 🧠 **AI-Powered Intelligence**
- **Face Recognition**: Identifies family members vs strangers
- **Context-Aware Alerts**: Different priorities based on who's present
- **Motion Detection**: Advanced background subtraction analysis
- **Threat Detection**: Integration with Google Cloud AI

### 🚨 **Alert System**
- **CRITICAL**: Unknown person alone (no family present)
- **HIGH**: Potential threats detected
- **MEDIUM**: Unknown person with family member present
- **LOW**: General notifications

### 📱 **Notification Types**
- **Real-time Console Alerts**: Immediate on-screen notifications
- **Email Notifications**: For critical alerts (configurable)
- **Alert Logging**: JSON logs saved to `logs/surveillance_alerts.json`

---

## ⚙️ Configuration

### Surveillance Settings
You can modify settings in the `AdvancedSurveillanceSystem` class:

```python
settings = {
    'face_recognition_threshold': 0.6,      # Face match sensitivity
    'unknown_person_alert_delay': 30,       # Seconds before alerting
    'fire_detection_confidence': 0.7,       # Fire detection threshold
    'intruder_timeout': 300,                # 5 minutes tracking timeout
    'motion_sensitivity': 1000,             # Motion detection threshold
    'alert_cooldown': 60,                   # Prevent spam alerts (seconds)
}
```

### Adding Family Members
1. Login to the system
2. When prompted, select "y" to add family members
3. Provide name, relation, and photo for face recognition

---

## 🎥 Camera Requirements

### Supported Cameras
- **Built-in webcams** (laptops)
- **USB cameras** (external webcams)
- **IP cameras** (with proper configuration)

### Optimal Conditions
- **Good lighting** for better face recognition
- **Stable camera position** for motion detection
- **Clear view** of the monitored area

---

## 📊 Alert Examples

### Critical Alert Example
```
🚨 CRITICAL ALERT: INTRUDER_DETECTED
⏰ Time: 2025-06-12 16:36:47
   👤 Person ID: unknown_0
   ⏱️ Time Present: 30.4 seconds
   📍 Location: (153, 392, 395, 150)

📱 IMMEDIATE NOTIFICATION:
📧 To: owner@example.com
💬 Message: 🚨 SECURITY ALERT: Unknown person detected at 16:36:47. 
           No authorized persons present.
```

### Medium Priority Alert
```
🚨 MEDIUM ALERT: UNKNOWN_PERSON
⏰ Time: 2025-06-12 14:22:15
   👤 Person ID: unknown_1
   ⏱️ Time Present: 35.1 seconds
   📍 Location: (200, 450, 350, 250)
   ✅ Authorized person also present
```

---

## 🛠️ Troubleshooting

### Common Issues

#### Camera Not Detected
```
❌ Failed to read from camera
```
**Solutions:**
- Check camera connections
- Close other apps using the camera
- Try a different camera (change index in code)
- Restart the application

#### Face Recognition Not Available
```
⚠️ Face recognition not available - using basic detection
```
**Solutions:**
- Install face_recognition: `pip install face-recognition`
- Install dlib dependencies
- System will fall back to basic face detection

#### Import Errors
```
❌ Advanced surveillance not available: ImportError
```
**Solutions:**
- Install required dependencies: `pip install -r requirements.txt`
- Check Python environment
- Verify module paths

### Dependency Installation

#### Core Dependencies
```bash
pip install opencv-python
pip install numpy
pip install pymongo
pip install google-cloud-videointelligence
```

#### Optional (Enhanced Face Recognition)
```bash
pip install cmake
pip install dlib
pip install face-recognition
```

---

## 📁 File Structure

### Important Files
- `src/main.py` - Main application entry point
- `src/modules/advanced_surveillance.py` - Core surveillance system
- `logs/surveillance_alerts.json` - Alert history
- `config/settings.py` - Configuration settings

### Log Files
- `logs/surveillance_alerts.json` - All surveillance alerts
- `logs/cloud_detection_log.txt` - Cloud AI analysis logs

---

## 🔧 Advanced Configuration

### Email Notifications (Future Enhancement)
The system has placeholders for email integration. To enable:
1. Configure SMTP settings in `config/settings.py`
2. Update `_send_immediate_notification()` method
3. Add email credentials

### Cloud AI Enhancement
- Google Cloud Video Intelligence is integrated
- Configure `gaurdia-ai-*.json` service account key
- Set environment variables for Google Cloud

### Database Integration
- MongoDB integration for user/family data
- Configure connection string in `config/settings.py`
- Automatic fallback to demo mode if unavailable

---

## 📈 Performance Optimization

### For Better Performance
- **Reduce frame processing frequency** (currently 0.5s intervals)
- **Adjust motion sensitivity** for your environment
- **Optimize camera resolution** (currently 640x480)
- **Configure alert cooldowns** to prevent spam

### Memory Management
- System uses background workers for processing
- Queue-based architecture prevents memory buildup
- Automatic cleanup of old tracking data

---

## 🔒 Security Considerations

### Privacy
- All processing is done locally (except cloud AI features)
- Face data is stored in memory only
- Alert logs contain minimal personal information

### Access Control
- System requires login credentials
- Family member verification through photos
- Alert notifications include timestamp and location data

---

## 📞 Support

### Getting Help
1. Check this user guide first
2. Review error messages in console
3. Check log files for detailed information
4. Verify camera and dependency installation

### System Status Check
Run the deployment verification script:
```bash
python deployment_verification.py
```

---

## 🎯 Production Deployment Checklist

- ✅ Python 3.7+ installed
- ✅ Required dependencies installed
- ✅ Camera accessible
- ✅ User accounts configured
- ✅ Family member photos added (optional)
- ✅ Alert settings configured
- ✅ Log directories writable
- ✅ Google Cloud credentials (optional)

**Ready for deployment! 🚀**
