"""
Data Models for Guardia AI Enhanced
Pydantic models for type safety and validation
"""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator, EmailStr
from bson import ObjectId
import uuid

class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic v2"""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema, handler):
        field_schema.update(type="string")
        return field_schema

class UserRole(str, Enum):
    OWNER = "owner"
    FAMILY = "family"
    GUEST = "guest"
    ADMIN = "admin"

class DetectionType(str, Enum):
    KNOWN_PERSON = "known_person"
    UNKNOWN_PERSON = "unknown_person"
    MASKED_PERSON = "masked_person"
    LOITERING = "loitering"
    MULTIPLE_UNKNOWN = "multiple_unknown"
    NIGHT_INTRUSION = "night_intrusion"

class AlertStatus(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"

class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Base Models
class BaseMongoModel(BaseModel):
    """Base model for MongoDB documents"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str}
    }

# User Models
class UserBase(BaseModel):
    """Base user model"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.FAMILY

class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    """User update model"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None

class User(BaseMongoModel, UserBase):
    """Complete user model"""
    hashed_password: str
    is_active: bool = True
    last_login: Optional[datetime] = None
    face_encodings: List[List[float]] = Field(default_factory=list)
    
class UserInDB(User):
    """User model as stored in database"""
    pass

# Family Member Models
class FamilyMemberBase(BaseModel):
    """Base family member model"""
    name: str = Field(..., min_length=2, max_length=100)
    relation: str = Field(..., min_length=2, max_length=50)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    priority_level: PriorityLevel = PriorityLevel.MEDIUM

class FamilyMemberCreate(FamilyMemberBase):
    """Family member creation model"""
    owner_id: PyObjectId

class FamilyMember(BaseMongoModel, FamilyMemberBase):
    """Complete family member model"""
    owner_id: PyObjectId
    face_encodings: List[List[float]] = Field(default_factory=list)
    photos: List[str] = Field(default_factory=list)  # File paths
    is_active: bool = True

# Detection Models
class BoundingBox(BaseModel):
    """Bounding box coordinates"""
    x: int
    y: int
    width: int
    height: int

class FaceEncoding(BaseModel):
    """Face encoding data"""
    encoding: List[float]
    confidence: float
    landmarks: Optional[Dict[str, Any]] = None

class DetectionResult(BaseModel):
    """Detection result model"""
    detection_type: DetectionType
    confidence: float
    bounding_box: BoundingBox
    person_id: Optional[PyObjectId] = None
    person_name: Optional[str] = None
    face_encoding: Optional[FaceEncoding] = None
    is_masked: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SurveillanceFrame(BaseModel):
    """Surveillance frame data"""
    frame_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    camera_id: str
    detections: List[DetectionResult] = Field(default_factory=list)
    frame_path: Optional[str] = None
    processed: bool = False

# Alert Models
class AlertBase(BaseModel):
    """Base alert model"""
    detection_type: DetectionType
    priority: PriorityLevel
    message: str
    frame_id: str
    camera_id: str

class AlertCreate(AlertBase):
    """Alert creation model"""
    user_id: PyObjectId
    detection_data: Dict[str, Any] = Field(default_factory=dict)

class Alert(BaseMongoModel, AlertBase):
    """Complete alert model"""
    user_id: PyObjectId
    status: AlertStatus = AlertStatus.PENDING
    detection_data: Dict[str, Any] = Field(default_factory=dict)
    acknowledged_by: Optional[PyObjectId] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    photos: List[str] = Field(default_factory=list)
    videos: List[str] = Field(default_factory=list)

# Surveillance Session Models
class SurveillanceSessionBase(BaseModel):
    """Base surveillance session model"""
    name: Optional[str] = None
    camera_id: str
    settings: Dict[str, Any] = Field(default_factory=dict)

class SurveillanceSessionCreate(SurveillanceSessionBase):
    """Surveillance session creation model"""
    user_id: PyObjectId

class SurveillanceSession(BaseMongoModel, SurveillanceSessionBase):
    """Complete surveillance session model"""
    user_id: PyObjectId
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    is_active: bool = True
    total_detections: int = 0
    alerts_generated: int = 0
    recordings: List[str] = Field(default_factory=list)

# System Models
class SystemStats(BaseModel):
    """System statistics model"""
    total_users: int = 0
    total_family_members: int = 0
    active_sessions: int = 0
    total_detections: int = 0
    alerts_today: int = 0
    system_uptime: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CameraInfo(BaseModel):
    """Camera information model"""
    camera_id: str
    name: Optional[str] = None
    location: Optional[str] = None
    is_active: bool = True
    resolution: str = "1280x720"
    fps: int = 30
    last_frame: Optional[datetime] = None

# API Response Models
class TokenData(BaseModel):
    """Token data model"""
    username: Optional[str] = None

class Token(BaseModel):
    """JWT token model"""
    access_token: str
    token_type: str

class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None

class PaginatedResponse(BaseModel):
    """Paginated response model"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int

# Configuration Models
class NotificationSettings(BaseModel):
    """Notification settings model"""
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    alert_types: List[DetectionType] = Field(default_factory=list)
    quiet_hours_start: Optional[str] = None  # HH:MM format
    quiet_hours_end: Optional[str] = None    # HH:MM format

class UserPreferences(BaseModel):
    """User preferences model"""
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    detection_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)
    auto_resolve_alerts: bool = False
    theme: str = "light"
    language: str = "en"

# Export all models
__all__ = [
    # Base
    "BaseMongoModel", "PyObjectId",
    # Enums
    "UserRole", "DetectionType", "AlertStatus", "PriorityLevel",
    # User models
    "UserBase", "UserCreate", "UserUpdate", "User", "UserInDB",
    # Family models
    "FamilyMemberBase", "FamilyMemberCreate", "FamilyMember",
    # Detection models
    "BoundingBox", "FaceEncoding", "DetectionResult", "SurveillanceFrame",
    # Alert models
    "AlertBase", "AlertCreate", "Alert",
    # Session models
    "SurveillanceSessionBase", "SurveillanceSessionCreate", "SurveillanceSession",
    # System models
    "SystemStats", "CameraInfo",
    # API models
    "TokenData", "Token", "APIResponse", "PaginatedResponse",
    # Configuration models
    "NotificationSettings", "UserPreferences"
]
