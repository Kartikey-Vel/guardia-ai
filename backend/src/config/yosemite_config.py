import os
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """App configuration settings."""
    
    # API Server settings
    APP_NAME: str = "Guardia AI"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "t")
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "guardia_super_secret_key_replace_in_production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # MongoDB settings
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "guardia_db")
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # Frontend development server
        "https://guardia-ai.example.com",  # Production domain
    ]
    
    # AI Settings
    MOTION_DETECTION_THRESHOLD: float = float(os.getenv("MOTION_DETECTION_THRESHOLD", "0.6"))
    ANOMALY_DETECTION_THRESHOLD: float = float(os.getenv("ANOMALY_DETECTION_THRESHOLD", "0.7"))
    WEAPON_DETECTION_THRESHOLD: float = float(os.getenv("WEAPON_DETECTION_THRESHOLD", "0.8"))
    GUNSHOT_DETECTION_THRESHOLD: float = float(os.getenv("GUNSHOT_DETECTION_THRESHOLD", "0.75"))
    SCREAM_DETECTION_THRESHOLD: float = float(os.getenv("SCREAM_DETECTION_THRESHOLD", "0.65"))
    
    # Alert settings
    ALERT_EMAIL: str = os.getenv("ALERT_EMAIL", "alerts@example.com")
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    
    # Video sources
    VIDEO_SOURCES: List[str] = [s.strip() for s in os.getenv("VIDEO_SOURCES", "").split(",") if s.strip()]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }

# Create settings instance
settings = Settings()
