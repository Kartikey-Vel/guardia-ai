"""
Groq Fusion Controller
=======================
Uses Groq's fast LLM inference to combine signals from:
  - Motion detector (motion_score, contour_count)
  - Gemini vision (classification, severity, confidence)
  - Camera zone / risk level metadata

Produces a final FusionResult with a definitive threat classification,
severity, and a human-readable action hint.

Falls back to a weighted-average heuristic when the Groq key is absent.
"""

import json
import logging
import re
from typing import Optional

from config import get_settings
from models.schemas import FusionResult, MotionResult, VisionResult, YOLOResult
from utils.confidence_scorer import ConfidenceScorer
from ai.utils import KeyRotator

logger = logging.getLogger(__name__)

_FUSION_PROMPT = """\
You are a senior security operations centre (SOC) analyst.
You receive multi-signal data from a surveillance system and must produce
a final, authoritative threat assessment.

Input signals:
{signals_json}

Rules:
- Weigh Gemini confidence: if gemini_confidence > 0.7 trust it heavily.
- Escalate severity by +1 if the zone risk_level >= 4.
- Escalate severity by +1 if motion_score > 0.4.
- Final severity must be clamped to 1-10.
- If both signals agree the scene is "normal_activity" keep severity <= 3.

Respond ONLY with a single JSON object (no markdown, no explanation):
{{
  "classification": "<final classification string>",
  "severity": <int 1-10>,
  "confidence": <float 0.00-1.00>,
  "description": "<≤2 sentence action-oriented summary>",
  "action_hint": "<recommended immediate action>"
}}
"""

class GroqFusionController:
    """
    Orchestrates the fusion of vision, motion, and audio signals using Groq LLM.
    """

    def __init__(self) -> None:
        self._cfg = get_settings()
        self._rotator = KeyRotator(self._cfg.groq_api_keys)
        self._client = None
        self._initialized = False
        self._init_client()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        api_key = self._rotator.current_key
        if not api_key:
            logger.warning("No Groq API keys available — fusion will use weighted heuristic.")
            return
        try:
            from groq import Groq  # type: ignore

            self._client = Groq(api_key=api_key)
            self._initialized = True
            logger.info("Groq fusion initialised — model=%s", self._cfg.groq_model)
        except Exception as exc:
            logger.error("Failed to initialise Groq client: %s", exc)

    def reinitialize(self) -> None:
        """Re-run setup after settings update."""
        self._initialized = False
        self._client = None
        self._init_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fuse(
        self,
        motion: MotionResult,
        vision: VisionResult,
        yolo: Optional[YOLOResult] = None,
        audio: Optional[dict] = None,
        zone: str = "general",
        risk_level: int = 2,
        camera_id: str = "default",
    ) -> FusionResult:
        """
        Produce a final FusionResult from motion + vision + audio signals.
        """
        if self._initialized and self._client:
            return self._groq_fusion(motion, vision, yolo, audio, zone, risk_level, camera_id)
        return self._heuristic_fusion(motion, vision, yolo, audio, zone, risk_level)

    # ------------------------------------------------------------------
    # Groq-powered fusion
    # ------------------------------------------------------------------

    def _groq_fusion(
        self,
        motion: MotionResult,
        vision: VisionResult,
        yolo: Optional[YOLOResult],
        audio: Optional[dict],
        zone: str,
        risk_level: int,
        camera_id: str,
    ) -> FusionResult:
        signals = {
            "motion": {
                "detected": motion.motion_detected,
                "score": round(motion.motion_score, 4),
            },
            "vision": {
                "classification": vision.classification,
                "severity": vision.severity,
                "confidence": round(vision.confidence, 4),
                "description": vision.description,
            },
            "yolo": {
                "detections": yolo.detection_count if yolo else 0,
                "labels": yolo.labels if yolo else [],
                "max_confidence": round(yolo.max_confidence, 4) if yolo else 0.0,
            },
            "audio": audio if audio else {"anomaly_detected": False, "label": "normal", "score": 0.0},
            "context": {
                "zone": zone,
                "risk_level": risk_level
            }
        }
        prompt = _FUSION_PROMPT.format(signals_json=json.dumps(signals, indent=2))

        try:
            response = self._client.chat.completions.create(
                model=self._cfg.groq_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=256,
            )
            raw_text = response.choices[0].message.content.strip()
            return self._parse_groq_response(raw_text, vision, motion, yolo, audio, risk_level)
        except Exception as exc:
            # Handle rotation
            err_msg = str(exc).lower()
            if "429" in err_msg or "rate_limit" in err_msg:
                if self._rotator.rotate():
                    self._init_client()
                    # retry logic omitted for brevity, fallback will take over
            
            logger.error("Groq fusion failed [cam=%s]: %s", camera_id, exc)
            return self._heuristic_fusion(motion, vision, yolo, audio, zone, risk_level)

    @staticmethod
    def _parse_groq_response(
        raw_text: str,
        vision: VisionResult,
        motion: MotionResult,
        yolo: Optional[YOLOResult],
        audio: Optional[dict],
        risk_level: int,
    ) -> FusionResult:
        cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError(f"Cannot parse Groq JSON: {cleaned[:80]}")

        classification = str(data.get("classification", vision.classification))
        severity = max(1, min(10, int(data.get("severity", vision.severity))))
        confidence = max(0.0, min(1.0, float(data.get("confidence", vision.confidence))))
        description = str(data.get("description", vision.description))
        action_hint = str(data.get("action_hint", "Monitor the scene."))

        alert_threshold = get_settings().alert_threshold
        return FusionResult(
            classification=classification,
            severity=severity,
            confidence=confidence,
            description=f"{description} | Action: {action_hint}",
            attribution={
                "gemini": True,
                "groq": True,
                "yolo": bool(yolo and yolo.detection_count > 0),
                "audio": bool(audio and audio.get("anomaly_detected")),
                "audio_label": audio.get("label") if audio else None,
                "yolo_detections": yolo.detection_count if yolo else 0,
                "motion_score": round(motion.motion_score, 4),
                "risk_level": risk_level,
            },
            ai_model="groq+multimodal",
            should_alert=severity >= alert_threshold,
        )

    # ------------------------------------------------------------------
    # Heuristic fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _heuristic_fusion(
        motion: MotionResult,
        vision: VisionResult,
        yolo: Optional[YOLOResult],
        audio: Optional[dict],
        zone: str,
        risk_level: int,
    ) -> FusionResult:
        """Weighted combination without LLM inference."""
        # Start from the strongest of Gemini and YOLO signals
        severity = vision.severity
        classification = vision.classification

        if yolo and yolo.detection_count > 0:
            severity = max(severity, yolo.suggested_severity)
            if yolo.suggested_severity >= vision.severity + 1:
                classification = yolo.suggested_classification

        # Boost for high motion
        if motion.motion_score > 0.4:
            severity = min(10, severity + 1)

        # Boost for dangerous zones
        if risk_level >= 4:
            severity = min(10, severity + 1)

        # Boost for audio anomalies
        if audio and audio.get("anomaly_detected"):
            severity = min(10, severity + 2)
            if severity > vision.severity:
                classification = f"audio_alert_{audio.get('label')}"

        # Suppress if both agree it's calm
        if vision.classification == "normal_activity" and motion.motion_score < 0.05:
            severity = min(severity, 3)

        yolo_conf = yolo.max_confidence if (yolo and yolo.detection_count > 0) else None
        confidence = ConfidenceScorer.compute_fused_confidence(
            vision_conf=vision.confidence,
            motion_score=motion.motion_score,
            yolo_conf=yolo_conf
        )

        alert_threshold = get_settings().alert_threshold
        return FusionResult(
            classification=classification,
            severity=severity,
            confidence=round(confidence, 4),
            description=vision.description,
            attribution={
                "gemini": True,
                "groq": False,  # fallback — no LLM call
                "yolo": bool(yolo and yolo.detection_count > 0),
                "yolo_detections": yolo.detection_count if yolo else 0,
                "motion_score": round(motion.motion_score, 4),
                "risk_level": risk_level,
            },
            ai_model="gemini+yolo+heuristic" if yolo else "gemini+heuristic",
            should_alert=severity >= alert_threshold,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

groq_fusion = GroqFusionController()
