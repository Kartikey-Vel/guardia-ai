"""
Audio Detector — Placeholder / Future Module
=============================================
Detects audio anomalies (glass breaking, screaming, gunshots) from
microphone input.  Full implementation is outside scope of this sprint;
this module provides a compatible interface so the pipeline can import it
without errors.
"""

import logging

logger = logging.getLogger(__name__)


class AudioDetector:
    """
    Stub audio anomaly detector.

    In a future sprint this will use PyAudio + a small ML model (e.g.
    YAMNet or a fine-tuned wav2vec2 checkpoint) to classify audio events.
    """

    def __init__(self) -> None:
        logger.info("AudioDetector initialised (stub — no active inference).")

    def analyze_chunk(self, audio_bytes: bytes) -> dict:
        """
        Analyse an audio chunk.  Currently returns a no-event result.

        Parameters
        ----------
        audio_bytes: Raw PCM bytes (16-bit, 16 kHz mono assumed).

        Returns
        -------
        dict with keys: anomaly_detected (bool), score (float), label (str)
        """
        return {
            "anomaly_detected": False,
            "score": 0.0,
            "label": "silence",
        }


audio_detector = AudioDetector()
