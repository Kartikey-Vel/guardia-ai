"""
System API — health, status, frame-upload, demo, logs endpoints.

TASK-059: /health and /ping (also in main.py for Kubernetes probes)
TASK-044: Enriched docstrings for auto-generated API docs
TASK-045: POST /demo/trigger — demo scenario launcher
TASK-078: GET /logs — last N in-memory log lines
TASK-043: GET /iot/status — current simulated IoT sensor snapshot
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from ai.pipeline import pipeline
from config import get_settings
from database import Camera, Event, get_db
from websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# System status (TASK-059 + TASK-044)
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    summary="System status overview",
    description="Returns the operational health of all sub-systems: database, AI models, WebSocket, demo mode.",
)
def system_status(db: Session = Depends(get_db)):
    """Return a comprehensive system health summary."""
    cfg = get_settings()
    from ai.yolo_detector import yolo_detector
    from ai.video_stream import video_stream

    total_events = db.query(Event).count()
    total_cameras = db.query(Camera).count()

    return {
        "status": "operational",
        "version": "1.0.0",
        "alert_threshold": cfg.alert_threshold,
        "analysis_interval_frames": cfg.analysis_interval_frames,
        "gemini_configured": bool(cfg.gemini_api_key),
        "groq_configured": bool(cfg.groq_api_key),
        "yolo_enabled": bool(cfg.yolo_enabled),
        "yolo_ready": yolo_detector.is_ready,
        "yolo_model": cfg.yolo_model,
        "websocket_clients": manager.connection_count,
        "total_events_logged": total_events,
        "total_cameras_registered": total_cameras,
        "demo_mode": video_stream._demo_mode,
        "stream_running": video_stream._running,
    }


@router.get(
    "/models/status",
    summary="AI model readiness",
    description="Detailed connectivity and readiness status for each AI model.",
)
def models_status():
    """Return status of all configured AI models."""
    cfg = get_settings()
    from ai.yolo_detector import yolo_detector

    return {
        "yolo": {
            "enabled": cfg.yolo_enabled,
            "ready": yolo_detector.is_ready,
            "model_name": cfg.yolo_model,
        },
        "gemini": {
            "configured": bool(cfg.gemini_api_key),
            "model_name": cfg.gemini_model,
        },
        "groq": {
            "configured": bool(cfg.groq_api_key),
            "model_name": cfg.groq_model,
        },
        "ollama": {
            "fallback_enabled": True,
            "note": "Ollama fallback activates automatically when Groq fails",
        },
    }


# ---------------------------------------------------------------------------
# Frame analysis upload endpoint (TASK-022)
# ---------------------------------------------------------------------------

@router.post(
    "/analyze-frame",
    summary="Upload frame for AI analysis",
    description=(
        "Upload a single JPEG/PNG frame for immediate motion detection and AI analysis. "
        "Results are persisted to the database and broadcast via WebSocket if severity "
        "exceeds the configured alert threshold."
    ),
)
async def analyze_frame(
    camera_id: str = Form(default="default"),
    zone: str = Form(default="general"),
    risk_level: int = Form(default=2),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Process an uploaded image frame through the full AI pipeline."""
    image_bytes = await file.read()
    fusion_result, motion_result = pipeline.process_bytes(
        image_bytes,
        camera_id=camera_id,
        zone=zone,
        risk_level=risk_level,
    )

    if fusion_result is None:
        return {
            "analyzed": False,
            "motion_detected": motion_result.motion_detected,
            "motion_score": motion_result.motion_score,
            "message": "Frame processed — AI analysis not triggered at this interval.",
        }

    event_payload = pipeline.build_event_payload(fusion_result, camera_id, motion_result)
    from api.events import create_event
    event = create_event(event_payload, db)

    if fusion_result.should_alert:
        await manager.broadcast_alert({
            "event_id": event.event_id,
            "camera_id": camera_id,
            "classification": fusion_result.classification,
            "severity": fusion_result.severity,
            "confidence": fusion_result.confidence,
            "description": fusion_result.description,
        })

    return {
        "analyzed": True,
        "motion_detected": motion_result.motion_detected,
        "motion_score": motion_result.motion_score,
        "result": fusion_result.model_dump(),
        "event_id": event.event_id,
        "alerted": fusion_result.should_alert,
    }


# ---------------------------------------------------------------------------
# Demo scenario trigger (TASK-045)
# ---------------------------------------------------------------------------

@router.post(
    "/demo/trigger",
    summary="Trigger a demo scenario",
    description=(
        "Starts a pre-scripted threat scenario that emits events over WebSocket "
        "to demonstrate the system without a real camera.\n\n"
        "Available scenarios: `fight`, `intrusion`, `fall`, `loitering`, `crowd_surge`"
    ),
)
async def trigger_demo(
    scenario: str = Query(default="fight", description="Scenario name"),
    camera_id: str = Query(default="CAM_001"),
):
    """Start a scripted demo scenario sequence."""
    from demo.scenarios import demo_runner, SCENARIOS
    result = await demo_runner.trigger(scenario, camera_id)
    return result


@router.get(
    "/demo/scenarios",
    summary="List available demo scenarios",
)
def list_scenarios():
    """Return all available demo scenario names and their step counts."""
    from demo.scenarios import SCENARIOS
    return {
        name: {
            "steps": len(steps),
            "max_severity": max(s["severity"] for s in steps),
            "duration_seconds": steps[-1]["delay"] + 2,
        }
        for name, steps in SCENARIOS.items()
    }


# ---------------------------------------------------------------------------
# IoT sensor status (TASK-043)
# ---------------------------------------------------------------------------

@router.get(
    "/iot/status",
    summary="Current IoT sensor readings",
    description="Returns the latest simulated IoT sensor snapshot including sound level, door sensors, PIR, and temperature.",
)
def iot_status(scenario: str = Query(default="normal")):
    """Get a live IoT sensor snapshot."""
    from ai.iot_simulator import iot_simulator
    snapshot = iot_simulator.get_for_fusion(threat_scenario=scenario)
    return snapshot


# ---------------------------------------------------------------------------
# Log viewer (TASK-078)
# ---------------------------------------------------------------------------

@router.get(
    "/logs",
    summary="Recent application logs",
    description="Returns the last N log entries from the in-memory log buffer.",
)
def get_logs(n: int = Query(default=100, ge=1, le=1000)):
    """Return last N in-memory log lines for monitoring / debugging."""
    from utils.logger import memory_handler
    return {
        "count": n,
        "logs": memory_handler.get_logs(n),
    }


# ---------------------------------------------------------------------------
# Database backup (TASK-077)
# ---------------------------------------------------------------------------

@router.post(
    "/backup",
    summary="Create database backup",
    description="Triggers an immediate SQLite database backup to the ./backups/ directory.",
)
def create_backup():
    """Create a timestamped backup of the guardia.db database."""
    from utils.backup import backup_manager
    path = backup_manager.create_backup()
    if path:
        return {"status": "success", "backup_path": path}
    return {"status": "failed", "message": "Backup failed — check logs."}


@router.get(
    "/backup/list",
    summary="List database backups",
)
def list_backups():
    """List all existing database backup files."""
    from utils.backup import backup_manager
    return {"backups": backup_manager.list_backups()}
