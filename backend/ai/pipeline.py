"""
AI Pipeline — Frame Orchestration
===================================
Central coordinator that:
  1. Receives a raw frame (bytes or numpy).
  2. Runs MotionDetector.
  3. Conditionally calls GeminiVisionAnalyzer when motion triggers analysis.
  4. Feeds both results to GroqFusionController.
  5. Returns a FusionResult (or None when motion is absent / interval not reached).

Also handles database persistence and WebSocket broadcast when a result
exceeds the alert threshold.
"""

import base64
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple

import numpy as np

from ai.gemini_vision import gemini_analyzer
from ai.groq_fusion import groq_fusion
from ai.motion_detector import motion_detector
from config import get_settings
from models.schemas import EventCreate, FusionResult, MotionResult, VisionResult

logger = logging.getLogger(__name__)


class AIFramePipeline:
    """
    End-to-end per-frame AI pipeline.

    Usage (inside a FastAPI route / background task)
    -----
    >>> pipeline = AIFramePipeline()
    >>> result = pipeline.process(frame_bgr, camera_id="cam-01", zone="entrance", risk_level=3)
    >>> if result:
    ...     print(result.classification, result.severity)
    """

    def __init__(self) -> None:
        self._cfg = get_settings()

    def initialize_ai(self) -> None:
        """Re-initialize all AI clients (called after API key settings update)."""
        gemini_analyzer.reinitialize()
        groq_fusion.reinitialize()
        logger.info("AI modules reinitialized after settings update.")

    # ------------------------------------------------------------------
    # Primary pipeline entry point
    # ------------------------------------------------------------------

    def process(
        self,
        frame: np.ndarray,
        camera_id: str = "default",
        zone: str = "general",
        risk_level: int = 2,
    ) -> Optional[FusionResult]:
        """
        Process a single frame through the full pipeline.

        Returns
        -------
        FusionResult if motion was detected AND the interval triggered an
        AI analysis, else None (normal / quiet frame).
        """
        # --- Step 1: Motion detection ---
        motion: MotionResult = motion_detector.process_frame(frame, camera_id)

        if not motion.motion_detected:
            return None  # No motion — skip AI inference entirely

        if not motion.should_analyze:
            # Motion present but not at the analysis interval yet
            return None

        # --- Step 2: Gemini vision analysis ---
        vision: VisionResult = gemini_analyzer.analyze_frame(
            frame,
            camera_id=camera_id,
            motion_score=motion.motion_score,
        )

        # --- Step 3: Fusion ---
        result: FusionResult = groq_fusion.fuse(
            motion,
            vision,
            zone=zone,
            risk_level=risk_level,
            camera_id=camera_id,
        )

        logger.info(
            "Pipeline result [cam=%s]: cls=%s sev=%d alert=%s",
            camera_id,
            result.classification,
            result.severity,
            result.should_alert,
        )
        return result

    def process_bytes(
        self,
        image_bytes: bytes,
        camera_id: str = "default",
        zone: str = "general",
        risk_level: int = 2,
    ) -> Tuple[Optional[FusionResult], MotionResult]:
        """
        Process raw image bytes — useful for HTTP upload endpoints.

        Returns (FusionResult | None, MotionResult).
        The MotionResult is always returned so callers can track motion
        even when AI analysis is not triggered.
        """
        motion_result, frame = motion_detector.process_bytes(image_bytes, camera_id)

        if not motion_result.motion_detected or not motion_result.should_analyze:
            return None, motion_result

        vision: VisionResult = gemini_analyzer.analyze_frame(
            frame,
            camera_id=camera_id,
            motion_score=motion_result.motion_score,
        )
        fusion = groq_fusion.fuse(
            motion_result,
            vision,
            zone=zone,
            risk_level=risk_level,
            camera_id=camera_id,
        )
        return fusion, motion_result

    def build_event_payload(
        self,
        result: FusionResult,
        camera_id: str,
        motion: MotionResult,
        frame: Optional[np.ndarray] = None,
    ) -> EventCreate:
        """Convert a FusionResult into an EventCreate schema for DB insertion."""
        return EventCreate(
            camera_id=camera_id,
            classification=result.classification,
            severity=result.severity,
            confidence=result.confidence,
            description=result.description,
            attribution=result.attribution,
            ai_model=result.ai_model,
            motion_score=motion.motion_score,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

pipeline = AIFramePipeline()
