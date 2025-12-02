# Camera Manager Service

Advanced camera management system for Guardia AI supporting multiple camera types including DroidCam, USB webcams, IP cameras, and RTSP streams.

## Features

### Multi-Camera Support
- **DroidCam Integration**: Connect Android/iOS devices as IP cameras
- **USB Webcams**: Detect and manage built-in and external USB cameras
- **IP Cameras**: Support for ONVIF and RTSP protocols
- **Maximum 10 concurrent camera streams**

### Camera Management
- **Auto-Discovery**: Automatically detect available cameras on the network
- **Hot-Plug Support**: Handle camera connections/disconnections gracefully
- **Priority System**: Define camera priority for failover scenarios
- **Health Monitoring**: Real-time camera health and status tracking

### Failover Mechanisms
- **Automatic Reconnection**: Retry failed connections with exponential backoff
- **Priority Failover**: Switch to backup cameras when primary fails
- **Connection Pooling**: Maintain persistent connections for reliability
- **Heartbeat Monitoring**: Detect and respond to camera failures quickly

### Stream Management
- **Adaptive Quality**: Adjust stream quality based on bandwidth
- **Frame Rate Control**: Configurable FPS per camera
- **ROI Support**: Define regions of interest for each camera
- **Synchronized Streams**: Timestamp synchronization across cameras

## Configuration

```yaml
camera_manager:
  max_cameras: 10
  discovery_enabled: true
  discovery_interval: 30
  reconnect_attempts: 5
  reconnect_delay: 5
  heartbeat_interval: 10
  
cameras:
  - id: cam_laptop
    type: usb
    device_index: 0
    name: "Laptop Camera"
    priority: 1
    enabled: true
    
  - id: cam_droidcam_1
    type: droidcam
    host: 192.168.1.150
    port: 4747
    name: "Phone Camera 1"
    priority: 2
    enabled: true
    
  - id: cam_droidcam_2
    type: droidcam
    host: 192.168.1.151
    port: 4747
    name: "Phone Camera 2"
    priority: 3
    enabled: true
```

## API Endpoints

### Camera Management
- `GET /cameras` - List all cameras
- `GET /cameras/{camera_id}` - Get camera details
- `POST /cameras` - Add new camera
- `PUT /cameras/{camera_id}` - Update camera config
- `DELETE /cameras/{camera_id}` - Remove camera
- `POST /cameras/{camera_id}/start` - Start camera stream
- `POST /cameras/{camera_id}/stop` - Stop camera stream

### Discovery
- `POST /discovery/scan` - Scan network for cameras
- `GET /discovery/droidcam` - Find DroidCam devices
- `GET /discovery/usb` - List USB cameras

### Streaming
- `GET /stream/{camera_id}` - Get MJPEG stream
- `WS /ws/stream/{camera_id}` - WebSocket stream
- `GET /snapshot/{camera_id}` - Get current frame

### Health
- `GET /health` - Service health check
- `GET /status` - Detailed status of all cameras

## DroidCam Setup

1. Install DroidCam app on your phone
2. Connect phone to same network as Guardia AI
3. Note the IP address shown in DroidCam app
4. Add camera with type "droidcam" and the IP address
5. System will auto-detect and connect

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_MANAGER_PORT` | 8010 | Service port |
| `MAX_CAMERAS` | 10 | Maximum concurrent cameras |
| `DISCOVERY_ENABLED` | true | Enable auto-discovery |
| `REDIS_URL` | redis://redis:6379 | Redis connection |
| `ZMQ_PUB_PORT` | 5554 | ZeroMQ publisher port |
