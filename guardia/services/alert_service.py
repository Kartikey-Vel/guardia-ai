"""
Alert Management Service
Handles alert generation, notification, and management
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import json

from ..models.schemas import (
    Alert, AlertCreate, AlertStatus, DetectionType, 
    PriorityLevel, User, NotificationSettings
)
from ..db.repository import BaseRepository
from ..config.settings import settings, DETECTION_CONFIG
from .notification_service import NotificationService

class AlertRepository(BaseRepository[Alert]):
    """Repository for alert operations"""
    
    def __init__(self):
        super().__init__("alerts", Alert)
    
    async def get_by_user(self, user_id: str, status: Optional[AlertStatus] = None) -> List[Alert]:
        """Get alerts for a user, optionally filtered by status"""
        filter_dict = {"user_id": user_id}
        if status:
            filter_dict["status"] = status
        
        return await self.find_many(filter_dict, sort_by="created_at", sort_order=-1)
    
    async def get_recent_alerts(self, user_id: str, hours: int = 24) -> List[Alert]:
        """Get recent alerts within specified hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filter_dict = {
            "user_id": user_id,
            "created_at": {"$gte": cutoff_time}
        }
        
        return await self.find_many(filter_dict, sort_by="created_at", sort_order=-1)
    
    async def get_by_priority(self, priority: PriorityLevel, limit: int = 50) -> List[Alert]:
        """Get alerts by priority level"""
        return await self.find_many(
            {"priority": priority}, 
            limit=limit, 
            sort_by="created_at", 
            sort_order=-1
        )
    
    async def update_status(self, alert_id: str, status: AlertStatus, acknowledged_by: Optional[str] = None):
        """Update alert status"""
        update_data = {"status": status}
        
        if status == AlertStatus.ACKNOWLEDGED:
            update_data["acknowledged_at"] = datetime.utcnow()
            if acknowledged_by:
                update_data["acknowledged_by"] = acknowledged_by
        elif status == AlertStatus.RESOLVED:
            update_data["resolved_at"] = datetime.utcnow()
        
        await self.update(alert_id, update_data)

class AlertService:
    """Service for managing alerts and notifications"""
    
    def __init__(self):
        self.alert_repo = AlertRepository()
        self.notification_service = NotificationService()
        self.alert_cooldowns: Dict[str, datetime] = {}  # Prevent spam
        self.active_alerts: Dict[str, Alert] = {}  # Track active alerts
    
    async def create_alert(self, alert_data: AlertCreate) -> Alert:
        """Create a new alert"""
        try:
            # Check alert cooldown to prevent spam
            cooldown_key = f"{alert_data.user_id}_{alert_data.detection_type}_{alert_data.camera_id}"
            
            if self._is_in_cooldown(cooldown_key):
                logger.debug(f"Alert in cooldown: {cooldown_key}")
                return None
            
            # Set cooldown
            self.alert_cooldowns[cooldown_key] = datetime.utcnow()
            
            # Create alert
            alert = Alert(**alert_data.dict())
            created_alert = await self.alert_repo.create(alert)
            
            # Store as active alert
            self.active_alerts[str(created_alert.id)] = created_alert
            
            # Send notifications based on priority
            await self._send_alert_notifications(created_alert)
            
            logger.info(f"🚨 Alert created: {created_alert.detection_type} (Priority: {created_alert.priority})")
            return created_alert
            
        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            raise
    
    def _is_in_cooldown(self, cooldown_key: str) -> bool:
        """Check if alert type is in cooldown period"""
        if cooldown_key not in self.alert_cooldowns:
            return False
        
        last_alert = self.alert_cooldowns[cooldown_key]
        cooldown_period = timedelta(seconds=settings.alert_cooldown_seconds)
        
        return datetime.utcnow() - last_alert < cooldown_period
    
    async def _send_alert_notifications(self, alert: Alert):
        """Send notifications for the alert"""
        try:
            # Get detection configuration
            detection_config = DETECTION_CONFIG.get(alert.detection_type, {})
            notification_delay = detection_config.get("notification_delay", 0)
            
            # Apply delay if configured
            if notification_delay > 0:
                await asyncio.sleep(notification_delay)
            
            # Prepare notification data
            notification_data = {
                "alert_id": str(alert.id),
                "detection_type": alert.detection_type,
                "priority": alert.priority,
                "message": alert.message,
                "camera_id": alert.camera_id,
                "timestamp": alert.created_at.isoformat(),
                "photos": alert.photos,
                "videos": alert.videos
            }
            
            # Send notifications based on priority and user preferences
            if alert.priority in [PriorityLevel.HIGH, PriorityLevel.CRITICAL]:
                # High priority - send all enabled notifications
                await self.notification_service.send_email_notification(
                    alert.user_id, f"🚨 Security Alert: {alert.detection_type}", notification_data
                )
                
                await self.notification_service.send_push_notification(
                    alert.user_id, "Security Alert", alert.message, notification_data
                )
                
                if alert.priority == PriorityLevel.CRITICAL:
                    # Critical alerts also get SMS
                    await self.notification_service.send_sms_notification(
                        alert.user_id, f"CRITICAL ALERT: {alert.message}", notification_data
                    )
            else:
                # Medium/Low priority - push notification only
                await self.notification_service.send_push_notification(
                    alert.user_id, "Security Update", alert.message, notification_data
                )
            
        except Exception as e:
            logger.error(f"Failed to send alert notifications: {e}")
    
    async def get_user_alerts(self, user_id: str, status: Optional[AlertStatus] = None, 
                            limit: int = 50) -> List[Alert]:
        """Get alerts for a user"""
        return await self.alert_repo.get_by_user(user_id, status)
    
    async def get_recent_alerts(self, user_id: str, hours: int = 24) -> List[Alert]:
        """Get recent alerts"""
        return await self.alert_repo.get_recent_alerts(user_id, hours)
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            await self.alert_repo.update_status(
                alert_id, AlertStatus.ACKNOWLEDGED, acknowledged_by
            )
            
            # Remove from active alerts
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
            
            logger.info(f"✅ Alert acknowledged: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            await self.alert_repo.update_status(alert_id, AlertStatus.RESOLVED)
            
            # Remove from active alerts
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
            
            logger.info(f"✅ Alert resolved: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert: {e}")
            return False
    
    async def mark_false_positive(self, alert_id: str) -> bool:
        """Mark alert as false positive"""
        try:
            await self.alert_repo.update_status(alert_id, AlertStatus.FALSE_POSITIVE)
            
            # Remove from active alerts
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
            
            logger.info(f"✅ Alert marked as false positive: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark alert as false positive: {e}")
            return False
    
    async def get_alert_statistics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get alert statistics for a user"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all alerts in the period
            filter_dict = {
                "user_id": user_id,
                "created_at": {"$gte": cutoff_date}
            }
            
            alerts = await self.alert_repo.find_many(filter_dict, limit=1000)
            
            # Calculate statistics
            stats = {
                "total_alerts": len(alerts),
                "by_priority": {},
                "by_detection_type": {},
                "by_status": {},
                "by_day": {},
                "response_times": {
                    "avg_acknowledgment_time": 0.0,
                    "avg_resolution_time": 0.0
                }
            }
            
            acknowledgment_times = []
            resolution_times = []
            
            for alert in alerts:
                # Count by priority
                priority = alert.priority.value
                stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
                
                # Count by detection type
                det_type = alert.detection_type.value
                stats["by_detection_type"][det_type] = stats["by_detection_type"].get(det_type, 0) + 1
                
                # Count by status
                status = alert.status.value
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                
                # Count by day
                day_key = alert.created_at.strftime("%Y-%m-%d")
                stats["by_day"][day_key] = stats["by_day"].get(day_key, 0) + 1
                
                # Calculate response times
                if alert.acknowledged_at:
                    ack_time = (alert.acknowledged_at - alert.created_at).total_seconds()
                    acknowledgment_times.append(ack_time)
                
                if alert.resolved_at:
                    res_time = (alert.resolved_at - alert.created_at).total_seconds()
                    resolution_times.append(res_time)
            
            # Calculate average response times
            if acknowledgment_times:
                stats["response_times"]["avg_acknowledgment_time"] = sum(acknowledgment_times) / len(acknowledgment_times)
            
            if resolution_times:
                stats["response_times"]["avg_resolution_time"] = sum(resolution_times) / len(resolution_times)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}")
            return {}
    
    async def get_active_alerts(self) -> List[Alert]:
        """Get currently active (unresolved) alerts"""
        return list(self.active_alerts.values())
    
    async def cleanup_old_alerts(self, days: int = 90):
        """Cleanup old resolved alerts"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Find old resolved alerts
            old_alerts = await self.alert_repo.find_many({
                "status": {"$in": [AlertStatus.RESOLVED, AlertStatus.FALSE_POSITIVE]},
                "created_at": {"$lt": cutoff_date}
            }, limit=1000)
            
            # Delete old alerts
            deleted_count = 0
            for alert in old_alerts:
                if await self.alert_repo.delete(str(alert.id)):
                    deleted_count += 1
            
            logger.info(f"🧹 Cleaned up {deleted_count} old alerts")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old alerts: {e}")
            return 0
    
    async def handle_detection_result(self, user_id: str, detection_type: DetectionType, 
                                    camera_id: str, detection_data: Dict[str, Any],
                                    frame_id: str) -> Optional[Alert]:
        """Handle a detection result and create alert if necessary"""
        try:
            # Get detection configuration
            detection_config = DETECTION_CONFIG.get(detection_type, {})
            
            # Only create alerts for significant detections
            if detection_type in [DetectionType.KNOWN_PERSON]:
                # Don't create alerts for known persons (just log)
                logger.debug(f"Known person detected: {detection_data.get('person_name', 'Unknown')}")
                return None
            
            # Create alert message
            messages = {
                DetectionType.UNKNOWN_PERSON: "Unknown person detected",
                DetectionType.MASKED_PERSON: "Person with mask detected", 
                DetectionType.LOITERING: "Loitering behavior detected",
                DetectionType.MULTIPLE_UNKNOWN: "Multiple unknown persons detected",
                DetectionType.NIGHT_INTRUSION: "Night intrusion detected"
            }
            
            message = messages.get(detection_type, f"Detection: {detection_type}")
            
            # Create alert
            alert_data = AlertCreate(
                user_id=user_id,
                detection_type=detection_type,
                priority=detection_config.get("priority", PriorityLevel.MEDIUM),
                message=message,
                frame_id=frame_id,
                camera_id=camera_id,
                detection_data=detection_data
            )
            
            return await self.create_alert(alert_data)
            
        except Exception as e:
            logger.error(f"Failed to handle detection result: {e}")
            return None
