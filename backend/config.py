"""Configuration module — environment-driven settings for Guardia AI backend."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings resolved from environment variables or .env file."""

    # AI provider keys
    gemini_api_key: str = ""
    groq_api_key: str = ""
    huggingface_api_key: str = ""

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
