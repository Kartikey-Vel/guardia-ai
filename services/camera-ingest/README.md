# Camera Ingest Service

Manages RTSP/ONVIF camera connections and publishes frames to the preprocessing pipeline.

## Features

- Multi-camera support
- Automatic reconnection on failure
- Frame rate limiting
- ZeroMQ frame publishing
- Health monitoring via Redis
- RESTful API for status and management

## Configuration

Edit `config/cameras.yaml`:

```yaml
cameras:
  - camera_id: cam_01
    name: Front Entrance
    url: rtsp://192.168.1.100/stream
    username: admin
    password: password
    fps: 10
    enabled: true
    roi:
      x: 0
      y: 0
      width: 1920
      height: 1080
```

## Environment Variables

- `PORT`: HTTP API port (default: 8001)
- `ZMQ_PORT`: ZeroMQ publisher port (default: 5555)
- `REDIS_URL`: Redis connection URL
- `CONFIG_PATH`: Path to cameras.yaml
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

## API Endpoints

- `GET /health` - Health check
- `GET /status` - Service status with all cameras
- `GET /cameras` - List all cameras
- `GET /cameras/{camera_id}` - Get specific camera status

## Development

```bash
pip install -r requirements.txt
python src/main.py
```

## Docker Build

```bash
docker build -t guardia-camera-ingest .
docker run -p 8001:8001 -p 5555:5555 -v $(pwd)/config:/app/config guardia-camera-ingest
```
