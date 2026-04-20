"""
TASK-004: Gemini Vision API — Frame Analysis Module
=====================================================
Sends a camera frame to Google Gemini 1.5 Flash for security-scene
classification, returning a structured VisionResult with:
  - classification  (threat category string)
  - severity        (int 1-10)
  - confidence      (float 0.0-1.0)
  - description     (natural language summary)

Design decisions
----------------
* Uses google-generativeai SDK (google.generativeai).
* Frame is passed as pillow Image (from bytes / numpy array) — avoids
  writing temp files.
* Prompt engineering guides Gemini to always respond in parseable JSON
  so downstream fusion logic can reliably extract fields.
* Falls back to a conservative rule-based result if the API key is
  missing, the model is unavailable, or parsing fails.
* Module exposes a singleton `gemini_analyzer` for reuse across requests.
"""

import base64
import json
import logging
import re
from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image

from config import get_settings
from models.schemas import VisionResult
from ai.utils import KeyRotator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a professional security analyst reviewing CCTV / surveillance footage.

Analyse the provided image and respond ONLY with a single JSON object — no
markdown, no explanation outside the JSON block.

Required JSON fields:
  classification : string — one of:
      "normal_activity" | "suspicious_loitering" | "unauthorized_access" |
      "physical_altercation" | "theft_or_shoplifting" | "crowd_formation" |
      "fire_or_smoke" | "vehicle_incident" | "abandoned_object" | "unknown"
  severity       : integer 1-10 (1 = benign, 10 = critical emergency)
  confidence     : float 0.00-1.00 (your confidence in the classification)
  description    : string — ≤2 sentence human-readable summary of what you see

Example response (do NOT include backticks):
{
  "classification": "suspicious_loitering",
  "severity": 4,
  "confidence": 0.82,
  "description": "An individual has been standing near the entrance for an
extended period without apparent purpose. Recommend monitoring."
}
"""

# ---------------------------------------------------------------------------
# GeminiVisionAnalyzer
# ---------------------------------------------------------------------------


class GeminiVisionAnalyzer:
    """
    Wrapper around Gemini 1.5 Flash for single-frame security analysis.

    Usage
    -----
    >>> analyzer = GeminiVisionAnalyzer()
    >>> result = await analyzer.analyze_frame(frame_bgr)
    >>> print(result.classification, result.severity)
    """

    def __init__(self) -> None:
        self._cfg = get_settings()
        self._rotator = KeyRotator(self._cfg.gemini_api_keys)
        self._model = None
        self._initialized = False
        self._init_client()

    def _init_client(self) -> None:
        """Configure the Gemini client. Gracefully handles missing keys and supports rotation."""
        api_key = self._rotator.current_key
        if not api_key:
            logger.warning("No Gemini API keys available — Gemini vision will use rule-based fallback.")
            return

        try:
            # Use the current google-genai SDK
            try:
                import google.genai as genai  # type: ignore
                from google.genai import types as genai_types  # type: ignore
                self._sdk = "new"
            except ImportError:
                import google.generativeai as genai  # type: ignore
                self._sdk = "legacy"

            if self._sdk == "new":
                self._client = genai.Client(api_key=api_key)
                self._model_name = self._cfg.gemini_model
            else:
                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel(
                    model_name=self._cfg.gemini_model,
                    generation_config={
                        "temperature": 0.2,
                        "top_p": 0.8,
                        "max_output_tokens": 256,
                    },
                )
                self._client = None

            self._initialized = True
            logger.info("Gemini Vision initialised — model=%s sdk=%s", self._cfg.gemini_model, self._sdk)
        except Exception as exc:
            logger.error("Failed to initialise Gemini client: %s", exc)

    def reinitialize(self) -> None:
        """Re-run client setup (called after settings update)."""
        self._initialized = False
        self._model = None
        self._init_client()

    # ------------------------------------------------------------------
    # Public API — synchronous wrapper (FastAPI runs in threadpool)
    # ------------------------------------------------------------------

    def analyze_frame(
        self,
        frame: np.ndarray,
        camera_id: str = "default",
        motion_score: float = 0.0,
    ) -> VisionResult:
        """
        Analyse a BGR numpy frame and return a VisionResult.

        Falls back to rule-based scoring if Gemini is unavailable.
        """
        if not self._initialized:
            return self._rule_based_fallback(motion_score, reason="no_api_key")

        pil_image = self._bgr_to_pil(frame)
        if pil_image is None:
            return self._rule_based_fallback(motion_score, reason="decode_error")

        try:
            return self._call_gemini(pil_image, camera_id, motion_score)
        except Exception as exc:
            # TASK-052: API Key rotation on quota hit
            err_msg = str(exc).lower()
            if "429" in err_msg or "quota" in err_msg or "rate limit" in err_msg or "400" in err_msg or "invalid" in err_msg or "not valid" in err_msg:
                logger.warning("Gemini API error. Attempting key rotation...")
                if self._rotator.rotate():
                    self._init_client()
                    try:
                        return self._call_gemini(pil_image, camera_id, motion_score)
                    except Exception as retry_exc:
                        logger.error("Retry with rotated Gemini key failed: %s", retry_exc)

            logger.error("Gemini API call failed [cam=%s]: %s", camera_id, exc)
            return self._rule_based_fallback(motion_score, reason=str(exc)[:80])

    def analyze_bytes(
        self,
        image_bytes: bytes,
        camera_id: str = "default",
        motion_score: float = 0.0,
    ) -> VisionResult:
        """
        Analyse raw JPEG/PNG bytes.  Convenience method for upload endpoints.
        """
        try:
            pil_image = Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            logger.error("Cannot decode image bytes: %s", exc)
            return self._rule_based_fallback(motion_score, reason="decode_error")

        if not self._initialized or self._model is None:
            return self._rule_based_fallback(motion_score, reason="no_api_key")

        try:
            return self._call_gemini(pil_image, camera_id, motion_score)
        except Exception as exc:
            logger.error("Gemini API call failed [cam=%s]: %s", camera_id, exc)
            return self._rule_based_fallback(motion_score, reason=str(exc)[:80])

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _call_gemini(
        self,
        image: Image.Image,
        camera_id: str,
        motion_score: float,
    ) -> VisionResult:
        """Build the multimodal prompt, call the API, parse response."""
        context_note = (
            f"Motion intensity score for this frame: {motion_score:.3f} "
            f"(0=no motion, 1=maximum motion). Camera ID: {camera_id}."
        )

        if getattr(self, "_sdk", "legacy") == "new":
            # New google.genai SDK path
            import google.genai as genai  # type: ignore
            from google.genai import types as genai_types  # type: ignore
            # Convert PIL image to bytes
            buf = BytesIO()
            image.save(buf, format="JPEG", quality=80)
            img_bytes = buf.getvalue()
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=[
                    _SYSTEM_PROMPT + "\n" + context_note,
                    genai_types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                ],
            )
            raw_text = response.text.strip()
        else:
            # Legacy google.generativeai path
            prompt_parts = [_SYSTEM_PROMPT, context_note, image]
            response = self._model.generate_content(prompt_parts)
            raw_text = response.text.strip()

        logger.debug("Gemini raw response [cam=%s]: %s", camera_id, raw_text[:200])
        return self._parse_response(raw_text)

    @staticmethod
    def _parse_response(raw_text: str) -> VisionResult:
        """
        Parse JSON from Gemini's response into a VisionResult.
        Handles cases where the model wraps JSON in markdown code fences.
        """
        # Strip markdown fences if present
        cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract the first {...} block
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise ValueError(f"Cannot parse Gemini JSON: {cleaned[:100]}")

        # Validate and coerce fields
        classification = str(data.get("classification", "unknown")).lower()
        severity = max(1, min(10, int(data.get("severity", 5))))
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        description = str(data.get("description", ""))

        return VisionResult(
            classification=classification,
            severity=severity,
            confidence=confidence,
            description=description,
            raw_response=raw_text[:500],
        )

    @staticmethod
    def _bgr_to_pil(frame: np.ndarray) -> Optional[Image.Image]:
        """Convert OpenCV BGR frame to PIL RGB Image."""
        try:
            rgb = frame[:, :, ::-1]  # BGR → RGB
            return Image.fromarray(rgb.astype(np.uint8))
        except Exception as exc:
            logger.error("BGR→PIL conversion failed: %s", exc)
            return None

    @staticmethod
    def _rule_based_fallback(
        motion_score: float,
        reason: str = "unavailable",
    ) -> VisionResult:
        """
        Heuristic fallback when Gemini is unavailable.
        Maps motion intensity to a coarse classification + severity.
        """
        if motion_score < 0.02:
            cls, sev, conf = "normal_activity", 1, 0.90
            desc = "No significant activity detected. Scene appears calm."
        elif motion_score < 0.10:
            cls, sev, conf = "normal_activity", 2, 0.75
            desc = "Minor movement detected. Likely routine activity."
        elif motion_score < 0.25:
            cls, sev, conf = "suspicious_loitering", 4, 0.55
            desc = "Moderate motion detected. Manual review recommended."
        elif motion_score < 0.50:
            cls, sev, conf = "unauthorized_access", 6, 0.50
            desc = "Significant motion detected. Possible intrusion — review needed."
        else:
            cls, sev, conf = "physical_altercation", 8, 0.45
            desc = "High-intensity motion detected. Potential security incident."

        logger.info(
            "Gemini fallback used (reason=%s): cls=%s sev=%d conf=%.2f",
            reason, cls, sev, conf,
        )
        return VisionResult(
            classification=cls,
            severity=sev,
            confidence=conf,
            description=desc,
            raw_response=f"[fallback:{reason}]",
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

gemini_analyzer = GeminiVisionAnalyzer()
