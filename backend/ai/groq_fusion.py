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
from models.schemas import FusionResult, MotionResult, VisionResult

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
{
  "classification": "<final classification string>",
  "severity": <int 1-10>,
  "confidence": <float 0.00-1.00>,
  "description": "<≤2 sentence action-oriented summary>",
  "action_hint": "<recommended immediate action>"
}
"""


class GroqFusionController:
    """
    LLM-powered multi-signal fusion using Groq's llama3 endpoint.

    Usage
    -----
    >>> fusion = GroqFusionController()
    >>> result = fusion.fuse(motion_result, vision_result, zone="entrance", risk_level=3)
    """

    def __init__(self) -> None:
        self._cfg = get_settings()
        self._client = None
        self._initialized = False
        self._init_client()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_client(self) -> None:
        if not self._cfg.groq_api_key:
            logger.warning("GROQ_API_KEY not set — fusion will use weighted heuristic.")
            return
        try:
            from groq import Groq  # type: ignore

            self._client = Groq(api_key=self._cfg.groq_api_key)
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
        zone: str = "general",
        risk_level: int = 2,
        camera_id: str = "default",
    ) -> FusionResult:
        """
        Produce a final FusionResult from motion + vision signals.

        Parameters
        ----------
        motion:      Output of MotionDetector.process_frame()
        vision:      Output of GeminiVisionAnalyzer.analyze_frame()
        zone:        Camera zone label (e.g. "entrance", "warehouse")
        risk_level:  Camera risk level 1-5 (affects severity weights)
        camera_id:   Identifier for logging
        """
        if self._initialized and self._client:
            return self._groq_fusion(motion, vision, zone, risk_level, camera_id)
        return self._heuristic_fusion(motion, vision, zone, risk_level)

    # ------------------------------------------------------------------
    # Groq-powered fusion
    # ------------------------------------------------------------------

    def _groq_fusion(
        self,
        motion: MotionResult,
        vision: VisionResult,
        zone: str,
        risk_level: int,
        camera_id: str,
    ) -> FusionResult:
        signals = {
            "motion_detected": motion.motion_detected,
            "motion_score": round(motion.motion_score, 4),
            "contour_count": motion.contour_count,
            "gemini_classification": vision.classification,
            "gemini_severity": vision.severity,
            "gemini_confidence": round(vision.confidence, 4),
            "gemini_description": vision.description,
            "zone": zone,
            "zone_risk_level": risk_level,
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
            logger.debug("Groq fusion raw [cam=%s]: %s", camera_id, raw_text[:200])
            return self._parse_groq_response(raw_text, vision, motion, risk_level)
        except Exception as exc:
            logger.error("Groq fusion failed [cam=%s]: %s", camera_id, exc)
            return self._heuristic_fusion(motion, vision, zone, risk_level)

    @staticmethod
    def _parse_groq_response(
        raw_text: str,
        vision: VisionResult,
        motion: MotionResult,
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
                "motion_score": round(motion.motion_score, 4),
                "risk_level": risk_level,
            },
            ai_model="groq+gemini",
            should_alert=severity >= alert_threshold,
        )

    # ------------------------------------------------------------------
    # Heuristic fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _heuristic_fusion(
        motion: MotionResult,
        vision: VisionResult,
        zone: str,
        risk_level: int,
    ) -> FusionResult:
        """Weighted combination without LLM inference."""
        # Start from Gemini severity
        severity = vision.severity

        # Boost for high motion
        if motion.motion_score > 0.4:
            severity = min(10, severity + 1)

        # Boost for dangerous zones
        if risk_level >= 4:
            severity = min(10, severity + 1)

        # Suppress if both agree it's calm
        if vision.classification == "normal_activity" and motion.motion_score < 0.05:
            severity = min(severity, 3)

        confidence = (vision.confidence + min(motion.motion_score * 2, 1.0)) / 2

        alert_threshold = get_settings().alert_threshold
        return FusionResult(
            classification=vision.classification,
            severity=severity,
            confidence=round(confidence, 4),
            description=vision.description,
            attribution={
                "gemini": True,
                "groq": False,  # fallback — no LLM call
                "motion_score": round(motion.motion_score, 4),
                "risk_level": risk_level,
            },
            ai_model="gemini+heuristic",
            should_alert=severity >= alert_threshold,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

groq_fusion = GroqFusionController()
