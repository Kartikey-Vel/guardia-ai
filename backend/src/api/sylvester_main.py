from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.api.daffy_events import router as events_router
from src.api.tweety_auth import router as auth_router
from src.api.bugs_notify import router as notify_router
from src.api.roadrunner_detector import router as detector_router
from src.api.stats_api import router as stats_router
from src.api.dashboard_api import router as dashboard_router
from src.utils.tasmanian_logger import setup_logger
from src.config.yosemite_config import settings

# Create FastAPI app
app = FastAPI(
    title="Guardia AI API",
    description="Advanced AI-powered security and surveillance assistant API",
    version="0.1.0"
)

# Setup logging
logger = setup_logger(__name__)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(events_router, prefix="/events", tags=["Security Events"])
app.include_router(notify_router, prefix="/notify", tags=["Real-time Notifications"])
app.include_router(detector_router, prefix="/detectors", tags=["AI Detectors"])
app.include_router(stats_router, prefix="/stats", tags=["Statistics"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "service": "Guardia AI",
        "status": "online",
        "version": app.version
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "operational",
        "database": "connected",  # In a real app, you'd check DB connection
        "api_version": app.version
    }
