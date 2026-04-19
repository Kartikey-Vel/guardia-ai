"""
Ultralytics YOLO Detector
==========================
Provides local object detection via Ultralytics YOLO (v5/v8 compatible weights)
for security-scene enrichment.

The detector is optional and fails open: if model loading/inference fails,
the pipeline still runs using motion + Gemini + Groq.
"""

import logging
from typing import List

import numpy as np

from config import get_settings
from models.schemas import YOLODetection, YOLOResult

logger = logging.getLogger(__name__)


class YoloDetector:
    """Thin wrapper around ultralytics.YOLO with security-oriented summaries."""

    _WEAPON_LABELS = {
        "knife",
        "gun",
        "pistol",
        "rifle",
        "firearm",
        "baseball bat",
        "scissors",
    }

    def __init__(self) -> None:
        self._cfg = get_settings()
        self._model = None
        self._initialized = False
        self._init_model()

    def _init_model(self) -> None:
        if not self._cfg.yolo_enabled:
            logger.info("YOLO disabled via config")
            return

        try:
            from ultralytics import YOLO  # type: ignore

            self._model = YOLO(self._cfg.yolo_model)
            self._initialized = True
            logger.info("YOLO initialized | model=%s", self._cfg.yolo_model)
        except Exception as exc:
            self._initialized = False
            self._model = None
            logger.warning("YOLO init failed; continuing without YOLO: %s", exc)

    def reinitialize(self) -> None:
        self._initialized = False
        self._model = None
        self._init_model()

    @property
    def is_ready(self) -> bool:
        return self._initialized and self._model is not None

    def detect(self, frame: np.ndarray, camera_id: str = "default") -> YOLOResult:
        if not self.is_ready:
            return self._empty_result()

        try:
            prediction = self._model.predict(
                source=frame,
                conf=self._cfg.yolo_conf_threshold,
                iou=self._cfg.yolo_iou_threshold,
                max_det=self._cfg.yolo_max_detections,
                verbose=False,
            )
        except Exception as exc:
            logger.error("YOLO inference failed [cam=%s]: %s", camera_id, exc)
            return self._empty_result()

        if not prediction:
            return self._empty_result()

        result = prediction[0]
        names = result.names or {}
        boxes = result.boxes

        detections: List[YOLODetection] = []
        labels: List[str] = []
        max_conf = 0.0

        if boxes is not None:
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = [float(v) for v in box.xyxy[0].tolist()]
                label = str(names.get(cls_id, cls_id)).lower()

                labels.append(label)
                max_conf = max(max_conf, conf)
                detections.append(
                    YOLODetection(label=label, confidence=conf, bbox_xyxy=xyxy)
                )

        suggested_classification, suggested_severity = self._derive_security_signal(
            labels,
            max_conf,
        )

        return YOLOResult(
            enabled=True,
            model=self._cfg.yolo_model,
            detection_count=len(detections),
            labels=labels,
            max_confidence=round(max_conf, 4),
            detections=detections,
            suggested_classification=suggested_classification,
            suggested_severity=suggested_severity,
        )

    def _derive_security_signal(
        self,
        labels: List[str],
        max_confidence: float,
    ) -> tuple[str, int]:
        if not labels:
            return "normal_activity", 1

        unique_labels = set(labels)
        person_count = labels.count("person")

        if unique_labels.intersection(self._WEAPON_LABELS):
            return "unauthorized_access", 9

        if person_count >= 8:
            return "crowd_formation", 7

        if person_count >= 3:
            return "suspicious_loitering", 5

        if "person" in unique_labels and max_confidence >= 0.65:
            return "suspicious_loitering", 4

        return "normal_activity", 2

    def _empty_result(self) -> YOLOResult:
        return YOLOResult(
            enabled=bool(self._cfg.yolo_enabled),
            model=self._cfg.yolo_model,
            detection_count=0,
            labels=[],
            max_confidence=0.0,
            detections=[],
            suggested_classification="normal_activity",
            suggested_severity=1,
        )


yolo_detector = YoloDetector()
