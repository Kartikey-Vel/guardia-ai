"""
Logging utilities and configuration for Guardia AI Enhanced System

This module provides structured logging setup and utilities including:
- Async logging handlers
- Log rotation and archival
- Performance logging
- Security event logging
"""

import logging
import logging.handlers
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import sys
import traceback

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        if hasattr(record, 'detection_id'):
            log_entry["detection_id"] = record.detection_id
        if hasattr(record, 'performance_metrics'):
            log_entry["performance_metrics"] = record.performance_metrics
        
        return json.dumps(log_entry)

class SecurityEventLogger:
    """Specialized logger for security events"""
    
    def __init__(self, log_file: str = "security_events.log"):
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler for security events
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
    
    def log_authentication(self, user_id: str, success: bool, ip_address: str = None, 
                          user_agent: str = None):
        """Log authentication attempt"""
        self.logger.info(
            "Authentication attempt",
            extra={
                "event_type": "authentication",
                "user_id": user_id,
                "success": success,
                "ip_address": ip_address,
                "user_agent": user_agent
            }
        )
    
    def log_authorization_failure(self, user_id: str, resource: str, action: str):
        """Log authorization failure"""
        self.logger.warning(
            "Authorization failure",
            extra={
                "event_type": "authorization_failure",
                "user_id": user_id,
                "resource": resource,
                "action": action
            }
        )
    
    def log_suspicious_activity(self, user_id: str, activity: str, details: Dict[str, Any]):
        """Log suspicious activity"""
        self.logger.warning(
            "Suspicious activity detected",
            extra={
                "event_type": "suspicious_activity",
                "user_id": user_id,
                "activity": activity,
                "details": details
            }
        )

class PerformanceLogger:
    """Logger for performance metrics and monitoring"""
    
    def __init__(self, log_file: str = "performance.log"):
        self.logger = logging.getLogger("performance")
        self.logger.setLevel(logging.INFO)
        
        # Create file handler for performance logs
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=20*1024*1024,  # 20MB
            backupCount=3
        )
        handler.setFormatter(JSONFormatter())
        self.logger.addHandler(handler)
    
    def log_detection_performance(self, detection_type: str, processing_time: float, 
                                 confidence: float, image_size: tuple):
        """Log detection performance metrics"""
        self.logger.info(
            "Detection performance",
            extra={
                "performance_metrics": {
                    "detection_type": detection_type,
                    "processing_time_ms": processing_time * 1000,
                    "confidence": confidence,
                    "image_width": image_size[0],
                    "image_height": image_size[1]
                }
            }
        )
    
    def log_api_performance(self, endpoint: str, method: str, response_time: float, 
                           status_code: int, user_id: str = None):
        """Log API endpoint performance"""
        self.logger.info(
            "API performance",
            extra={
                "performance_metrics": {
                    "endpoint": endpoint,
                    "method": method,
                    "response_time_ms": response_time * 1000,
                    "status_code": status_code,
                    "user_id": user_id
                }
            }
        )
    
    def log_database_performance(self, operation: str, execution_time: float, 
                               affected_rows: int = None):
        """Log database operation performance"""
        self.logger.info(
            "Database performance",
            extra={
                "performance_metrics": {
                    "operation": operation,
                    "execution_time_ms": execution_time * 1000,
                    "affected_rows": affected_rows
                }
            }
        )

class AsyncLogHandler(logging.Handler):
    """Async log handler to prevent blocking"""
    
    def __init__(self, handler: logging.Handler):
        super().__init__()
        self.handler = handler
        self.queue = asyncio.Queue()
        self.task = None
    
    def emit(self, record: logging.LogRecord):
        """Add log record to async queue"""
        if self.queue:
            try:
                self.queue.put_nowait(record)
            except asyncio.QueueFull:
                # Drop log if queue is full to prevent memory issues
                pass
    
    async def start(self):
        """Start async log processing"""
        self.task = asyncio.create_task(self._process_logs())
    
    async def stop(self):
        """Stop async log processing"""
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
    
    async def _process_logs(self):
        """Process logs from queue"""
        while True:
            try:
                record = await self.queue.get()
                self.handler.emit(record)
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log processing error, but don't crash
                print(f"Error processing log: {e}", file=sys.stderr)

def setup_logging(
    log_level: str = "INFO",
    log_directory: str = "logs",
    enable_console: bool = True,
    enable_json: bool = False,
    enable_rotation: bool = True
) -> Dict[str, logging.Logger]:
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_directory: Directory for log files
        enable_console: Enable console logging
        enable_json: Use JSON formatter
        enable_rotation: Enable log rotation
        
    Returns:
        dict: Dictionary of configured loggers
    """
    
    # Create log directory
    log_dir = Path(log_directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter
    if enable_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handlers
    if enable_rotation:
        # Main application log with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "guardia_ai.log",
            maxBytes=50*1024*1024,  # 50MB
            backupCount=5
        )
    else:
        # Simple file handler
        file_handler = logging.FileHandler(log_dir / "guardia_ai.log")
    
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Error log handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=20*1024*1024,  # 20MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    loggers = {}
    
    # Application logger
    app_logger = logging.getLogger("guardia_ai")
    app_logger.setLevel(numeric_level)
    loggers["app"] = app_logger
    
    # Database logger
    db_logger = logging.getLogger("guardia_ai.db")
    db_logger.setLevel(numeric_level)
    loggers["db"] = db_logger
    
    # API logger
    api_logger = logging.getLogger("guardia_ai.api")
    api_logger.setLevel(numeric_level)
    loggers["api"] = api_logger
    
    # Surveillance logger
    surveillance_logger = logging.getLogger("guardia_ai.surveillance")
    surveillance_logger.setLevel(numeric_level)
    loggers["surveillance"] = surveillance_logger
    
    # AI/ML logger
    ai_logger = logging.getLogger("guardia_ai.ai")
    ai_logger.setLevel(numeric_level)
    loggers["ai"] = ai_logger
    
    # Security logger
    security_logger = SecurityEventLogger(log_dir / "security_events.log")
    loggers["security"] = security_logger
    
    # Performance logger
    performance_logger = PerformanceLogger(log_dir / "performance.log")
    loggers["performance"] = performance_logger
    
    logging.info(f"Logging configured - Level: {log_level}, Directory: {log_directory}")
    
    return loggers

def log_function_call(func):
    """Decorator to log function calls with performance metrics"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.utcnow()
        
        try:
            logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
            result = func(*args, **kwargs)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            logger.debug(
                f"Function {func.__name__} completed",
                extra={"performance_metrics": {"execution_time_ms": execution_time * 1000}}
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            logger.error(
                f"Function {func.__name__} failed",
                extra={
                    "performance_metrics": {"execution_time_ms": execution_time * 1000},
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    return wrapper

async def log_async_function_call(func):
    """Decorator to log async function calls with performance metrics"""
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.utcnow()
        
        try:
            logger.debug(f"Calling async {func.__name__} with args={args}, kwargs={kwargs}")
            result = await func(*args, **kwargs)
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            logger.debug(
                f"Async function {func.__name__} completed",
                extra={"performance_metrics": {"execution_time_ms": execution_time * 1000}}
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            logger.error(
                f"Async function {func.__name__} failed",
                extra={
                    "performance_metrics": {"execution_time_ms": execution_time * 1000},
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    return wrapper

def get_logger(name: str) -> logging.Logger:
    """Get logger instance with standard configuration"""
    return logging.getLogger(f"guardia_ai.{name}")

# Global loggers for easy access
security_logger = None
performance_logger = None

def init_global_loggers(log_directory: str = "logs"):
    """Initialize global logger instances"""
    global security_logger, performance_logger
    
    log_dir = Path(log_directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    security_logger = SecurityEventLogger(log_dir / "security_events.log")
    performance_logger = PerformanceLogger(log_dir / "performance.log")
