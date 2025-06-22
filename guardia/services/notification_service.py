"""
Notification Service
Handles various types of notifications (email, SMS, push)
"""
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import json

# Optional imports for different notification services
try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from ..config.settings import settings
from ..models.schemas import User, NotificationSettings

class NotificationService:
    """Service for sending various types of notifications"""
    
    def __init__(self):
        self.twilio_client = None
        self.email_enabled = settings.enable_email_alerts
        self.sms_enabled = settings.enable_sms_alerts and TWILIO_AVAILABLE
        self.push_enabled = settings.enable_push_notifications
        
        # Initialize Twilio if available and configured
        if self.sms_enabled and settings.twilio_account_sid and settings.twilio_auth_token:
            try:
                self.twilio_client = TwilioClient(
                    settings.twilio_account_sid,
                    settings.twilio_auth_token
                )
                logger.info("✅ Twilio SMS service initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio: {e}")
                self.sms_enabled = False
    
    async def send_email_notification(self, user_id: str, subject: str, 
                                    notification_data: Dict[str, Any]) -> bool:
        """Send email notification"""
        if not self.email_enabled:
            return False
        
        try:
            # Get user email (you would fetch this from user service)
            # For now, using a placeholder
            user_email = await self._get_user_email(user_id)
            if not user_email:
                logger.warning(f"No email found for user {user_id}")
                return False
            
            # Create email content
            html_content = self._create_email_html(notification_data)
            text_content = self._create_email_text(notification_data)
            
            # Send email in background task
            asyncio.create_task(self._send_email_async(
                user_email, subject, text_content, html_content
            ))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    async def _send_email_async(self, to_email: str, subject: str, 
                              text_content: str, html_content: str):
        """Send email asynchronously"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.email_from or settings.smtp_username
            msg['To'] = to_email
            
            # Add text and HTML parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"✅ Email sent to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    def _create_email_html(self, data: Dict[str, Any]) -> str:
        """Create HTML email content"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #ff4444; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .details {{ background-color: #f5f5f5; padding: 15px; margin: 10px 0; }}
                .timestamp {{ color: #666; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🛡️ Guardia AI Security Alert</h1>
            </div>
            <div class="content">
                <h2>{data.get('message', 'Security Alert')}</h2>
                <div class="details">
                    <p><strong>Detection Type:</strong> {data.get('detection_type', 'Unknown')}</p>
                    <p><strong>Priority:</strong> {data.get('priority', 'Medium')}</p>
                    <p><strong>Camera:</strong> {data.get('camera_id', 'Unknown')}</p>
                    <p class="timestamp"><strong>Time:</strong> {data.get('timestamp', 'Unknown')}</p>
                </div>
                <p>Please check your Guardia AI system for more details and take appropriate action.</p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _create_email_text(self, data: Dict[str, Any]) -> str:
        """Create plain text email content"""
        text = f"""
        GUARDIA AI SECURITY ALERT
        
        {data.get('message', 'Security Alert')}
        
        Details:
        - Detection Type: {data.get('detection_type', 'Unknown')}
        - Priority: {data.get('priority', 'Medium')}
        - Camera: {data.get('camera_id', 'Unknown')}
        - Time: {data.get('timestamp', 'Unknown')}
        
        Please check your Guardia AI system for more details.
        """
        return text
    
    async def send_sms_notification(self, user_id: str, message: str, 
                                  notification_data: Dict[str, Any]) -> bool:
        """Send SMS notification"""
        if not self.sms_enabled or not self.twilio_client:
            return False
        
        try:
            # Get user phone number
            user_phone = await self._get_user_phone(user_id)
            if not user_phone:
                logger.warning(f"No phone number found for user {user_id}")
                return False
            
            # Send SMS
            asyncio.create_task(self._send_sms_async(user_phone, message))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            return False
    
    async def _send_sms_async(self, to_phone: str, message: str):
        """Send SMS asynchronously"""
        try:
            # Truncate message if too long
            if len(message) > 160:
                message = message[:157] + "..."
            
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=settings.twilio_phone_number,
                to=to_phone
            )
            
            logger.info(f"✅ SMS sent to {to_phone}: {message_obj.sid}")
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
    
    async def send_push_notification(self, user_id: str, title: str, 
                                   message: str, data: Dict[str, Any]) -> bool:
        """Send push notification"""
        if not self.push_enabled:
            return False
        
        try:
            # For now, we'll implement a simple webhook-based push notification
            # In a real implementation, you would use Firebase, Apple Push, etc.
            
            notification_payload = {
                "user_id": user_id,
                "title": title,
                "message": message,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to websocket clients (implemented in API layer)
            asyncio.create_task(self._send_websocket_notification(notification_payload))
            
            logger.info(f"✅ Push notification sent to user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False
    
    async def _send_websocket_notification(self, payload: Dict[str, Any]):
        """Send notification via WebSocket (placeholder implementation)"""
        try:
            # This would integrate with your WebSocket manager
            # For now, just log the notification
            logger.info(f"WebSocket notification: {json.dumps(payload, indent=2)}")
            
        except Exception as e:
            logger.error(f"WebSocket notification error: {e}")
    
    async def send_batch_notifications(self, notifications: List[Dict[str, Any]]) -> Dict[str, int]:
        """Send multiple notifications in batch"""
        results = {"email": 0, "sms": 0, "push": 0}
        
        tasks = []
        for notification in notifications:
            user_id = notification.get("user_id")
            notification_type = notification.get("type")
            
            if notification_type == "email":
                task = self.send_email_notification(
                    user_id,
                    notification.get("subject", "Notification"),
                    notification.get("data", {})
                )
                tasks.append(("email", task))
                
            elif notification_type == "sms":
                task = self.send_sms_notification(
                    user_id,
                    notification.get("message", ""),
                    notification.get("data", {})
                )
                tasks.append(("sms", task))
                
            elif notification_type == "push":
                task = self.send_push_notification(
                    user_id,
                    notification.get("title", "Notification"),
                    notification.get("message", ""),
                    notification.get("data", {})
                )
                tasks.append(("push", task))
        
        # Execute all tasks
        for notification_type, task in tasks:
            try:
                success = await task
                if success:
                    results[notification_type] += 1
            except Exception as e:
                logger.error(f"Batch notification error ({notification_type}): {e}")
        
        return results
    
    async def _get_user_email(self, user_id: str) -> Optional[str]:
        """Get user email address"""
        # Placeholder - would integrate with user service
        # return await user_service.get_user_email(user_id)
        return "user@example.com"  # Placeholder
    
    async def _get_user_phone(self, user_id: str) -> Optional[str]:
        """Get user phone number"""
        # Placeholder - would integrate with user service
        # return await user_service.get_user_phone(user_id)
        return None  # Placeholder
    
    async def test_notification_channels(self, user_id: str) -> Dict[str, bool]:
        """Test all notification channels for a user"""
        results = {}
        
        # Test email
        if self.email_enabled:
            results["email"] = await self.send_email_notification(
                user_id, 
                "Guardia AI Test Notification",
                {
                    "message": "This is a test notification",
                    "detection_type": "test",
                    "priority": "low",
                    "camera_id": "test_camera",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Test SMS
        if self.sms_enabled:
            results["sms"] = await self.send_sms_notification(
                user_id,
                "Guardia AI test notification",
                {"test": True}
            )
        
        # Test push
        if self.push_enabled:
            results["push"] = await self.send_push_notification(
                user_id,
                "Test Notification",
                "This is a test from Guardia AI",
                {"test": True}
            )
        
        return results
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification service statistics"""
        return {
            "email_enabled": self.email_enabled,
            "sms_enabled": self.sms_enabled, 
            "push_enabled": self.push_enabled,
            "twilio_configured": self.twilio_client is not None,
            "smtp_configured": bool(settings.smtp_username and settings.smtp_password)
        }
