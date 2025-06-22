"""
Alerts API routes for Guardia AI Enhanced System

This module provides endpoints for alert management including:
- Creating and managing alerts
- Alert history and statistics
- Notification preferences
- Alert rule configuration
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
import logging

from ...models.schemas import (
    Alert,
    AlertCreate,
    AlertUpdate,
    AlertRule,
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertStatistics,
    NotificationPreferences,
    NotificationPreferencesUpdate
)
from ...services.alert_service import AlertService
from ...services.notification_service import NotificationService
from ..dependencies import get_current_user, get_alert_service, get_notification_service

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=Alert)
async def create_alert(
    alert_data: AlertCreate,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Create a new alert
    
    - Creates alert based on detection event or manual trigger
    - Applies alert rules and cooldown periods
    - Triggers notifications based on user preferences
    """
    try:
        alert = await alert_service.create_alert(
            user_id=current_user["user_id"],
            alert_data=alert_data
        )
        
        logger.info(f"Created alert {alert.alert_id} for user {current_user['user_id']}")
        return alert
        
    except Exception as e:
        logger.error(f"Failed to create alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}"
        )

@router.get("/", response_model=List[Alert])
async def get_alerts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    status: Optional[str] = Query(None, regex="^(active|acknowledged|resolved|dismissed)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    camera_id: Optional[str] = None,
    detection_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Get alerts for the current user with filtering options
    
    - Supports pagination with limit/offset
    - Filter by severity, status, date range
    - Filter by camera or detection type
    - Returns alerts in descending order by timestamp
    """
    try:
        filters = {
            "user_id": current_user["user_id"],
            "severity": severity,
            "status": status,
            "start_date": start_date,
            "end_date": end_date,
            "camera_id": camera_id,
            "detection_type": detection_type
        }
        
        # Remove None values from filters
        filters = {k: v for k, v in filters.items() if v is not None}
        
        alerts = await alert_service.get_alerts(
            filters=filters,
            limit=limit,
            offset=offset
        )
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )

@router.get("/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Get specific alert details"""
    try:
        alert = await alert_service.get_alert(alert_id)
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Verify user owns this alert
        if alert.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this alert"
            )
        
        return alert
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert: {str(e)}"
        )

@router.put("/{alert_id}", response_model=Alert)
async def update_alert(
    alert_id: str,
    update_data: AlertUpdate,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Update alert status or details
    
    - Allows acknowledging, resolving, or dismissing alerts
    - Updates alert metadata and tracking information
    - Logs status changes for audit trail
    """
    try:
        alert = await alert_service.update_alert(
            alert_id=alert_id,
            user_id=current_user["user_id"],
            update_data=update_data
        )
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        logger.info(f"Updated alert {alert_id} for user {current_user['user_id']}")
        return alert
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert: {str(e)}"
        )

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Soft delete alert (mark as deleted)"""
    try:
        success = await alert_service.delete_alert(
            alert_id=alert_id,
            user_id=current_user["user_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        logger.info(f"Deleted alert {alert_id} for user {current_user['user_id']}")
        return {"message": "Alert deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert: {str(e)}"
        )

@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Acknowledge an alert (mark as seen/reviewed)"""
    try:
        alert = await alert_service.acknowledge_alert(
            alert_id=alert_id,
            user_id=current_user["user_id"]
        )
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        logger.info(f"Acknowledged alert {alert_id} for user {current_user['user_id']}")
        return {"message": "Alert acknowledged successfully", "alert": alert}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}"
        )

@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    resolution_notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Resolve an alert (mark as handled/closed)"""
    try:
        alert = await alert_service.resolve_alert(
            alert_id=alert_id,
            user_id=current_user["user_id"],
            resolution_notes=resolution_notes
        )
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        logger.info(f"Resolved alert {alert_id} for user {current_user['user_id']}")
        return {"message": "Alert resolved successfully", "alert": alert}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}"
        )

@router.get("/statistics/summary", response_model=AlertStatistics)
async def get_alert_statistics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Get alert statistics for the user
    
    - Provides summary of alerts over specified time period
    - Includes counts by severity, status, and type
    - Shows trends and patterns in alert activity
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        statistics = await alert_service.get_alert_statistics(
            user_id=current_user["user_id"],
            start_date=start_date,
            end_date=end_date
        )
        
        return statistics
        
    except Exception as e:
        logger.error(f"Failed to get alert statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert statistics: {str(e)}"
        )

# Alert Rules Management

@router.post("/rules", response_model=AlertRule)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """
    Create a new alert rule
    
    - Defines conditions for automatic alert generation
    - Configures severity levels and thresholds
    - Sets up notification preferences for rule
    """
    try:
        rule = await alert_service.create_alert_rule(
            user_id=current_user["user_id"],
            rule_data=rule_data
        )
        
        logger.info(f"Created alert rule {rule.rule_id} for user {current_user['user_id']}")
        return rule
        
    except Exception as e:
        logger.error(f"Failed to create alert rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert rule: {str(e)}"
        )

@router.get("/rules", response_model=List[AlertRule])
async def get_alert_rules(
    active_only: bool = Query(False),
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Get alert rules for the current user"""
    try:
        rules = await alert_service.get_user_alert_rules(
            user_id=current_user["user_id"],
            active_only=active_only
        )
        
        return rules
        
    except Exception as e:
        logger.error(f"Failed to get alert rules: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert rules: {str(e)}"
        )

@router.get("/rules/{rule_id}", response_model=AlertRule)
async def get_alert_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Get specific alert rule details"""
    try:
        rule = await alert_service.get_alert_rule(rule_id)
        
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )
        
        # Verify user owns this rule
        if rule.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this alert rule"
            )
        
        return rule
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert rule: {str(e)}"
        )

@router.put("/rules/{rule_id}", response_model=AlertRule)
async def update_alert_rule(
    rule_id: str,
    update_data: AlertRuleUpdate,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Update alert rule configuration"""
    try:
        rule = await alert_service.update_alert_rule(
            rule_id=rule_id,
            user_id=current_user["user_id"],
            update_data=update_data
        )
        
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )
        
        logger.info(f"Updated alert rule {rule_id} for user {current_user['user_id']}")
        return rule
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update alert rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert rule: {str(e)}"
        )

@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Delete alert rule"""
    try:
        success = await alert_service.delete_alert_rule(
            rule_id=rule_id,
            user_id=current_user["user_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert rule not found"
            )
        
        logger.info(f"Deleted alert rule {rule_id} for user {current_user['user_id']}")
        return {"message": "Alert rule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete alert rule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert rule: {str(e)}"
        )

# Notification Preferences

@router.get("/notifications/preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """Get user's notification preferences for alerts"""
    try:
        preferences = await notification_service.get_user_preferences(
            user_id=current_user["user_id"]
        )
        
        return preferences
        
    except Exception as e:
        logger.error(f"Failed to get notification preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification preferences: {str(e)}"
        )

@router.put("/notifications/preferences", response_model=NotificationPreferences)
async def update_notification_preferences(
    preferences_data: NotificationPreferencesUpdate,
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Update user's notification preferences
    
    - Configure email, SMS, and push notification settings
    - Set delivery preferences for different alert severities
    - Manage quiet hours and notification scheduling
    """
    try:
        preferences = await notification_service.update_user_preferences(
            user_id=current_user["user_id"],
            preferences_data=preferences_data
        )
        
        logger.info(f"Updated notification preferences for user {current_user['user_id']}")
        return preferences
        
    except Exception as e:
        logger.error(f"Failed to update notification preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update notification preferences: {str(e)}"
        )

@router.post("/notifications/test")
async def test_notification(
    notification_type: str = Query(..., regex="^(email|sms|push|webhook)$"),
    current_user: dict = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service)
):
    """
    Send a test notification to verify configuration
    
    - Tests specific notification channel
    - Verifies delivery configuration and credentials
    - Returns delivery status and any errors
    """
    try:
        result = await notification_service.send_test_notification(
            user_id=current_user["user_id"],
            notification_type=notification_type
        )
        
        logger.info(f"Sent test {notification_type} notification for user {current_user['user_id']}")
        return {
            "message": f"Test {notification_type} notification sent",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to send test notification: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test notification: {str(e)}"
        )

@router.post("/batch/acknowledge")
async def batch_acknowledge_alerts(
    alert_ids: List[str],
    current_user: dict = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
):
    """Acknowledge multiple alerts in batch operation"""
    try:
        results = await alert_service.batch_acknowledge_alerts(
            alert_ids=alert_ids,
            user_id=current_user["user_id"]
        )
        
        success_count = sum(1 for r in results if r["success"])
        logger.info(f"Batch acknowledged {success_count}/{len(alert_ids)} alerts for user {current_user['user_id']}")
        
        return {
            "message": f"Acknowledged {success_count}/{len(alert_ids)} alerts",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to batch acknowledge alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch acknowledge alerts: {str(e)}"
        )
