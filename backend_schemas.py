# backend/models/schemas.py
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class EventCreate(BaseModel):
    camera_id: str
    classification: str
    severity: int
    confidence: float = 0.0
    description: Optional[str] = None

class EventResponse(BaseModel):
    event_id: str
    timestamp: datetime
    camera_id: str
    classification: str
    severity: int
    confidence: float
    description: Optional[str]
    attribution: Optional[Dict]
    ai_model: Optional[str]
    is_reviewed: bool

class CameraCreate(BaseModel):
    camera_id: str
    name: str
    rtsp_url: Optional[str] = None
    zone: str = "general"
    risk_level: int = 2

class SettingsUpdate(BaseModel):
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    alert_threshold: Optional[int] = None
    analysis_interval_frames: Optional[int] = None
