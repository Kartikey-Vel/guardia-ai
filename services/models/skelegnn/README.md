# SkeleGNN - Skeleton-Based Action Recognition

Graph Neural Network for real-time action classification from skeletal sequences.

## Features

- Skeleton keypoint extraction (17 COCO keypoints)
- Temporal sequence analysis (16-frame buffer)
- Action classification:
  - Normal behavior
  - Fight
  - Fall
  - Running
  - Trespassing
  - Threatening pose
  - Suspicious movement

## Model Architecture

- **Input**: Sequence of skeleton keypoints (16 frames × 17 joints × 3 features)
- **Output**: Action probabilities (7 classes)
- **Framework**: PyTorch → ONNX export

## Configuration

- `MODEL_PATH`: Path to ONNX model weights
- `PREPROCESSING_HOST`: Preprocessing service hostname
- `PREPROCESSING_ZMQ_PORT`: Preprocessing ZeroMQ port
- `ZMQ_PUB_PORT`: Publisher port (default: 5557)
- `PORT`: HTTP API port (default: 8003)

## Integration with Skeleton Extraction

For production deployment, integrate with:
- **MediaPipe Pose** (recommended for edge devices)
- **OpenPose** (higher accuracy, more compute)
- **AlphaPose** (multi-person scenarios)

## API Endpoints

- `GET /health` - Health check
- `GET /status` - Model status and statistics
