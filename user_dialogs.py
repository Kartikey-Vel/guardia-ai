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

class ModelTrainingDialog:
    """Dialog for training and improving face recognition models"""
    
    def __init__(self, parent, auth_system, callback=None):
        self.parent = parent
        self.auth_system = auth_system
        self.callback = callback
        
        # Training state
        self.training_photos = []
        self.selected_user = None
        self.is_capturing = False
        self.cap = None
        self.current_frame = None
        
        self._create_dialog()
        
    def _create_dialog(self):
        """Create the model training dialog"""
        self.dialog = ctk.CTkToplevel(self.parent)
        self.dialog.title("🧠 Face Model Training")
        self.dialog.geometry("900x700")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Configure grid
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(0, weight=1)
        
        # Main container
        self.main_frame = ctk.CTkFrame(self.dialog)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="🧠 Face Recognition Model Training",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=20)
        
        # Left panel - User selection and controls
        self.control_frame = ctk.CTkFrame(self.main_frame, width=300)
        self.control_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.control_frame.grid_propagate(False)
        
        # User selection
        user_label = ctk.CTkLabel(self.control_frame, text="👤 Select User:", font=ctk.CTkFont(weight="bold"))
        user_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        users = self.auth_system.list_users()
        user_names = [f"{user.name} ({user.user_id})" for user in users]
        
        self.user_selector = ctk.CTkOptionMenu(
            self.control_frame,
            values=user_names if user_names else ["No users available"],
            command=self._on_user_selected
        )
        self.user_selector.pack(fill="x", padx=15, pady=(0, 15))
        
        # Model quality display
        self.quality_frame = ctk.CTkFrame(self.control_frame)
        self.quality_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        quality_title = ctk.CTkLabel(self.quality_frame, text="📊 Current Model Quality", font=ctk.CTkFont(weight="bold"))
        quality_title.pack(pady=10)
        
        self.quality_text = ctk.CTkTextbox(self.quality_frame, height=150)
        self.quality_text.pack(fill="both", padx=10, pady=(0, 10))
        
        # Training controls
        self.training_controls = ctk.CTkFrame(self.control_frame)
        self.training_controls.pack(fill="x", padx=15, pady=(0, 15))
        
        controls_title = ctk.CTkLabel(self.training_controls, text="🎯 Training Options", font=ctk.CTkFont(weight="bold"))
        controls_title.pack(pady=10)
        
        self.optimize_button = ctk.CTkButton(
            self.training_controls,
            text="⚡ Optimize Current Model",
            command=self._optimize_model,
            height=35
        )
        self.optimize_button.pack(fill="x", padx=10, pady=5)
        
        self.add_photos_button = ctk.CTkButton(
            self.training_controls,
            text="📁 Add Photos from Files",
            command=self._add_photos_from_files,
            height=35
        )
        self.add_photos_button.pack(fill="x", padx=10, pady=5)
        
        self.capture_button = ctk.CTkButton(
            self.training_controls,
            text="📸 Capture New Photos",
            command=self._toggle_camera,
            height=35
        )
        self.capture_button.pack(fill="x", padx=10, pady=5)
        
        # Batch training
        batch_frame = ctk.CTkFrame(self.control_frame)
        batch_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        batch_title = ctk.CTkLabel(batch_frame, text="🔄 Batch Operations", font=ctk.CTkFont(weight="bold"))
        batch_title.pack(pady=10)
        
        self.batch_train_button = ctk.CTkButton(
            batch_frame,
            text="🚀 Train All Users",
            command=self._batch_train,
            height=35
        )
        self.batch_train_button.pack(fill="x", padx=10, pady=5)
        
        self.analyze_all_button = ctk.CTkButton(
            batch_frame,
            text="📊 Analyze All Models",
            command=self._analyze_all,
            height=35
        )
        self.analyze_all_button.pack(fill="x", padx=10, pady=5)
        
        # Right panel - Camera/photo display
        self.display_frame = ctk.CTkFrame(self.main_frame)
        self.display_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        self.display_frame.grid_columnconfigure(0, weight=1)
        self.display_frame.grid_rowconfigure(1, weight=1)
        
        # Display title
        display_title = ctk.CTkLabel(
            self.display_frame,
            text="📷 Training Photos",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        display_title.grid(row=0, column=0, pady=15)
        
        # Camera/photo canvas
        self.display_canvas = tk.Canvas(
            self.display_frame,
            bg="#2b2b2b",
            highlightthickness=0
        )
        self.display_canvas.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        # Photo controls
        self.photo_controls = ctk.CTkFrame(self.display_frame)
        self.photo_controls.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        
        self.capture_photo_button = ctk.CTkButton(
            self.photo_controls,
            text="📸 Capture Photo",
            command=self._capture_photo,
            state="disabled",
            height=35
        )
        self.capture_photo_button.pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        self.train_button = ctk.CTkButton(
            self.photo_controls,
            text="🧠 Train with Photos",
            command=self._train_with_photos,
            state="disabled",
            height=35
        )
        self.train_button.pack(side="right", padx=(10, 0), fill="x", expand=True)
        
        # Close button
        close_button = ctk.CTkButton(
            self.main_frame,
            text="✅ Close",
            command=self._close_dialog,
            height=40
        )
        close_button.grid(row=2, column=0, columnspan=2, pady=15)
        
        # Initialize with first user if available
        if users:
            self._on_user_selected(user_names[0])
    
    def _on_user_selected(self, selection):
        """Handle user selection"""
        try:
            # Extract user_id from selection
            user_id = selection.split("(")[-1].rstrip(")")
            
            users = self.auth_system.list_users()
            self.selected_user = next((user for user in users if user.user_id == user_id), None)
            
            if self.selected_user:
                self._update_quality_display()
                
        except Exception as e:
            print(f"❌ User selection error: {e}")
    
    def _update_quality_display(self):
        """Update the model quality display"""
        if not self.selected_user:
            return
            
        try:
            quality = self.auth_system.analyze_user_model_quality(self.selected_user.user_id)
            
            self.quality_text.delete("0.0", "end")
            
            # Quality score with visual indicator
            score = quality["quality_score"]
            if score >= 80:
                score_emoji = "🟢"
            elif score >= 60:
                score_emoji = "🟡"
            else:
                score_emoji = "🔴"
            
            quality_info = f"{score_emoji} Overall Quality: {score:.1f}/100\n\n"
            quality_info += f"📊 Encoding Count: {quality['encoding_count']}\n"
            quality_info += f"🔄 Diversity Score: {quality['diversity_score']:.1f}\n"
            quality_info += f"🎯 Consistency Score: {quality['consistency_score']:.1f}\n\n"
            
            quality_info += "💡 Recommendations:\n"
            for rec in quality["recommendations"]:
                quality_info += f"• {rec}\n"
            
            self.quality_text.insert("0.0", quality_info)
            
        except Exception as e:
            self.quality_text.delete("0.0", "end")
            self.quality_text.insert("0.0", f"❌ Error analyzing quality: {e}")
    
    def _optimize_model(self):
        """Optimize the current model without new photos"""
        if not self.selected_user:
            messagebox.showwarning("No User", "Please select a user first")
            return
            
        try:
            success, message = self.auth_system.train_face_model(self.selected_user.user_id)
            
            if success:
                messagebox.showinfo("Optimization Complete", message)
                self._update_quality_display()
                if self.callback:
                    self.callback()
            else:
                messagebox.showerror("Optimization Failed", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Optimization failed: {e}")
    
    def _add_photos_from_files(self):
        """Add training photos from files"""
        if not self.selected_user:
            messagebox.showwarning("No User", "Please select a user first")
            return
            
        file_paths = filedialog.askopenfilenames(
            title="Select Photos",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
        )
        
        if not file_paths:
            return
            
        photos = []
        for file_path in file_paths:
            try:
                img = cv2.imread(file_path)
                if img is not None:
                    photos.append(img)
            except Exception as e:
                print(f"❌ Error loading {file_path}: {e}")
        
        if photos:
            self.training_photos.extend(photos)
            self._update_photo_display()
            self.train_button.configure(state="normal")
    
    def _toggle_camera(self):
        """Toggle camera capture mode"""
        if not self.is_capturing:
            self._start_camera()
        else:
            self._stop_camera()
    
    def _start_camera(self):
        """Start camera for photo capture"""
        try:
            if not self.selected_user:
                messagebox.showwarning("No User", "Please select a user first")
                return
                
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                messagebox.showerror("Camera Error", "Could not open camera")
                return
            
            self.is_capturing = True
            self.capture_button.configure(text="🛑 Stop Camera")
            self.capture_photo_button.configure(state="normal")
            self._update_camera_feed()
            
        except Exception as e:
            messagebox.showerror("Camera Error", f"Failed to start camera: {e}")
    
    def _stop_camera(self):
        """Stop camera capture"""
        self.is_capturing = False
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.capture_button.configure(text="📸 Capture New Photos")
        self.capture_photo_button.configure(state="disabled")
        self._update_photo_display()
    
    def _update_camera_feed(self):
        """Update camera feed display"""
        if not self.is_capturing or not self.cap:
            return
            
        try:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                
                # Resize frame for display
                display_frame = cv2.resize(frame, (400, 300))
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_frame)
                photo = ImageTk.PhotoImage(img)
                
                # Update canvas
                self.display_canvas.delete("all")
                canvas_width = self.display_canvas.winfo_width()
                canvas_height = self.display_canvas.winfo_height()
                
                if canvas_width > 1 and canvas_height > 1:
                    x = (canvas_width - 400) // 2
                    y = (canvas_height - 300) // 2
                    self.display_canvas.create_image(x, y, anchor="nw", image=photo)
                    self.display_canvas.image = photo  # Keep reference
                
                # Schedule next update
                self.dialog.after(30, self._update_camera_feed)
                
        except Exception as e:
            print(f"❌ Camera feed error: {e}")
    
    def _capture_photo(self):
        """Capture a photo for training"""
        if not self.current_frame is None:
            self.training_photos.append(self.current_frame.copy())
            self.train_button.configure(state="normal")
            
            # Visual feedback
            self.capture_photo_button.configure(text="✅ Photo Captured!")
            self.dialog.after(1000, lambda: self.capture_photo_button.configure(text="📸 Capture Photo"))
    
    def _update_photo_display(self):
        """Update the photo display when not using camera"""
        if len(self.training_photos) > 0:
            # Show the last captured photo
            last_photo = self.training_photos[-1]
            display_photo = cv2.resize(last_photo, (400, 300))
            rgb_photo = cv2.cvtColor(display_photo, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_photo)
            photo = ImageTk.PhotoImage(img)
            
            self.display_canvas.delete("all")
            canvas_width = self.display_canvas.winfo_width()
            canvas_height = self.display_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                x = (canvas_width - 400) // 2
                y = (canvas_height - 300) // 2
                self.display_canvas.create_image(x, y, anchor="nw", image=photo)
                self.display_canvas.image = photo
                
                # Add counter text
                self.display_canvas.create_text(
                    canvas_width // 2, 20,
                    text=f"Training Photos: {len(self.training_photos)}",
                    fill="white",
                    font=("Arial", 12, "bold")
                )
        else:
            self.display_canvas.delete("all")
            canvas_width = self.display_canvas.winfo_width()
            canvas_height = self.display_canvas.winfo_height()
            self.display_canvas.create_text(
                canvas_width // 2, canvas_height // 2,
                text="No training photos\nCapture or load photos to begin",
                fill="white",
                font=("Arial", 14),
                justify="center"
            )
    
    def _train_with_photos(self):
        """Train the model with captured photos"""
        if not self.selected_user or len(self.training_photos) == 0:
            messagebox.showwarning("No Data", "Please select a user and capture/load photos first")
            return
            
        try:
            success, message = self.auth_system.train_face_model(
                self.selected_user.user_id, 
                self.training_photos
            )
            
            if success:
                messagebox.showinfo("Training Complete", message)
                self.training_photos = []
                self._update_quality_display()
                self._update_photo_display()
                self.train_button.configure(state="disabled")
                if self.callback:
                    self.callback()
            else:
                messagebox.showerror("Training Failed", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Training failed: {e}")
    
    def _batch_train(self):
        """Train all user models"""
        try:
            # Show progress dialog
            progress_dialog = ctk.CTkToplevel(self.dialog)
            progress_dialog.title("Batch Training")
            progress_dialog.geometry("400x200")
            progress_dialog.transient(self.dialog)
            progress_dialog.grab_set()
            
            progress_label = ctk.CTkLabel(progress_dialog, text="Training all user models...")
            progress_label.pack(pady=20)
            
            progress_bar = ctk.CTkProgressBar(progress_dialog)
            progress_bar.pack(pady=20, padx=20, fill="x")
            progress_bar.set(0)
            
            status_label = ctk.CTkLabel(progress_dialog, text="Starting...")
            status_label.pack(pady=10)
            
            def run_batch_training():
                try:
                    results = self.auth_system.batch_train_all_users()
                    
                    # Close progress dialog
                    progress_dialog.destroy()
                    
                    # Show results
                    result_msg = f"Training Complete!\n\n"
                    result_msg += f"✅ Trained: {results['trained_users']}\n"
                    result_msg += f"📈 Improved: {results['improved_users']}\n"
                    result_msg += f"❌ Failed: {results['failed_users']}\n"
                    
                    messagebox.showinfo("Batch Training Results", result_msg)
                    
                    if self.selected_user:
                        self._update_quality_display()
                    
                    if self.callback:
                        self.callback()
                        
                except Exception as e:
                    progress_dialog.destroy()
                    messagebox.showerror("Batch Training Error", f"Training failed: {e}")
            
            # Start training in thread
            threading.Thread(target=run_batch_training, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start batch training: {e}")
    
    def _analyze_all(self):
        """Analyze all user models"""
        try:
            stats = self.auth_system.get_recognition_accuracy_stats()
            
            analysis_msg = f"📊 Face Recognition Model Analysis\n\n"
            analysis_msg += f"👥 Total Users: {stats['total_users']}\n"
            analysis_msg += f"🧠 Users with Models: {stats['users_with_encodings']}\n"
            analysis_msg += f"📈 Total Encodings: {stats['total_encodings']}\n"
            analysis_msg += f"📊 Avg Encodings/User: {stats['average_encodings_per_user']:.1f}\n\n"
            analysis_msg += f"Quality Distribution:\n"
            analysis_msg += f"🟢 High Quality: {stats['high_quality_users']}\n"
            analysis_msg += f"🟡 Medium Quality: {stats['medium_quality_users']}\n"
            analysis_msg += f"🔴 Low Quality: {stats['low_quality_users']}\n"
            
            messagebox.showinfo("Model Analysis", analysis_msg)
            
        except Exception as e:
            messagebox.showerror("Analysis Error", f"Failed to analyze models: {e}")
    
    def _close_dialog(self):
        """Close the dialog and clean up"""
        self._stop_camera()
        self.dialog.destroy()
