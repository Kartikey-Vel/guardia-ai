"""Database layer — SQLAlchemy engine, session factory, and ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings

# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # required for SQLite
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------


class Camera(Base):
    """Registered camera / stream entry."""

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    rtsp_url = Column(String(512), nullable=True)
    zone = Column(String(64), default="general")
    risk_level = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    """Detected security event / alert record."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        String(64),
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    camera_id = Column(String(64), index=True, nullable=False)
    classification = Column(String(128), nullable=False)
    severity = Column(Integer, nullable=False)
    confidence = Column(Float, default=0.0)
    description = Column(Text, nullable=True)
    attribution = Column(JSON, nullable=True)  # dict: which models contributed
    ai_model = Column(String(64), nullable=True)
    is_reviewed = Column(Boolean, default=False)
    frame_path = Column(String(512), nullable=True)  # saved snapshot path
    motion_score = Column(Float, nullable=True)


class Setting(Base):
    """Key-value settings store."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all tables if they don't exist (idempotent)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency — yields a DB session and ensures cleanup."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
