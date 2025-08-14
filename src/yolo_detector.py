from __future__ import annotations
from typing import List, Tuple

import numpy as np

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None  # type: ignore


# A light wrapper to abstract Ultralytics output
class YoloDetector:
    def __init__(self, weights: str = "yolov8n.pt", conf: float = 0.25, iou: float = 0.45, imgsz: int = 640, device: str = "auto", half: bool = True):
        self.weights = weights
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.device = device
        self.half = half
        self.model = None
        if YOLO is not None:
            try:
                self.model = YOLO(self.weights)
                # set device if provided
                if hasattr(self.model, 'to') and self.device and self.device != 'auto':
                    try:
                        self.model.to(self.device)
                    except Exception:
                        pass
            except Exception:
                self.model = None

    def available(self) -> bool:
        return self.model is not None

    def detect(self, frame_bgr: np.ndarray) -> List[Tuple[int, int, int, int, str, float]]:
        """Return list of (x1,y1,x2,y2,label,conf) in pixel coords."""
        if not self.available():
            return []
        results = self.model.predict(source=frame_bgr, conf=self.conf, iou=self.iou, verbose=False, imgsz=self.imgsz, half=self.half)
        out = []
        if not results:
            return out
        r = results[0]
        names = r.names
        if r.boxes is None:
            return out
        for b in r.boxes:
            xyxy = b.xyxy[0].tolist()
            x1, y1, x2, y2 = map(int, xyxy)
            cls_id = int(b.cls[0].item())
            conf = float(b.conf[0].item())
            label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
            out.append((x1, y1, x2, y2, label, conf))
        return out
