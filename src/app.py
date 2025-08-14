from __future__ import annotations
import argparse
import os
import time
from typing import Tuple, List

import numpy as np
import cv2

from .config import AppConfig
from .yolo_detector import YoloDetector
from .vision_client import GoogleVisionClient
from .pose_analyzer import PoseAnalyzer
from .utils import FPSLimiter, motion_changed, draw_bbox, draw_label, crop_roi, EventLogger, save_image, name_color_hsv, SimpleTracker, evaluate_hazards, LoiteringMonitor


def parse_args() -> AppConfig:
    p = argparse.ArgumentParser(description="Guardia-AI: Real-time detection PoC")
    p.add_argument("--source", type=str, default="0", help="Camera index or video path")
    p.add_argument("--frameskip", type=int, default=3, help="Process every Nth frame")
    p.add_argument("--no-motion", action="store_true", help="Disable motion filter")
    p.add_argument("--vision", action="store_true", help="Enable Google Vision verification")
    p.add_argument("--pose", action="store_true", help="Enable Mediapipe Pose analysis")
    p.add_argument("--show", action="store_true", help="Show window")
    p.add_argument("--snapshots", action="store_true", help="Save harmful snapshots")
    p.add_argument("--max-vision-fps", type=float, default=None, help="Limit cloud calls per second (default from config)")

    args = p.parse_args()

    source: str | int
    source = int(args.source) if args.source.isdigit() else args.source

    cfg = AppConfig(
        source=source,
        frameskip=max(0, args.frameskip),
        use_motion_filter=not args.no_motion,
        use_vision=args.vision or bool(int(os.getenv("GUARDIA_USE_VISION", "0"))),
        use_pose=args.pose or bool(int(os.getenv("GUARDIA_USE_POSE", "0"))),
        save_snapshots=args.snapshots,
    )
    if args.max_vision_fps is not None:
        cfg.max_vision_fps = max(0.1, float(args.max_vision_fps))
    cfg.ensure_dirs()
    # attach show flag (not part of config dataclass for simplicity)
    cfg.show = bool(args.show)  # type: ignore[attr-defined]
    return cfg


def gender_from_labels(labels: List[tuple[str, float]]) -> str | None:
    # Very naive demo mapping
    for name, score in labels:
        if name in ("male", "man", "boy") and score > 0.6:
            return "male"
        if name in ("female", "woman", "girl") and score > 0.6:
            return "female"
    return None


def is_harmful(labels: List[str], harmful_set: set[str]) -> bool:
    return any(l.lower() in harmful_set for l in labels)


def main() -> None:
    cfg = parse_args()

    cap = cv2.VideoCapture(cfg.source)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open source: {cfg.source}")

    detector = YoloDetector(weights=cfg.yolo_weights, conf=cfg.yolo_conf_thresh, iou=cfg.yolo_iou_thresh, imgsz=cfg.yolo_imgsz, device=cfg.device, half=cfg.half)
    if not detector.available():
        print("Warning: YOLO model unavailable. The app will run but no detections will be produced.")

    vision = GoogleVisionClient(min_score=cfg.vision_min_score) if cfg.use_vision else GoogleVisionClient(1.0)
    if cfg.use_vision and not vision.available():
        print("Warning: Vision API not available; continuing without cloud verification.")

    pose = PoseAnalyzer(cfg.pose_min_detection_confidence, cfg.pose_min_tracking_confidence) if cfg.use_pose else PoseAnalyzer(1, 1)
    if cfg.use_pose and not pose.available():
        print("Warning: Pose not available; continuing without pose analysis.")

    vision_limiter = FPSLimiter(cfg.max_vision_fps)
    logger = EventLogger(cfg.log_dir)

    prev_gray = None
    frame_idx = 0
    tracker = SimpleTracker()
    loiter = LoiteringMonitor(seconds_threshold=cfg.loiter_seconds_threshold,
                              radius_px=cfg.loiter_radius_px,
                              classes=set(cfg.loiter_classes))

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            process_this = True
            if cfg.use_motion_filter:
                changed, prev_gray = motion_changed(prev_gray, frame)
                process_this = changed

            if cfg.frameskip > 0 and (frame_idx % cfg.frameskip != 0):
                process_this = False

            detections = []
            if process_this:
                if detector.available() and (cfg.track_interval <= 1 or frame_idx % cfg.track_interval == 0):
                    # run detector then update tracker
                    dets = detector.detect(frame)
                    detections = tracker.update(dets)
                else:
                    # rely on tracker state
                    detections = tracker.update([])

            # Iterate detections and analyze
            for (x1, y1, x2, y2, label, conf) in detections:
                labels = [label]
                is_person = label.lower() == "person"
                roi = None
                vlabels = []

                if cfg.use_vision and vision_limiter.allow():
                    roi = crop_roi(frame, (x1, y1, x2, y2))
                    vlabels = vision.label_image(roi)
                    labels.extend([n for n, s in vlabels])

                # Pose analysis only for person or if ROI used
                pose_flags = None
                if cfg.use_pose and (is_person or roi is not None):
                    roi_img = roi if roi is not None else frame[max(0, y1):y2, max(0, x1):x2]
                    pose_flags = pose.analyze(roi_img)

                # Clothing color heuristic for person
                clothing = None
                if is_person:
                    # Lower half as a proxy for clothing color
                    hmid = y1 + (y2 - y1) // 2
                    lower = frame[hmid:y2, x1:x2]
                    clothing = name_color_hsv(lower)

                harmful, hazard_tags = evaluate_hazards(label, vlabels, cfg.harmful_labels, cfg.advanced_detection)
                color = (0, 0, 255) if harmful else (0, 255, 0)
                draw_bbox(frame, (x1, y1, x2, y2), color=color)
                info = f"{label} {conf:.2f}"
                if cfg.use_vision and len(labels) > 1:
                    info += f" | {','.join([l for l in labels if l != label])}"
                if pose_flags and pose_flags.raised_hands:
                    info += " | raised_hands"
                if clothing:
                    info += f" | clothing:{clothing}"
                draw_label(frame, info, x1, y1, color=color)

                # Logs and snapshots for harmful
                if harmful:
                    ts = time.time()
                    event = {
                        "ts": ts,
                        "box": [int(x1), int(y1), int(x2), int(y2)],
                        "label": label,
                        "allLabels": labels,
                        "confidence": float(conf),
                        "pose": vars(pose_flags) if pose_flags else {},
                        "clothingColor": clothing,
                        "hazards": hazard_tags,
                    }
                    logger.log(event)
                    if cfg.save_snapshots:
                        snap_path = os.path.join(cfg.snapshot_dir, f"harmful_{int(ts)}_{x1}_{y1}.jpg")
                        crop = frame[max(0, y1):y2, max(0, x1):x2]
                        if crop.size > 0:
                            save_image(snap_path, crop)

            # Loitering detection
            for tid, tr in loiter.check(tracker.get_tracks()):
                bx = tr.get('box', (0, 0, 0, 0))
                x1, y1, x2, y2 = int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])
                draw_label(frame, "LOITERING", x1, y1 - 8, color=(0, 165, 255))
                draw_bbox(frame, (x1, y1, x2, y2), color=(0, 165, 255))
                event = {
                    "ts": time.time(),
                    "box": [x1, y1, x2, y2],
                    "label": tr.get('label', 'unknown'),
                    "allLabels": [tr.get('label', 'unknown')],
                    "confidence": float(tr.get('conf', 0.0)),
                    "pose": {},
                    "clothingColor": None,
                    "hazards": ["loitering"],
                }
                logger.log(event)

            if getattr(cfg, "show", False):
                # draw hazard zones
                for zx1, zy1, zx2, zy2 in cfg.hazard_zones:
                    cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (255, 0, 0), 1)
                cv2.imshow("Guardia-AI", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        try:
            pose.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
