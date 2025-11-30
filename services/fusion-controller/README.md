# FusionController - Decision Engine

Aggregates outputs from multiple AI models to make intelligent event classification and severity decisions.

## Features

- **Multi-model aggregation** - Combines SkeleGNN, MotionStream, and MoodTiny outputs
- **Weighted confidence scoring** - Configurable model weights per event type
- **Rule-based classification** - Transparent decision rules
- **Severity assessment** - Context-aware severity levels (low/medium/high/critical)
- **Explainability** - Attribution tracking for every decision
- **SQLite storage** - Persistent event history

## Event Classes

- **Fight** - Physical altercations (critical)
- **Fall** - Medical emergencies (high)
- **Trespassing** - Unauthorized access (medium)
- **Motion Anomaly** - Unusual movement patterns (medium)
- **Suspicious Behavior** - Combination of indicators (medium)
- **Crowd Stress** - Elevated stress levels (low)

## Decision Rules

Each event class has:
- Required models (must be present)
- Optional models (enhance confidence)
- Minimum confidence threshold
- Base severity level
- Model weights for aggregation
- Suggested action

## Severity Modifiers

- **Time of day** - Nighttime events escalated
- **Confidence level** - High confidence events escalated
- **Location** - Restricted zones (future)
- **Historical context** - Repeat events (future)

## Database Schema

### Events Table
- `id` - Unique event identifier
- `camera_id` - Source camera
- `timestamp` - Event time
- `event_class` - Classification
- `severity` - Severity level
- `confidence` - Aggregated confidence
- `attribution` - Model contributions
- `status` - pending/acknowledged/resolved

### Model Contributions Table
- Links models to events
- Stores per-model confidence
- Enables attribution analysis

## Configuration

- `DB_PATH`: SQLite database path (default: /app/data/guardia.db)
- `ZMQ_PUB_PORT`: Event publisher port (default: 5560)
- Model subscriber ports configured per model

## API Endpoints

- `GET /health` - Health check
- `GET /status` - Service status and event count
