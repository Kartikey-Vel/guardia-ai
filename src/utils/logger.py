"""
Logging utilities for Guardia AI
Centralized logging configuration
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from colorama import Fore, Style, init
import config.settings as settings

# Initialize colorama for cross-platform colored output
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages"""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA + Style.BRIGHT
    }
    
    def format(self, record):
        # Add color to the levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{Style.RESET_ALL}"
        return super().format(record)

def setup_logging():
    """Setup logging configuration for the application"""
    
    # Create logs directory if it doesn't exist
    settings.LOGS_DIR.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(settings.LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = settings.LOGS_DIR / "guardia_ai.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=settings.MAX_LOG_SIZE,
        backupCount=settings.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(settings.LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Alert handler for critical alerts
    alert_file = settings.LOGS_DIR / "alerts.log"
    alert_handler = RotatingFileHandler(
        alert_file,
        maxBytes=settings.MAX_LOG_SIZE,
        backupCount=settings.LOG_BACKUP_COUNT
    )
    alert_handler.setLevel(logging.WARNING)
    alert_handler.setFormatter(file_formatter)
    logger.addHandler(alert_handler)
    
    logger.info("🔧 Logging system initialized")
    return logger

def get_logger(name: str = __name__):
    """Get a logger instance for a specific module"""
    return logging.getLogger(name)
