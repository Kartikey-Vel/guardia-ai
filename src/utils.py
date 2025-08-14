from __future__ import annotations
import os
import time
import json
from dataclasses import asdict
from typing import List, Tuple, Dict, Any, Optional, Set

import cv2
import numpy as np


class FPSLimiter:
    def __init__(self, max_fps: float):
        self.period = 1.0 / max(1e-6, max_fps)
        self.last_ts = 0.0

    def allow(self) -> bool:
        now = time.time()
        if now - self.last_ts >= self.period:
            self.last_ts = now
            return True
        return False


def draw_label(img: np.ndarray, text: str, x: int, y: int, color=(0, 255, 0)) -> None:
    cv2.putText(img, text, (x, max(0, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)


def draw_bbox(img: np.ndarray, box: Tuple[int, int, int, int], color=(0, 255, 0), thickness=2) -> None:
    x1, y1, x2, y2 = box
    cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)


def crop_roi(frame: np.ndarray, box: Tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = box
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)
    return frame[y1:y2, x1:x2].copy()


def save_image(path: str, image: np.ndarray) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cv2.imwrite(path, image)


def name_color_hsv(bgr: np.ndarray) -> str:
    """Very rough color naming for demo purposes."""
    if bgr.size == 0:
        return "unknown"
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    h_mean = float(np.mean(np.asarray(h, dtype=np.float32)))
    s_mean = float(np.mean(np.asarray(s, dtype=np.float32)))
    v_mean = float(np.mean(np.asarray(v, dtype=np.float32)))
    if v_mean < 50:
        return "black"
    if s_mean < 30:
        return "white" if v_mean > 200 else "gray"
    # Hue-based
    if h_mean < 10 or h_mean >= 170:
        return "red"
    if 10 <= h_mean < 25:
        return "orange"
    if 25 <= h_mean < 35:
        return "yellow"
    if 35 <= h_mean < 85:
        return "green"
    if 85 <= h_mean < 125:
        return "blue"
    if 125 <= h_mean < 170:
        return "purple"
    return "unknown"


class EventLogger:
    def __init__(self, dirpath: str):
        self.dir = dirpath
        os.makedirs(self.dir, exist_ok=True)
        self.jsonl_path = os.path.join(self.dir, "events.jsonl")

    def log(self, event: Dict[str, Any]) -> None:
        with open(self.jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def motion_changed(prev_gray: np.ndarray | None, frame: np.ndarray, thresh: int = 20, min_area: int = 1500) -> tuple[bool, np.ndarray]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    if prev_gray is None:
        return True, gray
    frame_delta = cv2.absdiff(prev_gray, gray)
    _, thresh_img = cv2.threshold(frame_delta, thresh, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    thresh_img = cv2.dilate(thresh_img, kernel, iterations=2)
    contours, _ = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        if cv2.contourArea(c) >= min_area:
            return True, gray
    return False, gray


class SimpleTracker:
    """Very light IoU-based tracker to carry boxes across frames.
    Not for precise tracking; just reduces detector calls between intervals."""
    def __init__(self, iou_thresh: float = 0.3, ttl: int = 5):
        self.iou_thresh = iou_thresh
        self.ttl = ttl
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1

    @staticmethod
    def iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = a
        bx1, by1, bx2, by2 = b
        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        inter = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = area_a + area_b - inter + 1e-6
        return inter / union

    def update(self, dets: List[Tuple[int, int, int, int, str, float]]) -> List[Tuple[int, int, int, int, str, float]]:
        # match existing tracks by IoU
        used = set()
        for tid, t in list(self.tracks.items()):
            t['ttl'] -= 1
            if t['ttl'] <= 0:
                self.tracks.pop(tid, None)

        for d in dets:
            best_id = None
            best_iou = 0.0
            for tid, t in self.tracks.items():
                if tid in used:
                    continue
                iou = self.iou((d[0], d[1], d[2], d[3]), t['box'])
                if iou > best_iou:
                    best_iou = iou
                    best_id = tid
            if best_iou >= self.iou_thresh and best_id is not None:
                # update existing track with centroid and time history
                x1, y1, x2, y2 = d[0], d[1], d[2], d[3]
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                tr = self.tracks[best_id]
                tr['box'] = (x1, y1, x2, y2)
                tr['label'] = d[4]
                tr['conf'] = d[5]
                tr['ttl'] = self.ttl
                tr['last_seen'] = time.time()
                hist = tr.setdefault('history', [])
                hist.append((cx, cy, tr['last_seen']))
                if len(hist) > 60:
                    del hist[0:len(hist)-60]
                tr['centroid'] = (cx, cy)
                used.add(best_id)
            else:
                tid = self._next_id
                self._next_id += 1
                x1, y1, x2, y2 = d[0], d[1], d[2], d[3]
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                now = time.time()
                self.tracks[tid] = {
                    'box': (x1, y1, x2, y2),
                    'label': d[4],
                    'conf': d[5],
                    'ttl': self.ttl,
                    'first_seen': now,
                    'last_seen': now,
                    'centroid': (cx, cy),
                    'history': [(cx, cy, now)],
                }
                used.add(tid)

        # return active tracks as det-like tuples
        out: List[Tuple[int, int, int, int, str, float]] = []
        for tid, t in self.tracks.items():
            x1, y1, x2, y2 = t['box']
            out.append((x1, y1, x2, y2, t['label'], float(t['conf'])))
        return out

    def get_tracks(self) -> Dict[int, Dict[str, Any]]:
        return self.tracks


def rect_intersects(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)


def evaluate_hazards(yolo_label: str, vision_labels: List[Tuple[str, float]],
                     harmful_set: Set[str], advanced_enable: bool = True) -> Tuple[bool, List[str]]:
    """Return (harmful, hazard_tags) based on YOLO label and Vision labels.
    Hazard tags include: 'weapon', 'fire', 'smoke'.
    If advanced_enable, prefer Vision for 'gun/weapon' (YOLO often lacks 'gun').
    """
    hazards: List[str] = []
    ll = yolo_label.lower()
    weapon_syn = {"gun", "pistol", "rifle", "revolver", "weapon", "knife", "sword"}
    fire_syn = {"fire", "flame", "blaze"}
    smoke_syn = {"smoke", "smoky", "smoking"}

    # From YOLO
    if ll in harmful_set or ll in weapon_syn:
        hazards.append('weapon')

    # From Vision
    vnames = {n.lower() for n, s in vision_labels}
    if advanced_enable:
        if vnames & weapon_syn:
            if 'weapon' not in hazards:
                hazards.append('weapon')
    if vnames & fire_syn:
        hazards.append('fire')
    if vnames & smoke_syn:
        hazards.append('smoke')

    harmful = any(h in ('weapon',) for h in hazards)
    return harmful, hazards


class LoiteringMonitor:
    """Detect loitering when tracked objects stay nearly stationary beyond a time threshold."""
    def __init__(self, seconds_threshold: float = 20.0, radius_px: int = 40, classes: Optional[Set[str]] = None):
        self.seconds_threshold = seconds_threshold
        self.radius_px = radius_px
        self.classes = {c.lower() for c in (classes or {"person"})}
        self._reported: Dict[int, float] = {}

    @staticmethod
    def _max_spread(history: List[Tuple[int, int, float]]) -> float:
        if len(history) < 2:
            return 0.0
        xs = [p[0] for p in history]
        ys = [p[1] for p in history]
        return float(max(max(xs) - min(xs), max(ys) - min(ys)))

    def check(self, tracks: Dict[int, Dict[str, Any]]) -> List[Tuple[int, Dict[str, Any]]]:
        now = time.time()
        events: List[Tuple[int, Dict[str, Any]]] = []
        for tid, tr in tracks.items():
            label = str(tr.get('label', '')).lower()
            if label not in self.classes:
                continue
            first_seen = tr.get('first_seen', now)
            dur = now - first_seen
            hist = tr.get('history', [])
            if dur >= self.seconds_threshold and self._max_spread(hist) <= self.radius_px:
                last_report = self._reported.get(tid, 0.0)
                if now - last_report >= 10.0:
                    self._reported[tid] = now
                    events.append((tid, tr))
        for tid in list(self._reported.keys()):
            if tid not in tracks:
                self._reported.pop(tid, None)
        return events
