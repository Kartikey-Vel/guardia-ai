from __future__ import annotations
from typing import List, Tuple
import io
import os

import numpy as np

try:
    from google.cloud import vision
except Exception:  # pragma: no cover
    vision = None  # type: ignore


class GoogleVisionClient:
    def __init__(self, min_score: float = 0.6):
        self.min_score = min_score
        self.client = None
        if vision is not None and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                self.client = vision.ImageAnnotatorClient()
            except Exception:
                self.client = None

    def available(self) -> bool:
        return self.client is not None

    def label_image(self, image_bgr: np.ndarray) -> List[Tuple[str, float]]:
        if not self.available():
            return []
        # Convert BGR to JPEG bytes
        import cv2
        _, buf = cv2.imencode('.jpg', image_bgr)
        content = buf.tobytes()
        image = vision.Image(content=content)
        response = self.client.label_detection(image=image, max_results=10)
        labels = []
        if response.label_annotations:
            for l in response.label_annotations:
                desc = (l.description or "").strip()
                score = float(l.score or 0.0)
                if desc and score >= self.min_score:
                    labels.append((desc.lower(), score))
        return labels
