# Guardia AI 🛡️

**Advanced Privacy-First On-Premise Security Intelligence System**

Guardia AI transforms traditional CCTV networks into proactive, real-time threat detection platforms using adaptive AI models, lightweight decision engines, and seamless integration with existing cameras.

---

## 🚀 What Guardia AI Does

Guardia AI continuously analyzes live video streams from CCTV cameras to identify:

### 1. **Suspicious or Dangerous Human Actions**
- Fights and aggressive behavior
- Falls and medical emergencies
- Running or sudden aggressive movement
- Trespassing
- Unusual hand movements or threatening poses

### 2. **Motion Anomalies**
- Unexpected movement in restricted zones
- Sudden drops or collapses
- Crowd disturbances
- Abnormal motion patterns

### 3. **Emotional & Micro-Expression Cues**
- Stress, aggression, sadness, neutrality
- Crowd mood dynamics
- Privacy-first approach (no identity linking)

### 4. **Real-Time Event Classification & Severity Scoring**
Using the **FusionController** decision engine, Guardia AI:
- Aggregates outputs from multiple specialized models
- Assigns severity levels to events
- Determines whether an alert or recording should be triggered
- Provides transparent reasoning for every decision

---

## 🏗️ Architecture Overview

```mermaid
flowchart LR
  subgraph EDGE["Edge Node (on-prem device)"]
    Camera[Camera (RTSP/ONVIF)]
    Ingest[Camera Ingest Service]
    Preproc[Preprocessing Service]
    subgraph Models["Model Suite"]
      Skele[SkeleGNN]
      Motion[MotionStream]
      Mood[MoodTiny]
    end
    Fusion[FusionController]
    LocalDB[Local DB (SQLite / RocksDB)]
    Storage[Local Object Store (MinIO)]
    Alerts[Alerting Service (WS/Push)]
    OperatorUI[Operator Web UI (Next.js)]
  end

  subgraph CLOUD["Optional Cloud / Central"]
    API[Central API (FastAPI)]
    Postgres[(PostgreSQL)]
    Analytics[Analytics / Dashboard]
    ModelRegistry[Model Registry / Artifacts]
  end

  Camera --> Ingest --> Preproc --> Models
  Models --> Fusion --> LocalDB
  Fusion --> Alerts --> OperatorUI
  Fusion --> Storage
  OperatorUI -->|API Calls| API
  API --> Postgres
  Fusion -->|opt-in sync| API
  ModelRegistry -->|deploy| Models
  Analytics --> Postgres
```

---

## 🛠️ Tech Stack (MVP)

### **Edge (On-Premise Device)**
- **OS:** Ubuntu 22.04 / Ubuntu Server
- **Runtime:** Python 3.11
- **Model Runtime:** PyTorch (training), ONNX Runtime (inference)
- **Acceleration:** Optional TensorRT / OpenVINO
- **Video I/O:** GStreamer / OpenCV
- **IPC/Messaging:** ZeroMQ / MQTT
- **Database:** SQLite (local state), RocksDB (indexing)
- **Cache:** Redis (optional, for deduplication)

### **Backend / Cloud (Optional)**
- **API:** FastAPI (Python)
- **Auth:** JWT + API keys, Clerk / Auth0 (optional)
- **Database:** PostgreSQL + TimescaleDB (time-series)
- **Message Broker:** Kafka / RabbitMQ
- **Object Storage:** S3-compatible (MinIO for self-hosted)
- **Monitoring:** Prometheus + Grafana

### **Model Development**
- **Frameworks:** PyTorch, ONNX
- **Models:** SkeleGNN, MotionStream, MoodTiny
- **Tooling:** Weights & Biases / MLflow

### **Frontend / Admin**
- **Framework:** Next.js (React + TypeScript)
- **UI Kit:** TailwindCSS + Radix UI
- **Real-time:** WebSockets / WebRTC
- **Mobile/Push:** Firebase Cloud Messaging (optional)

### **DevOps**
- **Containerization:** Docker, docker-compose
- **Orchestration:** Kubernetes (future)
- **CI/CD:** GitHub Actions
- **Secrets:** Hashicorp Vault / GitHub Secrets
- **Logging:** ELK stack / Loki + Grafana

---

## 📁 Repository Structure

```
guardia-ai/
├── README.md
├── docker-compose.yml
├── .gitignore
├── infra/
│   ├── k8s/                      # Kubernetes manifests (future)
│   └── docker/                   # Docker scripts
├── services/
│   ├── camera-ingest/            # RTSP/ONVIF ingestion
│   ├── preprocessing/            # Frame preprocessing
│   ├── models/
│   │   ├── skelegnn/             # Skeleton-based action detection
│   │   ├── motionstream/         # Motion anomaly detection
│   │   ├── moodtiny/             # Micro-expression analysis
│   │   └── common/               # Shared model utilities
│   ├── fusion-controller/        # Decision engine
│   ├── api/                      # FastAPI backend
│   ├── storage/                  # MinIO wrapper
│   └── alerts/                   # Alert delivery
├── web/                          # Next.js operator dashboard
├── ml/                           # Training experiments
│   ├── data/
│   └── experiments/
├── scripts/                      # Utility scripts
├── docs/
│   ├── architecture.md
│   └── deployment.md
├── tests/
└── .github/
    └── workflows/                # CI/CD pipelines
```

---

## 🚦 Quick Start

### **Prerequisites**
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for web dashboard)
- NVIDIA GPU (optional, for acceleration)

### **1. Clone the Repository**
```bash
git clone https://github.com/codernotme/guardia.git
cd guardia
```

### **2. Start All Services (Docker Compose)**
```bash
docker-compose up -d
```

### **3. Access the Operator Dashboard**
Open your browser to: `http://localhost:3000`

### **4. Configure Cameras**
Edit `config/cameras.yaml` to add your RTSP/ONVIF camera URLs.

---

## 🔒 Privacy & Security

- **Local-First Design:** All data stays on-premise by default
- **Face Blur:** Privacy mode blurs faces in processed frames
- **Encryption:** At-rest encryption for clips and events
- **TLS:** Secure communication for all API endpoints
- **Role-Based Access Control:** Operator/Admin permissions
- **Audit Logs:** Full traceability for decisions and actions
- **Opt-In Cloud Sync:** Explicit consent required for data upload

---

## 📊 Hardware Requirements

### **Minimum (CPU-only)**
- 8 vCPU
- 16GB RAM
- 500GB SSD (for clip storage)
- 1 Gbps LAN

### **Recommended (GPU-accelerated)**
- NVIDIA T4 / Jetson Xavier NX
- 12 vCPU
- 32GB RAM
- 1TB SSD
- 1 Gbps LAN

---

## 🧪 Model Suite

### **SkeleGNN** (Skeletal Action Recognition)
- Extracts skeleton keypoints
- Classifies actions (fight, fall, run, trespass, etc.)
- Lightweight GNN architecture

### **MotionStream** (Motion Anomaly Detection)
- Optical flow-based analysis
- Detects unusual movement patterns
- Works in low-light & crowded scenes

### **MoodTiny** (Micro-Expression Analysis)
- Privacy-first mood estimation
- Detects stress, aggression, sadness, neutrality
- Aggregated output (no identity linking)

### **FusionController** (Decision Engine)
- Aggregates all model outputs
- Assigns event severity
- Provides explainability and attribution
- Configurable rules and thresholds

---

## 📖 Documentation

- [Architecture Overview](docs/architecture.md)
- [Deployment Guide](docs/deployment.md)
- [API Reference](docs/api.md)
- [Model Training](ml/experiments/README.md)

---

## 🤝 Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📜 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with ❤️ for privacy-conscious security professionals.

**Guardia AI** - Proactive Security, Zero Compromise.