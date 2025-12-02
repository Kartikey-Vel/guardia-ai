"""
Guardia AI Cloud API Service
FastAPI backend for event synchronization, model registry, analytics,
camera management, edge computing, and security fusion
"""

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import os
import httpx
import asyncio
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
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

# Service URLs for internal communication
CAMERA_MANAGER_URL = os.getenv("CAMERA_MANAGER_URL", "http://camera-manager:8006")
EDGE_COMPUTE_URL = os.getenv("EDGE_COMPUTE_URL", "http://edge-compute:8007")
SECURITY_FUSION_URL = os.getenv("SECURITY_FUSION_URL", "http://security-fusion:8008")
USER_MANAGEMENT_URL = os.getenv("USER_MANAGEMENT_URL", "http://user-management:8010")

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
event_counter = Counter('guardia_events_total', 'Total events synced', ['severity'])
api_request_duration = Histogram('guardia_api_request_duration_seconds', 'API request duration')
active_cameras = Gauge('guardia_active_cameras', 'Number of active cameras')
edge_nodes_online = Gauge('guardia_edge_nodes_online', 'Number of online edge nodes')
security_alerts = Counter('guardia_security_alerts_total', 'Total security alerts', ['alert_type'])

# HTTP client for service communication
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle"""
    global http_client
    
    # Startup: create tables and HTTP client
    logger.info("Starting Guardia API service...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
    
    # Create HTTP client for service communication
    http_client = httpx.AsyncClient(timeout=30.0)
    logger.info("HTTP client initialized for service communication")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Guardia API service...")
    if http_client:
        await http_client.aclose()
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


# ================================
# Camera Management API (Proxy to camera-manager)
# ================================

@app.get("/cameras")
async def list_cameras(current_user: User = Depends(get_current_user)):
    """List all cameras and their status"""
    try:
        response = await http_client.get(f"{CAMERA_MANAGER_URL}/cameras")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to camera manager: {e}")
        raise HTTPException(status_code=503, detail="Camera manager service unavailable")


@app.post("/cameras")
async def add_camera(
    camera_config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Add a new camera"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        response = await http_client.post(f"{CAMERA_MANAGER_URL}/cameras", json=camera_config)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to add camera: {e}")
        raise HTTPException(status_code=503, detail="Camera manager service unavailable")


@app.get("/cameras/{camera_id}")
async def get_camera(
    camera_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get camera details"""
    try:
        response = await http_client.get(f"{CAMERA_MANAGER_URL}/cameras/{camera_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Camera not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Camera manager service unavailable")


@app.delete("/cameras/{camera_id}")
async def remove_camera(
    camera_id: str,
    current_user: User = Depends(get_current_user)
):
    """Remove a camera"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        response = await http_client.delete(f"{CAMERA_MANAGER_URL}/cameras/{camera_id}")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Camera manager service unavailable")


@app.post("/cameras/{camera_id}/reconnect")
async def reconnect_camera(
    camera_id: str,
    current_user: User = Depends(get_current_user)
):
    """Force reconnect to a camera"""
    try:
        response = await http_client.post(f"{CAMERA_MANAGER_URL}/cameras/{camera_id}/reconnect")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Camera manager service unavailable")


@app.get("/cameras/droidcam/discover")
async def discover_droidcam(current_user: User = Depends(get_current_user)):
    """Discover DroidCam devices on the network"""
    try:
        response = await http_client.get(f"{CAMERA_MANAGER_URL}/droidcam/discover")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Camera manager service unavailable")


# ================================
# Edge Computing API (Proxy to edge-compute)
# ================================

@app.get("/edge/nodes")
async def list_edge_nodes(current_user: User = Depends(get_current_user)):
    """List all edge computing nodes"""
    try:
        response = await http_client.get(f"{EDGE_COMPUTE_URL}/status")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to edge compute service: {e}")
        raise HTTPException(status_code=503, detail="Edge compute service unavailable")


@app.get("/edge/bandwidth")
async def get_bandwidth_stats(current_user: User = Depends(get_current_user)):
    """Get bandwidth optimization statistics"""
    try:
        response = await http_client.get(f"{EDGE_COMPUTE_URL}/bandwidth")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Edge compute service unavailable")


@app.get("/edge/storage")
async def get_storage_stats(current_user: User = Depends(get_current_user)):
    """Get local storage statistics"""
    try:
        response = await http_client.get(f"{EDGE_COMPUTE_URL}/storage")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Edge compute service unavailable")


@app.post("/edge/config")
async def update_edge_config(
    config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update edge computing configuration"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        response = await http_client.post(f"{EDGE_COMPUTE_URL}/config", json=config)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Edge compute service unavailable")


# ================================
# Security Fusion API (Proxy to security-fusion)
# ================================

@app.get("/security/status")
async def get_security_status(current_user: User = Depends(get_current_user)):
    """Get overall security system status"""
    try:
        response = await http_client.get(f"{SECURITY_FUSION_URL}/status")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Security fusion service unavailable")


@app.get("/security/persons")
async def list_tracked_persons(current_user: User = Depends(get_current_user)):
    """List all tracked persons"""
    try:
        response = await http_client.get(f"{SECURITY_FUSION_URL}/persons")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Security fusion service unavailable")


@app.post("/security/faces/enroll")
async def enroll_face(
    enrollment_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Enroll a new face for recognition"""
    if current_user.role not in ["admin", "operator"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        response = await http_client.post(
            f"{SECURITY_FUSION_URL}/faces/enroll",
            json=enrollment_data
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Security fusion service unavailable")


@app.get("/security/faces")
async def list_enrolled_faces(current_user: User = Depends(get_current_user)):
    """List all enrolled faces"""
    try:
        response = await http_client.get(f"{SECURITY_FUSION_URL}/faces")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Security fusion service unavailable")


@app.delete("/security/faces/{person_id}")
async def remove_enrolled_face(
    person_id: str,
    current_user: User = Depends(get_current_user)
):
    """Remove an enrolled face"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        response = await http_client.delete(f"{SECURITY_FUSION_URL}/faces/{person_id}")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Security fusion service unavailable")


@app.post("/security/owner-protection")
async def toggle_owner_protection(
    enabled: bool,
    current_user: User = Depends(get_current_user)
):
    """Toggle owner protection mode"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        response = await http_client.post(
            f"{SECURITY_FUSION_URL}/owner-protection",
            json={"enabled": enabled}
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Security fusion service unavailable")


@app.get("/security/anomalies")
async def get_anomaly_history(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
):
    """Get anomaly detection history"""
    try:
        response = await http_client.get(
            f"{SECURITY_FUSION_URL}/anomalies",
            params={"hours": hours}
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Security fusion service unavailable")


# ================================
# User Management API (Proxy to user-management)
# ================================

@app.get("/profiles")
async def list_user_profiles(current_user: User = Depends(get_current_user)):
    """List all user profiles"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        response = await http_client.get(f"{USER_MANAGEMENT_URL}/users")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="User management service unavailable")


@app.post("/profiles")
async def create_user_profile(
    profile_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Create a new user profile"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        response = await http_client.post(f"{USER_MANAGEMENT_URL}/users", json=profile_data)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="User management service unavailable")


@app.get("/profiles/{user_id}")
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a user profile"""
    try:
        response = await http_client.get(f"{USER_MANAGEMENT_URL}/users/{user_id}")
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Profile not found")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="User management service unavailable")


@app.patch("/profiles/{user_id}")
async def update_user_profile(
    user_id: str,
    profile_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update a user profile"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        response = await http_client.patch(
            f"{USER_MANAGEMENT_URL}/users/{user_id}",
            json=profile_data
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="User management service unavailable")


@app.post("/profiles/{user_id}/family")
async def add_family_member(
    user_id: str,
    family_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Add a family member to a profile"""
    try:
        response = await http_client.post(
            f"{USER_MANAGEMENT_URL}/users/{user_id}/family",
            json=family_data
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="User management service unavailable")


@app.get("/profiles/{user_id}/activity")
async def get_profile_activity(
    user_id: str,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Get activity logs for a user profile"""
    try:
        response = await http_client.get(
            f"{USER_MANAGEMENT_URL}/users/{user_id}/activity",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="User management service unavailable")


# ================================
# System Dashboard API
# ================================

@app.get("/dashboard/overview")
async def get_dashboard_overview(current_user: User = Depends(get_current_user)):
    """Get comprehensive system overview for dashboard"""
    overview = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "cameras": {},
        "security": {},
        "edge": {},
        "recent_events": []
    }
    
    # Check service health
    services_to_check = [
        ("camera-manager", CAMERA_MANAGER_URL),
        ("edge-compute", EDGE_COMPUTE_URL),
        ("security-fusion", SECURITY_FUSION_URL),
        ("user-management", USER_MANAGEMENT_URL)
    ]
    
    for service_name, service_url in services_to_check:
        try:
            response = await http_client.get(f"{service_url}/health", timeout=5.0)
            overview["services"][service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            overview["services"][service_name] = {
                "status": "offline",
                "error": str(e)
            }
    
    # Get camera summary
    try:
        response = await http_client.get(f"{CAMERA_MANAGER_URL}/cameras", timeout=5.0)
        if response.status_code == 200:
            cameras = response.json()
            overview["cameras"] = {
                "total": len(cameras) if isinstance(cameras, list) else cameras.get("total", 0),
                "active": sum(1 for c in cameras if isinstance(cameras, list) and c.get("status") == "active") if isinstance(cameras, list) else cameras.get("active", 0)
            }
    except Exception:
        overview["cameras"] = {"total": 0, "active": 0, "error": "Service unavailable"}
    
    # Get security status
    try:
        response = await http_client.get(f"{SECURITY_FUSION_URL}/status", timeout=5.0)
        if response.status_code == 200:
            overview["security"] = response.json()
    except Exception:
        overview["security"] = {"status": "unavailable"}
    
    # Get edge status
    try:
        response = await http_client.get(f"{EDGE_COMPUTE_URL}/status", timeout=5.0)
        if response.status_code == 200:
            overview["edge"] = response.json()
    except Exception:
        overview["edge"] = {"status": "unavailable"}
    
    # Get recent events from database
    db = get_db()
    async for session in db:
        query = select(Event).order_by(Event.timestamp.desc()).limit(10)
        result = await session.execute(query)
        events = result.scalars().all()
        overview["recent_events"] = [
            {
                "id": e.event_id,
                "class": e.event_class,
                "severity": e.severity,
                "camera_id": e.camera_id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None
            }
            for e in events
        ]
        break
    
    return overview


@app.get("/dashboard/stats")
async def get_dashboard_stats(
    period: str = "24h",
    current_user: User = Depends(get_current_user)
):
    """Get statistics for dashboard charts"""
    # Parse period
    if period == "24h":
        start_date = datetime.utcnow() - timedelta(hours=24)
    elif period == "7d":
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        start_date = datetime.utcnow() - timedelta(days=30)
    else:
        start_date = datetime.utcnow() - timedelta(hours=24)
    
    end_date = datetime.utcnow()
    
    db = get_db()
    async for session in db:
        # Events timeline (hourly buckets)
        timeline_query = select(
            func.date_trunc('hour', Event.timestamp).label('hour'),
            func.count(Event.id).label('count')
        ).where(
            and_(Event.timestamp >= start_date, Event.timestamp <= end_date)
        ).group_by(func.date_trunc('hour', Event.timestamp)).order_by('hour')
        
        timeline_result = await session.execute(timeline_query)
        timeline = [{"hour": row.hour.isoformat(), "count": row.count} for row in timeline_result]
        
        # Severity distribution
        severity_query = select(
            Event.severity,
            func.count(Event.id).label('count')
        ).where(
            and_(Event.timestamp >= start_date, Event.timestamp <= end_date)
        ).group_by(Event.severity)
        
        severity_result = await session.execute(severity_query)
        severity_dist = {row.severity: row.count for row in severity_result}
        
        # Top event classes
        class_query = select(
            Event.event_class,
            func.count(Event.id).label('count')
        ).where(
            and_(Event.timestamp >= start_date, Event.timestamp <= end_date)
        ).group_by(Event.event_class).order_by(func.count(Event.id).desc()).limit(10)
        
        class_result = await session.execute(class_query)
        top_classes = [{"class": row.event_class, "count": row.count} for row in class_result]
        
        return {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timeline": timeline,
            "severity_distribution": severity_dist,
            "top_event_classes": top_classes
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
