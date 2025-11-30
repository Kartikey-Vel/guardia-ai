"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


# ================================
# Event Schemas
# ================================

class EventCreate(BaseModel):
    event_id: str
    camera_id: str
    event_class: str
    severity: str
    confidence: float = Field(ge=0.0, le=1.0)
    frame_id: Optional[str] = None
    timestamp: datetime
    clip_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EventResponse(BaseModel):
    id: int
    event_id: str
    camera_id: str
    event_class: str
    severity: str
    confidence: float
    frame_id: Optional[str]
    timestamp: datetime
    clip_url: Optional[str]
    metadata: Optional[Dict[str, Any]]
    acknowledged: bool
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class EventList(BaseModel):
    events: List[EventResponse]
    total: int
    skip: int
    limit: int


# ================================
# Model Schemas
# ================================

class ModelCreate(BaseModel):
    name: str
    version: str
    model_type: str
    framework: str = "onnx"
    input_shape: Optional[Dict[str, Any]] = None
    output_classes: Optional[List[str]] = None
    weights_url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, float]] = None


class ModelResponse(BaseModel):
    id: int
    name: str
    version: str
    model_type: str
    framework: str
    input_shape: Optional[Dict[str, Any]]
    output_classes: Optional[List[str]]
    weights_url: Optional[str]
    config: Optional[Dict[str, Any]]
    metrics: Optional[Dict[str, float]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ModelList(BaseModel):
    models: List[ModelResponse]
    total: int
    skip: int
    limit: int


# ================================
# User Schemas
# ================================

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: Optional[str] = "operator"


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ================================
# Analytics Schemas
# ================================

class AnalyticsQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    camera_id: Optional[str] = None
    severity: Optional[str] = None


class AnalyticsResponse(BaseModel):
    start_date: datetime
    end_date: datetime
    total_events: int
    events_by_severity: Dict[str, int]
    events_by_class: Dict[str, int]
    events_by_camera: Dict[str, int]
