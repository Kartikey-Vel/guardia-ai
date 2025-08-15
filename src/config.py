import os
from dataclasses import dataclass, field
from typing import List, Set


DEFAULT_HARMFUL_LABELS = {
    "knife", "gun", "rifle", "pistol", "revolver", "sword", "baton", "bat"
}


@dataclass
class AppConfig:
    source: str | int = 0  # webcam id or path
    frameskip: int = 3
    use_motion_filter: bool = True
    # Multimodal: enable these via env or GUARDIA_ENABLE_MULTIMODAL
    enable_multimodal: bool = bool(int(os.getenv("GUARDIA_ENABLE_MULTIMODAL", "1")))
    use_vision: bool = bool(int(os.getenv("GUARDIA_USE_VISION", os.getenv("GUARDIA_ENABLE_MULTIMODAL", "1"))))
    use_pose: bool = bool(int(os.getenv("GUARDIA_USE_POSE", os.getenv("GUARDIA_ENABLE_MULTIMODAL", "1"))))
    advanced_detection: bool = bool(int(os.getenv("GUARDIA_ADVANCED_DETECTION", "1")))  # prefer Vision for advanced hazards when available
    save_snapshots: bool = False
    snapshot_dir: str = os.path.abspath(os.getenv("GUARDIA_SNAPSHOT_DIR", "snapshots"))
    log_dir: str = os.path.abspath(os.getenv("GUARDIA_LOG_DIR", "logs"))
    outputs_dir: str = os.path.abspath(os.getenv("GUARDIA_OUTPUTS_DIR", "outputs"))

    # GCP
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
    gcs_bucket: str = os.getenv("GCS_BUCKET", "")
    use_gcs_upload: bool = bool(int(os.getenv("GUARDIA_USE_GCS_UPLOAD", "0")))
    pubsub_topic: str = os.getenv("PUBSUB_TOPIC", "")  # projects/{project_id}/topics/{topic_name}

    # Face auth
    use_face_auth: bool = bool(int(os.getenv("GUARDIA_USE_FACE_AUTH", "0")))
    face_db_dir: str = os.path.abspath(os.getenv("GUARDIA_FACE_DB_DIR", os.path.join("outputs", "faces")))
    trusted_people: List[str] = field(default_factory=list)

    # YOLO
    # YOLO primary weights; can be any Ultralytics-compatible weight file
    yolo_weights: str = os.getenv("YOLO_WEIGHTS", "yolov8n.pt")
    # Optional: additional YOLO weights for advanced/ensemble detection (comma-separated)
    yolo_extra_weights: List[str] = field(default_factory=lambda: [w for w in map(str.strip, os.getenv("YOLO_EXTRA_WEIGHTS", "").split(',')) if w])
    yolo_conf_thresh: float = 0.25
    yolo_iou_thresh: float = 0.45
    yolo_imgsz: int = int(os.getenv("YOLO_IMGSZ", "640"))
    device: str = os.getenv("GUARDIA_DEVICE", "auto")  # auto|cpu|cuda
    half: bool = bool(int(os.getenv("GUARDIA_HALF", "1")))  # use FP16 when supported

    # Tracking
    track_interval: int = int(os.getenv("GUARDIA_TRACK_INTERVAL", "5"))  # run YOLO every N frames; track otherwise

    # Loitering
    loiter_seconds_threshold: float = float(os.getenv("GUARDIA_LOITER_SECONDS", "20"))
    loiter_radius_px: int = int(os.getenv("GUARDIA_LOITER_RADIUS", "40"))
    loiter_classes: List[str] = field(default_factory=lambda: ["person"])  # classes to monitor for loitering

    # Hazard zones (x1,y1,x2,y2) screen-space rectangles; empty by default.
    hazard_zones: List[tuple[int, int, int, int]] = field(default_factory=list)
    zone_classes: List[str] = field(default_factory=lambda: ["person"])  # classes monitored for zone breaches

    # Vision
    max_vision_fps: float = float(os.getenv("GUARDIA_MAX_VISION_FPS", "2.0"))
    vision_min_score: float = 0.6

    # Pose
    pose_min_detection_confidence: float = 0.5
    pose_min_tracking_confidence: float = 0.5

    harmful_labels: Set[str] = field(default_factory=lambda: set(map(str.lower, DEFAULT_HARMFUL_LABELS)))

    # Security
    require_auth: bool = bool(int(os.getenv("GUARDIA_REQUIRE_AUTH", "1")))

    def ensure_dirs(self) -> None:
        os.makedirs(self.snapshot_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.outputs_dir, exist_ok=True)
