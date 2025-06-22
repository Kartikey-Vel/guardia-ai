# 🔥 Guardia AI Desktop Application

**Modern AI-Powered Surveillance System with Advanced GUI**

![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blue)
![OpenCV](https://img.shields.io/badge/Vision-OpenCV-green)
![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Essential GUI dependencies
pip install customtkinter pillow opencv-python

# Or install from requirements
pip install -r requirements_desktop.txt
```

### 2. Launch the Application
```bash
# Simple launch
python3 desktop_app.py

# Or use the launcher script
./launch_desktop.sh
```

### 3. Camera Demo (Simple Test)
```bash
# Test camera without GUI
python3 camera_demo.py
```

---

## 🎯 Features

### 🖥️ **Modern GUI Interface**
- **CustomTkinter** - Beautiful, modern interface with dark/light themes
- **Real-time Video Display** - Live camera feed with overlay information
- **Responsive Design** - Scales beautifully on different screen sizes
- **Intuitive Controls** - Professional surveillance system interface

### 📹 **Camera Management**
- **Multi-Camera Support** - USB, IP cameras, video files
- **Real-time Preview** - 30 FPS live video feed
- **Recording** - MP4 video recording with timestamps
- **Screenshots** - Instant snapshot capture
- **Auto-detection** - Automatic camera discovery

### 🧠 **AI Detection (Advanced Mode)**
- **Face Recognition** - Identify known vs unknown persons
- **Object Detection** - YOLO-powered object tracking
- **Smart Alerts** - Real-time detection notifications
- **Confidence Scoring** - Adjustable detection thresholds

### 📊 **Performance Monitoring**
- **Real-time Statistics** - FPS, detection count, uptime
- **Performance Graphs** - Visual performance tracking
- **Resource Usage** - Memory and CPU monitoring
- **Detection Analytics** - Historical detection data

---

## 🎨 Interface Overview

### Main Window Layout
```
┌─ Sidebar (300px) ─┬─── Main Content (1100px) ────┐
│                   │                              │
│ 🔥 Guardia AI     │  📹 Camera Feed              │
│                   │                              │
│ 📹 Camera Control │  [Live Video Display]       │
│ ▶️ Start Monitor  │                              │
│ ⏺️ Record         │                              │
│                   │                              │
│ 🧠 AI Detection   │  📊 Detection Overlays      │
│ ☑️ Face Recog     │                              │
│ ☑️ Object Detect  │                              │
│                   │                              │
│ 📊 Statistics     │  🎛️ Controls                │
│ FPS: 30.0         │  Camera: USB (0)             │
│ Detections: 42    │  Resolution: 1280x720        │
│ Uptime: 00:45:32  │  Status: 🟢 LIVE            │
│                   │                              │
│ ⚙️ Settings       │                              │
│ ℹ️ About          │                              │
└───────────────────┴──────────────────────────────┘
```

### Key Components

#### 🎛️ **Control Panel**
- **Start/Stop Monitoring** - Toggle camera feed
- **Recording Controls** - Start/stop video recording
- **Detection Toggles** - Enable/disable AI features
- **Camera Selection** - Choose between available cameras

#### 📊 **Statistics Display**
- **Real-time FPS** - Current frame rate
- **Detection Count** - Total detections made
- **Session Uptime** - Time since monitoring started
- **Resource Usage** - System performance metrics

#### 🖼️ **Video Display**
- **Live Camera Feed** - Real-time video stream
- **Detection Overlays** - Bounding boxes and labels
- **Status Indicators** - Connection and recording status
- **Info Overlays** - FPS, timestamp, camera info

---

## 💻 Operating Modes

### 🟢 **Full AI Mode** (Recommended)
```bash
# Install complete dependencies
pip install -r requirements_enhanced.txt

# Features available:
✅ Advanced face recognition
✅ YOLO object detection  
✅ Smart behavior analysis
✅ Google Cloud AI integration
✅ Real-time alerts
✅ Database storage
```

### 🟡 **Basic Mode** (OpenCV Only)
```bash
# Minimal installation
pip install customtkinter opencv-python pillow

# Features available:
✅ Modern GUI interface
✅ Real-time camera feed
✅ Basic face detection (OpenCV)
✅ Video recording
✅ Screenshot capture
⚠️ Limited AI features
```

### 🔴 **Camera-Only Mode**
```bash
# Features available:
✅ Live camera display
✅ Video recording
✅ Screenshot capture
❌ No AI detection
```

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `SPACE` | Toggle monitoring |
| `R` | Toggle recording |
| `D` | Toggle detection |
| `S` | Take snapshot |
| `ESC` | Stop all operations |
| `F11` | Toggle fullscreen |

---

## 📁 File Structure

```
guardia-ai/
├── desktop_app.py              # Main GUI application
├── camera_demo.py              # Simple camera test
├── launch_desktop.sh           # Launcher script
├── requirements_desktop.txt    # GUI dependencies
├── desktop_config.env          # Configuration file
├── recordings/                 # Video recordings
├── snapshots/                  # Screenshot captures
├── screenshots/                # Demo screenshots
└── guardia/                    # Full AI system (optional)
    ├── core/                   # AI detection modules
    ├── models/                 # Data models
    └── config/                 # Configuration
```

---

## 🔧 Configuration

### Camera Settings
```env
# desktop_config.env
DEFAULT_CAMERA_INDEX=0
DEFAULT_RESOLUTION=1280x720
DEFAULT_FPS=30
```

### UI Preferences
```env
THEME=dark                    # dark, light
WINDOW_WIDTH=1400
WINDOW_HEIGHT=900
SHOW_DETECTION_BOXES=true
```

### Performance
```env
MAX_FRAME_BUFFER=10
DETECTION_INTERVAL=0.1
UI_UPDATE_INTERVAL=0.033
```

---

## 🚨 Troubleshooting

### Common Issues

#### **"Camera not found"**
```bash
# Check available cameras
ls /dev/video*

# Test with different index
# In app: change camera selector to USB Camera (1)
```

#### **"GUI not displaying"**
```bash
# Linux: Ensure X11 forwarding
export DISPLAY=:0

# Install GUI dependencies
pip install customtkinter pillow
```

#### **"Low FPS"**
```bash
# Reduce resolution
# In app: change to 640x480

# Disable detection temporarily
# Click "Enable Detection" toggle
```

#### **"AI features disabled"**
```bash
# Install full dependencies
pip install -r requirements_enhanced.txt

# Configure credentials
cp .env.example .env
# Edit .env with your settings
```

---

## 🔄 Updates & Maintenance

### Regular Updates
```bash
# Update dependencies
pip install --upgrade customtkinter opencv-python

# Update AI models (if available)
pip install --upgrade ultralytics face-recognition
```

### Performance Optimization
```bash
# Clear old recordings
rm recordings/*.mp4

# Clear screenshots
rm snapshots/*.jpg

# Reset configuration
cp desktop_config.env.example desktop_config.env
```

---

## 📞 Support

### Quick Help
- **F1** - Show help dialog (in app)
- **ℹ️ About** - Version and feature info
- **⚙️ Settings** - Configuration options

### Documentation
- See `README.md` for full system documentation
- Check `CREDENTIALS_GUIDE.md` for AI setup
- Review `DEPLOYMENT_GUIDE.md` for advanced features

---

## 🎉 What's Next?

1. **Try the Basic Demo**
   ```bash
   python3 camera_demo.py
   ```

2. **Launch the Full GUI**
   ```bash
   ./launch_desktop.sh
   ```

3. **Enable AI Features**
   ```bash
   pip install -r requirements_enhanced.txt
   # Configure .env file
   ```

4. **Explore Advanced Features**
   - Multi-camera setups
   - Cloud AI integration
   - Smart alerting system
   - Web interface access

---

**🔥 Welcome to the future of AI surveillance!**
