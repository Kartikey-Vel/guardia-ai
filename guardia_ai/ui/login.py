"""
Main Authentication Window: Login + User Enrollment
"""
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox,
    QTabWidget, QFormLayout, QApplication, QListWidget, QListWidgetItem, QGroupBox,
    QFileDialog
)
from PySide6.QtCore import Qt
import cv2
import numpy as np
from guardia_ai.detection.face_auth import FaceAuthenticator
from guardia_ai.ui.dashboard import GuardiaDashboard

class AuthMainWindow(QWidget):
    def __init__(self, face_auth: FaceAuthenticator):
        super().__init__()
        self.face_auth = face_auth
        self.logged_in_user = None
        self.dashboard = None
        self.setWindowTitle("Guardia AI - Authentication")
        self.setFixedSize(500, 450)
        self._build_ui()

    def _build_ui(self):
        self.tabs = QTabWidget()
        self.login_tab = QWidget()
        self.enroll_tab = QWidget()
        self.manage_tab = QWidget()
        self.tabs.addTab(self.login_tab, "Login")
        self.tabs.addTab(self.enroll_tab, "Enroll User")
        self.tabs.addTab(self.manage_tab, "Manage Users")
        self._build_login_tab()
        self._build_enroll_tab()
        self._build_manage_tab()
        vbox = QVBoxLayout()
        vbox.addWidget(self.tabs)
        self.setLayout(vbox)

    def _build_login_tab(self):
        layout = QVBoxLayout()
        
        # Username + PIN login section
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("Enter PIN")
        self.login_btn = QPushButton("Login with Username + PIN")
        
        # PIN-only login section
        self.pin_only_input = QLineEdit()
        self.pin_only_input.setEchoMode(QLineEdit.Password)
        self.pin_only_input.setPlaceholderText("Enter PIN (any user)")
        self.pin_only_btn = QPushButton("Login with PIN Only")
        
        # Face login section
        self.face_btn = QPushButton("Login with Face")
        
        # Status display
        self.login_status = QLabel("")
        self.login_status.setAlignment(Qt.AlignCenter)
        
        # Layout assembly
        layout.addWidget(QLabel("Username + PIN Login:"))
        layout.addWidget(self.username_input)
        layout.addWidget(self.pin_input)
        layout.addWidget(self.login_btn)
        
        layout.addWidget(QLabel("or PIN Only:"))
        layout.addWidget(self.pin_only_input)
        layout.addWidget(self.pin_only_btn)
        
        layout.addWidget(QLabel("or Face Recognition:"))
        layout.addWidget(self.face_btn)
        layout.addWidget(self.login_status)
        
        self.login_tab.setLayout(layout)
        
        # Connect signals
        self.login_btn.clicked.connect(self._handle_username_pin_login)
        self.pin_only_btn.clicked.connect(self._handle_pin_only_login)
        self.face_btn.clicked.connect(self._handle_face_login)

    def _build_enroll_tab(self):
        form = QFormLayout()
        self.enroll_label = QLineEdit()
        self.enroll_pin = QLineEdit()
        self.enroll_pin.setEchoMode(QLineEdit.Password)
        self.enroll_face_btn = QPushButton("Capture Face & Enroll")
        self.enroll_status = QLabel("")
        self.enroll_status.setAlignment(Qt.AlignCenter)
        form.addRow("Name/Label:", self.enroll_label)
        form.addRow("PIN:", self.enroll_pin)
        form.addRow(self.enroll_face_btn)
        form.addRow(self.enroll_status)
        self.enroll_tab.setLayout(form)
        self.enroll_face_btn.clicked.connect(self._handle_enroll)

    def _handle_username_pin_login(self):
        """Handle username + PIN authentication"""
        username = self.username_input.text().strip()
        pin = self.pin_input.text().strip()
        
        if not username or not pin:
            self.login_status.setText("Username and PIN required.")
            return
            
        if self.face_auth.verify_user_credentials(username, pin):
            self.login_status.setText(f"Welcome, {username}! Access granted.")
            self.logged_in_user = username
            self._accept_login()
        else:
            self.login_status.setText("Invalid username or PIN.")

    def _handle_pin_only_login(self):
        """Handle PIN-only authentication (any user with matching PIN)"""
        pin = self.pin_only_input.text().strip()
        
        if not pin:
            self.login_status.setText("PIN required.")
            return
            
        if self.face_auth.verify_pin(pin):
            self.login_status.setText("PIN correct. Access granted.")
            self.logged_in_user = "PIN User"  # Generic name for PIN-only login
            self._accept_login()
        else:
            self.login_status.setText("Invalid PIN.")

    def _handle_face_login(self):
        self.login_status.setText("Scanning face...")
        img = self._capture_face()
        if img is None:
            self.login_status.setText("Camera error.")
            return
        user = self.face_auth.match_face(img)
        if user:
            self.login_status.setText(f"Welcome, {user['label']}!")
            self.logged_in_user = user['label']
            self._accept_login()
        else:
            self.login_status.setText("Face not recognized.")

    def _handle_enroll(self):
        label = self.enroll_label.text().strip()
        pin = self.enroll_pin.text().strip()
        if not label or not pin:
            self.enroll_status.setText("Label and PIN required.")
            return
        img = self._capture_face()
        if img is None:
            self.enroll_status.setText("Camera error.")
            return
        ok = self.face_auth.add_user(label, pin, img)
        if ok:
            self.enroll_status.setText(f"User '{label}' enrolled!")
        else:
            self.enroll_status.setText("Face not detected. Try again.")

    def _build_manage_tab(self):
        """Build user management tab"""
        layout = QVBoxLayout()
        
        # User list
        self.user_list = QListWidget()
        self.refresh_btn = QPushButton("Refresh User List")
        self.delete_btn = QPushButton("Delete Selected User")
        
        # Statistics group
        stats_group = QGroupBox("Database Statistics")
        stats_layout = QVBoxLayout()
        self.stats_label = QLabel("")
        stats_layout.addWidget(self.stats_label)
        stats_group.setLayout(stats_layout)
        
        # Export/Import group
        export_group = QGroupBox("Data Management")
        export_layout = QHBoxLayout()
        self.export_btn = QPushButton("Export to JSON")
        self.import_btn = QPushButton("Import from JSON")
        export_layout.addWidget(self.export_btn)
        export_layout.addWidget(self.import_btn)
        export_group.setLayout(export_layout)
        
        # Layout assembly
        layout.addWidget(QLabel("Registered Users:"))
        layout.addWidget(self.user_list)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.delete_btn)
        layout.addWidget(stats_group)
        layout.addWidget(export_group)
        
        self.manage_tab.setLayout(layout)
        
        # Connect signals
        self.refresh_btn.clicked.connect(self._refresh_user_list)
        self.delete_btn.clicked.connect(self._delete_selected_user)
        self.export_btn.clicked.connect(self._export_to_json)
        self.import_btn.clicked.connect(self._import_from_json)
        
        # Load initial data
        self._refresh_user_list()

    def _refresh_user_list(self):
        """Refresh the user list and statistics"""
        self.user_list.clear()
        users = self.face_auth.get_all_users()
        
        for user in users:
            face_status = "👤" if user["has_face"] else "🔢"
            item_text = f"{face_status} {user['label']} (ID: {user['id']})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, user["id"])  # Store user ID
            self.user_list.addItem(item)
        
        # Update statistics
        stats = self.face_auth.get_embedding_stats()
        stats_text = f"""Total Users: {stats['total_users']}
Users with Face: {stats['users_with_faces']}
PIN-only Users: {stats['users_pin_only']}"""
        self.stats_label.setText(stats_text)

    def _delete_selected_user(self):
        """Delete the selected user"""
        current_item = self.user_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a user to delete.")
            return
        
        user_id = current_item.data(Qt.UserRole)
        user_name = current_item.text().split(" (ID:")[0][2:]  # Remove emoji and ID
        
        reply = QMessageBox.question(
            self, "Confirm Deletion", 
            f"Are you sure you want to delete user '{user_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.face_auth.delete_user(user_id):
                QMessageBox.information(self, "Success", f"User '{user_name}' deleted successfully.")
                self._refresh_user_list()
            else:
                QMessageBox.critical(self, "Error", "Failed to delete user.")

    def _export_to_json(self):
        """Export user data to JSON"""
        try:
            filename = self.face_auth.export_to_json()
            QMessageBox.information(
                self, "Export Successful", 
                f"User data exported successfully to:\n{filename}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export data:\n{str(e)}")

    def _import_from_json(self):
        """Import user data from JSON"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import User Data", "", "JSON files (*.json)"
        )
        
        if filename:
            try:
                result = self.face_auth.import_from_json(filename)
                
                message = f"Import completed!\n\n"
                message += f"Users imported: {result['imported_count']}\n"
                message += f"Total in file: {result['total_in_file']}\n"
                
                if result['errors']:
                    message += f"\nErrors:\n"
                    for error in result['errors'][:5]:  # Show first 5 errors
                        message += f"• {error}\n"
                    if len(result['errors']) > 5:
                        message += f"... and {len(result['errors']) - 5} more errors"
                
                if result['imported_count'] > 0:
                    QMessageBox.information(self, "Import Results", message)
                    self._refresh_user_list()  # Refresh the user list
                else:
                    QMessageBox.warning(self, "Import Results", message)
                    
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to import data:\n{str(e)}")

    def _capture_face(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None
        return frame

    def _accept_login(self):
        """Handle successful login by opening the dashboard"""
        try:
            # Hide the login window
            self.hide()
            
            # Create and show the dashboard
            self.dashboard = GuardiaDashboard(self.face_auth, self.logged_in_user)
            self.dashboard.dashboard_closed.connect(self._on_dashboard_closed)
            self.dashboard.show()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open dashboard:\n{str(e)}")
            self.show()  # Show login again if dashboard fails
    
    def _on_dashboard_closed(self):
        """Handle dashboard being closed - show login window again"""
        self.dashboard = None
        self.logged_in_user = None
        
        # Clear login fields
        self.username_input.clear()
        self.pin_input.clear()
        self.pin_only_input.clear()
        self.login_status.setText("")
        
        # Show the login window again
        self.show()
    
    def showEvent(self, event):
        """Handle window show event - reset fields when window is reshown"""
        super().showEvent(event)
        if self.dashboard is None:  # Only clear if not coming from dashboard
            self.username_input.clear()
            self.pin_input.clear() 
            self.pin_only_input.clear()
            self.login_status.setText("")
            self.logged_in_user = None
    
    def closeEvent(self, event):
        """Handle window close event - close dashboard too"""
        if self.dashboard:
            self.dashboard.close()
        event.accept()
