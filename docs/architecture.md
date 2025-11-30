# Guardia AI Architecture

## System Overview

Guardia AI is a privacy-first, edge-computing security intelligence platform that transforms standard CCTV networks into intelligent threat detection systems. The architecture follows a **microservices pattern** with **edge-first processing** and **optional cloud sync**.

## Core Principles

1. **Privacy First** - All processing on-premise by default
2. **Edge Computing** - AI inference at the edge (no cloud dependency)
3. **Modular Design** - Independent, loosely-coupled services
4. **Explainable AI** - Transparent decision-making with attribution
5. **Scalable** - Horizontal scaling via containers and orchestration

---

## Architecture Layers

### 1. **Data Ingestion Layer**

**Camera Ingest Service**
- Connects to RTSP/ONVIF camera streams
- Handles multi-camera support with automatic reconnection
- Frame rate limiting and buffering
- Health monitoring

**Input:** RTSP/ONVIF streams  
**Output:** Raw frames via ZeroMQ (pub/sub)  
**Protocol:** ZeroMQ PUB on port 5555

### 2. **Preprocessing Layer**

**Preprocessing Service**
- Frame normalization and resizing
- Privacy protection (face blur)
- ROI (Region of Interest) extraction
- Optical flow computation for motion analysis
- Frame deduplication

**Input:** Raw frames from Camera Ingest  
**Output:** Preprocessed frames + optical flow  
**Protocol:** ZeroMQ SUB → PUB (topics: `skele_input`, `motion_input`, `mood_input`)

### 3. **AI Inference Layer**

Three specialized model services running in parallel:

#### **SkeleGNN (Skeleton-based Action Recognition)**
- Extracts skeletal keypoints (17 COCO joints)
- Temporal sequence analysis (16-frame buffer)
- Action classification: fight, fall, running, trespassing, etc.
- **Framework:** PyTorch → ONNX Runtime

#### **MotionStream (Motion Anomaly Detection)**
- Optical flow feature extraction
- Temporal convolutional network
- Detects unusual motion patterns
- **Framework:** Temporal CNN → ONNX

#### **MoodTiny (Micro-Expression Analysis)**
- Privacy-first emotion detection
- Aggregated mood estimation (no identity linking)
- Detects stress, aggression, anxiety, etc.
- **Framework:** Lightweight CNN → ONNX

**Input:** Preprocessed frames  
**Output:** Standardized JSON events with confidence scores  
**Protocol:** ZeroMQ SUB → PUB

### 4. **Decision Layer**

**FusionController**
- Aggregates outputs from all models
- Rule-based + lightweight ensemble decision engine
- Weighted confidence scoring
- Context-aware severity classification (low/medium/high/critical)
- Explainability via attribution tracking
- Event persistence in SQLite

**Decision Rules:**
```python
{
  "fight": {
    "required_models": ["skelegnn"],
    "weights": {"skelegnn": 0.7, "motionstream": 0.2, "moodtiny": 0.1},
    "min_confidence": 0.75,
    "severity": "critical",
    "action": "alert_immediately"
  }
}
```

**Input:** Model outputs  
**Output:** Event decisions with severity and suggested actions  
**Storage:** SQLite database

### 5. **Notification Layer**

**Alerting Service**
- WebSocket server for real-time alerts
- Webhook support for external integrations
- Severity filtering
- Multi-client broadcast

**Input:** Events from FusionController  
**Output:** Real-time alerts via WebSocket and webhooks  
**Protocol:** WebSocket + HTTP webhooks

### 6. **Storage Layer**

**MinIO (S3-compatible Object Storage)**
- Stores video clips for events
- Short retention policy (configurable)
- Presigned URLs for secure access

**SQLite (Local Database)**
- Event metadata and history
- Model contributions and attribution
- Camera configurations

### 7. **API Layer (Optional Cloud)**

**FastAPI Backend**
- RESTful API for event management
- Model registry and versioning
- Analytics and reporting
- JWT authentication
- PostgreSQL + TimescaleDB for time-series data

### 8. **Presentation Layer**

**Next.js Operator Dashboard**
- Live camera preview (WebRTC/MJPEG)
- Real-time event timeline
- Clip playback from object storage
- Severity filtering and search
- Event acknowledgment and resolution
- Role-based access control (operator/admin)

---

## Data Flow

```
Camera Stream (RTSP)
    ↓
Camera Ingest Service
    ↓ (ZeroMQ frames topic)
Preprocessing Service
    ↓ (ZeroMQ skele/motion/mood topics)
    ├→ SkeleGNN Model
    ├→ MotionStream Model
    └→ MoodTiny Model
    ↓ (ZeroMQ model_output topics)
FusionController
    ↓ (ZeroMQ event topic)
    ├→ SQLite (persistence)
    ├→ MinIO (clip storage)
    └→ Alerting Service
        ↓ (WebSocket)
    Operator Dashboard
```

---

## Communication Protocols

### Inter-Service Communication

- **ZeroMQ PUB/SUB** - High-throughput, low-latency messaging
  - Topic-based routing
  - No broker overhead
  - Fire-and-forget pattern

- **Redis** - State synchronization and caching
  - Frame deduplication
  - Health monitoring
  - Recent alerts cache

### External APIs

- **FastAPI** - RESTful HTTP/HTTPS
- **WebSocket** - Bidirectional real-time communication
- **Webhooks** - HTTP POST for external integrations

---

## Deployment Topologies

### 1. **Single-Node Edge Deployment** (MVP)
All services on one machine:
- Docker Compose orchestration
- Suitable for 1-4 cameras
- CPU-only or single GPU

### 2. **Multi-Node Edge Cluster**
Services distributed across multiple edge nodes:
- Kubernetes orchestration
- Camera ingest on dedicated nodes
- Model inference on GPU nodes
- Shared storage (NFS/Ceph)

### 3. **Hybrid Edge-Cloud**
Edge processing with cloud analytics:
- Edge: Real-time inference and alerting
- Cloud: Historical analytics, model retraining, centralized management
- Opt-in data sync with encryption

---

## Security & Privacy

### Privacy Protection
- **Face Blur** - Default privacy mode in preprocessing
- **Local-First** - All data stays on-premise by default
- **Aggregated Output** - MoodTiny outputs crowd-level stats only
- **No Identity Tracking** - No biometric identification

### Security Measures
- **Encryption at Rest** - SQLite and MinIO with encryption
- **TLS/HTTPS** - All external APIs
- **JWT Authentication** - Token-based auth for operators
- **Role-Based Access Control** - Operator vs. Admin permissions
- **Audit Logs** - All decisions and actions logged with attribution

---

## Scalability

### Horizontal Scaling
- **Camera Ingest** - One instance per N cameras
- **Model Services** - Scale based on inference load
- **FusionController** - Stateless, can run multiple instances
- **Load Balancing** - ZeroMQ naturally load-balances across subscribers

### Vertical Scaling
- **GPU Acceleration** - TensorRT/OpenVINO for model inference
- **Model Quantization** - INT8 quantization for 4x speedup
- **Batching** - Process multiple frames per inference call

---

## Monitoring & Observability

### Metrics (Prometheus)
- Frame processing rate
- Inference latency per model
- Event generation rate
- Alert delivery success rate
- Service health status

### Dashboards (Grafana)
- Real-time performance metrics
- Event severity distribution
- Camera status overview
- Model accuracy tracking

### Logging
- Structured logging (JSON)
- Centralized aggregation (ELK/Loki)
- Debug/info/warn/error levels

---

## Failure Handling

### Service Resilience
- **Automatic Reconnection** - Camera streams and ZeroMQ sockets
- **Health Checks** - All services expose `/health` endpoint
- **Graceful Degradation** - System operates with subset of models
- **Retry Logic** - Transient failures handled automatically

### Data Persistence
- **SQLite WAL Mode** - Crash-resistant writes
- **MinIO Replication** - Multi-node object storage redundancy
- **Event Queue** - Redis-backed buffer for alert delivery

---

## Model Development & Deployment

### Training Pipeline
1. Collect labeled data from operator feedback
2. Train models using PyTorch
3. Export to ONNX format
4. Quantize for edge deployment (INT8)
5. Validate accuracy and latency
6. Deploy via Model Registry

### Model Registry
- Versioned model artifacts (S3)
- Metadata: accuracy, latency, hardware requirements
- Rollback support
- A/B testing capability

---

## Future Enhancements

### Phase 2
- Clip extraction and smart cropping
- Human-in-the-loop labeling interface
- Model retraining automation
- Mobile operator app (PWA)
- Integration with alarm systems (SMS/SIP)

### Phase 3
- Multi-camera tracking and fusion
- Predictive analytics (anomaly forecasting)
- 3D scene reconstruction
- Advanced NLP for incident reports
- Federated learning across deployments

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Ingestion | OpenCV, GStreamer | Video capture |
| Messaging | ZeroMQ | Inter-service communication |
| Inference | ONNX Runtime | Model execution |
| Acceleration | TensorRT, OpenVINO | GPU/VPU optimization |
| Storage | SQLite, MinIO | Persistence |
| Cache | Redis | State & deduplication |
| API | FastAPI | REST endpoints |
| Frontend | Next.js, React | Operator UI |
| Monitoring | Prometheus, Grafana | Metrics & dashboards |
| Orchestration | Docker Compose, Kubernetes | Deployment |
| CI/CD | GitHub Actions | Automation |

---

**Guardia AI** - Privacy-first intelligence at the edge.
