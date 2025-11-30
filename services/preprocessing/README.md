# Preprocessing Service

Processes raw camera frames for AI model consumption.

## Features

- Frame resizing and normalization
- Face blur for privacy protection
- ROI (Region of Interest) extraction
- Optical flow computation for motion analysis
- Frame deduplication to reduce redundant processing
- Multi-topic publishing for parallel model inference

## Configuration

Environment variables:

- `FACE_BLUR_ENABLED`: Enable face blurring (default: true)
- `TARGET_WIDTH`: Target frame width (default: 640)
- `TARGET_HEIGHT`: Target frame height (default: 480)
- `CAMERA_INGEST_HOST`: Camera ingest service hostname
- `CAMERA_INGEST_ZMQ_PORT`: Camera ingest ZeroMQ port (default: 5555)
- `ZMQ_PUB_PORT`: Publisher port for models (default: 5556)
- `REDIS_URL`: Redis connection URL
- `LOG_LEVEL`: Logging level

## Processing Pipeline

1. **Receive Frame** - From camera-ingest service via ZeroMQ
2. **Deduplication** - Skip near-identical frames
3. **ROI Extraction** - Extract specified region of interest
4. **Face Blur** - Apply privacy protection (optional)
5. **Optical Flow** - Compute motion features
6. **Resize** - Standardize dimensions
7. **Normalize** - Scale pixel values to [0, 1]
8. **Publish** - Send to model services on multiple topics

## Output Topics

- `skele_input` - For SkeleGNN (action recognition)
- `motion_input` - For MotionStream (anomaly detection)
- `mood_input` - For MoodTiny (emotion analysis)

## API Endpoints

- `GET /health` - Health check
- `GET /status` - Service status and statistics

## Development

```bash
pip install -r requirements.txt
python src/main.py
```
