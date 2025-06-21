"""
Guardian System - Core surveillance management
Main system controller that coordinates all surveillance activities
"""
import threading
import time
from typing import Dict, List, Optional
from pathlib import Path

from src.core.camera_manager import CameraManager
from src.core.face_detector import FaceDetector
from src.core.alert_manager import AlertManager
from src.core.user_manager import UserManager
from src.utils.logger import get_logger
from src.utils.cli import *
import config.settings as settings

logger = get_logger(__name__)

class GuardianSystem:
    """Main Guardian surveillance system"""
    
    def __init__(self):
        self.camera_manager = None
        self.face_detector = None
        self.alert_manager = None
        self.user_manager = UserManager()
        self.surveillance_active = False
        self.surveillance_thread = None
        
        logger.info("🛡️ Guardian System initialized")
    
    def user_management_menu(self):
        """Handle user management operations"""
        options = [
            "👤 Create New User",
            "🔐 Login",
            "📝 List Users",
            "🗑️ Delete User",
            "🔙 Back to Main Menu"
        ]
        
        choice = display_menu("User Management", options)
        
        if choice == "1":
            self._create_user()
        elif choice == "2":
            self._login_user()
        elif choice == "3":
            self._list_users()
        elif choice == "4":
            self._delete_user()
    
    def family_management_menu(self):
        """Handle family member management"""
        if not self.user_manager.current_user:
            print_status("Please login first", "ERROR")
            return
        
        options = [
            "👨‍👩‍👧‍👦 Add Family Member",
            "📋 List Family Members",
            "🗑️ Remove Family Member",
            "📷 Update Face Photo",
            "🔙 Back to Main Menu"
        ]
        
        choice = display_menu("Family Management", options)
        
        if choice == "1":
            self._add_family_member()
        elif choice == "2":
            self._list_family_members()
        elif choice == "3":
            self._remove_family_member()
        elif choice == "4":
            self._update_face_photo()
    
    def start_surveillance(self):
        """Start the surveillance system"""
        if not self.user_manager.current_user:
            print_status("Please login first", "ERROR")
            return
        
        if self.surveillance_active:
            print_status("Surveillance is already running", "WARNING")
            return
        
        print_status("Initializing surveillance system...", "LOADING")
        
        try:
            # Initialize components
            self.camera_manager = CameraManager()
            self.face_detector = FaceDetector()
            self.alert_manager = AlertManager(self.user_manager.current_user["email"])
            
            # Load known faces
            known_faces = self.user_manager.get_family_faces()
            self.face_detector.load_known_faces(known_faces)
            
            print_status("Starting surveillance...", "SUCCESS")
            
            # Start surveillance in a separate thread
            self.surveillance_active = True
            self.surveillance_thread = threading.Thread(target=self._surveillance_loop, daemon=True)
            self.surveillance_thread.start()
            
            print_status("Surveillance active! Press 'q' to stop", "SUCCESS")
            
            # Wait for user to stop surveillance
            while self.surveillance_active:
                if input().lower() == 'q':
                    self.stop_surveillance()
                    break
                    
        except Exception as e:
            print_status(f"Failed to start surveillance: {e}", "ERROR")
            logger.error(f"Surveillance startup error: {e}")
    
    def stop_surveillance(self):
        """Stop the surveillance system"""
        if self.surveillance_active:
            print_status("Stopping surveillance...", "LOADING")
            self.surveillance_active = False
            
            if self.camera_manager:
                self.camera_manager.release()
            
            print_status("Surveillance stopped", "SUCCESS")
            logger.info("Surveillance stopped by user")
    
    def show_system_status(self):
        """Display system status information"""
        print_separator()
        print("📊 SYSTEM STATUS")
        print_separator()
        
        # User status
        if self.user_manager.current_user:
            print(f"👤 Current User: {self.user_manager.current_user['username']}")
            family_count = len(self.user_manager.get_family_members())
            print(f"👨‍👩‍👧‍👦 Family Members: {family_count}")
        else:
            print("👤 Current User: Not logged in")
        
        # System status
        print(f"🎥 Surveillance: {'Active' if self.surveillance_active else 'Inactive'}")
        print(f"📁 Data Directory: {settings.DATA_DIR}")
        print(f"📷 Camera Index: {settings.CAMERA_INDEX}")
        print(f"🔧 Debug Mode: {'Enabled' if settings.DEBUG_MODE else 'Disabled'}")
        
        # Database status
        db_status = self.user_manager.test_connection()
        print(f"🗄️ Database: {'Connected' if db_status else 'Disconnected'}")
        
        print_separator()
    
    def settings_menu(self):
        """Handle system settings"""
        options = [
            "📷 Camera Settings",
            "🚨 Alert Settings",
            "🗄️ Database Settings",
            "🔙 Back to Main Menu"
        ]
        
        choice = display_menu("System Settings", options)
        
        if choice == "1":
            self._camera_settings()
        elif choice == "2":
            self._alert_settings()
        elif choice == "3":
            self._database_settings()
    
    def _surveillance_loop(self):
        """Main surveillance processing loop"""
        logger.info("Surveillance loop started")
        
        while self.surveillance_active:
            try:
                # Capture frame
                frame = self.camera_manager.get_frame()
                if frame is None:
                    continue
                
                # Detect faces
                faces = self.face_detector.detect_faces(frame)
                
                # Process detections
                for face in faces:
                    if face["is_unknown"]:
                        self.alert_manager.handle_unknown_person(face)
                
                # Display frame (if in debug mode)
                if settings.DEBUG_MODE:
                    self.camera_manager.display_frame(frame, faces)
                
                time.sleep(settings.PROCESSING_INTERVAL)
                
            except Exception as e:
                logger.error(f"Surveillance loop error: {e}")
                time.sleep(1)
        
        logger.info("Surveillance loop ended")
    
    # Private helper methods
    def _create_user(self):
        """Create a new user account"""
        print_separator()
        username = get_user_input("👤 Enter username: ")
        email = get_user_input("📧 Enter email: ")
        password = get_user_input("🔐 Enter password: ")
        
        try:
            self.user_manager.create_user(username, email, password)
            print_status(f"User '{username}' created successfully", "SUCCESS")
        except Exception as e:
            print_status(f"Failed to create user: {e}", "ERROR")
    
    def _login_user(self):
        """Login user"""
        print_separator()
        username = get_user_input("👤 Username: ")
        password = get_user_input("🔐 Password: ")
        
        if self.user_manager.login(username, password):
            print_status(f"Welcome back, {username}!", "SUCCESS")
        else:
            print_status("Login failed", "ERROR")
    
    def _list_users(self):
        """List all users"""
        users = self.user_manager.list_users()
        print_separator()
        print("👥 REGISTERED USERS")
        print_separator()
        for user in users:
            print(f"👤 {user['username']} ({user['email']})")
    
    def _delete_user(self):
        """Delete a user"""
        username = get_user_input("👤 Username to delete: ")
        if confirm_action(f"Delete user '{username}'?"):
            try:
                self.user_manager.delete_user(username)
                print_status(f"User '{username}' deleted", "SUCCESS")
            except Exception as e:
                print_status(f"Failed to delete user: {e}", "ERROR")
    
    def _add_family_member(self):
        """Add a family member"""
        print_separator()
        name = get_user_input("👤 Family member name: ")
        relation = get_user_input("👨‍👩‍👧‍👦 Relation (e.g., spouse, child): ")
        
        try:
            self.user_manager.add_family_member(name, relation)
            print_status(f"Family member '{name}' added", "SUCCESS")
            
            if confirm_action("Add face photo for better recognition?"):
                self._capture_face_photo(name)
                
        except Exception as e:
            print_status(f"Failed to add family member: {e}", "ERROR")
    
    def _list_family_members(self):
        """List family members"""
        members = self.user_manager.get_family_members()
        print_separator()
        print("👨‍👩‍👧‍👦 FAMILY MEMBERS")
        print_separator()
        for member in members:
            has_photo = "📷" if member.get("has_photo") else "❌"
            print(f"{has_photo} {member['name']} ({member['relation']})")
    
    def _remove_family_member(self):
        """Remove a family member"""
        name = get_user_input("👤 Family member name to remove: ")
        if confirm_action(f"Remove '{name}' from family?"):
            try:
                self.user_manager.remove_family_member(name)
                print_status(f"Family member '{name}' removed", "SUCCESS")
            except Exception as e:
                print_status(f"Failed to remove family member: {e}", "ERROR")
    
    def _update_face_photo(self):
        """Update face photo for a family member"""
        name = get_user_input("👤 Family member name: ")
        self._capture_face_photo(name)
    
    def _capture_face_photo(self, name: str):
        """Capture face photo for recognition"""
        try:
            camera = CameraManager()
            print_status(f"Capturing photo for {name}. Look at the camera and press SPACE", "INFO")
            
            success = camera.capture_face_photo(name)
            if success:
                print_status(f"Photo captured for {name}", "SUCCESS")
            else:
                print_status("Failed to capture photo", "ERROR")
                
            camera.release()
            
        except Exception as e:
            print_status(f"Failed to capture photo: {e}", "ERROR")
    
    def _camera_settings(self):
        """Configure camera settings"""
        print_status("Camera settings - Not yet implemented", "WARNING")
    
    def _alert_settings(self):
        """Configure alert settings"""
        print_status("Alert settings - Not yet implemented", "WARNING")
    
    def _database_settings(self):
        """Configure database settings"""
        print_status("Database settings - Not yet implemented", "WARNING")
