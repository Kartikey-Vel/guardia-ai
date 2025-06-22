"""
Enhanced Guardia AI Configuration Settings
Modern configuration management with environment-based settings
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings
from enum import Enum

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Settings(BaseSettings):
    """Enhanced Guardia AI Configuration Settings"""
    
    # Project Settings
    project_name: str = Field(default="Guardia AI Enhanced")
    project_version: str = Field(default="2.0.0")
    environment: EnvironmentType = Field(default=EnvironmentType.DEVELOPMENT)
    debug: bool = Field(default=True)
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", alias="HOST")
    api_port: int = Field(default=8000, alias="PORT")
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, alias="CORS_CREDENTIALS")
    
    # Database Settings - MongoDB Atlas (from env)
    mongodb_url: str = Field(alias="MONGODB_URL")
    mongodb_database: str = Field(default="guardia_ai_db", alias="MONGODB_DATABASE")
    mongodb_max_connections: int = Field(default=100, alias="MONGODB_MAX_CONNECTIONS")
    mongodb_min_connections: int = Field(default=10, alias="MONGODB_MIN_CONNECTIONS")
    
    # Security Settings (from env)
    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, alias="JWT_EXPIRATION_MINUTES")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")
    session_timeout_minutes: int = Field(default=30, alias="SESSION_TIMEOUT_MINUTES")
    
    # Google Cloud Settings (from env)
    google_credentials_path: Optional[str] = Field(default="./guardia/config/google-credentials.json", alias="GOOGLE_APPLICATION_CREDENTIALS")
    google_storage_bucket: str = Field(default="guardia_ai_vi", alias="GCS_BUCKET_NAME")
    google_cloud_project_id: str = Field(default="gaurdia-ai", alias="GOOGLE_CLOUD_PROJECT_ID")
    enable_video_intelligence: bool = Field(default=True, alias="ENABLE_VIDEO_INTELLIGENCE")
    video_intelligence_features: str = Field(default="PERSON_DETECTION,OBJECT_TRACKING", alias="VIDEO_INTELLIGENCE_FEATURES")
    
    # Camera and Detection Settings (from env)
    camera_sources: str = Field(default="0", alias="CAMERA_SOURCES")
    face_detection_confidence: float = Field(default=0.5, alias="FACE_DETECTION_CONFIDENCE")
    object_detection_confidence: float = Field(default=0.5, alias="OBJECT_DETECTION_CONFIDENCE")
    mask_detection_confidence: float = Field(default=0.5, alias="MASK_DETECTION_CONFIDENCE")
    frame_skip_count: int = Field(default=2, alias="FRAME_SKIP_COUNT")
    max_frames_buffer: int = Field(default=30, alias="MAX_FRAMES_BUFFER")
    alert_cooldown_seconds: int = Field(default=30, alias="ALERT_COOLDOWN_SECONDS")
    max_video_duration_seconds: int = Field(default=30, alias="MAX_VIDEO_DURATION_SECONDS")
    
    # Storage Settings (from env)
    media_storage_path: str = Field(default="./storage/media", alias="MEDIA_STORAGE_PATH")
    images_path: str = Field(default="./storage/images", alias="IMAGES_PATH")
    videos_path: str = Field(default="./storage/videos", alias="VIDEOS_PATH")
    faces_path: str = Field(default="./storage/faces", alias="FACES_PATH")
    logs_path: str = Field(default="./storage/logs", alias="LOGS_PATH")
    max_storage_size_mb: int = Field(default=5000, alias="MAX_STORAGE_SIZE_MB")
    
    # Notification Settings (Email)
    enable_email_notifications: bool = Field(default=False, alias="ENABLE_EMAIL_NOTIFICATIONS")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")
    
    # Notification Settings (SMS)
    enable_sms_notifications: bool = Field(default=False, alias="ENABLE_SMS_NOTIFICATIONS")
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(default="", alias="TWILIO_FROM_NUMBER")
    
    # Push Notifications
    enable_push_notifications: bool = Field(default=True, alias="ENABLE_PUSH_NOTIFICATIONS")
    
    # Redis Configuration (optional)
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    
    # Performance and ML Settings (from env)
    face_detection_backend: str = Field(default="mediapipe", alias="FACE_DETECTION_BACKEND")
    yolo_model_size: str = Field(default="yolov8n.pt", alias="YOLO_MODEL_SIZE")
    yolo_device: str = Field(default="cpu", alias="YOLO_DEVICE")
    auto_update_models: bool = Field(default=False, alias="AUTO_UPDATE_MODELS")
    ml_model_update_interval_hours: int = Field(default=24, alias="MODEL_UPDATE_INTERVAL_HOURS")
    
    # Advanced Features
    enable_behavior_analysis: bool = Field(default=True, alias="ENABLE_BEHAVIOR_ANALYSIS")
    loitering_threshold_seconds: int = Field(default=30, alias="LOITERING_THRESHOLD_SECONDS")
    crowd_detection_threshold: int = Field(default=5, alias="CROWD_DETECTION_THRESHOLD")
    
    # Night Mode
    enable_night_mode: bool = Field(default=True, alias="ENABLE_NIGHT_MODE")
    night_mode_start_hour: int = Field(default=22, alias="NIGHT_MODE_START_HOUR")
    night_mode_end_hour: int = Field(default=6, alias="NIGHT_MODE_END_HOUR")
    
    # Privacy Settings
    blur_faces_in_recordings: bool = Field(default=False, alias="BLUR_FACES_IN_RECORDINGS")
    anonymize_unknown_persons: bool = Field(default=False, alias="ANONYMIZE_UNKNOWN_PERSONS")
    
    # Logging and Monitoring
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_directory: str = Field(default="./storage/logs", alias="LOG_DIRECTORY")
    log_max_size: str = Field(default="10MB", alias="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, alias="LOG_BACKUP_COUNT")
    enable_performance_monitoring: bool = Field(default=True, alias="ENABLE_PERFORMANCE_MONITORING")
    performance_sampling_rate: float = Field(default=0.1, alias="PERFORMANCE_SAMPLING_RATE")
    
    # Development Settings (from env)
    enable_api_docs: bool = Field(default=True, alias="ENABLE_API_DOCS")
    api_reload: bool = Field(default=True, alias="ENABLE_RELOAD")
    enable_profiling: bool = Field(default=False, alias="ENABLE_PROFILING")
    test_mode: bool = Field(default=False, alias="TEST_MODE")
    mock_cameras: bool = Field(default=False, alias="MOCK_CAMERAS")
    
    # Cleanup Settings (from env)
    enable_auto_cleanup: bool = Field(default=True, alias="ENABLE_AUTO_CLEANUP")
    cleanup_interval_hours: int = Field(default=24, alias="CLEANUP_INTERVAL_HOURS")
    retain_media_days: int = Field(default=30, alias="RETAIN_MEDIA_DAYS")
    retain_logs_days: int = Field(default=7, alias="RETAIN_LOGS_DAYS")
    
    # Backup Settings
    enable_auto_backup: bool = Field(default=False, alias="ENABLE_AUTO_BACKUP")
    backup_interval_hours: int = Field(default=24, alias="BACKUP_INTERVAL_HOURS")
    backup_retention_days: int = Field(default=30, alias="BACKUP_RETENTION_DAYS")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
        "protected_namespaces": ('settings_',)
    }

def get_settings() -> Settings:
    """Get settings instance"""
    return Settings()

# Create global settings instance
settings = get_settings()

# Export configuration
__all__ = ["Settings", "get_settings", "settings", "PriorityLevel"]
