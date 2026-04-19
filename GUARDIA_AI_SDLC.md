# 🛡️ GUARDIA AI — Complete Agile SDLC Package
### Real-Time Multimodal Surveillance MVP
**Project ID:** 26_CS_4A_12 | **Deadline:** 2 Days | **Institution:** PSIT Kanpur  
**Scrum Master:** Aryan Bajpai | **Supervisor:** Dr. Kumar Saurabh

---

# 📋 TABLE OF CONTENTS
1. [Product Requirements Document (PRD)](#1-product-requirements-document)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack (100% Free)](#3-tech-stack)
4. [Team Assignments & RACI](#4-team-assignments--raci)
5. [Sprint Plan (2-Day Breakdown)](#5-sprint-plan)
6. [User Stories & Acceptance Criteria](#6-user-stories)
7. [API Contracts](#7-api-contracts)
8. [Database Schema](#8-database-schema)
9. [File/Folder Structure](#9-project-structure)
10. [Complete Source Code](#10-source-code)
11. [Deployment Guide](#11-deployment-guide)
12. [Definition of Done](#12-definition-of-done)

---

# 1. PRODUCT REQUIREMENTS DOCUMENT

## 1.1 Executive Summary
Guardia AI is a next-generation, multimodal AI surveillance MVP that transforms standard CCTV feeds into an intelligent, real-time threat detection system. The MVP demonstrates core capabilities using **free AI APIs (Groq, Gemini, Ollama)** and a **Next.js + HeroUI** frontend dashboard.

## 1.2 Problem Statement
| Dimension | Problem |
|-----------|---------|
| Analytical Bottleneck | Humans cannot watch 500+ cameras simultaneously |
| Modality Limitation | Single-camera video misses audio/environmental signals |
| Response Latency | Human detection → response chain takes minutes |
| Scalability | Proprietary systems don't scale or customize |

## 1.3 MVP Scope (2-Day Build)

### ✅ IN SCOPE (Must Have)
- [ ] Live webcam/RTSP video stream ingestion
- [ ] Real-time motion anomaly detection (YOLOv5 via Groq Vision API)
- [ ] AI-powered threat analysis (Gemini Flash free tier)
- [ ] Alert generation with severity scoring (1-10)
- [ ] Real-time dashboard with Next.js + HeroUI
- [ ] WebSocket live alerts feed
- [ ] Event logging to SQLite
- [ ] REST API (FastAPI)
- [ ] Audio anomaly detection (browser Web Audio API)
- [ ] FusionController (rule-based + Groq LLM decision)

### ❌ OUT OF SCOPE (Future)
- Federated learning
- Custom model training
- Production cloud deployment
- Biometric database integration

## 1.4 Success Metrics
| Metric | Target |
|--------|--------|
| End-to-end detection latency | < 500ms (MVP, not edge hardware) |
| False Positive Rate | < 20% |
| Dashboard load time | < 2 seconds |
| Uptime during demo | 99% |
| AI API response | < 3 seconds |

## 1.5 Free AI API Strategy
| API | Use Case | Free Limit | Key |
|-----|----------|------------|-----|
| **Groq API** | Fast LLM inference (Llama 3, Mixtral) for FusionController | 14,400 req/day | groq.com |
| **Google Gemini Flash** | Vision analysis of video frames | 1,500 req/day | ai.google.dev |
| **Ollama (local)** | Fallback local inference, zero cost | Unlimited | ollama.ai |
| **HuggingFace Inference API** | Audio classification | 30,000 chars/month | huggingface.co |
| **OpenCV** | Frame processing, motion detection | Free/local | — |

---

# 2. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUARDIA AI MVP                           │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────────────────────────┐   │
│  │  DATA INPUT  │    │         EDGE PROCESSING NODE          │   │
│  │              │    │                                      │   │
│  │ 📷 Webcam    │───▶│  ┌─────────┐  ┌──────────────────┐  │   │
│  │ 📷 RTSP URL  │    │  │OpenCV   │  │  AI MODELS       │  │   │
│  │ 🎤 Microphone│    │  │Frame    │─▶│  ┌─ YOLOv5 via   │  │   │
│  │ 📡 IoT Sim   │    │  │Extractor│  │  │  Gemini Vision │  │   │
│  └──────────────┘    │  └─────────┘  │  ├─ Motion Stream │  │   │
│                      │               │  │  (OpenCV)      │  │   │
│                      │               │  ├─ Audio Detect  │  │   │
│                      │               │  │  (WebAudio)    │  │   │
│                      │               │  └─ FusionCtrl   │  │   │
│                      │               │     (Groq LLM)   │  │   │
│                      │               └──────────────────┘  │   │
│                      │                        │             │   │
│                      │               ┌────────▼──────────┐  │   │
│                      │               │  FastAPI Backend   │  │   │
│                      │               │  SQLite Database   │  │   │
│                      │               │  WebSocket Server  │  │   │
│                      └───────────────┴───────────────────┘  │   │
│                                       │                      │   │
│  ┌────────────────────────────────────▼──────────────────┐   │   │
│  │              NEXT.JS + HEROUI DASHBOARD                │   │   │
│  │  Live Feed | Alerts Panel | Analytics | Settings      │   │   │
│  └───────────────────────────────────────────────────────┘   │   │
└─────────────────────────────────────────────────────────────────┘
```

## 2.1 Data Flow
```
Camera Frame → OpenCV Extract → Gemini Vision API → Object Detection
                             → OpenCV Motion     → Anomaly Score
                             → Web Audio API     → Sound Events
                                    ↓
                           FusionController (Groq)
                           Severity Score (1-10)
                                    ↓
                    FastAPI → SQLite → WebSocket → Dashboard
```

---

# 3. TECH STACK

## Frontend (Zero Cost)
| Technology | Purpose | Why Free |
|------------|---------|----------|
| **Next.js 14** | React framework | Open source |
| **HeroUI (NextUI)** | UI component library | Open source |
| **Tailwind CSS** | Styling | Open source |
| **Framer Motion** | Animations | Open source |
| **Socket.io-client** | WebSocket client | Open source |
| **Recharts** | Analytics charts | Open source |
| **React-webcam** | Webcam access | Open source |
| **Vercel** | Hosting | Free tier |

## Backend (Zero Cost)
| Technology | Purpose | Why Free |
|------------|---------|----------|
| **Python 3.11** | Language | Open source |
| **FastAPI** | REST + WebSocket | Open source |
| **OpenCV** | Video processing | Open source |
| **SQLite** | Database | Embedded free |
| **SQLAlchemy** | ORM | Open source |
| **ultralytics** | YOLOv5/v8 | Open source |
| **Groq Python SDK** | LLM inference | Free 14k req/day |
| **google-generativeai** | Gemini Vision | Free 1.5k req/day |
| **Ollama** | Local LLM fallback | Completely free |
| **Railway/Render** | Hosting | Free tier |

---

# 4. TEAM ASSIGNMENTS & RACI

## Team Structure
```
┌────────────────────────────────────────────────────────┐
│                   SCRUM TEAM                           │
│                                                        │
│  🧑‍💼 ARYAN BAJPAI    - Scrum Master + Backend AI Lead  │
│  👩‍💻 OMISHA SINGH    - Frontend Lead (Next.js)         │
│  👨‍💻 KARTIKEY MISHRA - AI Models + API Integration     │
│  👨‍💻 AYUSHMAN DWIVEDI- DevOps + Database + Backend API │
└────────────────────────────────────────────────────────┘
```

## RACI Matrix

| Task | Aryan | Omisha | Kartikey | Ayushman |
|------|-------|--------|----------|----------|
| Project architecture | **R** | C | C | C |
| PRD & documentation | **R** | I | I | I |
| Sprint planning | **R** | C | C | C |
| FastAPI server setup | C | I | I | **R** |
| Database schema | C | I | C | **R** |
| WebSocket server | C | I | I | **R** |
| YOLOv5 integration | **R** | I | C | I |
| Gemini Vision API | **R** | I | C | I |
| Groq FusionController | **R** | I | **R** | I |
| Ollama local fallback | C | I | **R** | I |
| Motion detection algo | **R** | I | C | I |
| Audio detection | C | I | **R** | I |
| Dashboard layout | I | **R** | I | C |
| Live video feed UI | I | **R** | C | I |
| Alerts panel UI | I | **R** | I | C |
| Analytics charts | I | **R** | C | I |
| Settings UI | I | **R** | I | C |
| API integration (FE) | C | **R** | I | C |
| Docker compose | I | I | C | **R** |
| Deployment | C | C | I | **R** |
| Testing | **R** | C | C | C |
| Final demo | **R** | C | C | C |

**R** = Responsible | **A** = Accountable | **C** = Consulted | **I** = Informed

---

# 5. SPRINT PLAN

## 🗓️ DAY 1 — Foundation Sprint

### Sprint Goal
"Have a working backend with AI detection + basic dashboard skeleton by end of Day 1"

### Morning Block (9 AM – 1 PM)

#### 🧑‍💼 Aryan Bajpai
```
[ ] TASK-001: Initialize GitHub repo + project structure
[ ] TASK-002: Write requirements.txt + package.json
[ ] TASK-003: Implement OpenCV motion detection module
[ ] TASK-004: Integrate Gemini Vision API for frame analysis
[ ] TASK-005: Daily standup facilitation (15 min)
```

#### 👩‍💻 Omisha Singh
```
[ ] TASK-006: npx create-next-app guardia-ai-frontend
[ ] TASK-007: Install HeroUI + Tailwind setup
[ ] TASK-008: Create app layout (sidebar, topnav, main)
[ ] TASK-009: Build Dashboard page skeleton
[ ] TASK-010: Build Alerts page skeleton
```

#### 👨‍💻 Kartikey Mishra
```
[ ] TASK-011: Set up Groq API + test connection
[ ] TASK-012: Set up Ollama locally (pull llama3)
[ ] TASK-013: Write FusionController class (rule-based layer)
[ ] TASK-014: Write FusionController class (Groq LLM layer)
[ ] TASK-015: Write audio anomaly detection module
```

#### 👨‍💻 Ayushman Dwivedi
```
[ ] TASK-016: FastAPI project setup + folder structure
[ ] TASK-017: SQLite database + SQLAlchemy models
[ ] TASK-018: CRUD API for events (/api/v1/events)
[ ] TASK-019: WebSocket server setup
[ ] TASK-020: Camera management API
```

### Afternoon Block (2 PM – 7 PM)

#### 🧑‍💼 Aryan Bajpai
```
[ ] TASK-021: Pipeline orchestration main.py
[ ] TASK-022: Video stream processor (RTSP + webcam)
[ ] TASK-023: Integrate all AI models into pipeline
[ ] TASK-024: Alert generation module
[ ] TASK-025: Test full backend pipeline end-to-end
```

#### 👩‍💻 Omisha Singh
```
[ ] TASK-026: LiveFeed component (react-webcam integration)
[ ] TASK-027: AlertsPanel component (real-time list)
[ ] TASK-028: SeverityBadge component
[ ] TASK-029: Connect WebSocket to AlertsPanel
[ ] TASK-030: Navbar + Sidebar with HeroUI
```

#### 👨‍💻 Kartikey Mishra
```
[ ] TASK-031: YOLOv5/v8 integration via ultralytics
[ ] TASK-032: Frame annotation (bounding boxes overlay)
[ ] TASK-033: Confidence scoring system
[ ] TASK-034: API routes for model status
[ ] TASK-035: Test Groq + Gemini together
```

#### 👨‍💻 Ayushman Dwivedi
```
[ ] TASK-036: Alert broadcasting via WebSocket
[ ] TASK-037: Background task runner (FastAPI BackgroundTasks)
[ ] TASK-038: CORS setup for frontend
[ ] TASK-039: Environment variables + .env template
[ ] TASK-040: Basic Docker Compose file
```

### End of Day 1 Checkpoint ✅
- [ ] Backend API running on localhost:8000
- [ ] WebSocket broadcasting test alerts
- [ ] Frontend showing live dashboard skeleton
- [ ] At least 1 AI model returning results
- [ ] Database storing events

---

## 🗓️ DAY 2 — Integration & Polish Sprint

### Sprint Goal
"Full MVP working end-to-end with polished UI ready for demo"

### Morning Block (9 AM – 1 PM)

#### 🧑‍💼 Aryan Bajpai
```
[ ] TASK-041: Bug fixes from Day 1 integration
[ ] TASK-042: Optimize API response time
[ ] TASK-043: Add simulated IoT sensor data
[ ] TASK-044: Write API documentation
[ ] TASK-045: Prepare demo scenarios (fight, intrusion, fall)
```

#### 👩‍💻 Omisha Singh
```
[ ] TASK-046: Analytics page (Recharts integration)
[ ] TASK-047: Event history table with filters
[ ] TASK-048: Settings page (API keys, thresholds)
[ ] TASK-049: Severity color coding + animations
[ ] TASK-050: Mobile responsiveness check
```

#### 👨‍💻 Kartikey Mishra
```
[ ] TASK-051: Ollama fallback when Gemini quota hits
[ ] TASK-052: Rate limiting + API key rotation logic
[ ] TASK-053: Improve FusionController accuracy
[ ] TASK-054: Add HuggingFace audio classification
[ ] TASK-055: Model performance logging
```

#### 👨‍💻 Ayushman Dwivedi
```
[ ] TASK-056: Deploy backend to Railway/Render free tier
[ ] TASK-057: Deploy frontend to Vercel
[ ] TASK-058: Environment variable setup in prod
[ ] TASK-059: Health check endpoints
[ ] TASK-060: API rate limiting middleware
```

### Afternoon Block (2 PM – 6 PM)

#### 🧑‍💼 Aryan Bajpai
```
[ ] TASK-061: End-to-end integration testing
[ ] TASK-062: Performance benchmarking
[ ] TASK-063: Create demo video/screenshots
[ ] TASK-064: Final README.md
[ ] TASK-065: Project presentation prep
```

#### 👩‍💻 Omisha Singh
```
[ ] TASK-066: UI polish + Framer Motion animations
[ ] TASK-067: Dark mode implementation
[ ] TASK-068: Loading states + error boundaries
[ ] TASK-069: Logo + branding assets
[ ] TASK-070: Final UI review + bug fixes
```

#### 👨‍💻 Kartikey Mishra
```
[ ] TASK-071: Final AI pipeline testing
[ ] TASK-072: Latency measurement + logging
[ ] TASK-073: Create test cases document
[ ] TASK-074: API keys documentation
[ ] TASK-075: Handover tech notes
```

#### 👨‍💻 Ayushman Dwivedi
```
[ ] TASK-076: Final deployment verification
[ ] TASK-077: Database backup script
[ ] TASK-078: Monitoring setup (logs)
[ ] TASK-079: Final system test on live URLs
[ ] TASK-080: Demo environment preparation
```

### End of Day 2 — Definition of Done ✅
- [ ] Full pipeline working (video → AI → alert → dashboard)
- [ ] Frontend deployed on Vercel (live URL)
- [ ] Backend deployed on Railway (live URL)
- [ ] WebSocket real-time alerts working
- [ ] Analytics charts showing data
- [ ] < 500ms detection latency
- [ ] README complete
- [ ] Demo ready

---

# 6. USER STORIES

## Epic 1: Video Surveillance
```
US-001: As a security operator, I want to see a live camera feed on the dashboard
        so that I can monitor premises in real time.
        
        Acceptance Criteria:
        ✓ Webcam feed displays within 2 seconds of page load
        ✓ RTSP URL can be configured in settings
        ✓ Feed updates at minimum 10 FPS visually
        ✓ "No camera" placeholder shown when unavailable
        
US-002: As a security operator, I want motion to be detected automatically
        so that I don't have to watch the feed constantly.
        
        Acceptance Criteria:
        ✓ Motion triggers within 500ms of event
        ✓ Bounding box overlaid on detected region
        ✓ Sensitivity threshold configurable (1-10)
        ✓ False positive rate < 20% in normal conditions
```

## Epic 2: AI Threat Detection
```
US-003: As a security operator, I want each alert to have a severity score (1-10)
        so that I can prioritize my response.
        
        Acceptance Criteria:
        ✓ Every alert has severity 1-10
        ✓ Color coding: Green(1-3), Yellow(4-6), Red(7-10)
        ✓ Severity derived from FusionController, not single model
        ✓ Attribution shown (which model contributed)
        
US-004: As a security operator, I want AI to classify the type of threat
        so that I know what kind of incident occurred.
        
        Acceptance Criteria:
        ✓ Classification from: [FIGHT, FALL, INTRUSION, RUNNING, 
                                LOITERING, NORMAL, CROWD_SURGE, 
                                UNATTENDED_OBJECT, SUSPICIOUS]
        ✓ Confidence percentage shown
        ✓ AI model used shown in alert detail
        ✓ Timestamp accurate to second
```

## Epic 3: Real-Time Alerts
```
US-005: As a security operator, I want to receive instant alerts
        so that I can respond quickly to incidents.
        
        Acceptance Criteria:
        ✓ Alert appears on dashboard < 1 second after detection
        ✓ Alert panel auto-scrolls to newest alert
        ✓ Alert includes: timestamp, camera, severity, classification
        ✓ Alert count badge updates in navbar
        ✓ Browser notification shown for severity >= 7
        
US-006: As a security operator, I want to see alert history
        so that I can review past incidents.
        
        Acceptance Criteria:
        ✓ Last 100 alerts stored in database
        ✓ Filter by severity, time range, classification
        ✓ Export to CSV available
        ✓ Paginated (20 per page)
```

## Epic 4: Analytics
```
US-007: As a security manager, I want to see analytics charts
        so that I understand threat patterns over time.
        
        Acceptance Criteria:
        ✓ Alerts per hour bar chart
        ✓ Threat type distribution pie chart
        ✓ Severity trend line chart
        ✓ Camera activity heatmap (simulated)
        ✓ Charts update every 30 seconds
```

## Epic 5: Settings & Configuration
```
US-008: As a system administrator, I want to configure API keys and thresholds
        so that I can customize the system behavior.
        
        Acceptance Criteria:
        ✓ API key fields for Groq, Gemini
        ✓ Alert threshold slider (severity 1-10)
        ✓ Camera RTSP URL configuration
        ✓ Settings persisted to database
        ✓ "Test Connection" button for each API
```

---

# 7. API CONTRACTS

## Base URL: `http://localhost:8000`

### 7.1 Events API

```yaml
GET /api/v1/events
  Description: List events with optional filters
  Query Params:
    - limit: int (default: 50)
    - offset: int (default: 0)
    - severity_min: int (1-10)
    - severity_max: int (1-10)
    - classification: string
    - start_time: ISO8601
    - end_time: ISO8601
  Response 200:
    {
      "total": 100,
      "events": [
        {
          "event_id": "uuid",
          "timestamp": "2025-04-19T10:30:00Z",
          "camera_id": "CAM_001",
          "classification": "FIGHT",
          "severity": 8,
          "confidence": 0.94,
          "attribution": {
            "motion": 0.35,
            "vision_ai": 0.45,
            "audio": 0.20
          },
          "description": "Two individuals engaged in physical altercation",
          "ai_model": "gemini-flash + groq-llama3"
        }
      ]
    }

POST /api/v1/events
  Description: Create manual event
  Body:
    {
      "camera_id": "CAM_001",
      "classification": "INTRUSION",
      "severity": 7,
      "description": "Manual report"
    }
  Response 201: { "event_id": "uuid" }

GET /api/v1/events/{event_id}
  Response 200: Single event object

DELETE /api/v1/events/{event_id}
  Response 204: No content
```

### 7.2 Camera API

```yaml
GET /api/v1/cameras
  Response 200:
    {
      "cameras": [
        {
          "camera_id": "CAM_001",
          "name": "Main Entrance",
          "rtsp_url": "rtsp://...",
          "is_active": true,
          "zone": "entrance",
          "risk_level": 3
        }
      ]
    }

POST /api/v1/cameras
  Body: { "name": "string", "rtsp_url": "string", "zone": "string" }

GET /api/v1/cameras/{camera_id}/stream
  Description: Get current frame as base64 JPEG

POST /api/v1/cameras/{camera_id}/analyze
  Description: Trigger manual AI analysis of current frame
  Response 200:
    {
      "detection": { ... },
      "severity": 5,
      "classification": "NORMAL"
    }
```

### 7.3 Analytics API

```yaml
GET /api/v1/analytics/summary
  Response 200:
    {
      "total_alerts_today": 47,
      "high_severity_count": 3,
      "most_active_camera": "CAM_001",
      "avg_severity": 4.2,
      "alerts_by_hour": [...],
      "alerts_by_type": {...}
    }

GET /api/v1/analytics/trends
  Query: ?period=24h|7d|30d
  Response 200:
    { "data_points": [...] }
```

### 7.4 System API

```yaml
GET /api/v1/status
  Response 200:
    {
      "status": "healthy",
      "uptime_seconds": 3600,
      "models": {
        "yolo": "active",
        "gemini": "active",
        "groq": "active",
        "ollama": "fallback_ready"
      },
      "cameras_active": 2,
      "events_today": 47
    }

POST /api/v1/settings
  Body:
    {
      "groq_api_key": "gsk_...",
      "gemini_api_key": "AIza...",
      "alert_threshold": 6,
      "analysis_interval_ms": 2000
    }

GET /api/v1/settings
  Response 200: Current settings (keys redacted)
```

### 7.5 WebSocket

```yaml
WebSocket: ws://localhost:8000/ws/alerts

Server → Client Events:
  {
    "type": "ALERT",
    "payload": {
      "event_id": "uuid",
      "timestamp": "ISO8601",
      "camera_id": "CAM_001",
      "classification": "FIGHT",
      "severity": 9,
      "confidence": 0.94,
      "description": "...",
      "frame_base64": "data:image/jpeg;base64,..."
    }
  }
  
  {
    "type": "STATUS_UPDATE",
    "payload": {
      "cameras_active": 2,
      "processing_fps": 5,
      "models_status": {...}
    }
  }

Client → Server Events:
  { "type": "SUBSCRIBE", "cameras": ["CAM_001"] }
  { "type": "PING" }
```

---

# 8. DATABASE SCHEMA

```sql
-- Events table
CREATE TABLE events (
    event_id    TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    timestamp   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    camera_id   TEXT NOT NULL,
    classification TEXT NOT NULL,
    severity    INTEGER NOT NULL CHECK(severity BETWEEN 1 AND 10),
    confidence  REAL DEFAULT 0.0,
    description TEXT,
    attribution TEXT,  -- JSON string
    ai_model    TEXT,
    frame_ref   TEXT,  -- path to saved frame
    is_reviewed INTEGER DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Cameras table
CREATE TABLE cameras (
    camera_id   TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    rtsp_url    TEXT,
    zone        TEXT DEFAULT 'general',
    risk_level  INTEGER DEFAULT 2 CHECK(risk_level BETWEEN 1 AND 5),
    is_active   INTEGER DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Settings table
CREATE TABLE settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_severity ON events(severity DESC);
CREATE INDEX idx_events_camera ON events(camera_id);
CREATE INDEX idx_events_classification ON events(classification);
```

---

# 9. PROJECT STRUCTURE

```
guardia-ai/
├── README.md
├── .env.example
├── docker-compose.yml
├── .gitignore
│
├── backend/                          # FastAPI Backend
│   ├── main.py                       # App entry point
│   ├── requirements.txt
│   ├── .env
│   ├── config.py                     # Settings management
│   ├── database.py                   # SQLite + SQLAlchemy setup
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── events.py                 # Events CRUD router
│   │   ├── cameras.py                # Camera management router
│   │   ├── analytics.py              # Analytics router
│   │   ├── settings.py               # Settings router
│   │   └── system.py                 # Health/status router
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── event.py                  # SQLAlchemy Event model
│   │   ├── camera.py                 # SQLAlchemy Camera model
│   │   └── schemas.py                # Pydantic schemas
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── pipeline.py               # Main orchestration loop
│   │   ├── motion_detector.py        # OpenCV motion detection
│   │   ├── gemini_vision.py          # Gemini Flash frame analysis
│   │   ├── groq_fusion.py            # Groq LLM FusionController
│   │   ├── ollama_fallback.py        # Ollama local fallback
│   │   ├── audio_detector.py         # Audio anomaly detection
│   │   └── fusion_controller.py      # Main decision engine
│   │
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── manager.py                # WebSocket connection manager
│   │   └── broadcaster.py            # Alert broadcasting
│   │
│   └── utils/
│       ├── __init__.py
│       ├── frame_processor.py        # OpenCV preprocessing
│       ├── alert_manager.py          # Alert creation + storage
│       └── logger.py                 # Logging setup
│
└── frontend/                         # Next.js Frontend
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── .env.local
    │
    ├── app/
    │   ├── layout.tsx                # Root layout
    │   ├── page.tsx                  # Dashboard (redirect)
    │   ├── dashboard/
    │   │   └── page.tsx
    │   ├── alerts/
    │   │   └── page.tsx
    │   ├── analytics/
    │   │   └── page.tsx
    │   └── settings/
    │       └── page.tsx
    │
    ├── components/
    │   ├── layout/
    │   │   ├── Sidebar.tsx
    │   │   ├── Navbar.tsx
    │   │   └── AppLayout.tsx
    │   ├── dashboard/
    │   │   ├── LiveFeed.tsx          # Webcam + frame display
    │   │   ├── AlertsPanel.tsx       # Real-time alert list
    │   │   ├── SystemStatus.tsx      # Model status cards
    │   │   └── StatsCards.tsx        # Quick stat cards
    │   ├── alerts/
    │   │   ├── AlertsTable.tsx
    │   │   ├── AlertDetail.tsx
    │   │   └── SeverityBadge.tsx
    │   ├── analytics/
    │   │   ├── AlertsChart.tsx
    │   │   ├── ThreatPieChart.tsx
    │   │   └── TrendChart.tsx
    │   └── shared/
    │       ├── LoadingSpinner.tsx
    │       └── ErrorBoundary.tsx
    │
    ├── hooks/
    │   ├── useWebSocket.ts           # WS connection hook
    │   ├── useAlerts.ts              # Alerts state management
    │   └── useCamera.ts              # Camera hooks
    │
    ├── lib/
    │   ├── api.ts                    # API client (axios)
    │   └── types.ts                  # TypeScript interfaces
    │
    └── public/
        └── guardia-logo.svg
```

---

# 10. SOURCE CODE

## 10.1 Backend — `requirements.txt`
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-dotenv==1.0.1
sqlalchemy==2.0.30
pydantic==2.7.1
pydantic-settings==2.2.1
opencv-python-headless==4.9.0.80
ultralytics==8.2.0
groq==0.9.0
google-generativeai==0.7.2
requests==2.31.0
pillow==10.3.0
websockets==12.0
python-multipart==0.0.9
aiofiles==23.2.1
httpx==0.27.0
numpy==1.26.4
```

## 10.2 Backend — `main.py`
```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import logging

from database import init_db
from api import events, cameras, analytics, settings, system
from websocket.manager import ws_manager
from ai.pipeline import start_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    logger.info("✅ Database initialized")
    # Start AI pipeline in background
    pipeline_task = asyncio.create_task(start_pipeline())
    logger.info("✅ AI Pipeline started")
    yield
    # Shutdown
    pipeline_task.cancel()
    logger.info("🛑 Pipeline stopped")

app = FastAPI(
    title="Guardia AI API",
    description="Real-Time Multimodal Surveillance System",
    version="1.0.0-mvp",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(cameras.router, prefix="/api/v1/cameras", tags=["Cameras"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(system.router, prefix="/api/v1", tags=["System"])

# WebSocket endpoint
from fastapi import WebSocket, WebSocketDisconnect
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

## 10.3 Backend — `database.py`
```python
# backend/database.py
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

DATABASE_URL = "sqlite:///./guardia.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Event(Base):
    __tablename__ = "events"
    event_id      = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp     = Column(DateTime, default=datetime.utcnow)
    camera_id     = Column(String, nullable=False)
    classification= Column(String, nullable=False)
    severity      = Column(Integer, nullable=False)
    confidence    = Column(Float, default=0.0)
    description   = Column(Text)
    attribution   = Column(Text)  # JSON
    ai_model      = Column(String)
    frame_ref     = Column(String)
    is_reviewed   = Column(Integer, default=0)
    created_at    = Column(DateTime, default=datetime.utcnow)

class Camera(Base):
    __tablename__ = "cameras"
    camera_id     = Column(String, primary_key=True)
    name          = Column(String, nullable=False)
    rtsp_url      = Column(String)
    zone          = Column(String, default="general")
    risk_level    = Column(Integer, default=2)
    is_active     = Column(Integer, default=1)
    created_at    = Column(DateTime, default=datetime.utcnow)

class Setting(Base):
    __tablename__ = "settings"
    key           = Column(String, primary_key=True)
    value         = Column(String, nullable=False)
    updated_at    = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(bind=engine)
    # Seed default camera
    db = SessionLocal()
    if not db.query(Camera).first():
        db.add(Camera(camera_id="CAM_001", name="Main Camera", zone="entrance"))
        db.commit()
    db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## 10.4 Backend — `ai/motion_detector.py`
```python
# backend/ai/motion_detector.py
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class MotionResult:
    detected: bool
    score: float          # 0.0 - 1.0
    contours: list
    frame_delta: Optional[np.ndarray] = None
    description: str = ""

class MotionDetector:
    def __init__(self, sensitivity: float = 0.5):
        self.sensitivity = sensitivity
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=50, detectShadows=False
        )
        self.prev_frame = None
        self.min_contour_area = 500 * (1 - sensitivity)

    def detect(self, frame: np.ndarray) -> MotionResult:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Frame differencing
        if self.prev_frame is None:
            self.prev_frame = gray
            return MotionResult(detected=False, score=0.0, contours=[])
        
        frame_delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        significant_contours = [
            c for c in contours 
            if cv2.contourArea(c) > self.min_contour_area
        ]
        
        # Compute motion score
        motion_pixels = np.sum(fg_mask > 0)
        total_pixels = frame.shape[0] * frame.shape[1]
        score = min(motion_pixels / total_pixels * 10, 1.0)
        
        self.prev_frame = gray
        
        detected = len(significant_contours) > 0 and score > 0.01
        
        description = ""
        if detected:
            if score > 0.3:
                description = "High intensity motion detected across large area"
            elif score > 0.1:
                description = "Moderate motion detected in zone"
            else:
                description = "Minor motion detected"
        
        return MotionResult(
            detected=detected,
            score=score,
            contours=significant_contours,
            frame_delta=frame_delta,
            description=description
        )
    
    def draw_contours(self, frame: np.ndarray, result: MotionResult) -> np.ndarray:
        annotated = frame.copy()
        for contour in result.contours:
            (x, y, w, h) = cv2.boundingRect(contour)
            cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
        if result.detected:
            cv2.putText(annotated, f"MOTION: {result.score:.2f}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return annotated
```

## 10.5 Backend — `ai/gemini_vision.py`
```python
# backend/ai/gemini_vision.py
import google.generativeai as genai
import base64
import json
import logging
from PIL import Image
import io
import numpy as np

logger = logging.getLogger(__name__)

THREAT_PROMPT = """
You are a security AI analyzing a surveillance camera frame.
Analyze this image and respond with ONLY valid JSON (no markdown):
{
  "detected_objects": ["list of objects/people"],
  "activity": "description of what is happening",
  "threat_classification": "one of: NORMAL, FIGHT, FALL, INTRUSION, LOITERING, RUNNING, SUSPICIOUS, UNATTENDED_OBJECT, CROWD_SURGE",
  "threat_confidence": 0.0 to 1.0,
  "severity": 1 to 10,
  "reasoning": "brief explanation",
  "immediate_action_required": true or false
}

Be precise. Focus on security-relevant observations only.
"""

class GeminiVisionAnalyzer:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.request_count = 0
    
    def analyze_frame(self, frame: np.ndarray) -> dict:
        try:
            # Convert numpy frame to PIL Image
            rgb_frame = frame[:, :, ::-1]  # BGR to RGB
            pil_image = Image.fromarray(rgb_frame)
            
            # Resize to reduce API usage
            pil_image.thumbnail((640, 480), Image.LANCZOS)
            
            response = self.model.generate_content([THREAT_PROMPT, pil_image])
            
            # Parse JSON response
            text = response.text.strip()
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            result = json.loads(text)
            self.request_count += 1
            logger.info(f"Gemini analysis: {result['threat_classification']} (severity: {result['severity']})")
            return result
            
        except json.JSONDecodeError as e:
            logger.warning(f"Gemini JSON parse error: {e}")
            return self._default_result()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._default_result()
    
    def _default_result(self) -> dict:
        return {
            "detected_objects": [],
            "activity": "Unable to analyze",
            "threat_classification": "NORMAL",
            "threat_confidence": 0.0,
            "severity": 1,
            "reasoning": "API error or parse failure",
            "immediate_action_required": False
        }
```

## 10.6 Backend — `ai/groq_fusion.py`
```python
# backend/ai/groq_fusion.py
from groq import Groq
import json
import logging

logger = logging.getLogger(__name__)

FUSION_PROMPT = """
You are the FusionController for Guardia AI surveillance system.
You receive outputs from multiple detection models and must make a final decision.

Input data:
{input_data}

Your task:
1. Analyze all model outputs together
2. Assign final threat classification
3. Compute final severity score (1-10)
4. Determine recommended actions

Respond with ONLY valid JSON:
{{
  "final_classification": "FIGHT|FALL|INTRUSION|LOITERING|RUNNING|SUSPICIOUS|NORMAL|CROWD_SURGE|UNATTENDED_OBJECT",
  "final_severity": 1-10,
  "final_confidence": 0.0-1.0,
  "fusion_reasoning": "explanation of how models were combined",
  "recommended_actions": ["list of actions like ALERT_SECURITY, RECORD_CLIP, NOTIFY_ADMIN"],
  "attribution": {{
    "motion_weight": 0.0-1.0,
    "vision_weight": 0.0-1.0,
    "audio_weight": 0.0-1.0,
    "context_weight": 0.0-1.0
  }}
}}
"""

class GroqFusionController:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.model = "llama3-8b-8192"  # Free and fast
    
    def fuse(self, motion_result: dict, vision_result: dict, 
             audio_result: dict = None, context: dict = None) -> dict:
        
        input_data = {
            "motion_detection": {
                "detected": motion_result.get("detected", False),
                "score": motion_result.get("score", 0.0),
                "description": motion_result.get("description", "")
            },
            "vision_ai": {
                "classification": vision_result.get("threat_classification", "NORMAL"),
                "confidence": vision_result.get("threat_confidence", 0.0),
                "severity": vision_result.get("severity", 1),
                "objects": vision_result.get("detected_objects", []),
                "activity": vision_result.get("activity", "")
            },
            "audio": audio_result or {"detected": False, "event": "none"},
            "context": context or {"time_of_day": "day", "zone": "general", "risk_level": 2}
        }
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a security AI making threat assessment decisions. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": FUSION_PROMPT.format(input_data=json.dumps(input_data, indent=2))
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            text = completion.choices[0].message.content.strip()
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            result = json.loads(text)
            logger.info(f"Groq fusion: {result['final_classification']} severity={result['final_severity']}")
            return result
            
        except Exception as e:
            logger.error(f"Groq fusion error: {e}")
            # Rule-based fallback
            return self._rule_based_fallback(motion_result, vision_result)
    
    def _rule_based_fallback(self, motion: dict, vision: dict) -> dict:
        vision_severity = vision.get("severity", 1)
        motion_score = motion.get("score", 0.0)
        
        combined_severity = int(
            vision_severity * 0.7 + motion_score * 10 * 0.3
        )
        combined_severity = max(1, min(10, combined_severity))
        
        return {
            "final_classification": vision.get("threat_classification", "NORMAL"),
            "final_severity": combined_severity,
            "final_confidence": vision.get("threat_confidence", 0.5),
            "fusion_reasoning": "Rule-based fallback (Groq unavailable)",
            "recommended_actions": ["RECORD_CLIP"] if combined_severity > 5 else [],
            "attribution": {
                "motion_weight": 0.30,
                "vision_weight": 0.70,
                "audio_weight": 0.0,
                "context_weight": 0.0
            }
        }
```

## 10.7 Backend — `ai/pipeline.py`
```python
# backend/ai/pipeline.py
import cv2
import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Optional
import numpy as np

from config import get_settings
from database import SessionLocal, Event
from ai.motion_detector import MotionDetector
from ai.gemini_vision import GeminiVisionAnalyzer
from ai.groq_fusion import GroqFusionController
from websocket.manager import ws_manager

logger = logging.getLogger(__name__)

class GuardiaPipeline:
    def __init__(self):
        self.settings = get_settings()
        self.motion_detector = MotionDetector(sensitivity=0.5)
        self.gemini = None
        self.groq_fusion = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.frame_count = 0
        self.analysis_interval = 30  # Analyze every 30 frames (~3 sec at 10fps)
        
    def initialize_ai(self):
        cfg = self.settings
        if cfg.gemini_api_key:
            self.gemini = GeminiVisionAnalyzer(api_key=cfg.gemini_api_key)
            logger.info("✅ Gemini Vision initialized")
        if cfg.groq_api_key:
            self.groq_fusion = GroqFusionController(api_key=cfg.groq_api_key)
            logger.info("✅ Groq FusionController initialized")
    
    def connect_camera(self, source=0):
        """Connect to webcam (0) or RTSP URL"""
        self.cap = cv2.VideoCapture(source)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return self.cap.isOpened()
    
    async def process_frame(self, frame: np.ndarray, camera_id: str = "CAM_001"):
        self.frame_count += 1
        
        # Always run motion detection (fast, local)
        motion = self.motion_detector.detect(frame)
        
        vision_result = {"threat_classification": "NORMAL", "severity": 1, 
                        "threat_confidence": 0.0, "detected_objects": [], "activity": ""}
        fusion_result = None
        
        # Run AI analysis every N frames to save API quota
        should_analyze = (
            self.frame_count % self.analysis_interval == 0 or
            (motion.detected and motion.score > 0.2)
        )
        
        if should_analyze and self.gemini:
            vision_result = self.gemini.analyze_frame(frame)
        
        # Fuse results
        if self.groq_fusion and (motion.detected or vision_result["severity"] > 2):
            fusion_result = self.groq_fusion.fuse(
                motion_result={"detected": motion.detected, "score": motion.score, 
                              "description": motion.description},
                vision_result=vision_result,
                context={"time_of_day": self._get_time_context(), 
                        "zone": "entrance", "risk_level": 2}
            )
        
        # Determine if alert should fire
        final_severity = 1
        final_classification = "NORMAL"
        if fusion_result:
            final_severity = fusion_result["final_severity"]
            final_classification = fusion_result["final_classification"]
        elif motion.detected:
            final_severity = min(int(motion.score * 10) + 2, 7)
            final_classification = "SUSPICIOUS"
        
        # Save event and broadcast if severity >= threshold
        threshold = self.settings.alert_threshold
        if final_severity >= threshold:
            event = await self.save_event(
                camera_id=camera_id,
                classification=final_classification,
                severity=final_severity,
                confidence=vision_result.get("threat_confidence", motion.score),
                description=vision_result.get("activity") or motion.description,
                attribution=fusion_result.get("attribution") if fusion_result else {},
                frame=frame
            )
            
            # Broadcast to WebSocket clients
            frame_b64 = self.frame_to_base64(frame)
            await ws_manager.broadcast(json.dumps({
                "type": "ALERT",
                "payload": {
                    "event_id": event.event_id,
                    "timestamp": event.timestamp.isoformat(),
                    "camera_id": camera_id,
                    "classification": final_classification,
                    "severity": final_severity,
                    "confidence": event.confidence,
                    "description": event.description,
                    "frame_base64": frame_b64,
                    "attribution": fusion_result.get("attribution") if fusion_result else {}
                }
            }))
        
        # Always broadcast status update
        if self.frame_count % 50 == 0:
            await ws_manager.broadcast(json.dumps({
                "type": "STATUS_UPDATE",
                "payload": {
                    "cameras_active": 1,
                    "processing_fps": 10,
                    "motion_score": round(motion.score, 3),
                    "models_status": {
                        "gemini": "active" if self.gemini else "disabled",
                        "groq": "active" if self.groq_fusion else "disabled",
                        "motion": "active"
                    }
                }
            }))
    
    async def save_event(self, **kwargs) -> Event:
        frame = kwargs.pop("frame", None)
        attribution = kwargs.pop("attribution", {})
        
        db = SessionLocal()
        event = Event(
            camera_id=kwargs["camera_id"],
            classification=kwargs["classification"],
            severity=kwargs["severity"],
            confidence=kwargs.get("confidence", 0.0),
            description=kwargs.get("description", ""),
            attribution=json.dumps(attribution),
            ai_model="gemini-flash+groq-llama3"
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        db.close()
        logger.info(f"🚨 Event saved: {event.classification} severity={event.severity}")
        return event
    
    def frame_to_base64(self, frame: np.ndarray) -> str:
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return "data:image/jpeg;base64," + base64.b64encode(buffer).decode()
    
    def _get_time_context(self) -> str:
        hour = datetime.now().hour
        if 6 <= hour < 18:
            return "day"
        elif 18 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    async def run(self):
        self.initialize_ai()
        self.is_running = True
        
        # Try webcam first
        if not self.connect_camera(0):
            logger.warning("No webcam found, using demo mode with simulated data")
            await self.run_demo_mode()
            return
        
        logger.info("✅ Camera connected, pipeline running")
        
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                await asyncio.sleep(0.1)
                continue
            
            await self.process_frame(frame)
            await asyncio.sleep(0.05)  # ~20fps capture
        
        self.cap.release()
    
    async def run_demo_mode(self):
        """Generate simulated events for demo without camera"""
        import random
        logger.info("🎭 Demo mode active")
        
        DEMO_EVENTS = [
            {"classification": "FIGHT", "severity": 9, "confidence": 0.94},
            {"classification": "INTRUSION", "severity": 7, "confidence": 0.87},
            {"classification": "FALL", "severity": 8, "confidence": 0.91},
            {"classification": "LOITERING", "severity": 4, "confidence": 0.76},
            {"classification": "NORMAL", "severity": 1, "confidence": 0.98},
            {"classification": "SUSPICIOUS", "severity": 5, "confidence": 0.72},
        ]
        
        while self.is_running:
            await asyncio.sleep(random.uniform(5, 15))
            event_template = random.choice(DEMO_EVENTS)
            
            db = SessionLocal()
            event = Event(
                camera_id="CAM_001",
                classification=event_template["classification"],
                severity=event_template["severity"],
                confidence=event_template["confidence"],
                description=f"Demo: {event_template['classification']} detected",
                attribution=json.dumps({"motion": 0.35, "vision_ai": 0.45, "audio": 0.20}),
                ai_model="demo-mode"
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            db.close()
            
            await ws_manager.broadcast(json.dumps({
                "type": "ALERT",
                "payload": {
                    "event_id": event.event_id,
                    "timestamp": event.timestamp.isoformat(),
                    "camera_id": "CAM_001",
                    "classification": event.classification,
                    "severity": event.severity,
                    "confidence": event.confidence,
                    "description": event.description,
                    "frame_base64": None,
                    "attribution": {"motion": 0.35, "vision_ai": 0.45, "audio": 0.20}
                }
            }))

pipeline = GuardiaPipeline()

async def start_pipeline():
    await pipeline.run()
```

## 10.8 Backend — `config.py`
```python
# backend/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    gemini_api_key: str = ""
    groq_api_key: str = ""
    huggingface_api_key: str = ""
    alert_threshold: int = 5
    analysis_interval_frames: int = 30
    database_url: str = "sqlite:///./guardia.db"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

## 10.9 Backend — `websocket/manager.py`
```python
# backend/websocket/manager.py
from fastapi import WebSocket
from typing import List
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WS disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for ws in disconnected:
            self.disconnect(ws)
    
    async def handle_message(self, websocket: WebSocket, data: str):
        try:
            msg = json.loads(data)
            if msg.get("type") == "PING":
                await websocket.send_text(json.dumps({"type": "PONG"}))
        except Exception:
            pass

ws_manager = ConnectionManager()
```

## 10.10 Backend — `api/events.py`
```python
# backend/api/events.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
from typing import Optional
import json

from database import get_db, Event
from models.schemas import EventResponse, EventCreate

router = APIRouter()

@router.get("")
def list_events(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    severity_min: Optional[int] = Query(None, ge=1, le=10),
    severity_max: Optional[int] = Query(None, ge=1, le=10),
    classification: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Event)
    if severity_min:
        query = query.filter(Event.severity >= severity_min)
    if severity_max:
        query = query.filter(Event.severity <= severity_max)
    if classification:
        query = query.filter(Event.classification == classification)
    
    total = query.count()
    events = query.order_by(desc(Event.timestamp)).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "events": [
            {
                "event_id": e.event_id,
                "timestamp": e.timestamp.isoformat(),
                "camera_id": e.camera_id,
                "classification": e.classification,
                "severity": e.severity,
                "confidence": e.confidence,
                "description": e.description,
                "attribution": json.loads(e.attribution) if e.attribution else {},
                "ai_model": e.ai_model,
                "is_reviewed": bool(e.is_reviewed)
            }
            for e in events
        ]
    }

@router.get("/recent")
def recent_events(limit: int = 10, db: Session = Depends(get_db)):
    events = db.query(Event).order_by(desc(Event.timestamp)).limit(limit).all()
    return [
        {
            "event_id": e.event_id,
            "timestamp": e.timestamp.isoformat(),
            "camera_id": e.camera_id,
            "classification": e.classification,
            "severity": e.severity,
            "confidence": e.confidence,
            "description": e.description,
        }
        for e in events
    ]

@router.patch("/{event_id}/review")
def mark_reviewed(event_id: str, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.is_reviewed = 1
    db.commit()
    return {"status": "reviewed"}
```

## 10.11 Backend — `api/analytics.py`
```python
# backend/api/analytics.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from collections import defaultdict

from database import get_db, Event

router = APIRouter()

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    total_today = db.query(Event).filter(Event.timestamp >= today_start).count()
    high_severity = db.query(Event).filter(
        Event.timestamp >= today_start, Event.severity >= 7
    ).count()
    
    # Alerts by classification
    by_type = db.query(
        Event.classification, func.count(Event.event_id)
    ).filter(
        Event.timestamp >= today_start
    ).group_by(Event.classification).all()
    
    # Alerts by hour
    by_hour = defaultdict(int)
    recent = db.query(Event).filter(Event.timestamp >= today_start).all()
    for e in recent:
        by_hour[e.timestamp.hour] += 1
    
    # Average severity
    all_severities = [e.severity for e in recent]
    avg_severity = sum(all_severities) / len(all_severities) if all_severities else 0
    
    return {
        "total_alerts_today": total_today,
        "high_severity_count": high_severity,
        "avg_severity": round(avg_severity, 1),
        "alerts_by_type": {cls: count for cls, count in by_type},
        "alerts_by_hour": [{"hour": h, "count": by_hour.get(h, 0)} for h in range(24)],
        "most_active_camera": "CAM_001"
    }

@router.get("/trends")
def get_trends(period: str = "24h", db: Session = Depends(get_db)):
    if period == "24h":
        start = datetime.utcnow() - timedelta(hours=24)
        interval = "hour"
    elif period == "7d":
        start = datetime.utcnow() - timedelta(days=7)
        interval = "day"
    else:
        start = datetime.utcnow() - timedelta(days=30)
        interval = "day"
    
    events = db.query(Event).filter(Event.timestamp >= start).all()
    
    buckets = defaultdict(list)
    for e in events:
        if interval == "hour":
            key = e.timestamp.strftime("%Y-%m-%d %H:00")
        else:
            key = e.timestamp.strftime("%Y-%m-%d")
        buckets[key].append(e.severity)
    
    data_points = [
        {
            "time": k,
            "count": len(v),
            "avg_severity": round(sum(v)/len(v), 1) if v else 0
        }
        for k, v in sorted(buckets.items())
    ]
    
    return {"period": period, "data_points": data_points}
```

## 10.12 Backend — `api/system.py`
```python
# backend/api/system.py
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()
_start_time = datetime.utcnow()

@router.get("/status")
def get_status():
    from ai.pipeline import pipeline
    uptime = (datetime.utcnow() - _start_time).seconds
    return {
        "status": "healthy",
        "uptime_seconds": uptime,
        "models": {
            "gemini": "active" if pipeline.gemini else "disabled",
            "groq": "active" if pipeline.groq_fusion else "disabled",
            "motion": "active",
            "ollama": "fallback_ready"
        },
        "cameras_active": 1,
        "demo_mode": pipeline.cap is None or not pipeline.cap.isOpened()
    }
```

## 10.13 Backend — `.env.example`
```env
# Guardia AI Environment Variables
# Copy this to .env and fill in your keys

# Google Gemini (FREE) - Get at: https://ai.google.dev/
GEMINI_API_KEY=your_gemini_api_key_here

# Groq (FREE) - Get at: https://console.groq.com/
GROQ_API_KEY=your_groq_api_key_here

# HuggingFace (FREE) - Get at: https://huggingface.co/settings/tokens
HUGGINGFACE_API_KEY=your_hf_token_here

# System Settings
ALERT_THRESHOLD=5
ANALYSIS_INTERVAL_FRAMES=30
DATABASE_URL=sqlite:///./guardia.db
```

---

## 10.14 Frontend — `package.json`
```json
{
  "name": "guardia-ai-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "^14.2.0",
    "@nextui-org/react": "^2.4.0",
    "framer-motion": "^11.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "axios": "^1.6.0",
    "recharts": "^2.12.0",
    "react-webcam": "^7.2.0",
    "socket.io-client": "^4.7.0",
    "date-fns": "^3.6.0",
    "@heroicons/react": "^2.1.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "@types/react": "^18.3.0",
    "typescript": "^5.4.0"
  }
}
```

## 10.15 Frontend — `tailwind.config.js`
```javascript
// tailwind.config.js
const { nextui } = require("@nextui-org/react");

module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./node_modules/@nextui-org/theme/dist/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        "guardia-red": "#FF2D55",
        "guardia-orange": "#FF9500",
        "guardia-green": "#34C759",
        "guardia-dark": "#1C1C1E",
      }
    }
  },
  darkMode: "class",
  plugins: [nextui({
    themes: {
      dark: {
        colors: {
          primary: { DEFAULT: "#FF2D55" },
          secondary: { DEFAULT: "#FF9500" },
          success: { DEFAULT: "#34C759" },
          danger: { DEFAULT: "#FF3B30" },
        }
      }
    }
  })]
};
```

## 10.16 Frontend — `app/layout.tsx`
```tsx
// app/layout.tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "./providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Guardia AI — Real-Time Surveillance",
  description: "AI-powered multimodal surveillance platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-black text-white`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

## 10.17 Frontend — `app/providers.tsx`
```tsx
// app/providers.tsx
"use client";
import { NextUIProvider } from "@nextui-org/react";

export function Providers({ children }: { children: React.ReactNode }) {
  return <NextUIProvider>{children}</NextUIProvider>;
}
```

## 10.18 Frontend — `components/layout/AppLayout.tsx`
```tsx
// components/layout/AppLayout.tsx
"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge, Button, Chip } from "@nextui-org/react";
import { useAlerts } from "@/hooks/useAlerts";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "🖥️" },
  { href: "/alerts", label: "Alerts", icon: "🚨" },
  { href: "/analytics", label: "Analytics", icon: "📊" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { alerts, unreadCount } = useAlerts();

  return (
    <div className="flex h-screen bg-[#1C1C1E]">
      {/* Sidebar */}
      <aside className="w-64 bg-[#2C2C2E] border-r border-[#3A3A3C] flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-[#3A3A3C]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-500 rounded-xl flex items-center justify-center text-xl">
              🛡️
            </div>
            <div>
              <h1 className="font-bold text-white text-lg leading-none">Guardia</h1>
              <p className="text-[#8E8E93] text-xs">AI Surveillance</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => (
            <Link key={item.href} href={item.href}>
              <div className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all
                ${pathname === item.href 
                  ? "bg-red-500/20 text-red-400 border border-red-500/30" 
                  : "text-[#8E8E93] hover:bg-[#3A3A3C] hover:text-white"
                }`}>
                <span className="text-xl">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
                {item.href === "/alerts" && unreadCount > 0 && (
                  <Chip size="sm" color="danger" className="ml-auto text-xs">
                    {unreadCount}
                  </Chip>
                )}
              </div>
            </Link>
          ))}
        </nav>

        {/* Live Indicator */}
        <div className="p-4 border-t border-[#3A3A3C]">
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span>System Online</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
```

## 10.19 Frontend — `app/dashboard/page.tsx`
```tsx
// app/dashboard/page.tsx
"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import LiveFeed from "@/components/dashboard/LiveFeed";
import AlertsPanel from "@/components/dashboard/AlertsPanel";
import SystemStatus from "@/components/dashboard/SystemStatus";
import StatsCards from "@/components/dashboard/StatsCards";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function DashboardPage() {
  const { alerts, status, isConnected } = useWebSocket();
  
  return (
    <AppLayout>
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Live Dashboard</h1>
            <p className="text-[#8E8E93] text-sm">Real-time threat monitoring</p>
          </div>
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium
            ${isConnected ? "bg-green-500/20 text-green-400 border border-green-500/30" 
                         : "bg-red-500/20 text-red-400 border border-red-500/30"}`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-400 animate-pulse" : "bg-red-400"}`} />
            {isConnected ? "Connected" : "Disconnected"}
          </div>
        </div>

        {/* Stats Row */}
        <StatsCards />

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
          {/* Live Feed - takes 2 columns */}
          <div className="lg:col-span-2">
            <LiveFeed />
          </div>
          
          {/* Alerts Panel */}
          <div className="lg:col-span-1">
            <AlertsPanel alerts={alerts} />
          </div>
        </div>

        {/* System Status */}
        <div className="mt-6">
          <SystemStatus status={status} />
        </div>
      </div>
    </AppLayout>
  );
}
```

## 10.20 Frontend — `components/dashboard/LiveFeed.tsx`
```tsx
// components/dashboard/LiveFeed.tsx
"use client";
import { useRef, useState, useEffect, useCallback } from "react";
import Webcam from "react-webcam";
import { Card, CardBody, CardHeader, Button, Chip, Switch } from "@nextui-org/react";

export default function LiveFeed() {
  const webcamRef = useRef<Webcam>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [lastFrame, setLastFrame] = useState<string | null>(null);
  const [motionScore, setMotionScore] = useState(0);
  const [cameraAvailable, setCameraAvailable] = useState(true);
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const captureAndSend = useCallback(async () => {
    if (webcamRef.current && isCapturing) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        setLastFrame(imageSrc);
        // In a full implementation, send frame to backend via POST
        // The backend pipeline runs independently via WebSocket alerts
      }
    }
  }, [isCapturing]);

  useEffect(() => {
    if (!isCapturing) return;
    const interval = setInterval(captureAndSend, 2000);
    return () => clearInterval(interval);
  }, [isCapturing, captureAndSend]);

  return (
    <Card className="bg-[#2C2C2E] border border-[#3A3A3C]">
      <CardHeader className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-white">📷 Live Camera Feed</span>
          <Chip size="sm" variant="flat" color="default">CAM_001 — Main Entrance</Chip>
        </div>
        <div className="flex items-center gap-3">
          {isCapturing && (
            <div className="flex items-center gap-1.5 text-red-400 text-sm">
              <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              LIVE
            </div>
          )}
          <Switch
            isSelected={isCapturing}
            onValueChange={setIsCapturing}
            size="sm"
            color="danger"
          >
            <span className="text-sm text-[#8E8E93]">Stream</span>
          </Switch>
        </div>
      </CardHeader>
      <CardBody className="p-0">
        <div className="relative bg-black rounded-b-xl overflow-hidden" style={{minHeight: "360px"}}>
          {cameraAvailable ? (
            <Webcam
              ref={webcamRef}
              audio={false}
              screenshotFormat="image/jpeg"
              className="w-full h-full object-cover"
              onUserMediaError={() => setCameraAvailable(false)}
              videoConstraints={{ width: 640, height: 480, facingMode: "environment" }}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-[#8E8E93]">
              <span className="text-5xl mb-4">📷</span>
              <p className="text-lg font-medium">Camera unavailable</p>
              <p className="text-sm">Running in demo mode</p>
              <p className="text-xs mt-1 text-[#636366]">Simulated alerts are being generated</p>
            </div>
          )}
          
          {/* Overlay HUD */}
          <div className="absolute top-4 left-4 bg-black/60 rounded-lg px-3 py-2 text-xs text-green-400 font-mono">
            REC ● {new Date().toLocaleTimeString()}
          </div>
          <div className="absolute top-4 right-4 bg-black/60 rounded-lg px-3 py-2 text-xs text-white">
            AI ACTIVE
          </div>
          <div className="absolute bottom-4 left-4 right-4 flex gap-2">
            <div className="bg-black/60 rounded-lg px-3 py-1 text-xs text-[#8E8E93]">
              FusionController: Monitoring
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
```

## 10.21 Frontend — `components/dashboard/AlertsPanel.tsx`
```tsx
// components/dashboard/AlertsPanel.tsx
"use client";
import { useEffect, useRef } from "react";
import { Card, CardBody, CardHeader, Chip, ScrollShadow } from "@nextui-org/react";
import { motion, AnimatePresence } from "framer-motion";
import { formatDistanceToNow } from "date-fns";

const SEVERITY_COLORS: Record<number, string> = {
  1: "text-green-400",
  2: "text-green-400",
  3: "text-green-400",
  4: "text-yellow-400",
  5: "text-yellow-400",
  6: "text-orange-400",
  7: "text-red-400",
  8: "text-red-400",
  9: "text-red-500",
  10: "text-red-600",
};

const SEVERITY_BG: Record<string, string> = {
  low: "bg-green-500/10 border-green-500/20",
  medium: "bg-yellow-500/10 border-yellow-500/20",
  high: "bg-red-500/10 border-red-500/20",
};

function getSeverityLevel(severity: number) {
  if (severity <= 3) return "low";
  if (severity <= 6) return "medium";
  return "high";
}

export interface Alert {
  event_id: string;
  timestamp: string;
  camera_id: string;
  classification: string;
  severity: number;
  confidence: number;
  description: string;
}

export default function AlertsPanel({ alerts }: { alerts: Alert[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [alerts]);

  return (
    <Card className="bg-[#2C2C2E] border border-[#3A3A3C] h-full">
      <CardHeader className="flex items-center justify-between px-6 py-4">
        <span className="font-semibold text-white">🚨 Live Alerts</span>
        <Chip size="sm" color="danger" variant="flat">
          {alerts.length} events
        </Chip>
      </CardHeader>
      <CardBody className="p-3">
        <ScrollShadow className="h-[400px] overflow-y-auto space-y-2">
          <AnimatePresence>
            {alerts.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-32 text-[#636366]">
                <span className="text-3xl mb-2">✅</span>
                <p className="text-sm">No alerts — system normal</p>
              </div>
            ) : (
              alerts.map((alert) => (
                <motion.div
                  key={alert.event_id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className={`p-3 rounded-xl border ${SEVERITY_BG[getSeverityLevel(alert.severity)]}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-bold text-sm ${SEVERITY_COLORS[alert.severity]}`}>
                          {alert.classification}
                        </span>
                        <span className="text-[#636366] text-xs">
                          {alert.camera_id}
                        </span>
                      </div>
                      <p className="text-[#8E8E93] text-xs truncate">
                        {alert.description || "Threat detected"}
                      </p>
                      <p className="text-[#636366] text-xs mt-1">
                        {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
                      </p>
                    </div>
                    <div className={`text-2xl font-black ${SEVERITY_COLORS[alert.severity]}`}>
                      {alert.severity}
                    </div>
                  </div>
                  <div className="mt-2 bg-black/20 rounded-full h-1">
                    <div 
                      className="h-1 rounded-full bg-current transition-all"
                      style={{ width: `${alert.confidence * 100}%` }}
                    />
                  </div>
                  <p className="text-[#636366] text-xs mt-1">
                    Confidence: {Math.round(alert.confidence * 100)}%
                  </p>
                </motion.div>
              ))
            )}
          </AnimatePresence>
          <div ref={bottomRef} />
        </ScrollShadow>
      </CardBody>
    </Card>
  );
}
```

## 10.22 Frontend — `components/dashboard/StatsCards.tsx`
```tsx
// components/dashboard/StatsCards.tsx
"use client";
import { Card, CardBody } from "@nextui-org/react";
import { useEffect, useState } from "react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function StatsCards() {
  const [summary, setSummary] = useState({
    total_alerts_today: 0,
    high_severity_count: 0,
    avg_severity: 0,
  });

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/v1/analytics/summary`);
        setSummary(res.data);
      } catch {}
    };
    fetch();
    const interval = setInterval(fetch, 30000);
    return () => clearInterval(interval);
  }, []);

  const cards = [
    { label: "Alerts Today", value: summary.total_alerts_today, icon: "🚨", color: "text-red-400" },
    { label: "High Severity", value: summary.high_severity_count, icon: "⚠️", color: "text-orange-400" },
    { label: "Avg Severity", value: summary.avg_severity.toFixed(1), icon: "📊", color: "text-yellow-400" },
    { label: "System Status", value: "ONLINE", icon: "✅", color: "text-green-400" },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => (
        <Card key={card.label} className="bg-[#2C2C2E] border border-[#3A3A3C]">
          <CardBody className="p-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{card.icon}</span>
              <div>
                <p className="text-[#8E8E93] text-xs">{card.label}</p>
                <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
              </div>
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
```

## 10.23 Frontend — `hooks/useWebSocket.ts`
```typescript
// hooks/useWebSocket.ts
"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { Alert } from "@/components/dashboard/AlertsPanel";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/alerts";
const MAX_ALERTS = 50;

export function useWebSocket() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<any>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        console.log("✅ WebSocket connected");
        // Ping to keep alive
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "PING" }));
          }
        }, 30000);
        ws.onclose = () => clearInterval(pingInterval);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "ALERT") {
            const alert = msg.payload as Alert;
            setAlerts(prev => {
              const updated = [alert, ...prev].slice(0, MAX_ALERTS);
              return updated;
            });
            // Browser notification for high severity
            if (alert.severity >= 7 && "Notification" in window && Notification.permission === "granted") {
              new Notification(`🚨 ${alert.classification}`, {
                body: `Severity ${alert.severity} — ${alert.description}`,
              });
            }
          } else if (msg.type === "STATUS_UPDATE") {
            setStatus(msg.payload);
          }
        } catch (e) {
          console.error("WS parse error:", e);
        }
      };

      ws.onerror = () => console.error("WebSocket error");
      
      ws.onclose = () => {
        setIsConnected(false);
        // Reconnect after 3 seconds
        reconnectTimer.current = setTimeout(connect, 3000);
      };
    } catch (e) {
      console.error("WS connection failed:", e);
      reconnectTimer.current = setTimeout(connect, 5000);
    }
  }, []);

  useEffect(() => {
    // Request notification permission
    if ("Notification" in window) {
      Notification.requestPermission();
    }
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  return { alerts, status, isConnected };
}
```

## 10.24 Frontend — `hooks/useAlerts.ts`
```typescript
// hooks/useAlerts.ts
"use client";
import { useState, useEffect } from "react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useAlerts() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await axios.get(`${API_URL}/api/v1/events/recent?limit=5`);
        setAlerts(res.data);
        setUnreadCount(res.data.filter((a: any) => !a.is_reviewed).length);
      } catch {}
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000);
    return () => clearInterval(interval);
  }, []);

  return { alerts, unreadCount };
}
```

## 10.25 Frontend — `app/analytics/page.tsx`
```tsx
// app/analytics/page.tsx
"use client";
import { useState, useEffect } from "react";
import AppLayout from "@/components/layout/AppLayout";
import { Card, CardBody, CardHeader } from "@nextui-org/react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend
} from "recharts";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PIE_COLORS = {
  FIGHT: "#FF2D55",
  INTRUSION: "#FF9500",
  FALL: "#FF6B35",
  LOITERING: "#FFCC00",
  NORMAL: "#34C759",
  SUSPICIOUS: "#AF52DE",
  RUNNING: "#007AFF",
  DEFAULT: "#636366"
};

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<any>(null);
  const [trends, setTrends] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [sumRes, trendRes] = await Promise.all([
          axios.get(`${API_URL}/api/v1/analytics/summary`),
          axios.get(`${API_URL}/api/v1/analytics/trends?period=24h`)
        ]);
        setSummary(sumRes.data);
        setTrends(trendRes.data.data_points || []);
      } catch {}
    };
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const pieData = summary ? Object.entries(summary.alerts_by_type || {}).map(([name, value]) => ({
    name, value: value as number
  })) : [];

  return (
    <AppLayout>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-white mb-6">📊 Analytics</h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Alerts by Hour */}
          <Card className="bg-[#2C2C2E] border border-[#3A3A3C]">
            <CardHeader><span className="text-white font-semibold">Alerts by Hour (Today)</span></CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={summary?.alerts_by_hour || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#3A3A3C" />
                  <XAxis dataKey="hour" stroke="#8E8E93" fontSize={11} />
                  <YAxis stroke="#8E8E93" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#2C2C2E", border: "1px solid #3A3A3C" }} />
                  <Bar dataKey="count" fill="#FF2D55" radius={4} />
                </BarChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* Threat Distribution */}
          <Card className="bg-[#2C2C2E] border border-[#3A3A3C]">
            <CardHeader><span className="text-white font-semibold">Threat Distribution</span></CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" outerRadius={80} dataKey="value" label={({name}) => name}>
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={(PIE_COLORS as any)[entry.name] || PIE_COLORS.DEFAULT} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#2C2C2E", border: "1px solid #3A3A3C" }} />
                </PieChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>

          {/* Trends */}
          <Card className="bg-[#2C2C2E] border border-[#3A3A3C] lg:col-span-2">
            <CardHeader><span className="text-white font-semibold">Alert Trend (24h)</span></CardHeader>
            <CardBody>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#3A3A3C" />
                  <XAxis dataKey="time" stroke="#8E8E93" fontSize={10} />
                  <YAxis stroke="#8E8E93" fontSize={10} />
                  <Tooltip contentStyle={{ background: "#2C2C2E", border: "1px solid #3A3A3C" }} />
                  <Legend />
                  <Line type="monotone" dataKey="count" stroke="#FF2D55" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="avg_severity" stroke="#FF9500" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardBody>
          </Card>
        </div>
      </div>
    </AppLayout>
  );
}
```

## 10.26 Frontend — `.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/alerts
```

---

# 11. DEPLOYMENT GUIDE

## 11.1 Local Development Setup

### Step 1: Clone & Setup
```bash
git clone https://github.com/YOUR_USERNAME/guardia-ai
cd guardia-ai
```

### Step 2: Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

### Step 3: Frontend Setup
```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local if needed
npm run dev
```

### Step 4: Get Free API Keys (5 minutes)
```
1. GROQ (FAST, Free):
   → https://console.groq.com/
   → Sign up → Create API Key → Copy to .env

2. GEMINI FLASH (Free):
   → https://ai.google.dev/
   → "Get API key in Google AI Studio" 
   → Create key → Copy to .env

3. OLLAMA (Local, Zero Cost):
   → https://ollama.ai/download
   → ollama pull llama3
   → Runs locally, no key needed
```

## 11.2 Docker Setup
```yaml
# docker-compose.yml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - ALERT_THRESHOLD=5
    volumes:
      - ./backend/guardia.db:/app/guardia.db
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/alerts
    depends_on:
      - backend
    restart: unless-stopped
```

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## 11.3 Free Cloud Deployment

### Backend → Railway (Free $5/month credit)
```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
cd backend
railway init
railway up
# Set env vars in Railway dashboard
```

### Frontend → Vercel (Free forever)
```bash
npm install -g vercel
cd frontend
vercel
# Set NEXT_PUBLIC_API_URL to your Railway URL
```

---

# 12. DEFINITION OF DONE

## Per Task
- [ ] Code written and reviewed by 1 teammate
- [ ] No console errors
- [ ] Tested manually
- [ ] Committed to GitHub with descriptive message

## Per User Story
- [ ] All acceptance criteria met
- [ ] API endpoint documented
- [ ] Frontend integrated and working
- [ ] Error states handled

## MVP Launch Criteria
- [ ] ✅ Backend running and stable
- [ ] ✅ WebSocket delivering real-time alerts
- [ ] ✅ Dashboard showing live data
- [ ] ✅ At least 1 AI model returning analysis
- [ ] ✅ Events saving to database
- [ ] ✅ Demo mode working when no camera
- [ ] ✅ Deployed to public URL
- [ ] ✅ README complete with setup instructions
- [ ] ✅ Sub-500ms alert-to-display latency
- [ ] ✅ No critical bugs during demo

---

# 📅 DAILY STANDUP TEMPLATE

Use this every morning (15 minutes max):

```
🌅 GUARDIA AI DAILY STANDUP
Date: _______________

ARYAN:
  ✅ Yesterday: 
  🔨 Today:
  🚧 Blockers:

OMISHA:
  ✅ Yesterday:
  🔨 Today:
  🚧 Blockers:

KARTIKEY:
  ✅ Yesterday:
  🔨 Today:
  🚧 Blockers:

AYUSHMAN:
  ✅ Yesterday:
  🔨 Today:
  🚧 Blockers:

📊 Overall Progress: ___/80 tasks complete
🎯 On track for demo: YES / NO
```

---

# 🐛 BUG REPORT TEMPLATE

```markdown
**Bug ID:** BUG-XXX
**Reporter:** [Name]
**Date:** 
**Severity:** Critical / High / Medium / Low

**Title:** [Short description]

**Steps to Reproduce:**
1. 
2. 

**Expected:** 
**Actual:** 
**Screenshots:** 

**Assignee:** 
**Status:** Open / In Progress / Resolved
```

---

# 🚀 GIT WORKFLOW

## Branch Strategy
```
main            ← Production-ready code only
├── dev         ← Integration branch
│   ├── feat/aryan-ai-pipeline
│   ├── feat/omisha-dashboard
│   ├── feat/kartikey-fusion-controller
│   └── feat/ayushman-api-database
```

## Commit Convention
```
feat: Add Gemini Vision API integration
fix: WebSocket reconnection on disconnect
docs: Update API endpoints documentation
style: Fix dashboard layout on mobile
test: Add motion detector unit tests
```

## PR Template
```markdown
## What does this PR do?
[Description]

## Testing done
- [ ] Tested locally
- [ ] No console errors
- [ ] API endpoints verified

## Screenshots (if UI change)

## Reviewer: @[teammate]
```

---

# 📱 QUICK START COMMANDS CHEATSHEET

```bash
# Backend
cd backend && python main.py           # Start API
cd backend && pip install -r requirements.txt  # Install deps

# Frontend
cd frontend && npm run dev             # Start Next.js
cd frontend && npm install             # Install deps

# Docker (everything at once)
docker-compose up --build             # Start all services
docker-compose logs -f backend         # Watch backend logs

# Ollama local AI
ollama serve                           # Start Ollama
ollama pull llama3                     # Download model
ollama run llama3 "test"               # Test it

# Useful API tests
curl http://localhost:8000/api/v1/status
curl http://localhost:8000/api/v1/events
curl http://localhost:8000/api/v1/analytics/summary
```

---

*Generated by Scrum Master Aryan Bajpai — Guardia AI Team*  
*PSIT Kanpur | Dr. APJ Abdul Kalam Technical University*  
*Sprint Duration: 2 Days | May 2025*
