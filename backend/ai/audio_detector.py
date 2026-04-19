"""
Audio Detector — HuggingFace Inference Integration
===================================================
Detects audio anomalies (glass breaking, screaming, gunshots) using
the HuggingFace Inference API.

Model: MIT/ast-finetuned-audioset-10-10-0.4593
"""

import logging
import requests
from typing import Dict, Any, Optional
from config import get_settings

logger = logging.getLogger(__name__)


class AudioDetector:
    """
    Audio anomaly detector using HuggingFace Inference API.
    
    If the API key is missing, it falls back to a neutral state.
    """

    def __init__(self) -> None:
        self._cfg = get_settings()
        self._api_url = "https://api-inference.huggingface.co/models/MIT/ast-finetuned-audioset-10-10-0.4593"
        self._threshold = 0.5
        
        if not self._cfg.huggingface_api_key:
            logger.info("AudioDetector initialized in STUB mode (No HF API Key).")
        else:
            logger.info("AudioDetector initialized with HuggingFace Inference API.")

    def analyze_audio(self, audio_data: bytes) -> Dict[str, Any]:
        """
        Analyse audio bytes via HuggingFace.
        
        Parameters
        ----------
        audio_data: Raw audio data bytes (FLAC/WAV recommended for API).
        
        Returns
        -------
        dict with detection results.
        """
        if not self._cfg.huggingface_api_key:
            return self._default_result()

        headers = {"Authorization": f"Bearer {self._cfg.huggingface_api_key}"}
        
        try:
            response = requests.post(self._api_url, headers=headers, data=audio_data, timeout=5)
            response.raise_for_status()
            
            # The model returns a list of labels and scores
            # Example: [{"label": "Siren", "score": 0.9}, {"label": "Glass", "score": 0.1}]
            results = response.json()
            
            if not results or not isinstance(results, list):
                return self._default_result()

            # Find the highest scoring anomaly label
            # Security relevant labels in AST Audioset: Siren, Explosion, Gunshot, Glass breaking, Screaming
            security_labels = {"Siren", "Explosion", "Gunshot", "Glass", "Screaming", "Burst", "Alarm"}
            
            top_result = results[0]  # Usually sorted by score
            label = top_result.get("label", "unknown")
            score = top_result.get("score", 0.0)

            is_anomaly = label in security_labels and score > self._threshold

            logger.info(f"Audio Analysis: {label} ({score:.2f}) | Anomaly: {is_anomaly}")

            return {
                "anomaly_detected": is_anomaly,
                "score": score,
                "label": label,
                "raw_results": results[:3]
            }

        except Exception as exc:
            logger.error(f"HuggingFace Audio API error: {exc}")
            return self._default_result()

    def _default_result(self) -> Dict[str, Any]:
        return {
            "anomaly_detected": False,
            "score": 0.0,
            "label": "normal",
        }


audio_detector = AudioDetector()
