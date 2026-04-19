# Guardia AI

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=26&pause=1000&color=2ECC71&center=true&vCenter=true&width=920&lines=Real-Time+Multimodal+Surveillance+MVP;FastAPI+%2B+AI+Fusion+%2B+Live+Dashboard;Threat+Detection+to+Action+in+Seconds" alt="Guardia AI typing banner" />
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/Quick%20Start-5%20Minutes-0ea5e9?style=for-the-badge" alt="Quick Start" /></a>
  <a href="#system-architecture"><img src="https://img.shields.io/badge/Architecture-Multimodal-16a34a?style=for-the-badge" alt="Architecture" /></a>
  <a href="#api-highlights"><img src="https://img.shields.io/badge/API-FastAPI-f97316?style=for-the-badge" alt="API" /></a>
  <a href="#architecture-and-flow-suite"><img src="https://img.shields.io/badge/Flows-Architecture%20Suite-ef4444?style=for-the-badge" alt="Architecture Suite" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-059669?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Frontend-Next.js%2014-111827?logo=nextdotjs&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/Database-SQLite-0f766e?logo=sqlite&logoColor=white" alt="SQLite" />
  <img src="https://img.shields.io/badge/Realtime-WebSocket-7c3aed" alt="WebSocket" />
  <img src="https://img.shields.io/badge/License-MIT-22c55e" alt="MIT License" />
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/View-License-22c55e?style=flat-square" alt="View License" /></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/Contributing-Guide-0284c7?style=flat-square" alt="Contributing Guide" /></a>
</p>

---

## Premium Snapshot

<p align="center">
  <table>
    <tr>
      <td align="center"><strong>Detection Pipeline</strong><br />Motion + Vision + Fusion</td>
      <td align="center"><strong>Real-Time UX</strong><br />WebSocket-driven live alerts</td>
      <td align="center"><strong>Storage Layer</strong><br />SQLite event logging</td>
      <td align="center"><strong>Deployment Target</strong><br />Backend + Dashboard ready</td>
    </tr>
  </table>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Latency_Target-%3C500ms-16a34a?style=flat-square" alt="Latency Target" />
  <img src="https://img.shields.io/badge/Alert_Severity-1_to_10-f59e0b?style=flat-square" alt="Severity Scale" />
  <img src="https://img.shields.io/badge/Detection_Models-Motion%20%7C%20Vision%20%7C%20Fusion-0ea5e9?style=flat-square" alt="Detection Models" />
  <img src="https://img.shields.io/badge/Mode-Live%20and%20Demo-ef4444?style=flat-square" alt="Live and Demo" />
</p>

---

## What Is Guardia AI?
Guardia AI is a real-time multimodal surveillance MVP that turns live camera feeds into actionable security alerts.

It combines:
- Computer vision motion analysis
- AI vision reasoning
- LLM-based fusion logic
- Real-time alert broadcasting
- Dashboard-first monitoring workflow

The goal is to help operators detect and prioritize incidents faster by generating severity-scored alerts with context.

---

## Module Shields

### Backend Module
<p>
  <img src="https://img.shields.io/badge/FastAPI-Routing-059669?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI Routing" />
  <img src="https://img.shields.io/badge/SQLAlchemy-ORM-8b5cf6?style=flat-square" alt="SQLAlchemy ORM" />
  <img src="https://img.shields.io/badge/WebSocket-Live%20Broadcast-7c3aed?style=flat-square" alt="WebSocket Broadcast" />
  <img src="https://img.shields.io/badge/OpenCV-Motion%20Detection-16a34a?style=flat-square" alt="OpenCV Motion" />
</p>

### AI Module
<p>
  <img src="https://img.shields.io/badge/Gemini-Vision%20Analysis-0ea5e9?style=flat-square" alt="Gemini Vision" />
  <img src="https://img.shields.io/badge/Groq-Fusion%20Controller-f97316?style=flat-square" alt="Groq Fusion" />
  <img src="https://img.shields.io/badge/Fallback-Rule%20Based-64748b?style=flat-square" alt="Rule Based Fallback" />
</p>

### Frontend Module (Planned Structure)
<p>
  <img src="https://img.shields.io/badge/Next.js-Dashboard-111827?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js Dashboard" />
  <img src="https://img.shields.io/badge/HeroUI-Component%20System-ec4899?style=flat-square" alt="HeroUI" />
  <img src="https://img.shields.io/badge/Recharts-Analytics-14b8a6?style=flat-square" alt="Recharts" />
</p>

---

## System Architecture
```mermaid
flowchart LR
    A[Camera Feed / RTSP] --> B[OpenCV Motion Detector]
    A --> C[Vision AI Analyzer]
    D[Audio Signals] --> E[Audio Detector]
    B --> F[Fusion Controller]
    C --> F
    E --> F
    F --> G[FastAPI Backend]
    G --> H[(SQLite)]
    G --> I[WebSocket Alerts]
    I --> J[Next.js Dashboard]
```

---

## Architecture and Flow Suite

### 1) High-Level Context Diagram
```mermaid
flowchart TB
    U[Security Operator] --> F[Guardia Dashboard]
    C1[Webcam / RTSP] --> B[Backend Processing Node]
    M1[Mic / Audio Input] --> B
    B --> A1[AI Services\nGemini • Groq • Local Fallback]
    B --> DB[(SQLite Event Store)]
    B --> WS[WebSocket Alert Channel]
    WS --> F
    B --> API[REST API]
    API --> F
```

### 2) Runtime Processing Flow
```mermaid
flowchart LR
    F0[Capture Frame] --> F1[Motion Analysis]
    F1 --> F2{Analyze Now?}
    F2 -->|No| F6[Update Status Stream]
    F2 -->|Yes| F3[Vision AI Inference]
    F3 --> F4[Fusion Controller]
    F4 --> F5{Severity >= Threshold}
    F5 -->|Yes| F7[Persist Event]
    F7 --> F8[Broadcast Alert]
    F5 -->|No| F6
    F8 --> F6
    F6 --> F9[Dashboard Refresh]
```

### 3) Alert Lifecycle Sequence
```mermaid
sequenceDiagram
    participant Cam as Camera
    participant Pipe as AI Pipeline
    participant Fuse as Fusion Controller
    participant API as FastAPI
    participant DB as SQLite
    participant WS as WebSocket Manager
    participant UI as Dashboard

    Cam->>Pipe: Stream frame
    Pipe->>Pipe: Motion detection
    Pipe->>Fuse: Vision + Motion + Context
    Fuse-->>Pipe: Final classification + severity
    Pipe->>API: Create event payload
    API->>DB: Insert event record
    API->>WS: Publish ALERT
    WS-->>UI: Push real-time alert
    UI->>API: Fetch summary/trends
    API-->>UI: Updated analytics
```

### 4) Deployment Topology
```mermaid
flowchart LR
    subgraph Client
      B1[Browser]
    end

    subgraph AppLayer
      FE[Next.js Frontend]
      BE[FastAPI Backend]
      WSS[WebSocket Endpoint]
    end

    subgraph DataLayer
      SQL[(SQLite)]
    end

    subgraph AIProviders
      G1[Gemini Vision]
      G2[Groq LLM]
      G3[Local/Ollama Fallback]
    end

    B1 --> FE
    FE --> BE
    FE --> WSS
    BE --> SQL
    BE --> G1
    BE --> G2
    BE --> G3
```

### 5) Data Model Relationship View
```mermaid
flowchart TB
    CAM[Cameras]
    EVT[Events]
    SET[Settings]

    CAM -->|camera_id| EVT
    EVT -->|classification, severity, confidence| EVT
    SET -->|alert_threshold, analysis_interval| EVT
    EVT -->|timestamped analytics| RPT[Summary and Trends]
```

---

## API Highlights
Base URL:
```bash
http://localhost:8000
```

Important routes:
- GET /api/v1/status
- GET /api/v1/events
- GET /api/v1/events/recent
- PATCH /api/v1/events/{event_id}/review
- GET /api/v1/cameras
- POST /api/v1/cameras
- GET /api/v1/cameras/{camera_id}/snapshot
- GET /api/v1/analytics/summary
- GET /api/v1/analytics/trends
- GET /api/v1/settings
- POST /api/v1/settings
- POST /api/v1/settings/test-connection
- WS /ws/alerts

Quick health test:
```bash
curl http://localhost:8000/api/v1/status
```

---

<details>
  <summary><strong>Quick Start</strong></summary>

### 1) Clone
```bash
git clone https://github.com/codernotme/guardia-ai.git
cd guardia-ai
```

### 2) Create and Activate Virtual Environment (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3) Install Dependencies
If you create a backend requirements file from the SDLC plan:
```powershell
pip install -r backend/requirements.txt
```

### 4) Configure Environment
Create .env with keys:
```env
GEMINI_API_KEY=
GROQ_API_KEY=
HUGGINGFACE_API_KEY=
ALERT_THRESHOLD=5
ANALYSIS_INTERVAL_FRAMES=30
DATABASE_URL=sqlite:///./guardia.db
```

### 5) Run Backend
```powershell
python backend/main.py
```

### 6) Run Frontend
```powershell
cd frontend
npm install
npm run dev
```

</details>

---

<details>
  <summary><strong>Current Repository Snapshot</strong></summary>

This repository currently includes:
- Complete product and engineering blueprint in GUARDIA_AI_SDLC.md
- Backend schema models in backend_schemas.py
- Extra backend API route modules in backend_api_extras.py

The SDLC document also defines the intended backend/frontend folder structure, contracts, and implementation plan.

</details>

---

<details>
  <summary><strong>Roadmap and Delivery Status</strong></summary>

- [x] Product requirements and architecture drafted
- [x] API contracts documented
- [x] Core schemas defined
- [x] Supplemental backend routes drafted
- [ ] End-to-end backend package finalized in repository tree
- [ ] Frontend package finalized in repository tree
- [ ] Deployment and public demo URLs

</details>

---

<details>
  <summary><strong>Feature Highlights</strong></summary>

| Capability | What It Does | Benefit |
|---|---|---|
| Motion Detection | Detects scene activity from video frames | Triggers fast anomaly checks |
| Vision AI Analysis | Classifies scene threats and confidence | Adds semantic understanding |
| Fusion Controller | Combines motion, vision, and context | Produces final severity and action hints |
| Real-Time Alerts | Streams events over WebSocket | Enables instant operator response |
| Event Logging | Stores incidents in SQLite | Supports audits and analytics |
| Dashboard UX | Live feed, alerts, analytics, settings | End-to-end operator workflow |

</details>

---

## Repository Map
- GUARDIA_AI_SDLC.md: Full agile package, architecture, contracts, implementation blueprint
- backend_schemas.py: Pydantic request/response schemas
- backend_api_extras.py: Additional API route modules for settings and cameras
- CONTRIBUTING.md: Contribution workflow and standards
- LICENSE: MIT license terms

---

## Team
- Aryan Bajpai: Scrum Master, Backend AI Lead
- Omisha Singh: Frontend Lead
- Kartikey Mishra: AI Models and Fusion Logic
- Ayushman Dwivedi: DevOps, Database, Backend API

---

## Contributing
Read CONTRIBUTING.md for setup, branch naming, commit style, pull request checklist, and review expectations.

---

## License
This project is licensed under the MIT License. See LICENSE for full text.
