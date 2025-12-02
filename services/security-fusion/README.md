# Security Fusion Model Service

Advanced multi-modal security model for owner protection and home security with facial recognition, anomaly detection, and multi-person tracking.

## Features

### Facial Recognition
- **Owner Identification**: Recognize authorized household members
- **Visitor Detection**: Detect unknown persons
- **Face Encoding**: Secure storage of facial embeddings
- **Liveness Detection**: Anti-spoofing protection

### Multi-Person Tracking
- **Kalman Filter Tracking**: Smooth trajectory tracking
- **Re-identification**: Track persons across camera views
- **Behavior Analysis**: Detect suspicious movement patterns
- **Crowd Analytics**: Monitor multiple people simultaneously

### Anomaly Detection
- **Unusual Activity**: Detect abnormal behaviors
- **Intrusion Detection**: Identify unauthorized access
- **Loitering Detection**: Flag extended presence in areas
- **Time-based Rules**: Different rules for day/night

### Security Alerts
- **Real-time Notifications**: Instant threat alerts
- **Severity Scoring**: Prioritize security events
- **Multi-camera Correlation**: Cross-camera event linking
- **Evidence Collection**: Auto-capture of incidents

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 Security Fusion Model                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    Face      │  │   Person     │  │   Anomaly    │       │
│  │ Recognition  │  │  Tracking    │  │  Detection   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                  │               │
│         └─────────────────┼──────────────────┘               │
│                           ▼                                  │
│                   ┌───────────────┐                          │
│                   │ Multi-Modal   │                          │
│                   │   Fusion      │                          │
│                   └───────┬───────┘                          │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐               │
│         ▼                 ▼                 ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Owner      │  │   Security   │  │    Event     │       │
│  │   Database   │  │    Rules     │  │   Publisher  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Face Management
- `POST /faces/enroll` - Enroll a new face
- `GET /faces` - List enrolled faces
- `DELETE /faces/{face_id}` - Remove enrolled face
- `POST /faces/recognize` - Recognize face in image

### Person Tracking
- `GET /tracking/active` - Get active tracked persons
- `GET /tracking/history` - Get tracking history
- `POST /tracking/reset` - Reset tracking state

### Security Rules
- `GET /rules` - List security rules
- `POST /rules` - Create security rule
- `PUT /rules/{rule_id}` - Update rule
- `DELETE /rules/{rule_id}` - Delete rule

### Alerts
- `GET /alerts` - Get recent alerts
- `POST /alerts/{alert_id}/acknowledge` - Acknowledge alert

## Configuration

```yaml
security_fusion:
  # Face recognition
  face_recognition:
    model: hog  # hog or cnn
    tolerance: 0.6
    min_face_size: 50
    liveness_detection: true
    
  # Person tracking
  tracking:
    max_age: 30  # frames
    min_hits: 3
    iou_threshold: 0.3
    
  # Anomaly detection
  anomaly:
    loitering_threshold: 60  # seconds
    intrusion_zones: []
    night_mode_start: 22
    night_mode_end: 6
    
  # Security rules
  rules:
    - name: unknown_person
      severity: medium
      action: alert
    - name: intrusion
      severity: critical
      action: alert_and_record
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECURITY_FUSION_PORT` | 8012 | Service port |
| `FACE_MODEL` | hog | Face detection model |
| `FACE_TOLERANCE` | 0.6 | Recognition tolerance |
| `REDIS_URL` | redis://redis:6379 | Redis connection |
| `EMBEDDINGS_PATH` | /app/data/embeddings | Face embeddings storage |
