"""
Guardia AI — FastAPI Backend Entry Point
=========================================
Startup order:
  1. Create / migrate SQLite tables.
  2. Register all API routers under /api/v1.
  3. Mount the WebSocket alert channel at /ws/alerts.
  4. Serve via Uvicorn.
"""

import logging
import sys

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from api.events import router as events_router
from api.cameras import router as cameras_router
from api.settings import router as settings_router
from api.analytics import router as analytics_router
from api.system import router as system_router
from websocket.manager import manager

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("guardia")

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

cfg = get_settings()

app = FastAPI(
    title="Guardia AI",
    description=(
        "Real-time multimodal surveillance backend — "
        "motion detection + Gemini vision + Groq fusion."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Next.js frontend (and localhost dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(system_router, prefix=API_PREFIX, tags=["system"])
app.include_router(events_router, prefix=f"{API_PREFIX}/events", tags=["events"])
app.include_router(cameras_router, prefix=f"{API_PREFIX}/cameras", tags=["cameras"])
app.include_router(settings_router, prefix=f"{API_PREFIX}/settings", tags=["settings"])
app.include_router(analytics_router, prefix=f"{API_PREFIX}/analytics", tags=["analytics"])

# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Persistent WebSocket channel for real-time alert delivery to the dashboard.

    Clients connect and receive JSON messages of two types:
      { "type": "ALERT",  "payload": { ...event fields... } }
      { "type": "STATUS", "payload": { ...ping fields...  } }
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep the socket alive by waiting for any message from the client.
            # The client can send a "ping" text; we echo a pong.
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
# Startup / shutdown
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def on_startup():
    logger.info("Initialising Guardia AI backend...")
    init_db()
    logger.info(
        "Database ready | threshold=%d | interval=%d frames",
        cfg.alert_threshold,
        cfg.analysis_interval_frames,
    )
    logger.info("Guardia AI backend running at http://%s:%d", cfg.app_host, cfg.app_port)


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Guardia AI backend shutting down.")


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
