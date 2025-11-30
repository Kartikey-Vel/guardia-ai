# MoodTiny - Privacy-First Micro-Expression Analysis

Lightweight CNN for emotion and mood detection with privacy protection.

## Features

- Face detection (Haar Cascade)
- Mood classification (6 classes):
  - Neutral
  - Stress
  - Aggression
  - Sadness
  - Fear
  - Anxiety
- Privacy-first aggregation
- Multi-face support

## Privacy Protection

**Privacy Mode** (enabled by default):
- Outputs only aggregated mood statistics
- No individual face identification
- No identity linking
- Face count and distribution only

**Non-Privacy Mode** (opt-in):
- Per-face mood analysis
- Detailed probabilities
- Face-specific confidence scores

## Model Architecture

- **Input**: Grayscale face ROI (48×48)
- **Output**: Mood probabilities (6 classes)
- **Framework**: Lightweight CNN → ONNX

## Configuration

- `PRIVACY_MODE`: Enable privacy protection (default: true)
- `MODEL_PATH`: ONNX model path
- `CONFIDENCE_THRESHOLD`: Minimum confidence (default: 0.6)
- `MIN_FACE_SIZE`: Minimum face size in pixels (default: 48)

## API Endpoints

- `GET /health` - Health check
- `GET /status` - Model status
