"""
Guardia AI Cloud API Service
FastAPI backend for event synchronization, model registry, and analytics
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional
import logging
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

from .database import engine, get_db, Base
from .models import Event, Model, User
from .schemas import (
    EventCreate, EventResponse, EventList,
    ModelCreate, ModelResponse, ModelList,
    UserCreate, UserResponse, Token,
    AnalyticsQuery, AnalyticsResponse
)
from .auth import (
    create_access_token, verify_token, get_password_hash,
    verify_password, get_current_user
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
event_counter = Counter('guardia_events_total', 'Total events synced', ['severity'])
api_request_duration = Histogram('guardia_api_request_duration_seconds', 'API request duration')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    # Startup: create tables
    logger.info("Starting Guardia API service...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Guardia API service...")
    await engine.dispose()


app = FastAPI(
    title="Guardia AI API",
    description="Cloud API for Guardia AI security intelligence platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


# ================================
# Health & Metrics
# ================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "api"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ================================
# Authentication
# ================================

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register new user"""
    # Check if user exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role or "operator"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    logger.info(f"User registered: {user.email}")
    return user


@app.post("/auth/login", response_model=Token)
async def login(username: str, password: str, db: AsyncSession = Depends(get_db)):
    """Login and get access token"""
    # Find user
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create token
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    logger.info(f"User logged in: {user.username}")
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


# ================================
# Events API
# ================================

@app.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Sync event from edge device"""
    event = Event(
        event_id=event_data.event_id,
        camera_id=event_data.camera_id,
        event_class=event_data.event_class,
        severity=event_data.severity,
        confidence=event_data.confidence,
        frame_id=event_data.frame_id,
        timestamp=event_data.timestamp,
        clip_url=event_data.clip_url,
        metadata=event_data.metadata,
        acknowledged=False
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    # Update metrics
    event_counter.labels(severity=event.severity).inc()
    
    logger.info(f"Event created: {event.event_id} - {event.event_class} ({event.severity})")
    return event


@app.get("/events", response_model=EventList)
async def list_events(
    skip: int = 0,
    limit: int = 50,
    severity: Optional[str] = None,
    camera_id: Optional[str] = None,
    event_class: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    acknowledged: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List events with filtering"""
    query = select(Event)
    
    # Apply filters
    filters = []
    if severity:
        filters.append(Event.severity == severity)
    if camera_id:
        filters.append(Event.camera_id == camera_id)
    if event_class:
        filters.append(Event.event_class == event_class)
    if start_date:
        filters.append(Event.timestamp >= start_date)
    if end_date:
        filters.append(Event.timestamp <= end_date)
    if acknowledged is not None:
        filters.append(Event.acknowledged == acknowledged)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(Event)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(Event.timestamp.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()
    
    return {
        "events": events,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get event by ID"""
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event


@app.patch("/events/{event_id}/acknowledge")
async def acknowledge_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge an event"""
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event.acknowledged = True
    event.acknowledged_at = datetime.utcnow()
    event.acknowledged_by = current_user.username
    
    await db.commit()
    
    logger.info(f"Event acknowledged: {event_id} by {current_user.username}")
    return {"status": "acknowledged", "event_id": event_id}


@app.delete("/events/{event_id}")
async def delete_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an event (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    await db.delete(event)
    await db.commit()
    
    logger.info(f"Event deleted: {event_id} by {current_user.username}")
    return {"status": "deleted", "event_id": event_id}


# ================================
# Models Registry
# ================================

@app.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
async def register_model(
    model_data: ModelCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register a new model version"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    model = Model(
        name=model_data.name,
        version=model_data.version,
        model_type=model_data.model_type,
        framework=model_data.framework,
        input_shape=model_data.input_shape,
        output_classes=model_data.output_classes,
        weights_url=model_data.weights_url,
        config=model_data.config,
        metrics=model_data.metrics
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    
    logger.info(f"Model registered: {model.name} v{model.version}")
    return model


@app.get("/models", response_model=ModelList)
async def list_models(
    skip: int = 0,
    limit: int = 20,
    model_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List registered models"""
    query = select(Model)
    
    if model_type:
        query = query.where(Model.model_type == model_type)
    
    # Get total count
    count_query = select(func.count()).select_from(Model)
    if model_type:
        count_query = count_query.where(Model.model_type == model_type)
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(Model.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    models = result.scalars().all()
    
    return {
        "models": models,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@app.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get model by ID"""
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    
    return model


# ================================
# Analytics
# ================================

@app.post("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    query: AnalyticsQuery,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analytics data"""
    start_date = query.start_date or (datetime.utcnow() - timedelta(days=7))
    end_date = query.end_date or datetime.utcnow()
    
    # Events by severity
    severity_query = select(
        Event.severity,
        func.count(Event.id).label('count')
    ).where(
        and_(Event.timestamp >= start_date, Event.timestamp <= end_date)
    ).group_by(Event.severity)
    
    severity_result = await db.execute(severity_query)
    events_by_severity = {row.severity: row.count for row in severity_result}
    
    # Events by class
    class_query = select(
        Event.event_class,
        func.count(Event.id).label('count')
    ).where(
        and_(Event.timestamp >= start_date, Event.timestamp <= end_date)
    ).group_by(Event.event_class)
    
    class_result = await db.execute(class_query)
    events_by_class = {row.event_class: row.count for row in class_result}
    
    # Events by camera
    camera_query = select(
        Event.camera_id,
        func.count(Event.id).label('count')
    ).where(
        and_(Event.timestamp >= start_date, Event.timestamp <= end_date)
    ).group_by(Event.camera_id)
    
    camera_result = await db.execute(camera_query)
    events_by_camera = {row.camera_id: row.count for row in camera_result}
    
    # Total events
    total_query = select(func.count(Event.id)).where(
        and_(Event.timestamp >= start_date, Event.timestamp <= end_date)
    )
    total_result = await db.execute(total_query)
    total_events = total_result.scalar()
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_events": total_events,
        "events_by_severity": events_by_severity,
        "events_by_class": events_by_class,
        "events_by_camera": events_by_camera
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
