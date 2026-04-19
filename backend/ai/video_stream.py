"""
TASK-022: Video Stream Processor — RTSP + Webcam Live Feed
===========================================================
Runs as a long-lived asyncio background task.

Behavior
--------
* Tries to open the webcam (index 0) first.
* If a camera RTSP/HTTP URL is configured in the DB, opens that instead.
* Continuously reads frames and feeds them to the shared AIFramePipeline.
* Saves events to the DB and broadcasts alerts over WebSocket.
* Falls back to **demo mode** if no camera is accessible.
"""

import asyncio
import base64
import json
import logging
import random
import uuid
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

from config import get_settings
from database import Camera, Event, SessionLocal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Demo event templates for when no camera is available
# ---------------------------------------------------------------------------

DEMO_EVENTS = [
    {"classification": "physical_altercation", "severity": 9, "confidence": 0.94,
     "description": "Demo: Two individuals engaged in physical altercation near main entrance."},
    {"classification": "unauthorized_access", "severity": 7, "confidence": 0.87,
     "description": "Demo: Individual bypassed access control — intrusion detected."},
    {"classification": "suspicious_loitering", "severity": 5, "confidence": 0.76,
     "description": "Demo: Subject loitering at restricted zone for >10 minutes."},
    {"classification": "normal_activity", "severity": 1, "confidence": 0.98,
     "description": "Demo: Routine pedestrian movement. No threat detected."},
    {"classification": "abandoned_object", "severity": 6, "confidence": 0.81,
     "description": "Demo: Unattended bag detected near stairwell for >5 minutes."},
    {"classification": "crowd_formation", "severity": 4, "confidence": 0.72,
     "description": "Demo: Unusual crowd forming at secondary entrance."},
]


# ---------------------------------------------------------------------------
# Video Stream Processor
# ---------------------------------------------------------------------------

class VideoStreamProcessor:
    """
    Background asyncio task that continuously processes camera frames.

    TASK-022: Supports webcam (device index) and RTSP/HTTP URLs.
    """

    def __init__(self) -> None:
        self._cfg = get_settings()
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._demo_mode = False
        self._frame_count = 0

    # ------------------------------------------------------------------
    # Public control
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Entry point called from the lifespan startup hook."""
        logger.info("VideoStreamProcessor starting…")
        self._running = True
        await self._run_loop()

    def stop(self) -> None:
        self._running = False
        if self._cap and self._cap.isOpened():
            self._cap.release()
            logger.info("Camera released.")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _run_loop(self) -> None:
        # Lazy import to avoid circular dependency at module load time
        from ai.pipeline import pipeline
        from websocket.manager import manager

        source = self._pick_camera_source()
        connected = self._connect(source)

        if not connected:
            logger.warning(
                "No camera accessible (source=%s). Switching to demo mode.", source
            )
            self._demo_mode = True
            await self._demo_loop(manager)
            return

        logger.info("Camera connected (source=%s). Live stream active.", source)

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Frame read failed — attempting reconnect.")
                await asyncio.sleep(2)
                self._connect(source)
                continue

            self._frame_count += 1

            # Run the AI pipeline in a thread to avoid blocking the event loop
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda f=frame: pipeline.process(
                    f,
                    camera_id=self._get_active_camera_id(),
                    zone="entrance",
                    risk_level=2,
                ),
            )

            if result and result.should_alert:
                event = self._persist_event(result, self._get_active_camera_id(), frame)
                frame_b64 = self._encode_frame(frame)
                await manager.broadcast_alert({
                    "event_id": event.event_id,
                    "timestamp": event.timestamp.isoformat() + "Z",
                    "camera_id": event.camera_id,
                    "classification": event.classification,
                    "severity": event.severity,
                    "confidence": event.confidence,
                    "description": event.description,
                    "frame_base64": frame_b64,
                    "attribution": event.attribution or {},
                })

            # Status update every 100 frames
            if self._frame_count % 100 == 0:
                await manager.broadcast_status({
                    "cameras_active": 1,
                    "processing_fps": 10,
                    "frame_count": self._frame_count,
                    "demo_mode": False,
                    "models_status": {
                        "motion": "active",
                        "gemini": "active" if self._cfg.gemini_api_key else "disabled",
                        "groq": "active" if self._cfg.groq_api_key else "disabled",
                    },
                })

            # ~10 FPS — sleep to remain async-friendly
            await asyncio.sleep(0.1)

        if self._cap:
            self._cap.release()

    # ------------------------------------------------------------------
    # Demo mode (TASK-045 scaffold)
    # ------------------------------------------------------------------

    async def _demo_loop(self, manager) -> None:
        """Emit simulated events when no real camera is accessible."""
        logger.info("Demo loop running — will emit synthetic alerts.")
        while self._running:
            interval = self._cfg.demo_interval_seconds if hasattr(self._cfg, "demo_interval_seconds") else 10
            await asyncio.sleep(interval + random.uniform(-2, 5))

            template = random.choice(DEMO_EVENTS)
            event = self._persist_demo_event(template)

            await manager.broadcast_alert({
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat() + "Z",
                "camera_id": event.camera_id,
                "classification": event.classification,
                "severity": event.severity,
                "confidence": event.confidence,
                "description": event.description,
                "frame_base64": None,
                "attribution": {"motion": 0.35, "vision_ai": 0.45, "audio": 0.20},
            })
            logger.info(
                "Demo alert: cls=%s sev=%d", template["classification"], template["severity"]
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_camera_source(self):
        """Return RTSP URL from DB if configured, else default webcam index 0."""
        try:
            db = SessionLocal()
            cam = db.query(Camera).filter(Camera.is_active == True).first()
            db.close()
            if cam and cam.rtsp_url:
                return cam.rtsp_url
        except Exception:
            pass
        return 0  # default webcam

    def _get_active_camera_id(self) -> str:
        try:
            db = SessionLocal()
            cam = db.query(Camera).filter(Camera.is_active == True).first()
            db.close()
            return cam.camera_id if cam else "CAM_001"
        except Exception:
            return "CAM_001"

    def _connect(self, source) -> bool:
        if self._cap:
            self._cap.release()
        self._cap = cv2.VideoCapture(source)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return self._cap.isOpened()

    @staticmethod
    def _encode_frame(frame: np.ndarray) -> str:
        try:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            return "data:image/jpeg;base64," + base64.b64encode(buf).decode()
        except Exception:
            return ""

    @staticmethod
    def _persist_event(result, camera_id: str, frame: Optional[np.ndarray]) -> Event:
        db = SessionLocal()
        try:
            event = Event(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                camera_id=camera_id,
                classification=result.classification,
                severity=result.severity,
                confidence=result.confidence,
                description=result.description,
                attribution=result.attribution,
                ai_model=result.ai_model,
                motion_score=result.attribution.get("motion_score") if result.attribution else None,
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            return event
        finally:
            db.close()

    @staticmethod
    def _persist_demo_event(template: dict) -> Event:
        db = SessionLocal()
        try:
            event = Event(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                camera_id="CAM_001",
                classification=template["classification"],
                severity=template["severity"],
                confidence=template["confidence"],
                description=template["description"],
                attribution={"motion": 0.35, "vision_ai": 0.45, "audio": 0.20},
                ai_model="demo-mode",
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            return event
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

video_stream = VideoStreamProcessor()
