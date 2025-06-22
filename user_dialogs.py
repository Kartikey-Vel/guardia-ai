#!/usr/bin/env python3
"""
User Interface Dialogs for Face Authentication System
Registration and management dialogs for users and family members
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk
from pathlib import Path
from typing import List, Optional
import threading
import time

class UserRegistrationDialog:
    """Dialog for registering new users with face capture"""
    
    def __init__(self, parent, auth_system, callback=None):
        self.parent = parent
        self.auth_system = auth_system
        self.callback = callback
        
        # Dialog state
        self.captured_photos = []
        self.is_capturing = False
        self.cap = None
        self.current_frame = None
        
        self._create_dialog()
        self._start_camera()
    
    def _create_dialog(self):
        """Create the registration dialog"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("Register New User")
        self.dialog.geometry("800x600")
        self.dialog.resizable(False, False)
        
        # Make modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Main layout
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_columnconfigure(1, weight=1)
        
        # Left side - Camera feed
        self.camera_frame = ctk.CTkFrame(self.dialog)
        self.camera_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        self.camera_label = ctk.CTkLabel(self.camera_frame, text="📹 Live Camera Feed")
        self.camera_label.pack(pady=10)
        
        self.video_canvas = tk.Canvas(self.camera_frame, width=320, height=240, bg='black')
        self.video_canvas.pack(pady=10)
        
        # Capture controls
        self.capture_frame = ctk.CTkFrame(self.camera_frame)
        self.capture_frame.pack(pady=10, fill="x", padx=20)
        
        self.capture_button = ctk.CTkButton(
            self.capture_frame,
            text="📸 Capture Photo",
            command=self._capture_photo,
            height=40
        )
        self.capture_button.pack(pady=5)
        
        self.photos_count_label = ctk.CTkLabel(self.capture_frame, text="Photos captured: 0/5")
        self.photos_count_label.pack(pady=5)
        
        # Right side - User details and captured photos
        self.details_frame = ctk.CTkFrame(self.dialog)
        self.details_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # User details
        self.details_label = ctk.CTkLabel(self.details_frame, text="👤 User Details", font=ctk.CTkFont(size=18, weight="bold"))
        self.details_label.pack(pady=20)
        
        # Name entry
        self.name_label = ctk.CTkLabel(self.details_frame, text="Full Name:")
        self.name_label.pack(anchor="w", padx=20)
        
        self.name_entry = ctk.CTkEntry(self.details_frame, placeholder_text="Enter full name...")
        self.name_entry.pack(fill="x", padx=20, pady=(0, 10))
        
        # Role selection
        self.role_label = ctk.CTkLabel(self.details_frame, text="Role:")
        self.role_label.pack(anchor="w", padx=20)
        
        self.role_var = ctk.StringVar(value="user")
        self.role_frame = ctk.CTkFrame(self.details_frame)
        self.role_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.admin_radio = ctk.CTkRadioButton(self.role_frame, text="👑 Admin", variable=self.role_var, value="admin")
        self.admin_radio.pack(side="left", padx=10, pady=10)
        
        self.family_radio = ctk.CTkRadioButton(self.role_frame, text="👨‍👩‍👧‍👦 Family", variable=self.role_var, value="family")
        self.family_radio.pack(side="left", padx=10, pady=10)
        
        self.user_radio = ctk.CTkRadioButton(self.role_frame, text="👤 User", variable=self.role_var, value="user")
        self.user_radio.pack(side="left", padx=10, pady=10)
        
        # Captured photos display
        self.photos_label = ctk.CTkLabel(self.details_frame, text="📷 Captured Photos")
        self.photos_label.pack(pady=(20, 10))
        
        self.photos_scrollframe = ctk.CTkScrollableFrame(self.details_frame, height=150)
        self.photos_scrollframe.pack(fill="x", padx=20, pady=(0, 20))
        
        # Action buttons
        self.button_frame = ctk.CTkFrame(self.details_frame)
        self.button_frame.pack(fill="x", padx=20, pady=20)
        
        self.register_button = ctk.CTkButton(
            self.button_frame,
            text="✅ Register User",
            command=self._register_user,
            height=40,
            state="disabled"
        )
        self.register_button.pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        self.cancel_button = ctk.CTkButton(
            self.button_frame,
            text="❌ Cancel",
            command=self._cancel_registration,
            height=40
        )
        self.cancel_button.pack(side="right", padx=(10, 0), fill="x", expand=True)
        
        # Start video update
        self._update_video()
    
    def _start_camera(self):
        """Start camera for face capture"""
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Camera Error", "Could not open camera")
                return
            
            self.is_capturing = True
            
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to start camera: {e}")
    
    def _update_video(self):
        """Update video feed"""
        try:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    self.current_frame = frame.copy()
                    
                    # Resize for display
                    frame = cv2.resize(frame, (320, 240))
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to PhotoImage
                    img = Image.fromarray(frame_rgb)
                    photo = ImageTk.PhotoImage(img)
                    
                    # Update canvas
                    self.video_canvas.delete("all")
                    self.video_canvas.create_image(160, 120, image=photo)
                    self.video_canvas.image = photo  # Keep reference
            
            # Schedule next update
            if self.is_capturing:
                self.dialog.after(33, self._update_video)  # ~30 FPS
                
        except Exception as e:
            print(f"❌ Video update error: {e}")
            if self.is_capturing:
                self.dialog.after(100, self._update_video)
    
    def _capture_photo(self):
        """Capture a photo for face registration"""
        try:
            if self.current_frame is not None and len(self.captured_photos) < 5:
                # Detect faces to ensure there's a face in the photo
                gray = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2GRAY)
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                if len(faces) == 0:
                    messagebox.showwarning("No Face Detected", "Please position your face in the camera view and try again.")
                    return
                elif len(faces) > 1:
                    messagebox.showwarning("Multiple Faces", "Please ensure only one person is in the camera view.")
                    return
                
                # Add photo to collection
                self.captured_photos.append(self.current_frame.copy())
                
                # Update display
                self._update_photos_display()
                self.photos_count_label.configure(text=f"Photos captured: {len(self.captured_photos)}/5")
                
                # Enable register button if we have enough photos and name
                if len(self.captured_photos) >= 3 and self.name_entry.get().strip():
                    self.register_button.configure(state="normal")
                
                # Visual feedback
                self.capture_button.configure(text="✅ Photo Captured!")
                self.dialog.after(1000, lambda: self.capture_button.configure(text="📸 Capture Photo"))
                
        except Exception as e:
            messagebox.showerror("Capture Error", f"Failed to capture photo: {e}")
    
    def _update_photos_display(self):
        """Update the captured photos display"""
        try:
            # Clear existing photos
            for widget in self.photos_scrollframe.winfo_children():
                widget.destroy()
            
            # Display captured photos
            for i, photo in enumerate(self.captured_photos):
                # Resize photo for display
                photo_small = cv2.resize(photo, (80, 60))
                photo_rgb = cv2.cvtColor(photo_small, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(photo_rgb)
                photo_tk = ImageTk.PhotoImage(img)
                
                # Create photo label
                photo_frame = ctk.CTkFrame(self.photos_scrollframe)
                photo_frame.pack(side="left", padx=5, pady=5)
                
                photo_label = tk.Label(photo_frame, image=photo_tk)
                photo_label.image = photo_tk  # Keep reference
                photo_label.pack(pady=5)
                
                # Add remove button
                remove_btn = ctk.CTkButton(
                    photo_frame,
                    text="🗑️",
                    width=30,
                    height=20,
                    command=lambda idx=i: self._remove_photo(idx)
                )
                remove_btn.pack(pady=2)
                
        except Exception as e:
            print(f"❌ Photos display error: {e}")
    
    def _remove_photo(self, index):
        """Remove a captured photo"""
        try:
            if 0 <= index < len(self.captured_photos):
                self.captured_photos.pop(index)
                self._update_photos_display()
                self.photos_count_label.configure(text=f"Photos captured: {len(self.captured_photos)}/5")
                
                # Update register button state
                if len(self.captured_photos) < 3 or not self.name_entry.get().strip():
                    self.register_button.configure(state="disabled")
                    
        except Exception as e:
            print(f"❌ Remove photo error: {e}")
    
    def _register_user(self):
        """Register the new user"""
        try:
            name = self.name_entry.get().strip()
            role = self.role_var.get()
            
            if not name:
                messagebox.showerror("Invalid Input", "Please enter a name")
                return
            
            if len(self.captured_photos) < 3:
                messagebox.showerror("Insufficient Photos", "Please capture at least 3 photos")
                return
            
            # Register user
            success, message = self.auth_system.register_user(name, role, self.captured_photos)
            
            if success:
                messagebox.showinfo("Registration Successful", message)
                if self.callback:
                    self.callback()
                self._close_dialog()
            else:
                messagebox.showerror("Registration Failed", message)
                
        except Exception as e:
            messagebox.showerror("Registration Error", f"Failed to register user: {e}")
    
    def _cancel_registration(self):
        """Cancel registration and close dialog"""
        self._close_dialog()
    
    def _close_dialog(self):
        """Close the dialog and clean up"""
        self.is_capturing = False
        if self.cap:
            self.cap.release()
        self.dialog.destroy()

class UserManagementDialog:
    """Dialog for managing existing users"""
    
    def __init__(self, parent, auth_system, callback=None):
        self.parent = parent
        self.auth_system = auth_system
        self.callback = callback
        
        self._create_dialog()
        self._load_users()
    
    def _create_dialog(self):
        """Create the user management dialog"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("User Management")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        
        # Make modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Main layout
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(1, weight=1)
        
        # Header
        self.header_label = ctk.CTkLabel(self.dialog, text="👥 User Management", font=ctk.CTkFont(size=20, weight="bold"))
        self.header_label.grid(row=0, column=0, pady=20)
        
        # Statistics
        self.stats_frame = ctk.CTkFrame(self.dialog)
        self.stats_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        stats = self.auth_system.get_user_stats()
        self.stats_label = ctk.CTkLabel(
            self.stats_frame, 
            text=f"Total Users: {stats['total_users']} | Active: {stats['active_users']} | Family: {stats['family_members']}"
        )
        self.stats_label.pack(pady=10)
        
        # Users list
        self.users_frame = ctk.CTkScrollableFrame(self.dialog)
        self.users_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        
        # Action buttons
        self.buttons_frame = ctk.CTkFrame(self.dialog)
        self.buttons_frame.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.refresh_button = ctk.CTkButton(
            self.buttons_frame,
            text="🔄 Refresh",
            command=self._load_users,
            height=35
        )
        self.refresh_button.pack(side="left", padx=(0, 10))
        
        self.close_button = ctk.CTkButton(
            self.buttons_frame,
            text="❌ Close",
            command=self._close_dialog,
            height=35
        )
        self.close_button.pack(side="right", padx=(10, 0))
    
    def _load_users(self):
        """Load and display users"""
        try:
            # Clear existing users
            for widget in self.users_frame.winfo_children():
                widget.destroy()
            
            users = self.auth_system.list_users()
            
            if not users:
                no_users_label = ctk.CTkLabel(self.users_frame, text="No users registered yet")
                no_users_label.pack(pady=20)
                return
            
            # Display each user
            for user in users:
                user_frame = ctk.CTkFrame(self.users_frame)
                user_frame.pack(fill="x", padx=10, pady=5)
                user_frame.grid_columnconfigure(0, weight=1)
                
                # User info
                role_emoji = {"admin": "👑", "family": "👨‍👩‍👧‍👦", "user": "👤"}.get(user.role, "👤")
                status_emoji = "✅" if user.is_active else "❌"
                
                info_text = f"{role_emoji} {user.name} ({user.role.title()}) {status_emoji}"
                if user.last_seen:
                    info_text += f" | Last seen: {user.last_seen.strftime('%Y-%m-%d %H:%M')}"
                
                info_label = ctk.CTkLabel(user_frame, text=info_text)
                info_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
                
                # Action buttons
                button_frame = ctk.CTkFrame(user_frame)
                button_frame.grid(row=0, column=1, padx=10, pady=5)
                
                toggle_btn = ctk.CTkButton(
                    button_frame,
                    text="Deactivate" if user.is_active else "Activate",
                    command=lambda u=user: self._toggle_user(u),
                    width=80,
                    height=25
                )
                toggle_btn.pack(side="left", padx=2)
                
                delete_btn = ctk.CTkButton(
                    button_frame,
                    text="🗑️",
                    command=lambda u=user: self._delete_user(u),
                    width=30,
                    height=25,
                    fg_color="red"
                )
                delete_btn.pack(side="left", padx=2)
                
        except Exception as e:
            print(f"❌ Error loading users: {e}")
    
    def _toggle_user(self, user):
        """Toggle user active status"""
        try:
            user.is_active = not user.is_active
            self.auth_system.save_user_data()
            self._load_users()
            
            if self.callback:
                self.callback()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to toggle user: {e}")
    
    def _delete_user(self, user):
        """Delete a user"""
        try:
            result = messagebox.askyesno(
                "Confirm Delete", 
                f"Are you sure you want to delete user '{user.name}'?\nThis action cannot be undone."
            )
            
            if result:
                success = self.auth_system.delete_user(user.user_id)
                if success:
                    messagebox.showinfo("Success", f"User '{user.name}' deleted successfully")
                    self._load_users()
                    
                    if self.callback:
                        self.callback()
                else:
                    messagebox.showerror("Error", "Failed to delete user")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete user: {e}")
    
    def _close_dialog(self):
        """Close the dialog"""
        self.dialog.destroy()
