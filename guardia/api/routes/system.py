"""
System API routes for Guardia AI Enhanced System

This module provides endpoints for system management including:
- System health and status monitoring
- Configuration management
- Logging and debugging
- Performance metrics and analytics
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
import psutil
import logging
import asyncio
from pathlib import Path

from ...models.schemas import (
    SystemHealth,
    SystemConfiguration,
    SystemLog,
    PerformanceMetrics,
    CameraConfiguration,
    DatabaseStatus,
    UserActivity
)
from ...config.settings import get_settings
from ...services.surveillance_service import SurveillanceService
from ...services.user_service import UserService
from ...services.alert_service import AlertService
from ...db.connection import get_database_status
from ..dependencies import get_current_user, get_admin_user, get_surveillance_service

router = APIRouter(prefix="/system", tags=["system"])
logger = logging.getLogger(__name__)
settings = get_settings()

@router.get("/health", response_model=SystemHealth)
async def get_system_health(
    include_details: bool = Query(False),
    current_user: dict = Depends(get_current_user)
):
    """
    Get system health status
    
    - Returns overall system status and component health
    - Includes optional detailed metrics
    - Available to all authenticated users
    """
    try:
        # Get basic system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Check database connection
        try:
            db_status = await get_database_status()
            database_healthy = db_status.get("connected", False)
        except Exception:
            database_healthy = False
        
        # Basic health status
        health_status = {
            "status": "healthy" if cpu_percent < 80 and memory.percent < 85 and database_healthy else "degraded",
            "timestamp": datetime.utcnow(),
            "uptime_seconds": int((datetime.utcnow() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()),
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "disk_usage_percent": disk.percent,
            "database_connected": database_healthy,
            "active_sessions": 0,  # Will be populated by surveillance service
            "version": settings.app_version
        }
        
        if include_details:
            # Add detailed metrics for admin users or system monitoring
            health_status.update({
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_available_gb": round(memory.available / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                "network_connections": len(psutil.net_connections()),
                "process_count": len(psutil.pids())
            })
        
        return SystemHealth(**health_status)
        
    except Exception as e:
        logger.error(f"Failed to get system health: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )

@router.get("/status")
async def get_system_status(current_user: dict = Depends(get_current_user)):
    """
    Get simplified system status for quick health checks
    
    - Lightweight endpoint for monitoring and frontend status indicators
    - Returns basic OK/ERROR status with minimal details
    """
    try:
        # Quick health checks
        cpu_ok = psutil.cpu_percent(interval=0.1) < 90
        memory_ok = psutil.virtual_memory().percent < 90
        
        try:
            db_status = await get_database_status()
            db_ok = db_status.get("connected", False)
        except Exception:
            db_ok = False
        
        overall_status = "ok" if all([cpu_ok, memory_ok, db_ok]) else "error"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "cpu": "ok" if cpu_ok else "high_usage",
                "memory": "ok" if memory_ok else "high_usage", 
                "database": "ok" if db_ok else "disconnected"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get system status: {str(e)}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(
    period_hours: int = Query(24, ge=1, le=168),  # Last 24 hours by default, max 1 week
    current_user: dict = Depends(get_admin_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """
    Get detailed performance metrics (admin only)
    
    - Returns comprehensive system performance data
    - Includes detection rates, processing times, error rates
    - Available only to admin users
    """
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=period_hours)
        
        # Collect performance metrics
        metrics = await surveillance_service.get_performance_metrics(
            start_time=start_time,
            end_time=end_time
        )
        
        # Add current system metrics
        metrics.update({
            "current_cpu_percent": psutil.cpu_percent(interval=1),
            "current_memory_percent": psutil.virtual_memory().percent,
            "current_disk_percent": psutil.disk_usage('/').percent,
            "active_processes": len(psutil.pids()),
            "network_io": psutil.net_io_counters()._asdict(),
            "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}
        })
        
        return PerformanceMetrics(**metrics)
        
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )

@router.get("/configuration", response_model=SystemConfiguration)
async def get_system_configuration(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get system configuration (admin only)
    
    - Returns current system settings and parameters
    - Excludes sensitive values like secrets and passwords
    - Available only to admin users
    """
    try:
        # Get configuration from settings, excluding sensitive data
        config_dict = settings.dict()
        
        # Remove sensitive information
        sensitive_keys = [
            'secret_key', 'mongodb_url', 'smtp_password', 
            'twilio_auth_token', 'google_service_account_key', 'google_client_secret',
            'google_refresh_token', 'sendgrid_api_key', 'redis_password'
        ]
        
        for key in sensitive_keys:
            if key in config_dict:
                config_dict[key] = "***REDACTED***"
        
        # Add runtime configuration
        config_dict.update({
            "python_version": f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
            "platform": psutil.sys.platform,
            "cpu_count": psutil.cpu_count(),
            "total_memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_space_gb": round(psutil.disk_usage('/').total / (1024**3), 2)
        })
        
        return SystemConfiguration(**config_dict)
        
    except Exception as e:
        logger.error(f"Failed to get system configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system configuration: {str(e)}"
        )

@router.get("/logs", response_model=List[SystemLog])
async def get_system_logs(
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_admin_user)
):
    """
    Get system logs (admin only)
    
    - Returns filtered system logs for debugging and monitoring
    - Supports filtering by level, time range, and text search
    - Available only to admin users
    """
    try:
        # This is a simplified implementation
        # In a production system, you'd want to use a proper log aggregation system
        logs = []
        
        log_file_path = Path(settings.log_directory) / "guardia_ai.log"
        
        if log_file_path.exists():
            # Read and parse log file (simplified)
            with open(log_file_path, 'r') as f:
                lines = f.readlines()
                
            # Parse last N lines based on limit
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            for line in recent_lines:
                try:
                    # Simple log parsing - in production use proper log parsing
                    if level and level not in line:
                        continue
                    if search and search.lower() not in line.lower():
                        continue
                        
                    # Extract timestamp, level, and message (simplified)
                    parts = line.strip().split(' - ', 2)
                    if len(parts) >= 3:
                        timestamp_str = parts[0]
                        log_level = parts[1]
                        message = parts[2]
                        
                        logs.append(SystemLog(
                            timestamp=datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')),
                            level=log_level,
                            message=message,
                            source="guardia_ai",
                            module="unknown"
                        ))
                except Exception:
                    # Skip malformed log lines
                    continue
        
        # Filter by time range if specified
        if start_time:
            logs = [log for log in logs if log.timestamp >= start_time]
        if end_time:
            logs = [log for log in logs if log.timestamp <= end_time]
        
        # Sort by timestamp descending
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        return logs[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get system logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system logs: {str(e)}"
        )

@router.get("/cameras/config", response_model=List[CameraConfiguration])
async def get_camera_configurations(
    current_user: dict = Depends(get_admin_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """
    Get camera configurations (admin only)
    
    - Returns configuration for all system cameras
    - Includes connection status and capabilities
    - Available only to admin users
    """
    try:
        configurations = await surveillance_service.get_all_camera_configurations()
        return configurations
        
    except Exception as e:
        logger.error(f"Failed to get camera configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get camera configurations: {str(e)}"
        )

@router.post("/cameras/test")
async def test_camera_connection(
    camera_config: CameraConfiguration,
    current_user: dict = Depends(get_admin_user),
    surveillance_service: SurveillanceService = Depends(get_surveillance_service)
):
    """
    Test camera connection with provided configuration (admin only)
    
    - Validates camera connection and capabilities
    - Returns connection status and error details
    - Available only to admin users
    """
    try:
        test_result = await surveillance_service.test_camera_connection(camera_config)
        
        return {
            "success": test_result["success"],
            "message": test_result["message"],
            "details": test_result.get("details", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to test camera connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test camera connection: {str(e)}"
        )

@router.get("/users/activity", response_model=List[UserActivity])
async def get_user_activity(
    limit: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    current_user: dict = Depends(get_admin_user),
    user_service: UserService = Depends(get_surveillance_service)
):
    """
    Get user activity logs (admin only)
    
    - Returns recent user activity across the system
    - Supports filtering by user and activity type
    - Available only to admin users
    """
    try:
        activities = await user_service.get_user_activities(
            limit=limit,
            user_id=user_id,
            activity_type=activity_type
        )
        
        return activities
        
    except Exception as e:
        logger.error(f"Failed to get user activity: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user activity: {str(e)}"
        )

@router.post("/maintenance/cleanup")
async def perform_system_cleanup(
    background_tasks: BackgroundTasks,
    cleanup_logs: bool = Query(True),
    cleanup_recordings: bool = Query(False),
    cleanup_temp_files: bool = Query(True),
    days_to_keep: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_admin_user)
):
    """
    Perform system cleanup tasks (admin only)
    
    - Cleans up old logs, recordings, and temporary files
    - Runs in background to avoid blocking the request
    - Available only to admin users
    """
    try:
        async def cleanup_task():
            """Background task for system cleanup"""
            try:
                cleanup_results = {
                    "logs_cleaned": 0,
                    "recordings_cleaned": 0,
                    "temp_files_cleaned": 0,
                    "space_freed_mb": 0
                }
                
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
                
                if cleanup_logs:
                    # Clean up old log files
                    log_dir = Path(settings.log_directory)
                    if log_dir.exists():
                        for log_file in log_dir.glob("*.log*"):
                            if log_file.stat().st_mtime < cutoff_date.timestamp():
                                size = log_file.stat().st_size
                                log_file.unlink()
                                cleanup_results["logs_cleaned"] += 1
                                cleanup_results["space_freed_mb"] += size / (1024*1024)
                
                if cleanup_recordings:
                    # Clean up old recordings
                    recordings_dir = Path(settings.recordings_directory)
                    if recordings_dir.exists():
                        for recording_file in recordings_dir.glob("**/*"):
                            if recording_file.is_file() and recording_file.stat().st_mtime < cutoff_date.timestamp():
                                size = recording_file.stat().st_size
                                recording_file.unlink()
                                cleanup_results["recordings_cleaned"] += 1
                                cleanup_results["space_freed_mb"] += size / (1024*1024)
                
                if cleanup_temp_files:
                    # Clean up temporary files
                    temp_dir = Path("/tmp/guardia_ai")
                    if temp_dir.exists():
                        for temp_file in temp_dir.glob("**/*"):
                            if temp_file.is_file():
                                size = temp_file.stat().st_size
                                temp_file.unlink()
                                cleanup_results["temp_files_cleaned"] += 1
                                cleanup_results["space_freed_mb"] += size / (1024*1024)
                
                logger.info(f"System cleanup completed: {cleanup_results}")
                
            except Exception as e:
                logger.error(f"System cleanup failed: {str(e)}")
        
        # Add cleanup task to background tasks
        background_tasks.add_task(cleanup_task)
        
        return {
            "message": "System cleanup initiated",
            "task_id": "cleanup_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            "estimated_duration_minutes": 5,
            "cleanup_options": {
                "cleanup_logs": cleanup_logs,
                "cleanup_recordings": cleanup_recordings,
                "cleanup_temp_files": cleanup_temp_files,
                "days_to_keep": days_to_keep
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to initiate system cleanup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate system cleanup: {str(e)}"
        )

@router.post("/restart")
async def restart_system(
    component: str = Query("all", regex="^(all|surveillance|api|database)$"),
    current_user: dict = Depends(get_admin_user)
):
    """
    Restart system components (admin only)
    
    - Allows restarting specific system components or entire system
    - Returns restart status and estimated downtime
    - Available only to admin users
    """
    try:
        # This is a placeholder for restart functionality
        # In a production system, this would integrate with process managers
        # like systemd, Docker, or Kubernetes
        
        restart_info = {
            "component": component,
            "status": "initiated",
            "timestamp": datetime.utcnow().isoformat(),
            "estimated_downtime_seconds": 30 if component != "all" else 60,
            "message": f"Restart of {component} component(s) initiated"
        }
        
        logger.warning(f"System restart initiated by user {current_user['user_id']} for component: {component}")
        
        # In a real implementation, you would:
        # 1. Gracefully shutdown the specified component(s)
        # 2. Save current state and close connections
        # 3. Restart the service(s)
        # 4. Verify successful restart
        
        return restart_info
        
    except Exception as e:
        logger.error(f"Failed to restart system: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart system: {str(e)}"
        )

@router.get("/database/status", response_model=DatabaseStatus)
async def get_database_status_detailed(
    current_user: dict = Depends(get_admin_user)
):
    """
    Get detailed database status (admin only)
    
    - Returns comprehensive database health and performance metrics
    - Includes connection pool status and query performance
    - Available only to admin users
    """
    try:
        db_status = await get_database_status()
        
        # Add additional database metrics
        db_status.update({
            "timestamp": datetime.utcnow(),
            "configuration": {
                "host": settings.database_host,
                "port": settings.database_port,
                "name": settings.database_name,
                "ssl_enabled": settings.database_ssl
            }
        })
        
        return DatabaseStatus(**db_status)
        
    except Exception as e:
        logger.error(f"Failed to get database status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database status: {str(e)}"
        )
