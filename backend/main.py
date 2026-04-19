"""
Guardia AI — FastAPI Backend Entry Point
=========================================
Startup order:
  1. Configure structured logging (TASK-078).
  2. Create / migrate SQLite tables (TASK-016/017).
  3. Register rate-limiting middleware (TASK-060).
  4. Register all API routers under /api/v1 (TASK-018/019/020).
  5. Mount WebSocket alert channel at /ws/alerts (TASK-019/036).
  6. Start the AI video stream processor as a background task (TASK-037/022).
  7. Serve via Uvicorn.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ── Logging must be configured FIRST ────────────────────────────────────────
from utils.logger import configure_logging

configure_logging(log_level="INFO")
logger = logging.getLogger("guardia")

from config import get_settings
from database import init_db
from api.events import router as events_router
from api.cameras import router as cameras_router
from api.settings import router as settings_router
from api.analytics import router as analytics_router
from api.system import router as system_router
from middleware.rate_limiter import RateLimitMiddleware
from websocket.manager import manager

# ---------------------------------------------------------------------------
# App lifespan — startup + shutdown (TASK-037: background task runner)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and graceful shutdown."""
    logger.info("Initialising Guardia AI backend…")
    init_db()
    cfg = get_settings()
    logger.info(
        "Database ready | threshold=%d | interval=%d frames",
        cfg.alert_threshold,
        cfg.analysis_interval_frames,
    )

    # TASK-037: Start AI video stream as background asyncio task
    from ai.video_stream import video_stream
    stream_task = asyncio.create_task(video_stream.start(), name="video_stream")
    logger.info("✅ AI video stream background task started.")
    logger.info("Guardia AI running — http://%s:%d/docs", cfg.app_host, cfg.app_port)

    yield  # ─── Application is running ───

    # Shutdown
    logger.info("Guardia AI shutting down…")
    video_stream.stop()
    stream_task.cancel()
    try:
        await stream_task
    except asyncio.CancelledError:
        pass
    logger.info("Guardia AI stopped cleanly.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

cfg = get_settings()

app = FastAPI(
    title="Guardia AI",
    description=(
        "## Real-Time Multimodal Surveillance System\n\n"
        "Guardia AI transforms standard CCTV feeds into an intelligent threat "
        "detection platform using **Gemini Vision**, **Groq LLM fusion**, "
        "**YOLOv8** object detection, and **OpenCV** motion analysis.\n\n"
        "### Key Endpoints\n"
        "- `GET /api/v1/status` — System health\n"
        "- `GET /api/v1/events` — List security events\n"
        "- `GET /api/v1/analytics/summary` — Today's stats\n"
        "- `POST /api/v1/demo/trigger` — Trigger a demo scenario\n"
        "- `WS /ws/alerts` — Real-time alert WebSocket\n"
    ),
    version="1.0.0",
    contact={"name": "Aryan Bajpai", "email": "aryan@guardia.ai"},
    license_info={"name": "MIT"},
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware stack (TASK-060: rate limiting)
# ---------------------------------------------------------------------------

# CORS — allow the Next.js dev server and production frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "*",  # permissive for MVP/demo — tighten for production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter (TASK-060)
app.add_middleware(RateLimitMiddleware)

# ---------------------------------------------------------------------------
# API routers (TASK-044: enriched with tags + descriptions)
# ---------------------------------------------------------------------------

PREFIX = "/api/v1"

app.include_router(system_router,    prefix=PREFIX,               tags=["⚙️ System"])
app.include_router(events_router,    prefix=f"{PREFIX}/events",   tags=["🚨 Events"])
app.include_router(cameras_router,   prefix=f"{PREFIX}/cameras",  tags=["📷 Cameras"])
app.include_router(settings_router,  prefix=f"{PREFIX}/settings", tags=["🔧 Settings"])
app.include_router(analytics_router, prefix=f"{PREFIX}/analytics",tags=["📊 Analytics"])

# ---------------------------------------------------------------------------
# Health check + liveness probe (TASK-059)
# ---------------------------------------------------------------------------


@app.get("/health", tags=["⚙️ System"], summary="Kubernetes-style health probe")
def health():
    """Liveness + readiness probe for Docker/Railway health checks."""
    return {"status": "healthy", "service": "guardia-ai-backend"}


@app.get("/ping", tags=["⚙️ System"], summary="Simple ping")
def ping():
    """Minimal latency ping."""
    return {"pong": True}


# ---------------------------------------------------------------------------
# WebSocket endpoint (TASK-019 / TASK-036)
# ---------------------------------------------------------------------------


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Persistent WebSocket channel for real-time alert delivery.

    Message types:
      - `{ "type": "ALERT",  "payload": { ...event... } }`
      - `{ "type": "STATUS", "payload": { ...status... } }`
    
    Client can send `ping` → server responds `{ "type": "PONG" }`.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text('{"type":"PONG"}')
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected.")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Run directly: python main.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=cfg.app_host,
        port=cfg.app_port,
        reload=False,
        log_level=cfg.log_level.lower(),
    )
