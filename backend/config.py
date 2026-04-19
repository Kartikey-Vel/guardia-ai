"""Configuration module — environment-driven settings for Guardia AI backend."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings resolved from environment variables or .env file."""

    # AI provider keys (supports comma-separated list for rotation)
    gemini_api_keys: str = ""
    groq_api_keys: str = ""
    huggingface_api_keys: str = ""

    # Convenience properties for backward compatibility / single key usage
    @property
    def gemini_api_key(self) -> str:
        return self.gemini_api_keys.split(",")[0].strip() if self.gemini_api_keys else ""

    @property
    def groq_api_key(self) -> str:
        return self.groq_api_keys.split(",")[0].strip() if self.groq_api_keys else ""

    @property
    def huggingface_api_key(self) -> str:
        return self.huggingface_api_keys.split(",")[0].strip() if self.huggingface_api_keys else ""

    # Detection thresholds
    alert_threshold: int = 5
    analysis_interval_frames: int = 30

    # Database
    database_url: str = "sqlite:///./guardia.db"

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Motion detection tuning
    motion_min_contour_area: int = 500
    motion_gaussian_blur_kernel: int = 21
    motion_binary_threshold: int = 25
    motion_dilate_iterations: int = 2

    # Gemini model
    gemini_model: str = "gemini-1.5-flash"

    # Groq model
    groq_model: str = "llama3-8b-8192"

    # YOLO (Ultralytics)
    yolo_enabled: bool = True
    yolo_model: str = "yolov8n.pt"
    yolo_conf_threshold: float = 0.35
    yolo_iou_threshold: float = 0.45
    yolo_max_detections: int = 20

    # Demo mode settings
    demo_mode: bool = False
    demo_interval_seconds: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
