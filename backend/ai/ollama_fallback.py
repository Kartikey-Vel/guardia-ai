"""
Ollama Local Inference Fallback
================================
Provides a secondary fallback when both Gemini and Groq are unavailable,
using a locally running Ollama instance (e.g. llava multimodal model).

Gracefully no-ops when Ollama is not reachable.
"""

import base64
import json
import logging
import re
from typing import Optional

import numpy as np
import requests
from PIL import Image
from io import BytesIO

from config import get_settings
from models.schemas import VisionResult

logger = logging.getLogger(__name__)

_OLLAMA_URL = "http://localhost:11434/api/generate"
_OLLAMA_MODEL = "llava"

_PROMPT = (
    "You are a security AI. Analyse this CCTV frame and respond ONLY in JSON: "
    '{"classification":"<label>","severity":<1-10>,"confidence":<0-1>,"description":"<text>"}'
)


class OllamaFallback:
    """
    Attempts to classify a frame using a local Ollama llava model.
    Returns None when Ollama is not available so callers can use
    their own fallback chain.
    """

    def __init__(self) -> None:
        self._available: Optional[bool] = None  # lazy-checked on first call

    def _check_availability(self) -> bool:
        try:
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def analyze_frame(
        self,
        frame: np.ndarray,
        motion_score: float = 0.0,
    ) -> Optional[VisionResult]:
        """
        Send frame to Ollama llava.

        Returns VisionResult on success, None if Ollama is unreachable
        or inference fails.
        """
        if self._available is None:
            self._available = self._check_availability()

        if not self._available:
            return None

        try:
            # Encode frame as base64 JPEG
            rgb = frame[:, :, ::-1]
            img = Image.fromarray(rgb.astype("uint8"))
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=70)
            b64 = base64.b64encode(buf.getvalue()).decode()

            payload = {
                "model": _OLLAMA_MODEL,
                "prompt": _PROMPT,
                "images": [b64],
                "stream": False,
            }
            resp = requests.post(_OLLAMA_URL, json=payload, timeout=30)
            raw = resp.json().get("response", "")

            cleaned = re.sub(r"```(?:json)?", "", raw).strip()
            data = json.loads(cleaned)

            return VisionResult(
                classification=str(data.get("classification", "unknown")),
                severity=max(1, min(10, int(data.get("severity", 5)))),
                confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
                description=str(data.get("description", "")),
                raw_response=raw[:300],
            )
        except Exception as exc:
            logger.error("Ollama inference failed: %s", exc)
            self._available = False  # mark unavailable until next restart
            return None


ollama_fallback = OllamaFallback()
