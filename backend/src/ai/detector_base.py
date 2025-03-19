from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import time
import asyncio
from src.utils.tasmanian_logger import setup_logger

logger = setup_logger(__name__)

class DetectorBase(ABC):
    """Base class for all AI detectors."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the detector with configuration."""
        self.config = config or {}
        self.model = None
        self.is_running = False
        self.processing_time = 0
        self.name = self.__class__.__name__
        logger.info(f"Initializing {self.name}")
    
    @abstractmethod
    async def load_model(self) -> bool:
        """Load the AI model."""
        pass
        
    @abstractmethod
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process input data and return detection results."""
        pass
    
    async def warmup(self) -> bool:
        """Perform model warmup with sample data if needed."""
        logger.info(f"Warming up {self.name}")
        return True
        
    def get_stats(self) -> Dict[str, Any]:
        """Return detector stats."""
        return {
            "name": self.name,
            "is_running": self.is_running,
            "avg_processing_time": self.processing_time,
            "config": self.config
        }
