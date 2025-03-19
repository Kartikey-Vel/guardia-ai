import uvicorn
import asyncio
from fastapi.staticfiles import StaticFiles
from src.api.sylvester_main import app
from src.utils.tasmanian_logger import setup_logger
from src.config.yosemite_config import settings
from src.db.porky_mongo import create_indexes
from src.ai.video_processor import MotionDetector, WeaponDetector
from src.ai.audio_processor import GunshotDetector, ScreamDetector
from src.api.roadrunner_detector import video_detectors, audio_detectors

logger = setup_logger(__name__)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Guardia AI API server...")
    
    # Initialize database indexes
    try:
        await create_indexes()
        logger.info("Database indexes created/verified")
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
    
    # Initialize AI detectors
    try:
        # Initialize video detectors
        motion_detector = MotionDetector({"threshold": settings.MOTION_DETECTION_THRESHOLD})
        await motion_detector.load_model()
        video_detectors["motion"] = motion_detector
        
        weapon_detector = WeaponDetector({"threshold": settings.WEAPON_DETECTION_THRESHOLD})
        await weapon_detector.load_model()
        video_detectors["weapon"] = weapon_detector
        
        # Initialize audio detectors
        gunshot_detector = GunshotDetector({"threshold": 0.75})
        await gunshot_detector.load_model()
        audio_detectors["gunshot"] = gunshot_detector
        
        scream_detector = ScreamDetector({"threshold": 0.65})
        await scream_detector.load_model()
        audio_detectors["scream"] = scream_detector
        
        logger.info("AI detectors initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing AI detectors: {e}")

# Static files for documentation
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

if __name__ == "__main__":
    logger.info(f"Starting Guardia AI API server on {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "src.api.sylvester_main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG_MODE,
        log_level="info"
    )
