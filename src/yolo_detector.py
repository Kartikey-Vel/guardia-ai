from __future__ import annotations
from typing import List, Tuple

import numpy as np

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover
    YOLO = None  # type: ignore


# A light wrapper to abstract Ultralytics output
class YoloDetector:
    def __init__(self, weights: str = "yolov8n.pt", conf: float = 0.25, iou: float = 0.45, imgsz: int = 640, device: str = "auto", half: bool = True, extra_weights: List[str] | None = None):
        self.weights = weights
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.device = device
        self.half = half
        self.model = None
        self.extra_models: List[object] = []
        if YOLO is not None:
            try:
                self.model = YOLO(self.weights)
                if hasattr(self.model, 'to') and self.device and self.device != 'auto':
                    try:
                        self.model.to(self.device)
                    except Exception:
                        pass
            except Exception:
                self.model = None
            # Load extra models if provided
            if extra_weights:
                for w in extra_weights:
                    try:
                        m = YOLO(w)
                        if hasattr(m, 'to') and self.device and self.device != 'auto':
                            try:
                                m.to(self.device)
                            except Exception:
                                pass
                        self.extra_models.append(m)
                    except Exception:
                        continue

    def available(self) -> bool:
        return self.model is not None

    def detect(self, frame_bgr: np.ndarray) -> List[Tuple[int, int, int, int, str, float]]:
        """Return list of (x1,y1,x2,y2,label,conf) in pixel coords."""
        if not self.available():
            return []
        # call predict safely
        if self.model is None:
            return []
        predict = getattr(self.model, 'predict', None)
        if predict is None:
            return []
        results = predict(source=frame_bgr, conf=self.conf, iou=self.iou, verbose=False, imgsz=self.imgsz, half=self.half)
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

    def available_multi(self) -> bool:
        return self.available() or bool(self.extra_models)

    def detect_multi(self, frame_bgr: np.ndarray) -> List[Tuple[int, int, int, int, str, float]]:
        """Run detections across primary and extra models; merge by simple max-conf on identical class and overlapping boxes."""
        boxes = []  # (x1,y1,x2,y2,label,conf)
        if self.available():
            boxes.extend(self.detect(frame_bgr))
        # Collect from extra models
        if YOLO is None:
            return boxes
        for m in self.extra_models:
            try:
                predict = getattr(m, 'predict', None)
                if predict is None:
                    continue
                results = predict(source=frame_bgr, conf=self.conf, iou=self.iou, verbose=False, imgsz=self.imgsz, half=self.half)
                if not results:
                    continue
                r = results[0]
                names = r.names
                if r.boxes is None:
                    continue
                for b in r.boxes:
                    xyxy = b.xyxy[0].tolist()
                    x1, y1, x2, y2 = map(int, xyxy)
                    cls_id = int(b.cls[0].item())
                    conf = float(b.conf[0].item())
                    label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
                    boxes.append((x1, y1, x2, y2, label, conf))
            except Exception:
                continue
        # Simple NMS by class + IoU threshold: keep max-conf
        def iou(a, b):
            ax1, ay1, ax2, ay2 = a
            bx1, by1, bx2, by2 = b
            inter_x1 = max(ax1, bx1)
            inter_y1 = max(ay1, by1)
            inter_x2 = min(ax2, bx2)
            inter_y2 = min(ay2, by2)
            iw = max(0, inter_x2 - inter_x1)
            ih = max(0, inter_y2 - inter_y1)
            inter = iw * ih
            a_area = max(0, (ax2 - ax1)) * max(0, (ay2 - ay1))
            b_area = max(0, (bx2 - bx1)) * max(0, (by2 - by1))
            union = a_area + b_area - inter
            return inter / union if union > 0 else 0.0
        merged: List[Tuple[int,int,int,int,str,float]] = []
        boxes.sort(key=lambda t: t[-1], reverse=True)
        used = [False] * len(boxes)
        for i, bi in enumerate(boxes):
            if used[i]:
                continue
            used[i] = True
            x1,y1,x2,y2,lab,conf = bi
            for j in range(i+1, len(boxes)):
                if used[j]:
                    continue
                bj = boxes[j]
                if bj[4] != lab:
                    continue
                if iou((x1,y1,x2,y2), bj[:4]) >= 0.5:
                    used[j] = True
            merged.append((x1,y1,x2,y2,lab,conf))
        return merged
