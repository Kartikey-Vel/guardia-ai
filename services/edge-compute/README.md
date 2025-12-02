# Edge Computing Service

Local edge processing for Guardia AI providing real-time video analysis, bandwidth optimization, and local storage.

## Features

### Real-Time Video Analysis
- **Motion Detection**: Frame differencing with adaptive thresholds
- **Object Detection**: Lightweight YOLO inference
- **Face Detection**: Privacy-aware face detection
- **Scene Change Detection**: Detect significant scene changes

### Bandwidth Optimization
- **Smart Compression**: Adaptive JPEG quality based on content
- **Frame Dropping**: Skip redundant frames
- **ROI Extraction**: Process only regions of interest
- **Delta Encoding**: Send only frame differences

### Local Storage
- **Critical Footage**: Store important clips locally before sync
- **Ring Buffer**: Continuous recording with auto-cleanup
- **Event Snapshots**: Capture frames for detected events
- **Metadata Cache**: Local event metadata storage

### Edge Intelligence
- **Local Inference**: Run models on edge device
- **Event Pre-filtering**: Reduce false positives locally
- **Latency Optimization**: Sub-100ms processing
- **Resource Management**: CPU/GPU load balancing

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Edge Node                         │
│  ┌─────────────┐    ┌──────────────┐                │
│  │   Camera    │───▶│ Edge Compute │                │
│  │   Manager   │    │   Service    │                │
│  └─────────────┘    └──────┬───────┘                │
│                            │                         │
│    ┌───────────────────────┼───────────────────┐    │
│    ▼                       ▼                   ▼    │
│  ┌─────────┐        ┌─────────────┐     ┌──────────┐│
│  │ Motion  │        │   Object    │     │  Local   ││
│  │Detector │        │  Detector   │     │ Storage  ││
│  └────┬────┘        └──────┬──────┘     └────┬─────┘│
│       │                    │                  │      │
│       └────────────────────┼──────────────────┘      │
│                            ▼                         │
│                    ┌───────────────┐                 │
│                    │ Event Filter  │                 │
│                    └───────┬───────┘                 │
│                            │                         │
└────────────────────────────┼─────────────────────────┘
                             ▼
                    ┌───────────────┐
                    │ Cloud Sync    │
                    │ (Optional)    │
                    └───────────────┘
```

## Configuration

```yaml
edge_compute:
  # Processing settings
  motion_threshold: 25
  min_contour_area: 500
  frame_skip: 2
  
  # Storage settings
  local_storage_path: /app/data
  clip_duration: 30
  max_storage_gb: 50
  retention_days: 7
  
  # Bandwidth optimization
  compression_quality: 75
  max_frame_size: 640x480
  delta_encoding: true
  
  # Inference settings
  inference_device: cpu  # cpu, cuda, tensorrt
  batch_size: 1
  model_path: /app/models
```

## API Endpoints

### Processing
- `POST /process/frame` - Process a single frame
- `POST /process/batch` - Process multiple frames
- `GET /process/stats` - Processing statistics

### Storage
- `GET /storage/clips` - List stored clips
- `GET /storage/clips/{clip_id}` - Get clip
- `DELETE /storage/clips/{clip_id}` - Delete clip
- `GET /storage/snapshots` - List snapshots
- `POST /storage/sync` - Sync to cloud

### Monitoring
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /status` - Detailed status

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EDGE_COMPUTE_PORT` | 8011 | Service port |
| `MOTION_THRESHOLD` | 25 | Motion detection sensitivity |
| `LOCAL_STORAGE_PATH` | /app/data | Local storage path |
| `MAX_STORAGE_GB` | 50 | Maximum storage size |
| `INFERENCE_DEVICE` | cpu | Inference device |
| `REDIS_URL` | redis://redis:6379 | Redis connection |
| `MINIO_ENDPOINT` | minio:9000 | MinIO endpoint |
