"""
SQLAlchemy database models
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func
from .database import Base


class Event(Base):
    """Event model for security events"""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(50), unique=True, index=True, nullable=False)
    camera_id = Column(String(50), index=True, nullable=False)
    event_class = Column(String(50), index=True, nullable=False)
    severity = Column(String(20), index=True, nullable=False)
    confidence = Column(Float, nullable=False)
    frame_id = Column(String(50))
    timestamp = Column(DateTime, index=True, nullable=False)
    clip_url = Column(String(500))
    metadata = Column(JSON)
    
    # Acknowledgement
    acknowledged = Column(Boolean, default=False, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Model(Base):
    """Model registry for AI models"""
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    version = Column(String(20), nullable=False)
    model_type = Column(String(50), index=True, nullable=False)  # skelegnn, motionstream, moodtiny
    framework = Column(String(50))  # onnx, pytorch, tensorflow
    input_shape = Column(JSON)
    output_classes = Column(JSON)
    weights_url = Column(String(500))
    config = Column(JSON)
    metrics = Column(JSON)  # accuracy, precision, recall, etc.
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="operator")  # operator, admin
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)
