from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

try:
    import mediapipe as mp
except Exception:  # pragma: no cover
    mp = None  # type: ignore


@dataclass
class PoseFlags:
    raised_hands: bool = False


class PoseAnalyzer:
    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        self.enabled = mp is not None
        if self.enabled:
            self.pose = mp.solutions.pose.Pose(
                min_detection_confidence=min_detection_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
        else:
            self.pose = None

    def available(self) -> bool:
        return self.enabled and self.pose is not None

    def analyze(self, image_bgr: np.ndarray) -> PoseFlags:
        if not self.available():
            return PoseFlags()
        # Mediapipe expects RGB
        import cv2
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)
        if not results.pose_landmarks:
            return PoseFlags()
        # Simple heuristic: hand y (wrist) is above nose y
        lm = results.pose_landmarks.landmark
        # Landmarks indices: 0: nose, 15/16 wrists, 11/12 shoulders
        def ly(idx: int) -> float:
            return float(lm[idx].y)
        raised = (ly(15) < ly(0)) or (ly(16) < ly(0))
        return PoseFlags(raised_hands=raised)

    def close(self):
        if self.available():
            self.pose.close()
