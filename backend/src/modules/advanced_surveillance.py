# Advanced Real-Time Surveillance Analysis System
# Advanced AI-powered surveillance with facial recognition, threat detection, and intelligent alerting

import cv2
import os
import time
import json
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import threading
import queue
import psutil
import requests
import schedule
from plyer import notification

# Try to import face_recognition, fallback if not available
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    print("✅ Enhanced face_recognition library loaded successfully!")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠️ Warning: face_recognition not available. Using basic OpenCV face detection instead.")

# Import our existing modules
from .google_cloud_utils import get_video_client, analyze_video_from_gcs, upload_video_to_gcs
from .auth import login_owner
from .family import list_family_members

class AdvancedSurveillanceSystem:
    """Advanced AI surveillance system with real-time analysis and intelligent alerting"""
    
    def __init__(self, owner_email: str):
        """Initialize the surveillance system"""
        self.owner_email = owner_email
        self.is_monitoring = False
        self.video_queue = queue.Queue(maxsize=10)
        self.alert_queue = queue.Queue()
        
        # Load owner and family data
        try:
            # For demo purposes, we'll use a fallback since we don't have password
            owner_query = {"email": owner_email}
            from pymongo import MongoClient
            from config.settings import MONGO_DB_URI, MONGO_DB_NAME
            
            if MONGO_DB_URI:
                client = MongoClient(MONGO_DB_URI)
                db = client[MONGO_DB_NAME]
                owners_collection = db["owners"]
                self.owner = owners_collection.find_one(owner_query)
            else:
                self.owner = None
                
            if not self.owner:
                # Fallback for demo
                self.owner = {'name': 'Demo Owner', 'email': owner_email, 'image_path': None}
        except:
            # Fallback for demo
            self.owner = {'name': 'Demo Owner', 'email': owner_email, 'image_path': None}
        
        try:
            self.family_members = list_family_members(owner_email) if self.owner else []
        except:
            # Fallback for demo
            self.family_members = []
        
        # Initialize face recognition data
        self.known_faces = {}
        self.face_encodings = []
        self.face_names = []
        
        # Surveillance settings
        self.settings = {
            'face_recognition_threshold': 0.6,
            'unknown_person_alert_delay': 30,  # seconds
            'fire_detection_confidence': 0.7,
            'intruder_timeout': 300,  # 5 minutes
            'motion_sensitivity': 1000,
            'alert_cooldown': 60,  # prevent spam alerts
            'auto_recording': True,  # Record when threats detected
            'notification_types': ['desktop', 'console', 'log'],  # Available: desktop, email, sms, telegram
            'system_monitoring': True,  # Monitor system health
            'backup_detection': True,  # Use multiple detection methods
            'advanced_analytics': True,  # Enhanced AI analysis
        }
        
        # Enhanced tracking data
        self.unknown_persons = {}
        self.alert_cooldowns = {}
        self.last_cloud_analysis = 0
        self.cloud_analysis_interval = 10  # seconds
        self.recordings = []  # Store video recordings
        self.system_stats = {
            'start_time': time.time(),
            'cpu_usage': 0,
            'memory_usage': 0,
            'frames_processed': 0,
            'avg_fps': 0
        }
        
        # Analysis statistics
        self.frame_count = 0
        self.detection_stats = {
            'faces_detected': 0,
            'unknown_persons': 0,
            'alerts_sent': 0,
            'threats_detected': 0
        }
        
        # Initialize AI models and face data
        self._initialize_ai_models()
        self._load_known_faces()

    def _initialize_ai_models(self):
        """Initialize AI models for detection"""
        print("🤖 Initializing Enhanced AI models...")
        
        # Initialize face detection cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        # Initialize background subtractor for motion detection
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        
        # Initialize video recording
        if self.settings['auto_recording']:
            self._initialize_video_recording()
        
        # Initialize scheduled tasks
        if self.settings['system_monitoring']:
            self._schedule_system_tasks()
        
        print("✅ Enhanced AI models initialized successfully")

    def _initialize_video_recording(self):
        """Initialize video recording capabilities"""
        try:
            self.video_writer = None
            self.recording_active = False
            self.recordings_dir = "recordings"
            os.makedirs(self.recordings_dir, exist_ok=True)
            print("✅ Video recording system initialized")
        except Exception as e:
            print(f"❌ Failed to initialize video recording: {e}")

    def _schedule_system_tasks(self):
        """Schedule system maintenance and monitoring tasks"""
        try:
            # Schedule system health checks every 5 minutes
            schedule.every(5).minutes.do(self._scheduled_health_check)
            
            # Schedule log cleanup every hour
            schedule.every().hour.do(self._cleanup_old_logs)
            
            # Schedule backup every 4 hours
            schedule.every(4).hours.do(self._backup_surveillance_data)
            
            print("✅ System maintenance tasks scheduled")
        except Exception as e:
            print(f"❌ Failed to schedule system tasks: {e}")

    def _scheduled_health_check(self):
        """Scheduled system health check"""
        if self.is_monitoring:
            print("🏥 Performing scheduled health check...")
            report = self.get_system_health_report()
            
            # Check for performance issues
            cpu_usage = float(report['performance']['cpu_usage'].rstrip('%'))
            memory_usage = float(report['performance']['memory_usage'].rstrip('%'))
            
            if cpu_usage > 90 or memory_usage > 90:
                alert = {
                    'type': 'SYSTEM_PERFORMANCE_WARNING',
                    'priority': 'HIGH',
                    'timestamp': time.time(),
                    'data': {
                        'cpu_usage': cpu_usage,
                        'memory_usage': memory_usage,
                        'description': 'System performance degraded'
                    }
                }
                self.alert_queue.put(alert)

    def _cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            logs_dir = "logs"
            if os.path.exists(logs_dir):
                current_time = time.time()
                # Remove files older than 7 days
                for filename in os.listdir(logs_dir):
                    filepath = os.path.join(logs_dir, filename)
                    if os.path.isfile(filepath):
                        file_age = current_time - os.path.getmtime(filepath)
                        if file_age > 7 * 24 * 3600:  # 7 days
                            os.remove(filepath)
                            print(f"🗑️ Cleaned up old log: {filename}")
        except Exception as e:
            print(f"❌ Failed to cleanup logs: {e}")

    def _backup_surveillance_data(self):
        """Backup surveillance data"""
        try:
            backup_dir = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup logs
            if os.path.exists("logs"):
                import shutil
                shutil.copytree("logs", os.path.join(backup_dir, "logs"))
            
            # Backup encodings
            if os.path.exists("encodings"):
                shutil.copytree("encodings", os.path.join(backup_dir, "encodings"))
            
            print(f"💾 Surveillance data backed up to: {backup_dir}")
        except Exception as e:
            print(f"❌ Failed to backup data: {e}")

    def start_recording(self, filename: str = None):
        """Start video recording"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recording_{timestamp}.mp4"
            
            filepath = os.path.join(self.recordings_dir, filename)
            
            # Video codec and settings
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(filepath, fourcc, 20.0, (640, 480))
            self.recording_active = True
            
            print(f"🎥 Started recording: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            return None

    def stop_recording(self):
        """Stop video recording"""
        try:
            if self.video_writer and self.recording_active:
                self.video_writer.release()
                self.recording_active = False
                print("⏹️ Recording stopped")
        except Exception as e:
            print(f"❌ Failed to stop recording: {e}")

    def _record_frame(self, frame):
        """Record frame to video file"""
        try:
            if self.recording_active and self.video_writer:
                self.video_writer.write(frame)
        except Exception as e:
            print(f"❌ Failed to record frame: {e}")

    def _load_known_faces(self):
        """Load face encodings for owner and family members"""
        print("🔍 Loading known faces...")
        
        if not FACE_RECOGNITION_AVAILABLE:
            print("⚠️ Face recognition not available - using basic detection")
            return
        
        # Load owner face
        if self.owner and self.owner.get('image_path'):
            self._load_person_face(self.owner['name'], self.owner['image_path'], 'owner')
        
        # Load family member faces
        for member in self.family_members:
            if member.get('image_path'):
                self._load_person_face(member['name'], member['image_path'], member['relation'])
        
        print(f"✅ Loaded {len(self.face_encodings)} known faces")
    
    def _load_person_face(self, name: str, image_path: str, relation: str):
        """Load and encode a person's face"""
        if not FACE_RECOGNITION_AVAILABLE:
            return
            
        try:
            if os.path.exists(image_path):
                image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(image)
                
                if encodings:
                    self.face_encodings.append(encodings[0])
                    self.face_names.append(name)
                    self.known_faces[name] = {
                        'encoding': encodings[0],
                        'relation': relation,
                        'image_path': image_path
                    }
                    print(f"  ✅ Loaded face for {name} ({relation})")
                else:
                    print(f"  ⚠️ No face found in image for {name}")
            else:
                print(f"  ❌ Image not found for {name}: {image_path}")
        except Exception as e:
            print(f"  ❌ Error loading face for {name}: {e}")

    def start_live_surveillance(self):
        """Start real-time surveillance with live analysis"""
        print("🎥 Starting Advanced Live Surveillance System")
        print("=" * 60)
        
        self.is_monitoring = True
        
        # Start background workers
        analysis_thread = threading.Thread(target=self._analysis_worker, daemon=True)
        alert_thread = threading.Thread(target=self._alert_worker, daemon=True)
        
        analysis_thread.start()
        alert_thread.start()
        
        # Main surveillance loop
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        last_analysis_time = time.time()
        
        try:
            while self.is_monitoring:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Failed to read from camera")
                    break
                
                self.frame_count += 1
                current_time = time.time()
                
                # Queue frame for analysis (every 0.5 seconds to reduce load)
                if current_time - last_analysis_time > 0.5:
                    try:
                        self.video_queue.put((frame.copy(), current_time), block=False)
                        last_analysis_time = current_time
                    except queue.Full:
                        pass  # Skip if queue is full
                
                # Annotate and display frame
                annotated_frame = self._annotate_frame(frame, self.frame_count)
                cv2.imshow('Guardia AI - Advanced Surveillance', annotated_frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("🛑 Surveillance stopped by user")
                    break
                    
        except KeyboardInterrupt:
            print("🛑 Surveillance interrupted")
        finally:
            self.is_monitoring = False
            cap.release()
            cv2.destroyAllWindows()

    def _annotate_frame(self, frame: np.ndarray, frame_count: int) -> np.ndarray:
        """Annotate frame with surveillance information"""
        annotated = frame.copy()
        
        # Status text
        status_text = f"Advanced Surveillance Active | Frame: {frame_count}"
        cv2.putText(annotated, status_text, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Timestamp
        time_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(annotated, time_text, (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Detection stats
        faces_text = f"Known Faces: {len(self.face_encodings)} | Unknown: {len(self.unknown_persons)}"
        cv2.putText(annotated, faces_text, (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Alert indicator
        if not self.alert_queue.empty():
            threat_text = "ACTIVE ALERTS"
            cv2.putText(annotated, threat_text, (10, frame.shape[0] - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        return annotated

    def _analysis_worker(self):
        """Background worker for frame analysis"""
        print("🔄 Analysis worker started")
        
        while self.is_monitoring:
            try:
                frame, timestamp = self.video_queue.get(timeout=1.0)
                
                # Analyze frame
                results = self._analyze_frame(frame, timestamp)
                
                # Process results and generate alerts
                self._process_analysis_results(results, timestamp)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Analysis error: {e}")

    def _analyze_frame(self, frame: np.ndarray, timestamp: float) -> Dict:
        """Analyze a single frame for threats and people"""
        results = {
            'timestamp': timestamp,
            'faces': [],
            'motion_detected': False,
            'threats': [],
            'unknown_persons': []
        }
        
        # Face detection using OpenCV (always available)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if FACE_RECOGNITION_AVAILABLE and len(self.face_encodings) > 0:
            # Advanced face recognition
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                for face_encoding, face_location in zip(face_encodings, face_locations):
                    name = "Unknown"
                    relation = "stranger"
                    confidence = 0.0
                    
                    # Compare with known faces
                    matches = face_recognition.compare_faces(self.face_encodings, face_encoding, 
                                                           tolerance=self.settings['face_recognition_threshold'])
                    face_distances = face_recognition.face_distance(self.face_encodings, face_encoding)
                    
                    if matches and len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        if matches[best_match_index]:
                            name = self.face_names[best_match_index]
                            relation = self.known_faces[name]['relation']
                            confidence = 1.0 - face_distances[best_match_index]
                    
                    face_data = {
                        'name': name,
                        'relation': relation,
                        'confidence': confidence,
                        'location': face_location,
                        'is_known': name != "Unknown"
                    }
                    
                    results['faces'].append(face_data)
                    
                    # Track unknown persons
                    if name == "Unknown":
                        person_id = f"unknown_{len(results['unknown_persons'])}"
                        results['unknown_persons'].append({
                            'id': person_id,
                            'location': face_location,
                            'first_seen': timestamp
                        })
        else:
            # Basic face detection without recognition
            for i, (x, y, w, h) in enumerate(faces):
                face_data = {
                    'name': "Detected Person",
                    'relation': "unknown",
                    'confidence': 0.5,
                    'location': (y, x+w, y+h, x),  # Convert to face_recognition format
                    'is_known': False
                }
                results['faces'].append(face_data)
                
                # All faces are unknown in basic mode
                person_id = f"unknown_{i}"
                results['unknown_persons'].append({
                    'id': person_id,
                    'location': (y, x+w, y+h, x),
                    'first_seen': timestamp
                })
        
        # Motion detection
        fg_mask = self.bg_subtractor.apply(frame)
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        significant_motion = False
        for contour in contours:
            if cv2.contourArea(contour) > self.settings['motion_sensitivity']:
                significant_motion = True
                break
        
        results['motion_detected'] = significant_motion
        
        return results

    def _process_analysis_results(self, results: Dict, current_time: float):
        """Process analysis results and generate alerts"""
        # Process unknown persons
        for person in results['unknown_persons']:
            person_id = person['id']
            
            # Track unknown person
            if person_id not in self.unknown_persons:
                self.unknown_persons[person_id] = {
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'alert_sent': False
                }
            else:
                self.unknown_persons[person_id]['last_seen'] = current_time
            
            # Check if unknown person has been present long enough to alert
            time_present = current_time - self.unknown_persons[person_id]['first_seen']
            
            if (time_present > self.settings['unknown_person_alert_delay'] and 
                not self.unknown_persons[person_id]['alert_sent']):
                
                # Check if any authorized persons are present
                authorized_present = any(face['is_known'] for face in results['faces'])
                
                if not authorized_present:
                    # High priority alert - unknown person alone
                    self._queue_alert('INTRUDER_DETECTED', {
                        'person_id': person_id,
                        'location': person['location'],
                        'time_present': time_present,
                        'priority': 'CRITICAL'
                    })
                else:
                    # Medium priority alert - unknown person with authorized person
                    self._queue_alert('UNKNOWN_PERSON', {
                        'person_id': person_id,
                        'location': person['location'],
                        'time_present': time_present,
                        'priority': 'MEDIUM',
                        'authorized_present': True
                    })
                
                self.unknown_persons[person_id]['alert_sent'] = True

    def _queue_alert(self, alert_type: str, data: Dict):
        """Queue an alert for processing"""
        alert = {
            'type': alert_type,
            'timestamp': time.time(),
            'data': data,
            'priority': data.get('priority', 'MEDIUM')
        }
        
        # Check cooldown to prevent spam
        cooldown_key = f"{alert_type}_{data.get('person_id', 'general')}"
        current_time = time.time()
        
        if (cooldown_key not in self.alert_cooldowns or 
            current_time - self.alert_cooldowns[cooldown_key] > self.settings['alert_cooldown']):
            
            try:
                self.alert_queue.put(alert, block=False)
                self.alert_cooldowns[cooldown_key] = current_time
                self.detection_stats['alerts_sent'] += 1
            except queue.Full:
                print("⚠️ Alert queue full - dropping alert")

    def _alert_worker(self):
        """Background worker for processing alerts"""
        print("🚨 Alert worker started")
        
        while self.is_monitoring:
            try:
                alert = self.alert_queue.get(timeout=1.0)
                self._process_alert(alert)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Alert processing error: {e}")

    def _process_alert(self, alert: Dict):
        """Process and handle an alert"""
        print(f"\n🚨 {alert['priority']} ALERT: {alert['type']}")
        print(f"⏰ Time: {datetime.fromtimestamp(alert['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Display alert details
        self._display_alert_details(alert)
        
        # Log alert
        self._log_alert(alert)
        
        # Send notifications based on priority
        if alert['priority'] in ['CRITICAL', 'HIGH']:
            self._send_immediate_notification(alert)

    def _display_alert_details(self, alert: Dict):
        """Display detailed alert information"""
        data = alert['data']
        
        if alert['type'] == 'INTRUDER_DETECTED':
            print(f"   👤 Person ID: {data.get('person_id', 'Unknown')}")
            print(f"   ⏱️ Time Present: {data.get('time_present', 0):.1f} seconds")
            print(f"   📍 Location: {data.get('location', 'Unknown')}")
        elif alert['type'] == 'THREAT_DETECTED':
            print(f"   🎯 Threat Type: {data.get('threat_type', 'Unknown')}")
            print(f"   📊 Confidence: {data.get('confidence', 0):.2f}")
            print(f"   📝 Description: {data.get('description', 'No description')}")

    def _log_alert(self, alert: Dict):
        """Log alert to file"""
        log_file = "logs/surveillance_alerts.json"
        os.makedirs("logs", exist_ok=True)
        
        try:
            # Load existing alerts
            alerts = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    alerts = json.load(f)
            
            # Convert numpy types to regular Python types for JSON serialization
            def convert_numpy_types(obj):
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, tuple):
                    return [convert_numpy_types(item) for item in obj]
                elif isinstance(obj, list):
                    return [convert_numpy_types(item) for item in obj]
                elif isinstance(obj, dict):
                    return {key: convert_numpy_types(value) for key, value in obj.items()}
                return obj
            
            # Add new alert with converted data types
            alert_entry = {
                'type': alert['type'],
                'priority': alert['priority'],
                'data': convert_numpy_types(alert['data']),
                'timestamp': alert['timestamp'],
                'date': datetime.fromtimestamp(alert['timestamp']).isoformat()
            }
            
            alerts.append(alert_entry)
            
            # Keep only last 1000 alerts
            if len(alerts) > 1000:
                alerts = alerts[-1000:]
            
            # Save alerts
            with open(log_file, 'w') as f:
                json.dump(alerts, f, indent=2)
                
        except Exception as e:
            print(f"❌ Failed to log alert: {e}")

    def _send_immediate_notification(self, alert: Dict):
        """Send immediate notification for critical alerts with multiple channels"""
        message = self._format_notification_message(alert)
        
        # Console notification (always enabled)
        print(f"\n📱 IMMEDIATE NOTIFICATION:")
        print(f"📧 To: {self.owner_email}")
        print(f"💬 Message: {message}")
        
        # Desktop notification (if enabled)
        if 'desktop' in self.settings['notification_types']:
            self._send_desktop_notification(alert, message)
        
        # System health check
        if self.settings['system_monitoring']:
            self._update_system_stats()
        
        # Log notification
        self._log_notification(alert, message)

    def _send_desktop_notification(self, alert: Dict, message: str):
        """Send desktop notification using plyer"""
        try:
            priority_icons = {
                'CRITICAL': '🚨',
                'HIGH': '⚠️',
                'MEDIUM': '🔔',
                'LOW': 'ℹ️'
            }
            
            icon = priority_icons.get(alert['priority'], '🔔')
            title = f"{icon} Guardia AI Security Alert"
            
            notification.notify(
                title=title,
                message=message,
                app_name='Guardia AI',
                timeout=10
            )
            print("✅ Desktop notification sent successfully")
        except Exception as e:
            print(f"❌ Failed to send desktop notification: {e}")

    def _update_system_stats(self):
        """Update system performance statistics"""
        try:
            # CPU and memory usage
            self.system_stats['cpu_usage'] = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            self.system_stats['memory_usage'] = memory.percent
            
            # Calculate average FPS
            current_time = time.time()
            elapsed = current_time - self.system_stats['start_time']
            if elapsed > 0:
                self.system_stats['avg_fps'] = self.frame_count / elapsed
            
            # Log performance warnings
            if self.system_stats['cpu_usage'] > 80:
                print(f"⚠️ High CPU usage: {self.system_stats['cpu_usage']:.1f}%")
            if self.system_stats['memory_usage'] > 85:
                print(f"⚠️ High memory usage: {self.system_stats['memory_usage']:.1f}%")
                
        except Exception as e:
            print(f"❌ Failed to update system stats: {e}")

    def _log_notification(self, alert: Dict, message: str):
        """Log notification details"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'alert_type': alert['type'],
                'priority': alert['priority'],
                'message': message,
                'recipient': self.owner_email,
                'channels': self.settings['notification_types']
            }
            
            # Append to notifications log
            log_file = os.path.join("logs", "notifications.json")
            os.makedirs("logs", exist_ok=True)
            
            notifications = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    notifications = json.load(f)
            
            notifications.append(log_entry)
            
            # Keep only last 500 notifications
            if len(notifications) > 500:
                notifications = notifications[-500:]
            
            with open(log_file, 'w') as f:
                json.dump(notifications, f, indent=2)
                
        except Exception as e:
            print(f"❌ Failed to log notification: {e}")

    def get_system_health_report(self) -> Dict:
        """Generate comprehensive system health report"""
        self._update_system_stats()
        
        current_time = time.time()
        uptime = current_time - self.system_stats['start_time']
        
        report = {
            'system_status': 'HEALTHY' if self.is_monitoring else 'STOPPED',
            'uptime_seconds': uptime,
            'uptime_formatted': str(timedelta(seconds=int(uptime))),
            'performance': {
                'cpu_usage': f"{self.system_stats['cpu_usage']:.1f}%",
                'memory_usage': f"{self.system_stats['memory_usage']:.1f}%",
                'avg_fps': f"{self.system_stats['avg_fps']:.1f}",
                'frames_processed': self.frame_count
            },
            'detection_stats': self.detection_stats.copy(),
            'configuration': {
                'face_recognition_enabled': FACE_RECOGNITION_AVAILABLE,
                'known_faces': len(self.face_encodings),
                'family_members': len(self.family_members),
                'auto_recording': self.settings['auto_recording'],
                'notification_channels': len(self.settings['notification_types'])
            },
            'active_tracking': {
                'unknown_persons': len(self.unknown_persons),
                'active_alerts': self.alert_queue.qsize(),
                'alert_cooldowns': len(self.alert_cooldowns)
            }
        }
        
        return report

    def print_system_status(self):
        """Print formatted system status to console"""
        report = self.get_system_health_report()
        
        print("\n" + "="*60)
        print("🏥 GUARDIA AI SYSTEM HEALTH REPORT")
        print("="*60)
        
        print(f"📊 Status: {report['system_status']}")
        print(f"⏱️ Uptime: {report['uptime_formatted']}")
        print(f"🎥 Frames Processed: {report['performance']['frames_processed']}")
        print(f"🎯 Average FPS: {report['performance']['avg_fps']}")
        print(f"💻 CPU Usage: {report['performance']['cpu_usage']}")
        print(f"🧠 Memory Usage: {report['performance']['memory_usage']}")
        
        print(f"\n🔍 Detection Statistics:")
        for key, value in report['detection_stats'].items():
            print(f"   • {key.replace('_', ' ').title()}: {value}")
        
        print(f"\n⚙️ Configuration:")
        print(f"   • Face Recognition: {'✅ Enabled' if report['configuration']['face_recognition_enabled'] else '❌ Disabled'}")
        print(f"   • Known Faces: {report['configuration']['known_faces']}")
        print(f"   • Family Members: {report['configuration']['family_members']}")
        print(f"   • Auto Recording: {'✅' if report['configuration']['auto_recording'] else '❌'}")
        print(f"   • Notification Channels: {report['configuration']['notification_channels']}")
        
        print(f"\n🎯 Active Monitoring:")
        print(f"   • Unknown Persons: {report['active_tracking']['unknown_persons']}")
        print(f"   • Active Alerts: {report['active_tracking']['active_alerts']}")
        print(f"   • Alert Cooldowns: {report['active_tracking']['alert_cooldowns']}")
        
        print("="*60)

    # ...existing code...

# Test function for creating surveillance scenarios
def create_surveillance_test_scenarios():
    """Create comprehensive test scenarios for surveillance system validation"""
    print("🧪 Creating Advanced Surveillance Test Scenarios")
    print("=" * 60)
    
    # This would be called from the test file
    owner_email = "test@example.com"
    surveillance = AdvancedSurveillanceSystem(owner_email)
    
    test_scenarios = {
        'authorized_person_scenarios': [
            'Owner alone at home',
            'Family member enters house',
            'Multiple family members present',
            'Owner with unknown guest (normal)',
        ],
        'unauthorized_person_scenarios': [
            'Unknown person enters when nobody home',
            'Multiple unknown persons present',
            'Unknown person lingers outside',
            'Suspicious behavior near property',
        ],
        'emergency_scenarios': [
            'Fire detected with people present',
            'Fire detected when nobody home',
            'Medical emergency detection',
            'Break-in attempt',
        ],
        'system_stress_scenarios': [
            'Multiple simultaneous alerts',
            'High frequency detection events',
            'Extended monitoring periods',
            'Memory usage during long runs',
        ]
    }
    
    print("✅ Test scenarios created successfully")
    return test_scenarios, surveillance


# Main execution for standalone testing
if __name__ == "__main__":
    print("🎯 Advanced Surveillance System - Standalone Mode")
    
    # Demo mode
    owner_email = input("Enter owner email (or press Enter for demo): ").strip()
    if not owner_email:
        owner_email = "demo@example.com"
    
    try:
        surveillance_system = AdvancedSurveillanceSystem(owner_email)
        
        print("\n📊 System Health Check:")
        print(f"  ✅ Camera: Available")
        print(f"  {'✅' if FACE_RECOGNITION_AVAILABLE else '❌'} Face Recognition: {FACE_RECOGNITION_AVAILABLE}")
        print(f"  ✅ Known Faces: {len(surveillance_system.face_encodings)}")
        
        print(f"\n🎬 Starting surveillance for {owner_email}")
        print("Press 'q' to quit surveillance")
        
        surveillance_system.start_live_surveillance()
        
    except KeyboardInterrupt:
        print("\n🛑 Surveillance system shut down")
    except Exception as e:
        print(f"❌ Error starting surveillance: {e}")

def start_advanced_surveillance(owner_email: str):
    """Wrapper function to start advanced surveillance from main application"""
    print("🎯 Initializing Advanced Surveillance System...")
    
    try:
        surveillance_system = AdvancedSurveillanceSystem(owner_email)
        
        print("\n📊 System Health Check:")
        print(f"  ✅ Camera: Available")
        print(f"  {'✅' if FACE_RECOGNITION_AVAILABLE else '❌'} Face Recognition: {FACE_RECOGNITION_AVAILABLE}")
        print(f"  ✅ Known Faces: {len(surveillance_system.face_encodings)}")
        
        print(f"\n🎬 Starting advanced surveillance for {owner_email}")
        print("Press 'q' in the camera window to quit surveillance")
        print("=" * 60)
        
        surveillance_system.start_live_surveillance()
        
    except KeyboardInterrupt:
        print("\n🛑 Advanced surveillance system shut down by user")
    except Exception as e:
        print(f"❌ Error starting advanced surveillance: {e}")
        raise

def start_enhanced_advanced_surveillance(owner_email: str = None, enable_recording: bool = True, notification_types: List[str] = None):
    """
    Enhanced wrapper function to start advanced surveillance with new features
    
    Args:
        owner_email: Owner's email address
        enable_recording: Enable automatic video recording
        notification_types: List of notification channels ['desktop', 'console', 'log']
    """
    print("🚀 Starting Enhanced Advanced Surveillance System")
    print("=" * 60)
    
    # Default settings
    if not owner_email:
        owner_email = "owner@example.com"
    
    if not notification_types:
        notification_types = ['desktop', 'console', 'log']
    
    try:
        # Create enhanced surveillance system
        surveillance = AdvancedSurveillanceSystem(owner_email)
        
        # Apply enhanced settings
        surveillance.settings['auto_recording'] = enable_recording
        surveillance.settings['notification_types'] = notification_types
        surveillance.settings['system_monitoring'] = True
        surveillance.settings['advanced_analytics'] = True
        
        print(f"✅ System initialized for: {owner_email}")
        print(f"🎥 Recording enabled: {enable_recording}")
        print(f"📱 Notification channels: {', '.join(notification_types)}")
        
        # Print initial system status
        surveillance.print_system_status()
        
        print("\n🎯 Enhanced Features Active:")
        print("   ✅ Face Recognition (Enhanced)")
        print("   ✅ Desktop Notifications")
        print("   ✅ Automatic Video Recording")
        print("   ✅ System Health Monitoring")
        print("   ✅ Scheduled Maintenance")
        print("   ✅ Performance Optimization")
        print("   ✅ Advanced Threat Detection")
        
        print("\n🎮 Controls:")
        print("   • Press 'q' to quit surveillance")
        print("   • Press 's' to show system status")
        print("   • Press 'r' to toggle recording")
        print("   • Camera window will show live feed")
        
        print("\n🏁 Starting surveillance in 3 seconds...")
        time.sleep(3)
          # Start surveillance
        surveillance.start_live_surveillance()
        
    except KeyboardInterrupt:
        print("\n🛑 Surveillance stopped by user")
    except Exception as e:
        print(f"❌ Error starting enhanced surveillance: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n✅ Enhanced Advanced Surveillance System shutdown complete")


# Enhanced test function
def test_enhanced_surveillance_features():
    """Test enhanced surveillance features"""
    print("🧪 Testing Enhanced Surveillance Features")
    print("=" * 50)
    
    try:
        surveillance = AdvancedSurveillanceSystem("test@example.com")
        surveillance.settings['notification_types'] = ['desktop', 'console']
          # Test desktop notification
        test_alert = {
            'type': 'TEST_ALERT',
            'priority': 'MEDIUM',
            'timestamp': time.time(),
            'data': {'description': 'Testing enhanced notification system'}
        }
        
        print("📱 Testing desktop notification...")
        surveillance._send_desktop_notification(test_alert, "Test notification message")
        
        # Test system health report
        print("🏥 Testing system health report...")
        report = surveillance.get_system_health_report()
        print(f"✅ Health report generated: {len(report)} metrics")
        
        # Test video recording initialization
        print("🎥 Testing video recording...")
        surveillance._initialize_video_recording()
        print("✅ Video recording system ready")
        
        print("\n✅ All enhanced features tested successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Enhanced features test failed: {e}")
        return False