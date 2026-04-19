"""Pydantic request / response schemas for Guardia AI backend."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------------------


class EventCreate(BaseModel):
    camera_id: str
    classification: str
    severity: int = Field(..., ge=1, le=10)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    description: Optional[str] = None
    attribution: Optional[Dict[str, Any]] = None
    ai_model: Optional[str] = None
    frame_path: Optional[str] = None
    motion_score: Optional[float] = None


class EventResponse(BaseModel):
    event_id: str
    timestamp: datetime
    camera_id: str
    classification: str
    severity: int
    confidence: float
    description: Optional[str]
    attribution: Optional[Dict[str, Any]]
    ai_model: Optional[str]
    is_reviewed: bool
    frame_path: Optional[str] = None
    motion_score: Optional[float] = None

    class Config:
        from_attributes = True


class EventReviewUpdate(BaseModel):
    is_reviewed: bool = True


# ---------------------------------------------------------------------------
# Camera schemas
# ---------------------------------------------------------------------------


class CameraCreate(BaseModel):
    camera_id: str
    name: str
    rtsp_url: Optional[str] = None
    zone: str = "general"
    risk_level: int = Field(default=2, ge=1, le=5)


class CameraResponse(BaseModel):
    camera_id: str
    name: str
    rtsp_url: Optional[str]
    zone: str
    risk_level: int
    is_active: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Settings schemas
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseModel):
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    alert_threshold: Optional[int] = None
    analysis_interval_frames: Optional[int] = None


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------


class AnalyticsSummary(BaseModel):
    total_events: int
    reviewed_events: int
    unreviewed_events: int
    avg_severity: float
    top_classification: Optional[str]
    cameras_active: int


class TrendPoint(BaseModel):
    hour: str
    count: int
    avg_severity: float


# ---------------------------------------------------------------------------
# Motion detection result
# ---------------------------------------------------------------------------


class MotionResult(BaseModel):
    motion_detected: bool
    motion_score: float  # 0.0 – 1.0 normalised
    contour_count: int
    frame_delta_mean: float
    should_analyze: bool  # True when interval triggers AI call


# ---------------------------------------------------------------------------
# Gemini vision result
# ---------------------------------------------------------------------------


class VisionResult(BaseModel):
    classification: str
    severity: int
    confidence: float
    description: str
    raw_response: Optional[str] = None


# ---------------------------------------------------------------------------
# Fusion result
# ---------------------------------------------------------------------------


class FusionResult(BaseModel):
    classification: str
    severity: int
    confidence: float
    description: str
    attribution: Dict[str, Any]
    ai_model: str
    should_alert: bool
