from __future__ import annotations
import os
import time
import threading
import queue
from collections import deque
from typing import Deque, Dict, Any, List, Tuple, Callable, Optional
import json
from datetime import datetime
import hmac
import hashlib
import base64

import cv2
import numpy as np
from flask import Flask, Response, render_template, jsonify, request, make_response, redirect, url_for
import psutil
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    try:
        from .config import AppConfig
        from .yolo_detector import YoloDetector
        from .vision_client import GoogleVisionClient
        from .pose_analyzer import PoseAnalyzer
        from .utils import FPSLimiter, motion_changed, draw_bbox, draw_label, crop_roi, EventLogger, save_image, name_color_hsv, SimpleTracker, evaluate_hazards, LoiteringMonitor
        from .gcp_clients import GCSUploader, PubSubPublisher
        from . import environments as envmgr
        from . import trusted_store
        from .face_auth import FaceAuth
        from . import user_store
        from . import federated
        from .training import JobManager
    except ImportError:
        # Allow running this file directly: python src/server.py
        import sys as _sys, os as _os
        _sys.path.append(_os.path.dirname(_os.path.dirname(__file__)))
        from src.config import AppConfig
        from src.yolo_detector import YoloDetector
        from src.vision_client import GoogleVisionClient
        from src.pose_analyzer import PoseAnalyzer
        from src.utils import FPSLimiter, motion_changed, draw_bbox, draw_label, crop_roi, EventLogger, save_image, name_color_hsv, SimpleTracker, evaluate_hazards, LoiteringMonitor
        from src.gcp_clients import GCSUploader, PubSubPublisher
        from src import environments as envmgr
        from src import trusted_store
        from src.face_auth import FaceAuth
        from src import user_store
        from src import federated
        from src.training import JobManager
except ImportError:
    # Fallback for running as a script: python src/server.py
    from src.config import AppConfig
    from src.yolo_detector import YoloDetector
    from src.vision_client import GoogleVisionClient
    from src.pose_analyzer import PoseAnalyzer
    from src.utils import FPSLimiter, motion_changed, draw_bbox, draw_label, crop_roi, EventLogger, save_image, name_color_hsv, SimpleTracker, evaluate_hazards, LoiteringMonitor
    from src.gcp_clients import GCSUploader, PubSubPublisher
    from src import environments as envmgr
    from src import trusted_store
    from src.face_auth import FaceAuth
    from src import user_store
    from src import federated
    from src.training import JobManager
# Enhanced system modules
try:
    # Use global singletons/instances where provided
    from .performance_monitor import performance_monitor as perf_mon
    from .cache_manager import (
        detection_cache,
        api_cache,
        image_processor,
        frame_buffer,
        get_cache_stats,
    )
    from .alert_system import (
        alert_manager,
        AlertSeverity,
        AlertType,
        create_threat_alert,
        create_zone_breach_alert,
        create_performance_alert,
    )
    from . import mobile_webapp
    ENHANCED_MODULES_AVAILABLE = True
except ImportError:
    try:
        from src.performance_monitor import performance_monitor as perf_mon
        from src.cache_manager import (
            detection_cache,
            api_cache,
            image_processor,
            frame_buffer,
            get_cache_stats,
        )
        from src.alert_system import (
            alert_manager,
            AlertSeverity,
            AlertType,
            create_threat_alert,
            create_zone_breach_alert,
            create_performance_alert,
        )
        from src import mobile_webapp
        ENHANCED_MODULES_AVAILABLE = True
    except ImportError:
        ENHANCED_MODULES_AVAILABLE = False
        perf_mon = None
        detection_cache = None
        api_cache = None
        image_processor = None
        frame_buffer = None
        def get_cache_stats():
            return {}
        alert_manager = None
        class _DummySeverity:
            def __init__(self, *_args, **_kwargs):
                pass
        class _DummyType(_DummySeverity):
            pass
        AlertSeverity = _DummySeverity  # type: ignore
        AlertType = _DummyType  # type: ignore

# Optional: Gemini summaries
try:
    import google.generativeai as genai
except Exception:
    genai = None

## Inline HTML moved to templates/index.html and templates/login.html

# Lightweight async frame grabber to avoid capture->inference blocking
class FrameGrabber(threading.Thread):
    def __init__(self, det: "DetectorThread"):
        super().__init__(daemon=True)
        self.det = det
        self._cap = None
        self._lock = threading.Lock()
        self._latest = None
        self._stop = threading.Event()

    def run(self):
        # open capture with retries using detector's helper
        retries = 0
        cap = None
        while not self._stop.is_set() and retries < 5:
            cap = self.det._open_capture()
            if cap and cap.isOpened():
                break
            retries += 1
            time.sleep(0.5)
        if not cap or not cap.isOpened():
            self.det.last_error = 'open_failed'
            return
        self._cap = cap
        # initialize resolution into metrics
        try:
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            self.det.metrics['frame_width'] = w
            self.det.metrics['frame_height'] = h
        except Exception:
            pass
        # tight loop grabbing latest frame
        while not self._stop.is_set():
            ok, frame = cap.read()
            if not ok:
                self.det.read_failures += 1
                self.det.last_error = 'read_failed'
                time.sleep(0.01)
                continue
            with self._lock:
                self._latest = frame
            # small sleep to yield but keep latency low
            time.sleep(0.001)

        try:
            cap.release()
        except Exception:
            pass

    def get_latest(self):
        with self._lock:
            return None if self._latest is None else self._latest.copy()

    def stop(self):
        self._stop.set()


class DetectorThread(threading.Thread):
    # Class-level defaults for analyzers
    capture_backend: Optional[str] = None
    read_failures: int = 0
    last_error: Optional[str] = None

    def __init__(
        self,
        cfg: AppConfig,
        metrics: Dict[str, Any],
        events: Deque[Dict[str, Any]],
        event_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
        face_auth=None,
        perf=None,
        dcache=None,
    ):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.metrics = metrics
        self.events = events
        self.stop_flag = threading.Event()
        self.frame_lock = threading.Lock()
        # last processed frame buffer
        self.last_frame = None
        # hooks and collaborators
        self.event_hook = event_hook
        self.face_auth = face_auth
        self.perf = perf
        self.dcache = dcache
        # capture diagnostics
        self.capture_backend = None
        self.read_failures = 0
        self.last_error = None
        # last detections snapshot for high-level API
        self._last_detections = []
        # live model reload controls
        self.ctrl_lock = threading.Lock()
        self.reload_requested = False
        self.reload_to_weights = None

    def _open_capture(self):
        src = self.cfg.source
        try:
            # Prefer DirectShow on Windows for webcams
            if isinstance(src, int) or (isinstance(src, str) and src.isdigit()):
                cam_idx = int(src)
                cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
                self.capture_backend = 'CAP_DSHOW'
            else:
                # Try default backend
                cap = cv2.VideoCapture(src)
                self.capture_backend = 'DEFAULT'
                # Fallback to FFMPEG for network streams
                if not cap.isOpened() and str(src).lower().startswith(("rtsp://", "http://", "https://")):
                    cap.release()
                    cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
                    self.capture_backend = 'CAP_FFMPEG'
        except Exception:
            cap = cv2.VideoCapture(self.cfg.source)
            self.capture_backend = 'DEFAULT'
        return cap

    def run(self) -> None:
        # Start a background frame grabber to avoid blocking on slow inference
        grabber = FrameGrabber(self)
        grabber.start()
        # Allow a brief warm-up
        t_start = time.time()
        while grabber.is_alive() and grabber.get_latest() is None and (time.time() - t_start) < 5.0:
            time.sleep(0.02)
        if not grabber.is_alive() or grabber.get_latest() is None:
            print("[Guardia] FATAL: Frame grabber failed to start.")
            self.last_error = 'open_failed'
            try:
                grabber.stop()
            except Exception:
                pass
            return
        # Allow auto-discovery of latest ONNX if a folder or placeholder is provided
        def _resolve_weights(path_like: str) -> str:
            p = str(path_like).strip()
            # If path is a directory, search for best.onnx inside
            try:
                if os.path.isdir(p):
                    for root, _dirs, files in os.walk(p):
                        for f in files:
                            if f.lower() == 'best.onnx':
                                return os.path.join(root, f)
                # If not found, search common runs path
                runs_dir = os.path.abspath(os.path.join(os.getcwd(), 'runs'))
                latest = None
                latest_mtime = -1
                for root, _dirs, files in os.walk(runs_dir):
                    if 'weights' in root.replace('\\','/').lower():
                        for f in files:
                            if f.lower() == 'best.onnx':
                                fp = os.path.join(root, f)
                                try:
                                    mt = os.path.getmtime(fp)
                                except Exception:
                                    mt = 0
                                if mt > latest_mtime:
                                    latest = fp; latest_mtime = mt
                if latest:
                    return latest
            except Exception:
                pass
            return p

        resolved_primary = _resolve_weights(self.cfg.yolo_weights)
        detector = YoloDetector(
            weights=resolved_primary,
            conf=self.cfg.yolo_conf_thresh,
            iou=self.cfg.yolo_iou_thresh,
            imgsz=self.cfg.yolo_imgsz,
            device=self.cfg.device,
            half=self.cfg.half,
            extra_weights=[_resolve_weights(w) for w in (self.cfg.yolo_extra_weights or [])],
        )
        try:
            self.metrics['model_weights'] = str(resolved_primary)
            self.metrics['model_reload_ts'] = int(time.time())
        except Exception:
            pass
        vision = GoogleVisionClient(min_score=self.cfg.vision_min_score) if self.cfg.use_vision else GoogleVisionClient(1.0)
        pose = PoseAnalyzer(self.cfg.pose_min_detection_confidence, self.cfg.pose_min_tracking_confidence) if self.cfg.use_pose else PoseAnalyzer(1, 1)
        vision_limiter = FPSLimiter(self.cfg.max_vision_fps)
        logger = EventLogger(self.cfg.log_dir)

        prev_gray = None
        frame_idx = 0
        tracker = SimpleTracker()
        loiter = LoiteringMonitor(seconds_threshold=self.cfg.loiter_seconds_threshold,
                                  radius_px=self.cfg.loiter_radius_px,
                                  classes=set(self.cfg.loiter_classes))
        t0 = time.time()
        
        # Performance monitoring integration (placeholders for future enhancement)
        fps_counter = 0
        fps_timer = time.time()
        frames_skipped = 0

        while not self.stop_flag.is_set():
            # Handle live model reload requests
            try:
                do_reload = False
                new_weights: Optional[str] = None
                with self.ctrl_lock:
                    if self.reload_requested:
                        do_reload = True
                        new_weights = self.reload_to_weights
                        self.reload_requested = False
                        self.reload_to_weights = None
                if do_reload:
                    w = _resolve_weights(new_weights or self.cfg.yolo_weights)
                    detector = YoloDetector(
                        weights=w,
                        conf=self.cfg.yolo_conf_thresh,
                        iou=self.cfg.yolo_iou_thresh,
                        imgsz=self.cfg.yolo_imgsz,
                        device=self.cfg.device,
                        half=self.cfg.half,
                        extra_weights=[_resolve_weights(wx) for wx in (self.cfg.yolo_extra_weights or [])],
                    )
                    self.metrics['model_weights'] = str(w)
                    self.metrics['model_reload_ts'] = int(time.time())
            except Exception:
                pass
            frame_start_time = time.time()
            frame = grabber.get_latest()
            if frame is None:
                time.sleep(0.01)
                continue
            frame_idx += 1
            fps_counter += 1
            self.metrics['frames'] = frame_idx

            process_this = True
            skip_reason = None
            
            if self.cfg.use_motion_filter:
                changed, prev_gray = motion_changed(prev_gray, frame)
                if not changed:
                    process_this = False
                    skip_reason = "no_motion"

            if self.cfg.frameskip > 0 and (frame_idx % self.cfg.frameskip != 0):
                process_this = False
                skip_reason = "frameskip"
                frames_skipped += 1

            detections: List[Tuple[int, int, int, int, str, float]] = []
            detection_details: List[Dict[str, Any]] = []
            inference_start = time.time()
            detection_count = 0
            
            if process_this and detector.available():
                if self.cfg.track_interval <= 1 or frame_idx % self.cfg.track_interval == 0:
                    # Attempt cache
                    dets_cached = None
                    if ENHANCED_MODULES_AVAILABLE and self.dcache is not None:
                        try:
                            dets_cached = self.dcache.get_detection(frame)
                        except Exception:
                            dets_cached = None
                    if dets_cached is not None:
                        dets = dets_cached
                    else:
                        # if extra models exist, use merged detection
                        if getattr(detector, 'available_multi', lambda: False)():
                            dets = getattr(detector, 'detect_multi')(frame)
                        else:
                            dets = getattr(detector, 'detect')(frame)
                        if ENHANCED_MODULES_AVAILABLE and self.dcache is not None:
                            try:
                                self.dcache.cache_detection(frame, dets)
                            except Exception:
                                pass
                    detections = tracker.update(dets)
                else:
                    detections = tracker.update([])
                
                detection_count = len(detections)
            
            inference_time = (time.time() - inference_start) * 1000

            harmful_count = 0
            for (x1, y1, x2, y2, label, conf) in detections:
                labels = [label]
                is_person = label.lower() == 'person'
                roi = None
                vlabels: List[Tuple[str, float]] = []
                recognized_name = None
                recognized_matches = 0

                if self.cfg.use_vision and vision_limiter.allow() and vision.available():
                    roi = crop_roi(frame, (x1, y1, x2, y2))
                    vlabels = vision.label_image(roi)
                    labels.extend([n for n, s in vlabels])

                pose_flags = None
                if self.cfg.use_pose and (is_person or roi is not None) and pose.available():
                    roi_img = roi if roi is not None else frame[max(0, y1):y2, max(0, x1):x2]
                    pose_flags = pose.analyze(roi_img)

                clothing = None
                if is_person:
                    hmid = y1 + (y2 - y1) // 2
                    lower = frame[hmid:y2, x1:x2]
                    clothing = name_color_hsv(lower)

                    # Optional face recognition on person ROI
                    if self.cfg.use_face_auth and self.face_auth is not None:
                        face_roi = frame[max(0, y1):y2, max(0, x1):x2]
                        rec = self.face_auth.recognize(face_roi)
                        if rec:
                            recognized_name, recognized_matches = rec[0], int(rec[1])

                harmful, hazard_tags = evaluate_hazards(label, vlabels, self.cfg.harmful_labels, self.cfg.advanced_detection)
                if harmful:
                    harmful_count += 1

                color = (0, 0, 255) if harmful else (0, 255, 0)
                draw_bbox(frame, (x1, y1, x2, y2), color=color)
                info = f"{label} {conf:.2f}"
                if self.cfg.use_vision and len(labels) > 1:
                    info += f" | {','.join([l for l in labels if l != label])}"
                if pose_flags and pose_flags.raised_hands:
                    info += " | raised_hands"
                if clothing:
                    info += f" | clothing:{clothing}"
                if recognized_name:
                    info += f" | trusted:{recognized_name}"
                draw_label(frame, info, x1, y1, color=color)

                # If a trusted person is recognized, down-weight harmful only for selected labels
                if recognized_name:
                    try:
                        tl = {n.lower() for n in trusted_store.list_trusted()}
                        if recognized_name.lower() in tl:
                            # Suppression list is global or last saved; per-request scoping not available in the detector thread
                            suppress = {l.lower() for l in trusted_store.get_suppress_labels(None)}
                            if label.lower() in suppress:
                                harmful = False
                    except Exception:
                        pass
                # record detail for snapshot
                det_item = {
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                    'label': label,
                    'confidence': float(conf),
                    'harmful': bool(harmful),
                    'hazards': list(hazard_tags) if isinstance(hazard_tags, (list, tuple, set)) else (hazard_tags or []),
                }
                if recognized_name:
                    det_item['trustedName'] = recognized_name
                detection_details.append(det_item)

                if harmful:
                    ts = time.time()
                    ev = {
                        'ts': ts,
                        'box': [int(x1), int(y1), int(x2), int(y2)],
                        'label': label,
                        'allLabels': labels,
                        'confidence': float(conf),
                        'pose': vars(pose_flags) if pose_flags else {},
                        'clothingColor': clothing,
                        'harmful': True,
                        'hazards': hazard_tags,
                    }
                    if recognized_name:
                        ev['trustedName'] = recognized_name
                    if self.event_hook is not None:
                        try:
                            self.event_hook(ev)
                        except Exception:
                            pass
                    self.events.appendleft(ev)
                    if len(self.events) > 200:
                        self.events.pop()
                    logger.log(ev)
                    if ENHANCED_MODULES_AVAILABLE and (alert_manager is not None):
                        try:
                            sev_hi = getattr(AlertSeverity, 'CRITICAL', None)
                            sev_hi2 = getattr(AlertSeverity, 'HIGH', None)
                            t_threat = getattr(AlertType, 'THREAT_DETECTED', None)
                            if sev_hi and sev_hi2 and t_threat:
                                sev = sev_hi if any(h in ('gun','rifle','pistol') for h in [label.lower(), *[l.lower() for l in labels]]) else sev_hi2
                                alert_manager.create_alert(t_threat, sev, f"Harmful object detected: {label}", f"Detected {label} with conf {conf:.2f}", data=ev)
                        except Exception:
                            pass

            # loitering detection based on tracks
            for tid, tr in loiter.check(tracker.get_tracks()):
                bx = tr.get('box', (0, 0, 0, 0))
                x1, y1, x2, y2 = int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])
                draw_label(frame, "LOITERING", x1, y1 - 8, color=(0, 165, 255))
                draw_bbox(frame, (x1, y1, x2, y2), color=(0, 165, 255))
                ev = {
                    'ts': time.time(),
                    'box': [x1, y1, x2, y2],
                    'label': tr.get('label', 'unknown'),
                    'allLabels': [tr.get('label', 'unknown')],
                    'confidence': float(tr.get('conf', 0.0)),
                    'pose': {},
                    'clothingColor': None,
                    'harmful': False,
                    'hazards': ['loitering'],
                }
                self.events.appendleft(ev)
                if len(self.events) > 200:
                    self.events.pop()
                logger.log(ev)
                if ENHANCED_MODULES_AVAILABLE and (alert_manager is not None):
                    try:
                        sev_med = getattr(AlertSeverity, 'MEDIUM', None)
                        t_loit = getattr(AlertType, 'LOITERING', None)
                        if sev_med and t_loit:
                            alert_manager.create_alert(t_loit, sev_med, "Loitering detected", "An individual has been detected loitering.", data=ev)
                    except Exception:
                        pass

            # draw hazard zones and check breaches
            for zx1, zy1, zx2, zy2 in self.cfg.hazard_zones:
                cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (255, 0, 0), 1)
            if self.cfg.hazard_zones:
                zclasses = {c.lower() for c in self.cfg.zone_classes}
                for tid, tr in tracker.get_tracks().items():
                    lbl = str(tr.get('label', '')).lower()
                    if lbl not in zclasses:
                        continue
                    bx = tr.get('box', (0, 0, 0, 0))
                    for zone in self.cfg.hazard_zones:
                        if (bx[0] < zone[2] and bx[2] > zone[0] and bx[1] < zone[3] and bx[3] > zone[1]):
                            ev = {
                                'ts': time.time(),
                                'box': [int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])],
                                'label': tr.get('label', 'unknown'),
                                'allLabels': [tr.get('label', 'unknown')],
                                'confidence': float(tr.get('conf', 0.0)),
                                'pose': {},
                                'clothingColor': None,
                                'harmful': False,
                                'hazards': ['zone-breach'],
                            }
                            self.events.appendleft(ev)
                            if len(self.events) > 200:
                                self.events.pop()
                            logger.log(ev)
                            if ENHANCED_MODULES_AVAILABLE and (alert_manager is not None):
                                try:
                                    sev_med = getattr(AlertSeverity, 'MEDIUM', None)
                                    t_zb = getattr(AlertType, 'ZONE_BREACH', None)
                                    if sev_med and t_zb:
                                        alert_manager.create_alert(t_zb, sev_med, "Zone breach detected", "Object entered restricted zone.", data=ev)
                                except Exception:
                                    pass
                            break

            # Calculate performance metrics
            frame_processing_time = (time.time() - frame_start_time) * 1000
            frame_skip_ratio = frames_skipped / max(1, frame_idx)
            
            # Update FPS calculation
            if time.time() - fps_timer >= 1.0:
                actual_fps = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

            # metrics
            dt = time.time() - t0
            current_fps = round(frame_idx / dt, 1) if dt > 0 else 0.0
            self.metrics['fps'] = current_fps
            self.metrics['harmful_last_frame'] = harmful_count
            self.metrics['last_update'] = int(time.time())
            # capture diagnostics in metrics
            try:
                h, w = frame.shape[:2]
                self.metrics['frame_width'] = int(w)
                self.metrics['frame_height'] = int(h)
            except Exception:
                pass
            self.metrics['capture_backend'] = (self.capture_backend or 'unknown')
            self.metrics['capture_source'] = str(self.cfg.source)
            self.metrics['frames_skipped'] = frames_skipped
            self.metrics['frame_skip_ratio'] = frame_skip_ratio
            self.metrics['read_failures'] = self.read_failures
            if self.last_error:
                self.metrics['last_error'] = self.last_error

            # publish last detections snapshot
            self._last_detections = detection_details

            # Record performance metrics
            if ENHANCED_MODULES_AVAILABLE and self.perf is not None:
                try:
                    self.perf.record_metrics(
                        fps=current_fps,
                        inference_time_ms=inference_time,
                        frame_processing_time_ms=frame_processing_time,
                        detection_count=detection_count,
                        frame_skip_ratio=frame_skip_ratio,
                    )
                except Exception:
                    pass

            with self.frame_lock:
                self.last_frame = frame

    def get_last_detections(self):
        return list(self._last_detections)



    def get_jpeg(self) -> bytes | None:
        with self.frame_lock:
            if self.last_frame is None:
                return None
            ok, jpg = cv2.imencode('.jpg', self.last_frame)
            if not ok:
                return None
            return jpg.tobytes()

    def request_model_reload(self, weights: Optional[str] = None) -> None:
        """Signal the detector thread to reload its model.
        If weights is None, auto-discover latest ONNX/PT via _resolve_weights logic.
        """
        with self.ctrl_lock:
            self.reload_to_weights = weights
            self.reload_requested = True


def create_app(cfg: AppConfig) -> Flask:
    templates_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app = Flask(__name__, template_folder=templates_dir)
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret')
    jobs = JobManager()

    metrics: Dict[str, Any] = {'fps': 0.0, 'frames': 0, 'harmful_last_frame': 0}
    events: Deque[Dict[str, Any]] = deque(maxlen=200)
    def _user_dir(u: str) -> str:
        safe = str(u).strip().lower().replace('/', '_').replace('\\', '_')
        base = os.path.join(cfg.outputs_dir, 'users', safe)
        os.makedirs(base, exist_ok=True)
        return base

    # zones path is per-user; default global path when not logged in
    zones_path = os.path.join(cfg.outputs_dir, 'zones.json')
    zones_lock = threading.Lock()
    os.makedirs(cfg.outputs_dir, exist_ok=True)
    # load zones if present
    try:
        if os.path.exists(zones_path):
            with open(zones_path, 'r', encoding='utf-8') as f:
                z = json.load(f)
                if isinstance(z, list):
                    new_zones: List[Tuple[int, int, int, int]] = []
                    for zz in z:
                        if isinstance(zz, (list, tuple)) and len(zz) == 4:
                            x1, y1, x2, y2 = map(int, zz)
                        elif isinstance(zz, dict):
                            x1 = int(zz.get('x1', 0)); y1 = int(zz.get('y1', 0)); x2 = int(zz.get('x2', 0)); y2 = int(zz.get('y2', 0))
                        else:
                            continue
                        new_zones.append((x1, y1, x2, y2))
                    cfg.hazard_zones.clear()
                    cfg.hazard_zones.extend(new_zones)
    except Exception:
        pass

    # Optional: GCS and Pub/Sub clients for mirroring harmful events
    gcs = GCSUploader(cfg.gcs_bucket)
    pub = PubSubPublisher(cfg.pubsub_topic)

    def _mirror_event(ev: Dict[str, Any]) -> None:
        # Publish harmful events and optionally upload snapshot to GCS
        try:
            if not ev.get('harmful'):
                return
            if pub.available():
                pub.publish_json(ev)
            if cfg.use_gcs_upload and gcs.available():
                jpg = det.get_jpeg() if det is not None else None
                if jpg:
                    ts = int(ev.get('ts', time.time()))
                    label = str(ev.get('label', 'event')).replace(' ', '_')
                    blob = f"events/{ts}_{label}.jpg"
                    uri = gcs.upload_bytes(jpg, blob, content_type='image/jpeg')
                    if uri:
                        ev.setdefault('artifacts', {})['snapshot_gcs'] = uri
        except Exception:
            pass

    # Shared helpers
    face = FaceAuth(cfg.face_db_dir) if cfg.use_face_auth else None

    det: DetectorThread | None = None
    det_lock = threading.Lock()
    def ensure_detector_started():
        nonlocal det
        with det_lock:
            if det is None:
                d = DetectorThread(
                    cfg, metrics, events,
                    event_hook=_mirror_event,
                    face_auth=face,
                    perf=(perf_mon if ENHANCED_MODULES_AVAILABLE else None),
                    dcache=(detection_cache if ENHANCED_MODULES_AVAILABLE else None),
                )
                d.start()
                det = d

    # Gemini client (optional)
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    model = None
    if genai is not None and gemini_api_key:
        try:
            # Lazy import methods to avoid linter complaints when stubs are absent
            getattr(genai, "configure")(api_key=gemini_api_key)
            model = getattr(genai, "GenerativeModel")('gemini-1.5-flash')
        except Exception:
            model = None

    # Auth & tokens (moved early so routes below can reference current_user())
    def _b64url(data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')

    def _b64url_decode(s: str) -> bytes:
        import base64
        pad = '=' * (-len(s) % 4)
        return base64.urlsafe_b64decode(s + pad)

    def _secret_key_bytes() -> bytes:
        sk = app.secret_key or 'dev-secret'
        if isinstance(sk, (bytes, bytearray)):
            return bytes(sk)
        return str(sk).encode('utf-8')

    def sign_token(username: str, ttl_sec: int = 12*3600) -> str:
        import hmac, hashlib, json as _json
        u = username.strip().lower()
        exp = int(time.time()) + ttl_sec
        payload = _b64url(_json.dumps({'u': u, 'exp': exp}).encode('utf-8'))
        sig = hmac.new(_secret_key_bytes(), payload.encode('ascii'), hashlib.sha256).digest()
        return payload + '.' + _b64url(sig)

    def verify_token(token: str) -> Optional[str]:
        import hmac, hashlib, json as _json
        try:
            payload_b64, sig_b64 = token.split('.')
            expected = hmac.new(_secret_key_bytes(), payload_b64.encode('ascii'), hashlib.sha256).digest()
            if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
                return None
            data = _json.loads(_b64url_decode(payload_b64).decode('utf-8'))
            if int(data.get('exp', 0)) < int(time.time()):
                return None
            return str(data.get('u', '')) or None
        except Exception:
            return None

    def current_user() -> Optional[str]:
        # Authorization: Bearer <token> or cookie 'auth'
        authz = request.headers.get('Authorization', '')
        if authz.lower().startswith('bearer '):
            u = verify_token(authz.split(' ', 1)[1].strip())
            if u:
                return u
        tok = request.cookies.get('auth')
        if tok:
            u = verify_token(tok)
            if u:
                return u
        return None

    @app.route('/login')
    def login_page():
        # If already logged in, go home
        if cfg.require_auth and current_user():
            return redirect('/')
        return render_template('login.html')

    @app.route('/')
    def index():
        if cfg.require_auth and not current_user():
            return redirect(url_for('login_page'))
        ensure_detector_started()
        return render_template('index.html')

    @app.route('/stream')
    def stream():
        if cfg.require_auth and not current_user():
            return redirect(url_for('login_page'))
        ensure_detector_started()
        dref = det  # after ensure, det should be non-None
        def gen():
            while True:
                jpg = dref.get_jpeg() if (dref is not None) else None
                if jpg is None:
                    time.sleep(0.05)
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpg + b'\r\n')
                time.sleep(0.03)
        return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.route('/api/metrics')
    def api_metrics():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        u = current_user()
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            cached = api_cache.get_response('/api/metrics', user=u)
            if cached is not None:
                return jsonify(cached)
        data = dict(metrics)
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            api_cache.cache_response('/api/metrics', data, user=u)
        return jsonify(data)

    @app.route('/api/events')
    def api_events():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        u = current_user()
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            cached = api_cache.get_response('/api/events', user=u)
            if cached is not None:
                return jsonify(cached)
        data = list(events)[:50]
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            api_cache.cache_response('/api/events', data, user=u)
        return jsonify(data)

    @app.route('/api/model', methods=['GET'])
    def api_model_info():
        if cfg.require_auth and not current_user():
            return jsonify({'error': 'unauthorized'}), 401
        ensure_detector_started()
        info = {
            'weights': metrics.get('model_weights'),
            'reload_ts': metrics.get('model_reload_ts'),
            'imgsz': cfg.yolo_imgsz,
            'conf': cfg.yolo_conf_thresh,
            'iou': cfg.yolo_iou_thresh,
            'device': cfg.device,
        }
        return jsonify(info)

    @app.route('/api/model/reload', methods=['POST'])
    def api_model_reload():
        if cfg.require_auth and not current_user():
            return jsonify({'error': 'unauthorized'}), 401
        ensure_detector_started()
        payload = request.get_json(silent=True) or {}
        weights = payload.get('weights')
        if weights:
            try:
                if not os.path.exists(str(weights)):
                    return jsonify({'error': 'weights path not found'}), 400
            except Exception:
                return jsonify({'error': 'invalid weights value'}), 400
        dref = det
        if dref is None:
            return jsonify({'error': 'detector not ready'}), 503
        try:
            dref.request_model_reload(weights)
            return jsonify({'status': 'reloading', 'target': weights or 'auto'}), 202
        except Exception as ex:
            return jsonify({'error': str(ex)}), 500

    @app.route('/api/system')
    def api_system():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        u = current_user()
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            cached = api_cache.get_response('/api/system', user=u)
            if cached is not None:
                return jsonify(cached)
        cpu = psutil.cpu_percent(interval=0.0)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        data = {
            'cpu_percent': cpu,
            'mem_total_mb': round(mem.total / (1024*1024), 1),
            'mem_used_mb': round(mem.used / (1024*1024), 1),
            'mem_percent': mem.percent,
            'swap_total_mb': round(swap.total / (1024*1024), 1),
            'swap_used_mb': round(swap.used / (1024*1024), 1),
            'swap_percent': swap.percent,
        }
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            api_cache.cache_response('/api/system', data, user=u)
        return jsonify(data)

    @app.route('/api/detections')
    def api_detections():
        if cfg.require_auth and not current_user():
            return jsonify({'error': 'unauthorized'}), 401
        ensure_detector_started()
        dref = det
        objs = dref.get_last_detections() if dref else []
        # aggregate summary
        by_label: Dict[str, int] = {}
        by_hazard: Dict[str, int] = {}
        harmful = 0
        trusted = set()
        for o in objs:
            lbl = str(o.get('label',''))
            by_label[lbl] = by_label.get(lbl, 0) + 1
            if o.get('harmful'):
                harmful += 1
            for h in o.get('hazards') or []:
                by_hazard[str(h)] = by_hazard.get(str(h), 0) + 1
            tn = o.get('trustedName')
            if tn:
                trusted.add(str(tn))
        out = {
            'timestamp': int(time.time()),
            'objects': objs,
            'summary': {
                'total': len(objs),
                'harmful': harmful,
                'by_label': by_label,
                'by_hazard': by_hazard,
                'trusted_present': sorted(list(trusted)),
            }
        }
        return jsonify(out)

    @app.route('/api/summary')
    def api_summary():
        if cfg.require_auth and not current_user():
            return jsonify({'summary': ''})
        u = current_user()
        if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
            cached = api_cache.get_response('/api/summary', user=u)
            if cached is not None:
                return jsonify(cached)
        if model is None or not events:
            return jsonify({'summary': ''})
        try:
            recent = list(events)[:20]
            text = "\n".join([
                f"{time.strftime('%H:%M:%S', time.localtime(e['ts']))} | harmful={e.get('harmful')} label={e.get('label')} conf={e.get('confidence')} labels={','.join(e.get('allLabels', []))}"
                for e in recent
            ])
            prompt = (
                "Summarize the following security detection events into 2-4 bullet points. "
                "Focus on harmful items and trends.\n\n" + text + "\n"
            )
            resp = model.generate_content(prompt)
            out = resp.text if hasattr(resp, 'text') else ''
            data = {'summary': out}
            if ENHANCED_MODULES_AVAILABLE and api_cache is not None:
                api_cache.cache_response('/api/summary', data, user=u)
            return jsonify(data)
        except Exception:
            return jsonify({'summary': ''})

    @app.route('/api/auth/register', methods=['POST'])
    def api_register():
        body = request.get_json(silent=True) or {}
        u = str(body.get('username', '')).strip().lower()
        p = str(body.get('password', ''))
        if not u or not p:
            return jsonify({'ok': False, 'error': 'missing creds'}), 400
        ok = user_store.register_user(u, p)
        if not ok:
            return jsonify({'ok': False, 'error': 'exists'}), 400
        token = sign_token(u)
        resp = make_response(jsonify({'ok': True, 'username': u, 'token': token}))
        resp.set_cookie('auth', token, httponly=True, samesite='Lax')
        return resp

    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        body = request.get_json(silent=True) or {}
        u = str(body.get('username', '')).strip().lower()
        p = str(body.get('password', ''))
        if not u or not p:
            return jsonify({'ok': False, 'error': 'missing creds'}), 400
        if user_store.authenticate(u, p):
            token = sign_token(u)
            resp = make_response(jsonify({'ok': True, 'username': u, 'token': token}))
            resp.set_cookie('auth', token, httponly=True, samesite='Lax')
            return resp
        return jsonify({'ok': False, 'error': 'invalid creds'}), 401

    @app.route('/api/auth/state')
    def api_auth_state():
        return jsonify({'username': current_user()})

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        resp = make_response(jsonify({'ok': True}))
        resp.delete_cookie('auth')
        return resp

    # Onboarding APIs
    def _onboard_get(u: str) -> Dict[str, Any]:
        prof = user_store.load_profile(u)
        ob = prof.get('onboarding') if isinstance(prof, dict) else None
        if not isinstance(ob, dict):
            ob = {'steps': {'face_intent': 'unknown', 'face_enrolled': False}, 'done': False}
        return ob

    def _onboard_save(u: str, ob: Dict[str, Any]) -> None:
        prof = user_store.load_profile(u)
        if not isinstance(prof, dict):
            prof = {}
        prof['onboarding'] = ob
        user_store.save_profile(u, prof)

    @app.route('/api/onboarding/state')
    def api_onboarding_state():
        u = current_user()
        if not u:
            return jsonify({'done': False, 'steps': {'face_intent': 'unknown', 'face_enrolled': False}})
        return jsonify(_onboard_get(u))

    @app.route('/api/onboarding/face/intent', methods=['POST'])
    def api_onboarding_face_intent():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        body = request.get_json(silent=True) or {}
        choice = str(body.get('choice','unknown')).strip().lower()
        if choice not in ('enroll','later','declined'):
            return jsonify({'ok': False, 'error': 'invalid choice'}), 400
        ob = _onboard_get(u)
        ob['steps']['face_intent'] = choice
        # If declined, mark done right away
        if choice in ('later','declined'):
            ob['done'] = True
        _onboard_save(u, ob)
        return jsonify({'ok': True, 'state': ob})

    @app.route('/api/onboarding/face/enroll-upload', methods=['POST'])
    def api_onboarding_face_enroll_upload():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        if not face:
            return jsonify({'ok': False, 'error': 'face auth disabled'}), 400
        file = request.files.get('file')
        if not file:
            return jsonify({'ok': False, 'error': 'file required'}), 400
        img_array = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'ok': False, 'error': 'decode failed'}), 400
        ok = face.enroll(u, img)
        ob = _onboard_get(u)
        if ok:
            ob['steps']['face_enrolled'] = True
        _onboard_save(u, ob)
        return jsonify({'ok': ok, 'state': ob})

    @app.route('/api/onboarding/face/enroll-from-frame', methods=['POST'])
    def api_onboarding_face_enroll_from_frame():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        if not face:
            return jsonify({'ok': False, 'error': 'face auth disabled'}), 400
        ensure_detector_started()
        jpg = det.get_jpeg() if det else None
        if not jpg:
            return jsonify({'ok': False, 'error': 'no frame'}), 400
        img_array = np.frombuffer(jpg, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'ok': False, 'error': 'decode failed'}), 400
        ok = face.enroll(u, img)
        ob = _onboard_get(u)
        if ok:
            ob['steps']['face_enrolled'] = True
        _onboard_save(u, ob)
        return jsonify({'ok': ok, 'state': ob})

    @app.route('/api/onboarding/complete', methods=['POST'])
    def api_onboarding_complete():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        ob = _onboard_get(u)
        ob['done'] = True
        _onboard_save(u, ob)
        return jsonify({'ok': True, 'state': ob})

    @app.route('/api/profile', methods=['GET'])
    def api_profile():
        u = current_user()
        if not u:
            return jsonify({'profile': None})
        return jsonify({'profile': user_store.load_profile(u)})

    @app.route('/api/profile/suggest', methods=['POST'])
    def api_profile_suggest():
        body = request.get_json(silent=True) or {}
        purpose = str(body.get('purpose', '')).strip() or 'home security'
        # Use Gemini to produce a suggested config specific to the user's purpose
        if model is not None:
            try:
                prompt = (
                    "Design a JSON config for a personalized security detection environment optimized for '"
                    + purpose +
                    "'. Include: frameskip, yolo_imgsz, track_interval, harmful_labels (list), zone_classes (list), loiter_seconds_threshold, advanced_detection (bool). Keep values practical for a low-resource laptop. Return JSON only."
                )
                resp = model.generate_content(prompt)
                txt = resp.text if hasattr(resp, 'text') else '{}'
                import json as _json
                cfg = _json.loads(txt)
                return jsonify({'purpose': purpose, 'config': cfg})
            except Exception:
                pass
        # Fallback template
        fallback = {
            'frameskip': 2,
            'yolo_imgsz': 480,
            'track_interval': 6,
            'harmful_labels': ['knife','gun','rifle','pistol'],
            'zone_classes': ['person'],
            'loiter_seconds_threshold': 30,
            'advanced_detection': True
        }
        return jsonify({'purpose': purpose, 'config': fallback})

    @app.route('/api/profile/train', methods=['POST'])
    def api_profile_train():
        u = current_user()
        if not u:
            return jsonify({'ok': False, 'error': 'not logged in'}), 401
        # Simulate training/personalization & federated learning coordination
        # In practice: send anonymized gradients to a coordinator; here we just mark personalized
        prof = user_store.load_profile(u)
        prof['personalized'] = True
        # Apply env suggestion if present in the dashboard textarea
        body = request.get_json(silent=True) or {}
        if ('purpose' not in prof or not prof.get('purpose')) and isinstance(body.get('purpose'), str):
            prof['purpose'] = body.get('purpose')
        # Persist suggested config if provided
        if isinstance(body.get('config'), dict):
            prof['config'] = body['config']
        user_store.save_profile(u, prof)
        # Optionally apply the profile to the running detector config
        applied = False
        try:
            cfg_blob = prof.get('config') if isinstance(prof, dict) else None
            if isinstance(cfg_blob, dict):
                cfg.frameskip = int(cfg_blob.get('frameskip', cfg.frameskip))
                cfg.yolo_imgsz = int(cfg_blob.get('yolo_imgsz', cfg.yolo_imgsz))
                cfg.track_interval = int(cfg_blob.get('track_interval', cfg.track_interval))
                if isinstance(cfg_blob.get('harmful_labels'), list):
                    cfg.harmful_labels = set(map(str.lower, cfg_blob['harmful_labels']))
                if isinstance(cfg_blob.get('zone_classes'), list):
                    cfg.zone_classes = list(map(str, cfg_blob['zone_classes']))
                if 'loiter_seconds_threshold' in cfg_blob:
                    cfg.loiter_seconds_threshold = float(cfg_blob['loiter_seconds_threshold'])
                if 'advanced_detection' in cfg_blob:
                    cfg.advanced_detection = bool(cfg_blob['advanced_detection'])
                applied = True
        except Exception:
            applied = False
        # Submit federated update (stub)
        try:
            federated.submit_update(u, prof)
            federated.aggregate()
        except Exception:
            pass
        return jsonify({'ok': True, 'applied': applied})

    # Training job APIs
    @app.route('/api/train/jobs', methods=['GET', 'POST'])
    def api_train_jobs():
        u = current_user()
        if not u:
            return jsonify({'error': 'not logged in'}), 401
        if request.method == 'GET':
            return jsonify({'jobs': jobs.list_for_user(u)})
        body = request.get_json(silent=True) or {}
        purpose = str(body.get('purpose', '')).strip() or None
        cfg_blob = body.get('config', None)
        if cfg_blob is not None and not isinstance(cfg_blob, dict):
            return jsonify({'error': 'config must be object'}), 400
        job = jobs.submit(u, purpose, cfg_blob)
        return jsonify(job), 201

    @app.route('/api/train/jobs/<job_id>', methods=['GET'])
    def api_train_job_get(job_id: str):
        u = current_user()
        if not u:
            return jsonify({'error': 'not logged in'}), 401
        j = jobs.get(u, job_id)
        if not j:
            return jsonify({'error': 'not found'}), 404
        return jsonify(j)

    @app.route('/api/train/jobs/<job_id>/cancel', methods=['POST'])
    def api_train_job_cancel(job_id: str):
        u = current_user()
        if not u:
            return jsonify({'error': 'not logged in'}), 401
        ok = jobs.cancel(u, job_id)
        return jsonify({'ok': ok})

    # Environments API
    @app.route('/api/envs', methods=['GET', 'POST', 'DELETE'])
    def api_envs():
        u = current_user()
        if cfg.require_auth and not u:
            return jsonify({'error': 'not logged in'}), 401
        if request.method == 'GET':
            return jsonify({'active': envmgr.get_active(u), 'items': envmgr.list_envs(u)})
        if request.method == 'POST':
            body = request.get_json(silent=True) or {}
            name = str(body.get('name', '')).strip()
            cfg_blob = body.get('config', {})
            if not name:
                return jsonify({'error': 'name required'}), 400
            envmgr.create_env(name, cfg_blob, u)
            return jsonify({'ok': True}), 201
        # DELETE with ?name=
        name = request.args.get('name', '')
        if not name:
            return jsonify({'error': 'name required'}), 400
        ok = envmgr.delete_env(name, u)
        return jsonify({'ok': ok})

    @app.route('/api/envs/select', methods=['POST'])
    def api_envs_select():
        u = current_user()
        body = request.get_json(silent=True) or {}
        name = str(body.get('name', '')).strip()
        if not name:
            return jsonify({'error': 'name required'}), 400
        ok = envmgr.set_active(name, u)
        return jsonify({'ok': ok})

    @app.route('/api/envs/suggest', methods=['POST'])
    def api_envs_suggest():
        body = request.get_json(silent=True) or {}
        use_case = str(body.get('use_case', '')).strip()
        if not use_case:
            return jsonify({'error': 'use_case required'}), 400
        # If Gemini available, ask for a suggested config; else return a heuristic template
        if model is not None:
            try:
                prompt = f"Design a JSON config for a security detection environment optimized for '{use_case}'. Include fields: frameskip, yolo_imgsz, track_interval, harmful_labels (list), zone_classes (list), loiter_seconds_threshold, advanced_detection (bool). Keep it concise. Return JSON only."
                resp = model.generate_content(prompt)
                txt = resp.text if hasattr(resp, 'text') else '{}'
                import json as _json
                cfg = _json.loads(txt)
                return jsonify({'use_case': use_case, 'config': cfg})
            except Exception:
                pass
        # Fallback templates
        templates = {
            'home security': {
                'frameskip': 2, 'yolo_imgsz': 480, 'track_interval': 6,
                'harmful_labels': ['knife','gun','rifle','pistol'],
                'zone_classes': ['person'], 'loiter_seconds_threshold': 30,
                'advanced_detection': True
            },
            'child security': {
                'frameskip': 1, 'yolo_imgsz': 640, 'track_interval': 4,
                'harmful_labels': ['knife','gun'],
                'zone_classes': ['person'], 'loiter_seconds_threshold': 10,
                'advanced_detection': True
            }
        }
        key = use_case.lower()
        cfg = templates.get(key, templates['home security'])
        return jsonify({'use_case': use_case, 'config': cfg})

    # Face auth API
    @app.route('/api/face/users', methods=['GET'])
    def api_face_users():
        if cfg.require_auth and not current_user():
            return jsonify({'enabled': False, 'users': []}), 401
        if not face:
            return jsonify({'enabled': False, 'users': []})
        return jsonify({'enabled': True, 'users': face.list_users()})

    @app.route('/api/face/users/<name>', methods=['DELETE'])
    def api_face_delete(name: str):
        if cfg.require_auth and not current_user():
            return jsonify({'enabled': False, 'ok': False}), 401
        if not face:
            return jsonify({'enabled': False, 'ok': False})
        ok = face.delete_user(name)
        return jsonify({'ok': ok})

    @app.route('/api/face/enroll/<name>', methods=['POST'])
    def api_face_enroll(name: str):
        if cfg.require_auth and not current_user():
            return jsonify({'enabled': False, 'ok': False}), 401
        if not face:
            return jsonify({'enabled': False, 'ok': False}), 400
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'file required'}), 400
        file_bytes = file.read()
        img_array = np.frombuffer(file_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'invalid image'}), 400
        ok = face.enroll(name, img)
        return jsonify({'ok': ok})

    @app.route('/api/face/enroll-from-frame/<name>', methods=['POST'])
    def api_face_enroll_from_frame(name: str):
        if cfg.require_auth and not current_user():
            return jsonify({'enabled': False, 'ok': False}), 401
        if not face:
            return jsonify({'enabled': False, 'ok': False}), 400
        ensure_detector_started()
        jpg = det.get_jpeg() if det else None
        if not jpg:
            return jsonify({'error': 'no frame'}), 400
        img_array = np.frombuffer(jpg, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({'error': 'decode failed'}), 400
        ok = face.enroll(name, img)
        return jsonify({'ok': ok})

    @app.route('/api/face/trusted', methods=['GET', 'POST', 'DELETE'])
    def api_face_trusted():
        u = current_user()
        if cfg.require_auth and not u:
            return jsonify({'error': 'not logged in'}), 401
        if request.method == 'GET':
            return jsonify({'items': trusted_store.list_trusted(u), 'suppress_labels': trusted_store.get_suppress_labels(u)})
        body = request.get_json(silent=True) or {}
        person = str(body.get('name', '')).strip()
        if not person:
            return jsonify({'error': 'name required'}), 400
        if request.method == 'POST':
            try:
                trusted_store.add_trusted(person, u)
            except Exception:
                pass
            return jsonify({'ok': True, 'items': trusted_store.list_trusted(u)})
        # DELETE
        try:
            trusted_store.remove_trusted(person, u)
        except Exception:
            pass
        return jsonify({'ok': True, 'items': trusted_store.list_trusted(u)})

    @app.route('/api/face/trusted/suppress-labels', methods=['GET', 'POST'])
    def api_face_trusted_labels():
        u = current_user()
        if cfg.require_auth and not u:
            return jsonify({'error': 'not logged in'}), 401
        if request.method == 'GET':
            return jsonify({'suppress_labels': trusted_store.get_suppress_labels(u)})
        body = request.get_json(silent=True) or {}
        labels = body.get('labels', [])
        if not isinstance(labels, list):
            return jsonify({'error': 'labels must be a list'}), 400
        labels = [str(x).lower() for x in labels]
        try:
            trusted_store.set_suppress_labels(labels, u)
        except Exception:
            pass
        return jsonify({'ok': True, 'suppress_labels': trusted_store.get_suppress_labels(u)})

    

    @app.route('/api/zones', methods=['GET', 'POST', 'DELETE'])
    def api_zones():
        u = current_user()
        if cfg.require_auth and not u:
            return jsonify({'error': 'not logged in'}), 401
        def persist():
            try:
                zp = zones_path
                if u:
                    zp = os.path.join(_user_dir(u), 'zones.json')
                with open(zp, 'w', encoding='utf-8') as f:
                    json.dump([
                        {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
                        for (x1, y1, x2, y2) in cfg.hazard_zones
                    ], f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        if request.method == 'GET':
            # Load per-user zones onto cfg.hazard_zones to render consistent view
            try:
                zp = zones_path
                if u:
                    zp = os.path.join(_user_dir(u), 'zones.json')
                if os.path.exists(zp):
                    with open(zp, 'r', encoding='utf-8') as f:
                        z = json.load(f)
                        new_z: List[Tuple[int, int, int, int]] = []
                        for zz in z:
                            x1 = int(zz.get('x1')); y1 = int(zz.get('y1')); x2 = int(zz.get('x2')); y2 = int(zz.get('y2'))
                            new_z.append((x1, y1, x2, y2))
                        with zones_lock:
                            cfg.hazard_zones.clear()
                            cfg.hazard_zones.extend(new_z)
            except Exception:
                pass
            return jsonify({
                'zones': [
                    {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}
                    for (x1, y1, x2, y2) in cfg.hazard_zones
                ],
                'classes': list(cfg.zone_classes),
            })

        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            try:
                def get_int(field: str) -> int:
                    v = data.get(field, None)
                    if v is None:
                        raise ValueError(f"Missing {field}")
                    return int(v)
                x1 = get_int('x1')
                y1 = get_int('y1')
                x2 = get_int('x2')
                y2 = get_int('y2')
            except (TypeError, ValueError):
                return jsonify({'error': 'x1,y1,x2,y2 must be integers'}), 400
            # Normalize order
            if x1 > x2:
                x1, x2 = x2, x1
            if y1 > y2:
                y1, y2 = y2, y1
            with zones_lock:
                cfg.hazard_zones.append((x1, y1, x2, y2))
                persist()
            return jsonify({'ok': True}), 201

        # DELETE
        with zones_lock:
            cfg.hazard_zones.clear()
            persist()
        return jsonify({'ok': True})

    # Performance monitoring endpoints
    @app.route('/api/performance')
    def api_performance():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE or perf_mon is None:
            return jsonify({'error': 'performance module not available'}), 503
        return jsonify(perf_mon.get_performance_summary())

    @app.route('/api/cache-stats')
    def api_cache_stats():
        if cfg.require_auth and not current_user():
            return jsonify({'error':'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE:
            return jsonify({'error': 'cache module not available'}), 503
        return jsonify(get_cache_stats())

    # Alert system endpoints
    @app.route('/api/alerts')
    def api_alerts():
        if cfg.require_auth and not current_user():
            return jsonify({'error': 'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE or alert_manager is None:
            return jsonify({'alerts': []})
        limit = int(request.args.get('limit', '100'))
        unack = request.args.get('unack', '0') == '1'
        # Keep it simple to avoid enum typing issues
        assert alert_manager is not None
        items = alert_manager.get_alerts(limit=limit, unacknowledged_only=unack)
        stats = alert_manager.get_alert_stats()
        return jsonify({'alerts': items, 'stats': stats})

    @app.route('/api/alerts/test', methods=['POST'])
    def api_test_alert():
        u = current_user()
        if not u:
            return jsonify({'error': 'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE or alert_manager is None:
            return jsonify({'ok': False, 'error': 'alert module not available'}), 503
        results = alert_manager.test_notifications()
        return jsonify({'ok': True, 'results': results})

    @app.route('/api/alerts/acknowledge', methods=['POST'])
    def api_acknowledge_alert():
        u = current_user()
        if not u:
            return jsonify({'error': 'unauthorized'}), 401
        if not ENHANCED_MODULES_AVAILABLE or alert_manager is None:
            return jsonify({'ok': False, 'error': 'alert module not available'}), 503
        body = request.get_json(silent=True) or {}
        alert_id = body.get('alert_id')
        if not alert_id:
            return jsonify({'error': 'alert_id required'}), 400
        try:
            assert alert_manager is not None
            ok = alert_manager.acknowledge_alert(str(alert_id), acknowledged_by=u)
        except Exception:
            ok = False
        return jsonify({'ok': ok, 'acknowledged': alert_id})

    # Mobile webapp endpoints (placeholder for future enhancement)
    @app.route('/manifest.json')
    def app_manifest():
        manifest = {
            "name": "Guardia-AI",
            "short_name": "Guardia",
            "description": "Real-time AI security monitoring system",
            "start_url": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "theme_color": "#1f2937",
            "background_color": "#0b0f14",
            "icons": [
                {
                    "src": "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTkyIiBoZWlnaHQ9IjE5MiIgdmlld0JveD0iMCAwIDE5MiAxOTIiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIxOTIiIGhlaWdodD0iMTkyIiBmaWxsPSIjMWYyOTM3Ii8+Cjx0ZXh0IHg9Ijk2IiB5PSIxMDAiIGZvcnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSI2MCIgZmlsbD0iI2VhZWNlZiIgdGV4dC1hbmNob3I9Im1pZGRsZSI+8J+boe+4jzwvdGV4dD4KPC9zdmc+",
                    "sizes": "192x192",
                    "type": "image/svg+xml",
                    "purpose": "any maskable"
                }
            ]
        }
        return jsonify(manifest)

    @app.route('/sw.js')
    def service_worker():
        sw_content = '''
// Basic service worker for Guardia-AI
const CACHE_NAME = 'guardia-ai-v1';
const urlsToCache = [
    '/',
    '/api/events',
    '/api/metrics',
    '/api/system'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => response || fetch(event.request))
    );
});
'''
        return Response(sw_content, mimetype='application/javascript')

    return app


if __name__ == '__main__':
    # basic CLI passthrough for source
    cfg = AppConfig()
    cfg.ensure_dirs()
    app = create_app(cfg)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=False, threaded=True)
