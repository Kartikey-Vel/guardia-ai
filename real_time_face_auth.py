#!/usr/bin/env python3
"""
Guardia AI - Real-Time Face Authentication System
Complete system with video feed, user authentication, family recognition, and training
"""

import cv2
import face_recognition
import numpy as np
import os
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

@dataclass
class UserProfile:
    """User profile data structure"""
    name: str
    user_id: str
    role: str = "family"  # family, guest, admin
    created_date: str = ""
    last_seen: str = ""
    confidence_threshold: float = 0.6
    is_active: bool = True
    photo_count: int = 0


class FaceAuthSystem:
    """Advanced Face Authentication System with training and family recognition"""
    
    def __init__(self, data_dir: str = "storage/faces"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # User data
        self.users: Dict[str, UserProfile] = {}
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_user_ids = []
        
        # Training data
        self.training_data = {}
        self.recognition_log = []
        
        # Configuration
        self.users_file = self.data_dir / "users.json"
        self.training_file = self.data_dir / "training_data.json"
        
        # Load existing data
        self.load_user_data()
        self.load_training_data()

    def load_user_data(self):
        """Load user profiles and face encodings"""
        print("🔄 Loading user data...")
        
        # Load user profiles
        if self.users_file.exists():
            with open(self.users_file, 'r') as f:
                users_data = json.load(f)
                self.users = {
                    uid: UserProfile(**data) for uid, data in users_data.items()
                }
        
        # Load face encodings
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_user_ids = []
        
        for user_dir in self.data_dir.iterdir():
            if user_dir.is_dir() and user_dir.name != "__pycache__":
                user_id = user_dir.name
                user_path = self.data_dir / user_id
                
                # Load face encodings for this user
                for image_file in user_path.glob("*.jpg"):
                    try:
                        image = face_recognition.load_image_file(str(image_file))
                        encodings = face_recognition.face_encodings(image)
                        if encodings:
                            self.known_face_encodings.append(encodings[0])
                            self.known_face_names.append(self.users.get(user_id, UserProfile(user_id, user_id)).name)
                            self.known_face_user_ids.append(user_id)
                    except Exception as e:
                        print(f"⚠️ Error loading {image_file}: {e}")
        
        print(f"✅ Loaded {len(self.users)} users with {len(self.known_face_encodings)} face encodings")

    def save_user_data(self):
        """Save user profiles to file"""
        users_data = {uid: asdict(user) for uid, user in self.users.items()}
        with open(self.users_file, 'w') as f:
            json.dump(users_data, f, indent=2)

    def load_training_data(self):
        """Load training statistics and logs"""
        if self.training_file.exists():
            with open(self.training_file, 'r') as f:
                self.training_data = json.load(f)
        else:
            self.training_data = {
                "recognition_stats": {},
                "training_sessions": [],
                "accuracy_metrics": {}
            }

    def save_training_data(self):
        """Save training data to file"""
        with open(self.training_file, 'w') as f:
            json.dump(self.training_data, f, indent=2)

    def register_user(self, name: str, photos: List[np.ndarray], role: str = "family") -> Tuple[bool, str]:
        """Register a new user with their photos"""
        try:
            # Generate user ID
            user_id = name.lower().replace(" ", "_")
            if user_id in self.users:
                return False, f"User {name} already exists!"
            
            # Create user directory
            user_path = self.data_dir / user_id
            user_path.mkdir(exist_ok=True)
            
            # Save photos and extract encodings
            valid_encodings = []
            for idx, photo in enumerate(photos):
                photo_path = user_path / f"photo_{idx}.jpg"
                cv2.imwrite(str(photo_path), photo)
                
                # Extract face encoding
                rgb_photo = cv2.cvtColor(photo, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(rgb_photo)
                if encodings:
                    valid_encodings.append(encodings[0])
            
            if not valid_encodings:
                return False, "No valid face encodings found in photos!"
            
            # Create user profile
            user_profile = UserProfile(
                name=name,
                user_id=user_id,
                role=role,
                created_date=datetime.now().isoformat(),
                photo_count=len(photos)
            )
            
            self.users[user_id] = user_profile
            self.save_user_data()
            self.load_user_data()  # Reload to update encodings
            
            print(f"✅ Registered user: {name} ({role}) with {len(valid_encodings)} face encodings")
            return True, f"Successfully registered {name}!"
            
        except Exception as e:
            return False, f"Registration failed: {str(e)}"

    def recognize_faces(self, frame: np.ndarray) -> Tuple[List, List, List]:
        """Recognize faces in the given frame with confidence scores"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        face_names = []
        face_user_ids = []
        face_confidences = []

        for face_encoding in face_encodings:
            name = "Unknown"
            user_id = "unknown"
            confidence = 0.0
            
            if self.known_face_encodings:
                # Calculate distances to all known faces
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                
                # Check if the best match is below threshold
                if face_distances[best_match_index] < 0.6:  # Adjustable threshold
                    name = self.known_face_names[best_match_index]
                    user_id = self.known_face_user_ids[best_match_index]
                    confidence = 1.0 - face_distances[best_match_index]
                    
                    # Update last seen
                    if user_id in self.users:
                        self.users[user_id].last_seen = datetime.now().isoformat()

            face_names.append(name)
            face_user_ids.append(user_id)
            face_confidences.append(confidence)

        return face_locations, face_names, face_confidences

    def add_training_photos(self, user_id: str, photos: List[np.ndarray]) -> Tuple[bool, str]:
        """Add more training photos for existing user"""
        if user_id not in self.users:
            return False, "User not found!"
        
        try:
            user_path = self.data_dir / user_id
            existing_photos = len(list(user_path.glob("*.jpg")))
            
            valid_count = 0
            for idx, photo in enumerate(photos):
                photo_path = user_path / f"photo_{existing_photos + idx}.jpg"
                cv2.imwrite(str(photo_path), photo)
                
                # Verify face encoding
                rgb_photo = cv2.cvtColor(photo, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(rgb_photo)
                if encodings:
                    valid_count += 1
            
            # Update user profile
            self.users[user_id].photo_count += valid_count
            self.save_user_data()
            self.load_user_data()  # Reload encodings
            
            return True, f"Added {valid_count} training photos for {self.users[user_id].name}"
            
        except Exception as e:
            return False, f"Failed to add training photos: {str(e)}"

    def get_users_list(self) -> List[UserProfile]:
        """Get list of all users"""
        return list(self.users.values())

    def delete_user(self, user_id: str) -> bool:
        """Delete a user and their data"""
        if user_id in self.users:
            user_path = self.data_dir / user_id
            if user_path.exists():
                import shutil
                shutil.rmtree(user_path)
            del self.users[user_id]
            self.save_user_data()
            self.load_user_data()
            return True
        return False

    def get_recognition_stats(self) -> Dict:
        """Get recognition statistics"""
        total_recognitions = len(self.recognition_log)
        family_count = sum(1 for u in self.users.values() if u.role == "family")
        guest_count = sum(1 for u in self.users.values() if u.role == "guest")
        
        return {
            "total_users": len(self.users),
            "family_members": family_count,
            "guests": guest_count,
            "total_recognitions": total_recognitions,
            "total_encodings": len(self.known_face_encodings)
        }

class RealTimeFaceAuthApp:
    """Real-time face authentication application with GUI"""
    
    def __init__(self):
        self.face_auth = FaceAuthSystem()
        self.video_capture = None
        self.is_running = False
        self.current_frame = None
        
        # UI State
        self.registration_mode = False
        self.training_mode = False
        self.current_user_photos = []
        self.registration_name = ""
        self.registration_role = "family"
        
        # Statistics
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        
        print("🚀 Real-Time Face Authentication App Initialized")
        print("📸 Controls:")
        print("   'r' - Start registration mode")
        print("   't' - Start training mode")
        print("   's' - Show statistics")
        print("   'c' - Capture photo (during registration/training)")
        print("   'f' - Finish registration/training")
        print("   'q' - Quit")

    def start_camera(self, camera_index: int = 0):
        """Initialize camera"""
        self.video_capture = cv2.VideoCapture(camera_index)
        if not self.video_capture.isOpened():
            print(f"❌ Cannot open camera {camera_index}")
            return False
        
        # Set camera properties
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.video_capture.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"✅ Camera {camera_index} initialized")
        return True

    def calculate_fps(self):
        """Calculate current FPS"""
        self.fps_counter += 1
        if self.fps_counter % 30 == 0:
            elapsed = time.time() - self.fps_start_time
            self.current_fps = 30 / elapsed
            self.fps_start_time = time.time()

    def draw_ui_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw UI overlay on frame"""
        height, width = frame.shape[:2]
        
        # Create overlay
        overlay = frame.copy()
        
        # FPS counter
        cv2.putText(overlay, f"FPS: {self.current_fps:.1f}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # User count
        stats = self.face_auth.get_recognition_stats()
        cv2.putText(overlay, f"Users: {stats['total_users']} | Family: {stats['family_members']}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Mode indicator
        if self.registration_mode:
            cv2.rectangle(overlay, (10, height-120), (400, height-10), (0, 0, 255), -1)
            cv2.putText(overlay, "REGISTRATION MODE", (20, height-90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(overlay, f"Name: {self.registration_name}", (20, height-60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(overlay, f"Photos: {len(self.current_user_photos)}", (20, height-40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(overlay, "Press 'c' to capture, 'f' to finish", (20, height-20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        elif self.training_mode:
            cv2.rectangle(overlay, (10, height-100), (350, height-10), (0, 255, 255), -1)
            cv2.putText(overlay, "TRAINING MODE", (20, height-70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            cv2.putText(overlay, f"Photos: {len(self.current_user_photos)}", (20, height-40), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            cv2.putText(overlay, "Press 'c' to capture, 'f' to finish", (20, height-20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
        
        return overlay

    def draw_face_detection(self, frame: np.ndarray, face_locations: List, 
                          face_names: List, face_confidences: List) -> np.ndarray:
        """Draw face detection boxes and labels"""
        for (top, right, bottom, left), name, confidence in zip(face_locations, face_names, face_confidences):
            # Determine color based on recognition
            if name == "Unknown":
                color = (0, 0, 255)  # Red for unknown
                label = "Unknown"
            else:
                # Get user info
                user_id = None
                for uid, user in self.face_auth.users.items():
                    if user.name == name:
                        user_id = uid
                        break
                
                if user_id and user_id in self.face_auth.users:
                    user = self.face_auth.users[user_id]
                    if user.role == "family":
                        color = (0, 255, 0)  # Green for family
                    else:
                        color = (255, 165, 0)  # Orange for guests
                    label = f"{name} ({user.role})"
                else:
                    color = (0, 255, 255)  # Yellow for recognized but unknown role
                    label = name
            
            # Draw face rectangle
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw label background
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            
            # Draw label text
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, label, (left + 6, bottom - 10), font, 0.5, (255, 255, 255), 1)
            
            # Draw confidence score
            if confidence > 0:
                cv2.putText(frame, f"{confidence:.2f}", (left + 6, bottom - 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        return frame

    def handle_registration_mode(self):
        """Handle user registration"""
        if not self.registration_name:
            self.registration_name = input("\n👤 Enter user name: ").strip()
            if not self.registration_name:
                print("❌ Invalid name!")
                self.registration_mode = False
                return
            
            role_choice = input("👥 Role (f=family, g=guest): ").strip().lower()
            self.registration_role = "family" if role_choice == "f" else "guest"
            print(f"📸 Registration started for {self.registration_name} ({self.registration_role})")
            print("Position your face in the camera and press 'c' to capture photos")

    def handle_training_mode(self):
        """Handle training mode for existing users"""
        users = self.face_auth.get_users_list()
        if not users:
            print("❌ No users found! Register users first.")
            self.training_mode = False
            return
        
        print("\n👥 Available users:")
        for i, user in enumerate(users):
            print(f"{i+1}. {user.name} ({user.role}) - {user.photo_count} photos")
        
        try:
            choice = int(input("Select user number: ")) - 1
            if 0 <= choice < len(users):
                self.selected_user = users[choice]
                print(f"🎯 Training mode for {self.selected_user.name}")
                print("Position your face and press 'c' to capture additional training photos")
            else:
                print("❌ Invalid selection!")
                self.training_mode = False
        except ValueError:
            print("❌ Invalid input!")
            self.training_mode = False

    def capture_photo(self):
        """Capture current frame as training photo"""
        if self.current_frame is not None:
            self.current_user_photos.append(self.current_frame.copy())
            print(f"📸 Captured photo {len(self.current_user_photos)}")

    def finish_registration(self):
        """Finish user registration"""
        if len(self.current_user_photos) < 3:
            print("❌ Please capture at least 3 photos!")
            return
        
        success, message = self.face_auth.register_user(
            self.registration_name, 
            self.current_user_photos, 
            self.registration_role
        )
        
        print(f"{'✅' if success else '❌'} {message}")
        
        # Reset registration state
        self.registration_mode = False
        self.registration_name = ""
        self.current_user_photos = []

    def finish_training(self):
        """Finish training session"""
        if not hasattr(self, 'selected_user') or len(self.current_user_photos) < 1:
            print("❌ Please capture at least 1 training photo!")
            return
        
        success, message = self.face_auth.add_training_photos(
            self.selected_user.user_id, 
            self.current_user_photos
        )
        
        print(f"{'✅' if success else '❌'} {message}")
        
        # Reset training state
        self.training_mode = False
        self.current_user_photos = []
        if hasattr(self, 'selected_user'):
            delattr(self, 'selected_user')

    def show_statistics(self):
        """Display system statistics"""
        stats = self.face_auth.get_recognition_stats()
        print("\n📊 System Statistics:")
        print(f"👥 Total Users: {stats['total_users']}")
        print(f"👨‍👩‍👧‍👦 Family Members: {stats['family_members']}")
        print(f"👤 Guests: {stats['guests']}")
        print(f"🧠 Face Encodings: {stats['total_encodings']}")
        print(f"🎯 Recognition Events: {stats['total_recognitions']}")
        
        print("\n👥 User List:")
        for user in self.face_auth.get_users_list():
            last_seen = user.last_seen if user.last_seen else "Never"
            print(f"  • {user.name} ({user.role}) - {user.photo_count} photos - Last seen: {last_seen}")

    def run(self):
        """Main application loop"""
        if not self.start_camera():
            return
        
        self.is_running = True
        print("\n🎥 Camera started! Press keys for controls...")
        
        try:
            while self.is_running:
                ret, frame = self.video_capture.read()
                if not ret:
                    print("❌ Failed to read frame")
                    break
                
                self.current_frame = frame
                self.calculate_fps()
                
                # Perform face recognition
                face_locations, face_names, face_confidences = self.face_auth.recognize_faces(frame)
                
                # Draw detections
                frame = self.draw_face_detection(frame, face_locations, face_names, face_confidences)
                
                # Draw UI overlay
                frame = self.draw_ui_overlay(frame)
                
                # Display frame
                cv2.imshow('Guardia AI - Real-Time Face Authentication', frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.registration_mode = True
                    self.handle_registration_mode()
                elif key == ord('t'):
                    self.training_mode = True
                    self.handle_training_mode()
                elif key == ord('c'):
                    if self.registration_mode or self.training_mode:
                        self.capture_photo()
                elif key == ord('f'):
                    if self.registration_mode:
                        self.finish_registration()
                    elif self.training_mode:
                        self.finish_training()
                elif key == ord('s'):
                    self.show_statistics()
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        self.is_running = False
        if self.video_capture:
            self.video_capture.release()
        cv2.destroyAllWindows()
        print("✅ Cleanup completed")

def main():
    """Main function"""
    print("🔥 Guardia AI - Real-Time Face Authentication System")
    print("=" * 50)
    
    # Create and run the application
    app = RealTimeFaceAuthApp()
    app.run()

if __name__ == "__main__":
    main()
