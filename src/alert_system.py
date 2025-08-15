"""
Advanced alerting and notification system for Guardia-AI.
Provides real-time alerts, email notifications, webhooks, and mobile push notifications.
"""

import time
import threading
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import os

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    THREAT_DETECTED = "threat_detected"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    LOITERING = "loitering"
    ZONE_BREACH = "zone_breach"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_ISSUE = "performance_issue"
    FACE_RECOGNITION = "face_recognition"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"

@dataclass
class Alert:
    """Alert data structure"""
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: float
    location: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'timestamp': self.timestamp,
            'location': self.location,
            'data': self.data,
            'image_path': self.image_path,
            'video_path': self.video_path,
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at
        }

@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    name: str
    enabled: bool = True
    min_severity: AlertSeverity = AlertSeverity.LOW
    rate_limit_minutes: int = 5  # Minimum time between notifications
    last_notification: float = 0.0

class EmailNotifier:
    """Email notification handler"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, 
                 password: str, from_email: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.enabled = True
    
    def send_alert(self, alert: Alert, to_emails: List[str]) -> bool:
        """Send alert via email"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = f"Guardia-AI Alert: {alert.title} [{alert.severity.value.upper()}]"
            
            # Create HTML body
            html_body = self._create_email_body(alert)
            msg.attach(MIMEText(html_body, 'html'))
            
            # Attach image if available
            if alert.image_path and os.path.exists(alert.image_path):
                try:
                    with open(alert.image_path, 'rb') as f:
                        img_data = f.read()
                    img = MIMEImage(img_data)
                    img.add_header('Content-Disposition', 'attachment', filename='alert_image.jpg')
                    msg.attach(img)
                except Exception as e:
                    logger.warning(f"Failed to attach image: {e}")
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent to {len(to_emails)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _create_email_body(self, alert: Alert) -> str:
        """Create HTML email body"""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107",
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }
        
        color = severity_colors.get(alert.severity, "#6c757d")
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(alert.timestamp))
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px;">
                <div style="background-color: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 24px;">Guardia-AI Security Alert</h1>
                    <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">Severity: {alert.severity.value.upper()}</p>
                </div>
                
                <div style="padding: 20px;">
                    <h2 style="color: {color}; margin-top: 0;">{alert.title}</h2>
                    <p style="font-size: 16px; margin: 15px 0;">{alert.message}</p>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #495057;">Alert Details</h3>
                        <p><strong>Type:</strong> {alert.type.value.replace('_', ' ').title()}</p>
                        <p><strong>Time:</strong> {timestamp_str}</p>
                        {"<p><strong>Location:</strong> " + alert.location + "</p>" if alert.location else ""}
                        <p><strong>Alert ID:</strong> {alert.id}</p>
                    </div>
                    
                    {"<div style='margin: 20px 0;'><h3>Additional Data</h3><pre style='background-color: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto;'>" + json.dumps(alert.data, indent=2) + "</pre></div>" if alert.data else ""}
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #6c757d;">
                        <p>This is an automated alert from Guardia-AI Security System.</p>
                        <p>To acknowledge this alert, please log into your dashboard.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html

class WebhookNotifier:
    """Webhook notification handler"""
    
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None,
                 timeout: int = 10):
        self.webhook_url = webhook_url
        self.headers = headers or {'Content-Type': 'application/json'}
        self.timeout = timeout
        self.enabled = True
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert via webhook"""
        try:
            payload = {
                'alert': alert.to_dict(),
                'system': 'guardia-ai',
                'timestamp': time.time()
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook alert sent successfully")
                return True
            else:
                logger.warning(f"Webhook returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
            return False

class SlackNotifier:
    """Slack notification handler"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.enabled = True
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert to Slack"""
        try:
            severity_colors = {
                AlertSeverity.LOW: "#28a745",
                AlertSeverity.MEDIUM: "#ffc107",
                AlertSeverity.HIGH: "#fd7e14",
                AlertSeverity.CRITICAL: "#dc3545"
            }
            
            color = severity_colors.get(alert.severity, "#6c757d")
            timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(alert.timestamp))
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 Guardia-AI Alert: {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value.upper(),
                                "short": True
                            },
                            {
                                "title": "Type",
                                "value": alert.type.value.replace('_', ' ').title(),
                                "short": True
                            },
                            {
                                "title": "Time",
                                "value": timestamp_str,
                                "short": True
                            },
                            {
                                "title": "Alert ID",
                                "value": alert.id,
                                "short": True
                            }
                        ],
                        "footer": "Guardia-AI Security System",
                        "ts": int(alert.timestamp)
                    }
                ]
            }
            
            if alert.location:
                payload["attachments"][0]["fields"].append({
                    "title": "Location",
                    "value": alert.location,
                    "short": True
                })
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Slack alert sent successfully")
                return True
            else:
                logger.warning(f"Slack returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

class AlertManager:
    """Main alert management system"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.channels: Dict[str, NotificationChannel] = {}
        self.notifiers: Dict[str, Any] = {}
        self.alert_callbacks: List[Callable] = []
        self.lock = threading.Lock()
        self.max_alerts = 1000
        
        # Load configuration from environment
        self._load_config()
        
        logger.info("Alert manager initialized")
    
    def _load_config(self):
        """Load notification configuration from environment"""
        # Email configuration
        smtp_server = os.getenv('GUARDIA_SMTP_SERVER')
        smtp_port = int(os.getenv('GUARDIA_SMTP_PORT', '587'))
        smtp_user = os.getenv('GUARDIA_SMTP_USER')
        smtp_pass = os.getenv('GUARDIA_SMTP_PASS')
        smtp_from = os.getenv('GUARDIA_SMTP_FROM')
        
        if all([smtp_server, smtp_user, smtp_pass, smtp_from]):
            # Cast to str (all() above ensures non-None)
            self.notifiers['email'] = EmailNotifier(
                str(smtp_server), smtp_port, str(smtp_user), str(smtp_pass), str(smtp_from)
            )
            self.channels['email'] = NotificationChannel(
                'email', 
                enabled=os.getenv('GUARDIA_EMAIL_ENABLED', '0') == '1',
                min_severity=AlertSeverity(os.getenv('GUARDIA_EMAIL_MIN_SEVERITY', 'medium'))
            )
        
        # Slack configuration
        slack_webhook = os.getenv('GUARDIA_SLACK_WEBHOOK')
        if slack_webhook:
            self.notifiers['slack'] = SlackNotifier(str(slack_webhook))
            self.channels['slack'] = NotificationChannel(
                'slack',
                enabled=os.getenv('GUARDIA_SLACK_ENABLED', '0') == '1',
                min_severity=AlertSeverity(os.getenv('GUARDIA_SLACK_MIN_SEVERITY', 'high'))
            )
        
        # Custom webhook configuration
        webhook_url = os.getenv('GUARDIA_WEBHOOK_URL')
        if webhook_url:
            headers = {}
            auth_header = os.getenv('GUARDIA_WEBHOOK_AUTH')
            if auth_header:
                headers['Authorization'] = auth_header
            
            self.notifiers['webhook'] = WebhookNotifier(str(webhook_url), headers)
            self.channels['webhook'] = NotificationChannel(
                'webhook',
                enabled=os.getenv('GUARDIA_WEBHOOK_ENABLED', '0') == '1',
                min_severity=AlertSeverity(os.getenv('GUARDIA_WEBHOOK_MIN_SEVERITY', 'medium'))
            )
    
    def create_alert(self, alert_type: AlertType, severity: AlertSeverity,
                    title: str, message: str, location: Optional[str] = None,
                    data: Optional[Dict[str, Any]] = None,
                    image_path: Optional[str] = None,
                    video_path: Optional[str] = None) -> Alert:
        """Create a new alert"""
        alert_id = f"{alert_type.value}_{int(time.time() * 1000)}"
        
        alert = Alert(
            id=alert_id,
            type=alert_type,
            severity=severity,
            title=title,
            message=message,
            timestamp=time.time(),
            location=location,
            data=data or {},
            image_path=image_path,
            video_path=video_path
        )
        
        with self.lock:
            self.alerts.append(alert)
            
            # Keep only most recent alerts
            if len(self.alerts) > self.max_alerts:
                self.alerts = self.alerts[-self.max_alerts:]
        
        # Send notifications
        threading.Thread(target=self._send_notifications, args=(alert,), daemon=True).start()
        
        # Call callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
        
        logger.info(f"Alert created: {alert.id} - {alert.title}")
        return alert
    
    def _send_notifications(self, alert: Alert):
        """Send notifications for alert"""
        current_time = time.time()
        
        for channel_name, channel in self.channels.items():
            if not channel.enabled:
                continue
            
            # Check severity threshold
            severity_levels = {
                AlertSeverity.LOW: 1,
                AlertSeverity.MEDIUM: 2,
                AlertSeverity.HIGH: 3,
                AlertSeverity.CRITICAL: 4
            }
            
            if severity_levels[alert.severity] < severity_levels[channel.min_severity]:
                continue
            
            # Check rate limiting
            time_since_last = current_time - channel.last_notification
            if time_since_last < (channel.rate_limit_minutes * 60):
                logger.debug(f"Rate limiting notification for channel {channel_name}")
                continue
            
            # Send notification
            notifier = self.notifiers.get(channel_name)
            if notifier and hasattr(notifier, 'send_alert'):
                try:
                    if channel_name == 'email':
                        # Get email addresses from environment
                        email_to = os.getenv('GUARDIA_EMAIL_TO', '').split(',')
                        email_to = [email.strip() for email in email_to if email.strip()]
                        
                        if email_to:
                            success = notifier.send_alert(alert, email_to)
                            if success:
                                channel.last_notification = current_time
                    else:
                        success = notifier.send_alert(alert)
                        if success:
                            channel.last_notification = current_time
                            
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel_name}: {e}")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        with self.lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    alert.acknowledged_by = acknowledged_by
                    alert.acknowledged_at = time.time()
                    logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                    return True
        return False
    
    def get_alerts(self, limit: int = 100, unacknowledged_only: bool = False,
                  min_severity: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """Get alerts with filtering"""
        with self.lock:
            filtered_alerts = self.alerts
            
            if unacknowledged_only:
                filtered_alerts = [a for a in filtered_alerts if not a.acknowledged]
            
            if min_severity:
                severity_levels = {
                    AlertSeverity.LOW: 1,
                    AlertSeverity.MEDIUM: 2,
                    AlertSeverity.HIGH: 3,
                    AlertSeverity.CRITICAL: 4
                }
                min_level = severity_levels[min_severity]
                filtered_alerts = [
                    a for a in filtered_alerts 
                    if severity_levels[a.severity] >= min_level
                ]
            
            # Sort by timestamp (newest first) and limit
            filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)
            
            return [alert.to_dict() for alert in filtered_alerts[:limit]]
    
    def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics"""
        with self.lock:
            total_alerts = len(self.alerts)
            unacknowledged = len([a for a in self.alerts if not a.acknowledged])
            
            by_severity = {}
            by_type = {}
            
            for alert in self.alerts:
                # Count by severity
                severity_key = alert.severity.value
                by_severity[severity_key] = by_severity.get(severity_key, 0) + 1
                
                # Count by type
                type_key = alert.type.value
                by_type[type_key] = by_type.get(type_key, 0) + 1
            
            # Recent alert rate (last hour)
            hour_ago = time.time() - 3600
            recent_alerts = len([a for a in self.alerts if a.timestamp >= hour_ago])
            
            return {
                'total_alerts': total_alerts,
                'unacknowledged': unacknowledged,
                'acknowledged': total_alerts - unacknowledged,
                'alerts_last_hour': recent_alerts,
                'by_severity': by_severity,
                'by_type': by_type,
                'channels_configured': len(self.channels),
                'channels_enabled': len([c for c in self.channels.values() if c.enabled])
            }
    
    def add_alert_callback(self, callback: Callable):
        """Add callback to be called when new alerts are created"""
        self.alert_callbacks.append(callback)
    
    def test_notifications(self) -> Dict[str, bool]:
        """Test all configured notification channels"""
        results = {}
        
        test_alert = Alert(
            id="test_alert",
            type=AlertType.SYSTEM_ERROR,
            severity=AlertSeverity.LOW,
            title="Test Alert",
            message="This is a test alert to verify notification channels are working correctly.",
            timestamp=time.time()
        )
        
        for channel_name, notifier in self.notifiers.items():
            try:
                if channel_name == 'email':
                    email_to = os.getenv('GUARDIA_EMAIL_TO', '').split(',')
                    email_to = [email.strip() for email in email_to if email.strip()]
                    if email_to:
                        results[channel_name] = notifier.send_alert(test_alert, email_to)
                    else:
                        results[channel_name] = False
                else:
                    results[channel_name] = notifier.send_alert(test_alert)
            except Exception as e:
                logger.error(f"Test notification failed for {channel_name}: {e}")
                results[channel_name] = False
        
        return results

# Global alert manager instance
alert_manager = AlertManager()

# Convenience functions
def create_threat_alert(title: str, message: str, severity: AlertSeverity = AlertSeverity.HIGH,
                       location: Optional[str] = None, data: Optional[Dict[str, Any]] = None,
                       image_path: Optional[str] = None) -> Alert:
    """Create a threat detection alert"""
    return alert_manager.create_alert(
        AlertType.THREAT_DETECTED, severity, title, message, location, data, image_path
    )

def create_zone_breach_alert(zone_name: str, detected_objects: List[str],
                           severity: AlertSeverity = AlertSeverity.MEDIUM,
                           image_path: Optional[str] = None) -> Alert:
    """Create a zone breach alert"""
    return alert_manager.create_alert(
        AlertType.ZONE_BREACH,
        severity,
        f"Zone Breach: {zone_name}",
        f"Detected objects in restricted zone: {', '.join(detected_objects)}",
        location=zone_name,
        data={'detected_objects': detected_objects},
        image_path=image_path
    )

def create_performance_alert(issue: str, metrics: Dict[str, Any],
                           severity: AlertSeverity = AlertSeverity.LOW) -> Alert:
    """Create a performance issue alert"""
    return alert_manager.create_alert(
        AlertType.PERFORMANCE_ISSUE,
        severity,
        f"Performance Issue: {issue}",
        f"System performance degraded: {issue}",
        data=metrics
    )
