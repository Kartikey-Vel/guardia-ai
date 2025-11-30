# MotionStream - Motion Anomaly Detection

Temporal convolutional network for detecting unusual motion patterns using optical flow.

## Features

- Optical flow analysis (Farneback method)
- Temporal sequence modeling (8-frame buffer)
- Motion feature extraction:
  - Magnitude statistics
  - Direction variance
  - Motion density
- Anomaly scoring and thresholding

## Detection Capabilities

- Sudden movements in restricted zones
- Unusual velocity patterns
- Erratic motion trajectories
- Crowd disturbances
- Object drops/falls

## Model Architecture

- **Input**: Motion feature sequences (8 frames × 4 features)
- **Output**: Anomaly probability [0, 1]
- **Framework**: Temporal Conv1D layers → ONNX

## Configuration

- `MODEL_PATH`: ONNX model path
- `ANOMALY_THRESHOLD`: Detection threshold (default: 0.7)
- `SEQUENCE_LENGTH`: Temporal window (default: 8 frames)

## API Endpoints

- `GET /health` - Health check
- `GET /status` - Model status
