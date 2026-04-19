"""System status and frame-upload API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ai.pipeline import pipeline
from config import get_settings
from database import Camera, Event, get_db
from websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
def system_status(db: Session = Depends(get_db)):
    """Return a health summary for the Guardia AI backend."""
    cfg = get_settings()
    from ai.yolo_detector import yolo_detector

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
    }


@router.post("/analyze-frame")
async def analyze_frame(
    camera_id: str = Form(default="default"),
    zone: str = Form(default="general"),
    risk_level: int = Form(default=2),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload a single frame for immediate motion + AI analysis.

    This endpoint is useful for:
    - Dashboard demo mode (upload a test image)
    - External integrations that push frames via HTTP instead of streaming

    Returns the full FusionResult if analysis is triggered, or a motion-only
    summary if the frame doesn't meet the analysis interval yet.
    """
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
            "message": "Frame processed — no AI analysis triggered at this interval.",
        }

    # Persist event
    event_payload = pipeline.build_event_payload(
        fusion_result, camera_id, motion_result
    )
    from api.events import create_event
    event = create_event(event_payload, db)

    # Broadcast to WebSocket clients if above threshold
    if fusion_result.should_alert:
        await manager.broadcast_alert(
            {
                "event_id": event.event_id,
                "camera_id": camera_id,
                "classification": fusion_result.classification,
                "severity": fusion_result.severity,
                "confidence": fusion_result.confidence,
                "description": fusion_result.description,
            }
        )

    return {
        "analyzed": True,
        "motion_detected": motion_result.motion_detected,
        "motion_score": motion_result.motion_score,
        "result": fusion_result.model_dump(),
        "event_id": event.event_id,
        "alerted": fusion_result.should_alert,
    }
