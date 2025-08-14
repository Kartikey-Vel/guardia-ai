from __future__ import annotations
from typing import List, Tuple, Dict, Any, Optional
import os
import json
import time

import cv2
import numpy as np


class FaceAuth:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        # Use OpenCV's built-in cascades
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.detector = cv2.CascadeClassifier(cascade_path)
        self.orb = cv2.ORB_create(nfeatures=500)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.index_path = os.path.join(self.base_dir, 'faces_index.json')
        self.index: Dict[str, List[str]] = {}
        self._load_index()

    def _load_index(self) -> None:
        try:
            if os.path.exists(self.index_path):
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    self.index = json.load(f)
        except Exception:
            self.index = {}

    def _save_index(self) -> None:
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _user_dir(self, name: str) -> str:
        d = os.path.join(self.base_dir, name)
        os.makedirs(d, exist_ok=True)
        return d

    def list_users(self) -> List[str]:
        return sorted(list(self.index.keys()))

    def delete_user(self, name: str) -> bool:
        user_path = self._user_dir(name)
        ok = False
        try:
            if name in self.index:
                del self.index[name]
                self._save_index()
                ok = True
            if os.path.isdir(user_path):
                for f in os.listdir(user_path):
                    try:
                        os.remove(os.path.join(user_path, f))
                    except Exception:
                        pass
                try:
                    os.rmdir(user_path)
                except Exception:
                    pass
        except Exception:
            pass
        return ok

    def _detect_face(self, gray: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(40, 40))
        if len(faces) == 0:
            return None
        # pick largest
        x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
        return (x, y, x + w, y + h)

    def _compute_desc(self, img: np.ndarray) -> Optional[np.ndarray]:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_rect = self._detect_face(gray)
        if not face_rect:
            return None
        x1, y1, x2, y2 = face_rect
        roi = gray[max(0, y1):y2, max(0, x1):x2]
        if roi.size == 0:
            return None
        kps, des = self.orb.detectAndCompute(roi, None)
        if des is None or len(des) == 0:
            return None
        return des

    def enroll(self, name: str, img: np.ndarray) -> bool:
        des = self._compute_desc(img)
        if des is None:
            return False
        user_dir = self._user_dir(name)
        ts = int(time.time())
        np.save(os.path.join(user_dir, f"{ts}.npy"), des)
        self.index.setdefault(name, [])
        self.index[name] = sorted(list(set(self.index[name] + [f"{ts}.npy"])) )
        self._save_index()
        return True

    def recognize(self, img: np.ndarray, min_matches: int = 25) -> Optional[Tuple[str, int]]:
        query = self._compute_desc(img)
        if query is None:
            return None
        best_name = None
        best_matches = 0
        for name, files in self.index.items():
            total = 0
            for f in files:
                try:
                    des = np.load(os.path.join(self._user_dir(name), f))
                    matches = self.bf.match(query, des)
                    total += len(matches)
                except Exception:
                    continue
            if total > best_matches:
                best_name = name
                best_matches = total
        if best_name and best_matches >= min_matches:
            return best_name, best_matches
        return None
