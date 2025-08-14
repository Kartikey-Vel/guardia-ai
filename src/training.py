from __future__ import annotations
from typing import Dict, Any, List, Optional
import os
import json
import time
import threading
import uuid

from . import federated
from . import user_store


JOBS_DIR = os.path.abspath(os.path.join(os.getenv("GUARDIA_OUTPUTS_DIR", "outputs"), "jobs"))
JOBS_FILE = os.path.join(JOBS_DIR, "jobs.json")


def _ensure_jobs_dir() -> None:
    os.makedirs(JOBS_DIR, exist_ok=True)


def _load_jobs() -> List[Dict[str, Any]]:
    _ensure_jobs_dir()
    if not os.path.exists(JOBS_FILE):
        return []
    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_jobs(jobs: List[Dict[str, Any]]) -> None:
    _ensure_jobs_dir()
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


class JobManager:
    """A simple in-process job orchestrator simulating remote VM training.

    - Persists jobs to outputs/jobs/jobs.json
    - Background thread picks queued jobs and simulates training
    - On completion, updates the user's profile and submits a federated update
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: List[Dict[str, Any]] = _load_jobs()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def list_for_user(self, user: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [j for j in self._jobs if j.get("user") == user]

    def get(self, user: str, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for j in self._jobs:
                if j.get("id") == job_id and j.get("user") == user:
                    return dict(j)
            return None

    def submit(self, user: str, purpose: Optional[str], cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        job = {
            "id": uuid.uuid4().hex[:12],
            "user": user,
            "purpose": purpose,
            "input_config": cfg or {},
            "status": "queued",
            "created_ts": int(time.time()),
            "updated_ts": int(time.time()),
        }
        with self._lock:
            self._jobs.append(job)
            _save_jobs(self._jobs)
        return dict(job)

    def cancel(self, user: str, job_id: str) -> bool:
        with self._lock:
            for j in self._jobs:
                if j.get("id") == job_id and j.get("user") == user:
                    if j.get("status") in ("queued", "running"):
                        j["status"] = "canceled"
                        j["updated_ts"] = int(time.time())
                        _save_jobs(self._jobs)
                        return True
        return False

    def _run(self) -> None:
        while not self._stop.is_set():
            job: Optional[Dict[str, Any]] = None
            with self._lock:
                for j in self._jobs:
                    if j.get("status") == "queued":
                        job = j
                        break
                if job:
                    job["status"] = "running"
                    job["updated_ts"] = int(time.time())
                    _save_jobs(self._jobs)
            if not job:
                time.sleep(0.5)
                continue

            try:
                # Check cancel before starting heavy work
                with self._lock:
                    if job.get("status") == "canceled":
                        continue
                # Simulate compute time
                for _ in range(6):
                    time.sleep(0.5)
                    with self._lock:
                        if job.get("status") == "canceled":
                            break
                with self._lock:
                    if job.get("status") == "canceled":
                        _save_jobs(self._jobs)
                        continue

                # Produce tuned config
                base_cfg = job.get("input_config") or {}
                tuned = dict(base_cfg)
                try:
                    imgsz = int(tuned.get("yolo_imgsz", 480))
                    if imgsz < 640:
                        tuned["yolo_imgsz"] = 640
                except Exception:
                    tuned["yolo_imgsz"] = 640
                try:
                    fs = int(tuned.get("frameskip", 2))
                    tuned["frameskip"] = max(1, fs)
                except Exception:
                    tuned["frameskip"] = 2
                try:
                    ti = int(tuned.get("track_interval", 6))
                    tuned["track_interval"] = max(4, ti)
                except Exception:
                    tuned["track_interval"] = 6

                result = {"config": tuned, "metrics": {"training_time_s": 3}}

                # Update user's profile
                user = str(job.get("user"))
                prof = user_store.load_profile(user)
                prof["purpose"] = job.get("purpose") or prof.get("purpose") or ""
                prof["config"] = tuned
                prof["personalized"] = True
                user_store.save_profile(user, prof)

                # Federated update
                try:
                    federated.submit_update(user, prof)
                    federated.aggregate()
                except Exception:
                    pass

                with self._lock:
                    job["result"] = result
                    job["status"] = "done"
                    job["updated_ts"] = int(time.time())
                    _save_jobs(self._jobs)
            except Exception as ex:
                with self._lock:
                    job["status"] = "failed"
                    job["error"] = str(ex)
                    job["updated_ts"] = int(time.time())
                    _save_jobs(self._jobs)