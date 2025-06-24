# Guardia AI Camera Management Guide

## Overview
Guardia AI now supports multiple camera sources including:
- **Local webcams** (USB cameras, built-in cameras)
- **IP cameras** (HTTP/HTTPS streaming cameras)
- **RTSP streams** (Professional security cameras)
- **Smart camera QR code onboarding** (CareCam-style setup)

## Quick Start

### 1. Launch the Dashboard
```bash
cd guardia-ai
python -m guardia_ai.ui.dashboard
```

### 2. Camera Management
In the dashboard, you'll find two new buttons:
- **Camera Management**: Add, remove, and manage camera sources
- **QR Connection**: Generate QR codes for smart camera onboarding

### 3. Adding Cameras

#### Local Webcams
1. Click "Camera Management"
2. Click "Scan Local Cameras"
3. Select detected cameras from the list
4. Click "Set Active" to use the camera

#### IP Cameras
1. Click "Camera Management" 
2. Click "Add IP Camera"
3. Enter camera details:
   - **Name**: Friendly name (e.g., "Front Door Camera")
   - **URL**: Camera stream URL (e.g., `http://192.168.1.100:8080/video`)
   - **Type**: Select "IP Camera" or "RTSP Stream"
   - **Description**: Optional notes

#### Smart Camera QR Code Setup
1. Click "QR Connection" in the dashboard
2. A QR code will be displayed with connection information
3. Smart cameras (like CareCam) can scan this code to auto-configure
4. The camera will connect to Guardia AI's web server at `http://[your-ip]:8080`

## Camera Configuration

### Persistent Storage
Camera configurations are saved in `~/.guardia_ai/camera_config.json` and persist between sessions.

### Web Server for Smart Cameras
- Runs on port 8080 by default
- Provides a web interface at `http://[your-ip]:8080`
- Smart cameras can POST their connection details to auto-register

### Supported Camera URLs
- **HTTP streams**: `http://camera-ip:port/stream`
- **RTSP streams**: `rtsp://camera-ip:port/stream`
- **M-JPEG streams**: `http://camera-ip:port/mjpeg`

## Features

### Real-time Feed Display
- The dashboard shows the active camera feed in real-time
- Face detection and object detection work with all camera types
- Automatic reconnection if camera disconnects

### Camera Status
- Connection status displayed in dashboard
- Error messages for troubleshooting
- Visual indicators for active cameras

### Multi-Camera Support
- Add multiple cameras and switch between them
- Each camera maintains its own connection settings
- Easy switching via the camera management dialog

## Troubleshooting

### Camera Not Detected
1. Check camera permissions (Linux may require `sudo` or adding user to `video` group)
2. Verify camera is not being used by another application
3. Try different camera indices (0, 1, 2, etc.)

### IP Camera Connection Issues
1. Verify the camera URL is correct
2. Check network connectivity to the camera
3. Ensure camera supports the specified stream format
4. Check firewall settings

### QR Code Connection Problems
1. Ensure your device and smart camera are on the same network
2. Check that port 8080 is not blocked by firewall
3. Verify the IP address in the QR code is accessible from the camera

## Advanced Configuration

### Custom Web Server Port
Edit the camera manager initialization in `dashboard.py`:
```python
web_server = CameraWebServer(camera_manager, port=8888)
```

### Camera Stream Settings
Modify camera properties in `camera_manager.py`:
```python
self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
self.cap.set(cv2.CAP_PROP_FPS, 30)
```

## Security Considerations
- The web server is intended for local network use only
- Consider using HTTPS for production deployments
- Implement authentication for sensitive environments
- Regularly update camera firmware

## API for Smart Cameras

Smart cameras can connect by POSTing to `http://[guardia-ip]:8080/connect`:
```json
{
    "name": "Camera Name",
    "stream_url": "http://camera-ip:port/stream",
    "camera_type": "ip",
    "description": "Camera Description"
}
```

Response:
```json
{
    "status": "success",
    "camera_id": "generated-id",
    "message": "Camera added successfully"
}
```
