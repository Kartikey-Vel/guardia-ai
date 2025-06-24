#!/usr/bin/env python3
"""
Guardia AI - Face Authentication Integration Example
Shows how to integrate the face authentication system with the main Guardia AI surveillance system
"""

import cv2
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, List
from real_time_face_auth import FaceAuthSystem, UserProfile

class GuardiaFaceIntegration:
    """Integration layer between face authentication and main surveillance system"""
    
    def __init__(self):
        self.face_auth = FaceAuthSystem()
        self.alert_callbacks = []
        self.recognition_history = []
        self.current_detections = {}
        
    def add_alert_callback(self, callback):
        """Add callback for face recognition alerts"""
        self.alert_callbacks.append(callback)
        
    def trigger_alert(self, alert_type: str, user_data: Dict, frame: Optional[cv2.Mat] = None):
        """Trigger alerts for face recognition events"""
        alert = {
            "timestamp": datetime.now().isoformat(),
            "type": alert_type,
            "user_data": user_data,
            "frame_available": frame is not None
        }
        
        # Store in history
        self.recognition_history.append(alert)
        
        # Call all registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert, frame)
            except Exception as e:
                print(f"⚠️ Alert callback error: {e}")
    
    def process_surveillance_frame(self, frame: cv2.Mat, source_id: str = "camera_0") -> Dict:
        """Process a frame from the surveillance system"""
        # Perform face recognition
        face_locations, face_names, face_confidences = self.face_auth.recognize_faces(frame)
        
        # Process results
        detection_results = []
        alerts_triggered = []
        
        for i, (location, name, confidence) in enumerate(zip(face_locations, face_names, face_confidences)):
            top, right, bottom, left = location
            
            # Create detection result
            detection = {
                "face_id": f"{source_id}_face_{i}",
                "location": {"top": top, "right": right, "bottom": bottom, "left": left},
                "name": name,
                "confidence": confidence,
                "timestamp": datetime.now().isoformat(),
                "source": source_id
            }
            
            # Determine user info
            if name != "Unknown":
                # Find user profile
                user_profile = None
                for user in self.face_auth.get_users_list():
                    if user.name == name:
                        user_profile = user
                        break
                
                if user_profile:
                    detection["user_id"] = user_profile.user_id
                    detection["role"] = user_profile.role
                    detection["is_family"] = user_profile.role == "family"
                    
                    # Family member detected
                    if user_profile.role == "family":
                        self.trigger_alert("family_detected", {
                            "name": name,
                            "user_id": user_profile.user_id,
                            "confidence": confidence,
                            "location": detection["location"]
                        }, frame)
                    else:
                        # Guest detected
                        self.trigger_alert("guest_detected", {
                            "name": name,
                            "user_id": user_profile.user_id,
                            "confidence": confidence,
                            "location": detection["location"]
                        }, frame)
                        
                    alerts_triggered.append("known_person_detected")
            else:
                # Unknown person detected
                detection["user_id"] = "unknown"
                detection["role"] = "unknown"
                detection["is_family"] = False
                
                self.trigger_alert("unknown_person_detected", {
                    "confidence": confidence,
                    "location": detection["location"],
                    "requires_attention": True
                }, frame)
                
                alerts_triggered.append("unknown_person_detected")
            
            detection_results.append(detection)
        
        # Update current detections
        self.current_detections[source_id] = detection_results
        
        return {
            "source_id": source_id,
            "timestamp": datetime.now().isoformat(),
            "face_count": len(detection_results),
            "detections": detection_results,
            "alerts": alerts_triggered,
            "processing_success": True
        }
    
    def get_security_status(self) -> Dict:
        """Get current security status based on face recognition"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "total_users": len(self.face_auth.users),
            "family_members": sum(1 for u in self.face_auth.users.values() if u.role == "family"),
            "guests": sum(1 for u in self.face_auth.users.values() if u.role == "guest"),
            "current_detections": self.current_detections,
            "recent_alerts": self.recognition_history[-10:],  # Last 10 alerts
            "security_level": "normal"
        }
        
        # Determine security level
        unknown_count = sum(
            len([d for d in detections if d["name"] == "Unknown"]) 
            for detections in self.current_detections.values()
        )
        
        if unknown_count > 0:
            status["security_level"] = "alert"
        elif any(detections for detections in self.current_detections.values()):
            status["security_level"] = "active"
        
        return status
    
    def export_recognition_data(self, filepath: str = None) -> str:
        """Export recognition history and user data"""
        if filepath is None:
            filepath = f"recognition_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "users": {uid: {
                "name": user.name,
                "role": user.role,
                "created_date": user.created_date,
                "last_seen": user.last_seen,
                "photo_count": user.photo_count
            } for uid, user in self.face_auth.users.items()},
            "recognition_history": self.recognition_history,
            "statistics": self.face_auth.get_recognition_stats()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filepath

# Example alert handlers
def security_alert_handler(alert: Dict, frame: Optional[cv2.Mat] = None):
    """Handle security alerts"""
    alert_type = alert["type"]
    timestamp = alert["timestamp"]
    
    if alert_type == "unknown_person_detected":
        print(f"🚨 SECURITY ALERT [{timestamp}]: Unknown person detected!")
        print(f"   Confidence: {alert['user_data']['confidence']:.2f}")
        print(f"   Location: {alert['user_data']['location']}")
        print(f"   Requires immediate attention!")
        
    elif alert_type == "family_detected":
        print(f"✅ FAMILY MEMBER [{timestamp}]: {alert['user_data']['name']} detected")
        print(f"   Confidence: {alert['user_data']['confidence']:.2f}")
        
    elif alert_type == "guest_detected":
        print(f"👤 GUEST [{timestamp}]: {alert['user_data']['name']} detected")
        print(f"   Confidence: {alert['user_data']['confidence']:.2f}")

def log_alert_handler(alert: Dict, frame: Optional[cv2.Mat] = None):
    """Log all alerts to file"""
    log_entry = {
        "timestamp": alert["timestamp"],
        "type": alert["type"],
        "user_data": alert["user_data"]
    }
    
    # Append to log file
    with open("face_recognition_alerts.log", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# Example integration usage
def demo_integration():
    """Demonstrate the integration with a surveillance system"""
    print("🔥 Guardia AI - Face Authentication Integration Demo")
    print("=" * 55)
    
    # Initialize integration
    integration = GuardiaFaceIntegration()
    
    # Add alert handlers
    integration.add_alert_callback(security_alert_handler)
    integration.add_alert_callback(log_alert_handler)
    
    print("✅ Integration initialized with alert handlers")
    print(f"👥 Loaded {len(integration.face_auth.users)} users")
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Camera not available")
        return
    
    print("📹 Camera initialized - Press 'q' to quit, 's' for status")
    
    try:
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Process frame every 5 frames (for performance)
            if frame_count % 5 == 0:
                result = integration.process_surveillance_frame(frame, "main_camera")
                
                # Draw detection results
                for detection in result["detections"]:
                    loc = detection["location"]
                    name = detection["name"]
                    confidence = detection["confidence"]
                    
                    # Color based on role
                    if detection["name"] == "Unknown":
                        color = (0, 0, 255)  # Red
                    elif detection.get("is_family", False):
                        color = (0, 255, 0)  # Green
                    else:
                        color = (255, 165, 0)  # Orange
                    
                    # Draw rectangle and label
                    cv2.rectangle(frame, (loc["left"], loc["top"]), 
                                (loc["right"], loc["bottom"]), color, 2)
                    
                    label = f"{name} ({confidence:.2f})"
                    cv2.putText(frame, label, (loc["left"], loc["top"] - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Display frame
            cv2.imshow("Guardia AI - Integrated Face Recognition", frame)
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                status = integration.get_security_status()
                print(f"\n📊 Security Status: {status['security_level'].upper()}")
                print(f"👥 Active detections: {sum(len(d) for d in status['current_detections'].values())}")
                print(f"🚨 Recent alerts: {len(status['recent_alerts'])}")
    
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        
        # Export data
        export_file = integration.export_recognition_data()
        print(f"📄 Recognition data exported to: {export_file}")

if __name__ == "__main__":
    demo_integration()
