#!/usr/bin/env python3
"""
User Authentication and Face Recognition System
Manages user profiles, face encodings, and family member recognition
"""
import os
import json
import pickle
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import cv2
import face_recognition

class UserProfile:
    """User profile with face recognition data"""
    
    def __init__(self, user_id: str, name: str, role: str = "user"):
        self.user_id = user_id
        self.name = name
        self.role = role  # "admin", "user", "family", "guest"
        self.face_encodings = []
        self.created_at = datetime.now()
        self.last_seen = None
        self.access_count = 0
        self.is_active = True
        
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "access_count": self.access_count,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create UserProfile from dictionary"""
        profile = cls(data["user_id"], data["name"], data["role"])
        profile.created_at = datetime.fromisoformat(data["created_at"])
        profile.last_seen = datetime.fromisoformat(data["last_seen"]) if data["last_seen"] else None
        profile.access_count = data["access_count"]
        profile.is_active = data["is_active"]
        return profile

class FaceAuthSystem:
    """Complete face authentication and recognition system"""
    
    def __init__(self, data_dir: str = "user_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # File paths
        self.users_file = self.data_dir / "users.json"
        self.encodings_file = self.data_dir / "face_encodings.pkl"
        self.photos_dir = self.data_dir / "photos"
        self.photos_dir.mkdir(exist_ok=True)
        
        # User data
        self.users: Dict[str, UserProfile] = {}
        self.face_encodings: Dict[str, List[np.ndarray]] = {}
        
        # Settings
        self.face_tolerance = 0.6
        self.min_face_size = 50
        self.max_faces_per_user = 10
        
        # Load existing data
        self.load_user_data()
    
    def load_user_data(self):
        """Load user profiles and face encodings"""
        try:
            # Load user profiles
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    self.users = {uid: UserProfile.from_dict(data) for uid, data in users_data.items()}
            
            # Load face encodings
            if self.encodings_file.exists():
                with open(self.encodings_file, 'rb') as f:
                    self.face_encodings = pickle.load(f)
            
            print(f"✅ Loaded {len(self.users)} user profiles with face recognition")
            
        except Exception as e:
            print(f"❌ Error loading user data: {e}")
            self.users = {}
            self.face_encodings = {}
    
    def save_user_data(self):
        """Save user profiles and face encodings"""
        try:
            # Save user profiles
            users_data = {uid: user.to_dict() for uid, user in self.users.items()}
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=2)
            
            # Save face encodings
            with open(self.encodings_file, 'wb') as f:
                pickle.dump(self.face_encodings, f)
            
            print(f"✅ Saved {len(self.users)} user profiles")
            
        except Exception as e:
            print(f"❌ Error saving user data: {e}")
    
    def register_user(self, name: str, role: str = "user", photos: List[np.ndarray] = None) -> Tuple[bool, str]:
        """Register a new user with face photos"""
        try:
            # Generate user ID
            user_id = f"user_{len(self.users) + 1:04d}"
            
            # Create user profile
            user = UserProfile(user_id, name, role)
            
            # Process face photos if provided
            if photos:
                success, message = self.add_face_photos(user_id, photos)
                if not success:
                    return False, f"Failed to process face photos: {message}"
            
            # Add user to system
            self.users[user_id] = user
            self.save_user_data()
            
            return True, f"User '{name}' registered successfully with ID: {user_id}"
            
        except Exception as e:
            return False, f"Registration failed: {e}"
    
    def add_face_photos(self, user_id: str, photos: List[np.ndarray]) -> Tuple[bool, str]:
        """Add face photos for a user and generate encodings"""
        try:
            if user_id not in self.users:
                return False, "User not found"
            
            encodings = []
            saved_photos = 0
            
            for i, photo in enumerate(photos):
                # Detect faces in the photo
                rgb_photo = cv2.cvtColor(photo, cv2.COLOR_BGR2RGB)
                face_locations = face_recognition.face_locations(rgb_photo)
                
                if len(face_locations) == 0:
                    print(f"⚠️ No face detected in photo {i+1}")
                    continue
                elif len(face_locations) > 1:
                    print(f"⚠️ Multiple faces detected in photo {i+1}, using largest")
                
                # Use the largest face if multiple detected
                largest_face = max(face_locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))
                
                # Check minimum face size
                face_height = largest_face[2] - largest_face[0]
                face_width = largest_face[1] - largest_face[3]
                if min(face_height, face_width) < self.min_face_size:
                    print(f"⚠️ Face too small in photo {i+1}")
                    continue
                
                # Generate face encoding
                face_encodings = face_recognition.face_encodings(rgb_photo, [largest_face])
                if len(face_encodings) > 0:
                    encodings.append(face_encodings[0])
                    
                    # Save photo
                    photo_path = self.photos_dir / f"{user_id}_{saved_photos + 1}.jpg"
                    cv2.imwrite(str(photo_path), photo)
                    saved_photos += 1
                    
                    if saved_photos >= self.max_faces_per_user:
                        break
            
            if len(encodings) == 0:
                return False, "No valid face encodings generated"
            
            # Store encodings
            self.face_encodings[user_id] = encodings
            self.users[user_id].face_encodings = encodings
            
            self.save_user_data()
            
            return True, f"Added {len(encodings)} face encodings for user"
            
        except Exception as e:
            return False, f"Error processing face photos: {e}"
    
    def recognize_face(self, frame: np.ndarray) -> Tuple[Optional[UserProfile], float, np.ndarray]:
        """Recognize face in frame and return user profile"""
        try:
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Find all face locations and encodings
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            best_match = None
            best_distance = float('inf')
            best_location = None
            
            for face_encoding, face_location in zip(face_encodings, face_locations):
                # Compare with all known users
                for user_id, known_encodings in self.face_encodings.items():
                    if not self.users[user_id].is_active:
                        continue
                    
                    # Calculate distances to all encodings for this user
                    distances = face_recognition.face_distance(known_encodings, face_encoding)
                    min_distance = np.min(distances)
                    
                    # Check if this is the best match so far
                    if min_distance < self.face_tolerance and min_distance < best_distance:
                        best_match = self.users[user_id]
                        best_distance = min_distance
                        best_location = face_location
            
            # Update user statistics if recognized
            if best_match:
                best_match.last_seen = datetime.now()
                best_match.access_count += 1
                self.save_user_data()
            
            return best_match, 1.0 - best_distance, best_location if best_location else np.array([])
            
        except Exception as e:
            print(f"❌ Face recognition error: {e}")
            return None, 0.0, np.array([])
    
    def get_user_stats(self) -> Dict:
        """Get system statistics"""
        total_users = len(self.users)
        active_users = sum(1 for user in self.users.values() if user.is_active)
        family_members = sum(1 for user in self.users.values() if user.role == "family")
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "family_members": family_members,
            "total_encodings": sum(len(encodings) for encodings in self.face_encodings.values())
        }
    
    def list_users(self) -> List[UserProfile]:
        """Get list of all users"""
        return list(self.users.values())
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user and their data"""
        try:
            if user_id not in self.users:
                return False
            
            # Remove face encodings
            if user_id in self.face_encodings:
                del self.face_encodings[user_id]
            
            # Remove user profile
            del self.users[user_id]
            
            # Remove photos
            for photo_file in self.photos_dir.glob(f"{user_id}_*.jpg"):
                photo_file.unlink()
            
            self.save_user_data()
            return True
            
        except Exception as e:
            print(f"❌ Error deleting user: {e}")
            return False
