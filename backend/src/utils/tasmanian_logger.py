import logging
import os
import sys
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Include exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)

def setup_logger(name):
    """Set up logger with console and file handlers."""
    logger = logging.getLogger(name)
    
    # Only configure handlers if they haven't been added yet
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # Create file handler for INFO level
        info_file_handler = RotatingFileHandler(
            "logs/info.log",
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        info_file_handler.setLevel(logging.INFO)
        info_file_handler.setFormatter(JSONFormatter())
        
        # Create file handler for ERROR level
        error_file_handler = RotatingFileHandler(
            "logs/error.log",
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(JSONFormatter())
        
        # Add handlers to logger
        logger.addHandler(console_handler)
        logger.addHandler(info_file_handler)
        logger.addHandler(error_file_handler)
    
    return logger

# Create a default logger for imports
default_logger = setup_logger("guardia_ai")
