#!/usr/bin/env python3
"""
Face Enrollment Module for Guardia AI
Dedicated script for adding trusted users via webcam face scan + label
"""
import cv2
import sys
import os
import argparse
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from guardia_ai.detection.face_auth import FaceAuthenticator

class FaceEnrollment:
    def __init__(self):
        self.face_auth = FaceAuthenticator()
        print("🛡️ Guardia AI - Face Enrollment System")
        print("=" * 50)
    
    def capture_face(self, label, pin=None):
        """Capture and register a new face"""
        print(f"\n📷 Starting face capture for: {label}")
        print("Position your face in the camera frame and press SPACE to capture")
        print("Press 'q' to quit")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Error: Could not access camera")
            return False
        
        # Set camera resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        captured_face = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Error reading from camera")
                break
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Draw instructions
            cv2.putText(frame, f"Enrolling: {label}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(frame, "Press SPACE to capture, 'q' to quit", (10, 450), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Try to detect face in current frame
            faces = self.face_auth.face_app.get(frame)
            if faces:
                for face in faces:
                    bbox = face.bbox.astype(int)
                    cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 255, 0), 2)
                    cv2.putText(frame, "Face Detected", (bbox[0], bbox[1]-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            cv2.imshow('Face Enrollment - Guardia AI', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):  # Space to capture
                if faces:
                    captured_face = frame.copy()
                    print("✓ Face captured successfully!")
                    break
                else:
                    print("⚠️ No face detected. Please position yourself properly.")
            elif key == ord('q'):  # Quit
                print("❌ Enrollment cancelled")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        if captured_face is not None:
            return self.register_user(label, pin, captured_face)
        
        return False
    
    def register_user(self, label, pin, face_img):
        """Register the captured face"""
        print(f"\n🔄 Processing face for {label}...")
        
        # Generate PIN if not provided
        if pin is None:
            pin = input("Enter a PIN for this user (4-8 digits): ").strip()
            if not pin.isdigit() or len(pin) < 4:
                print("❌ Invalid PIN. Must be 4-8 digits.")
                return False
        
        success = self.face_auth.add_user(label, pin, face_img)
        
        if success:
            print(f"✅ User '{label}' enrolled successfully!")
            print(f"📱 PIN: {pin}")
            return True
        else:
            print(f"❌ Failed to enroll user '{label}'. Face might not be detected properly.")
            return False
    
    def list_users(self):
        """List all enrolled users"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(self.face_auth.db_path)
            c = conn.cursor()
            c.execute("SELECT id, label, pin FROM users")
            users = c.fetchall()
            conn.close()
            
            if users:
                print("\n👥 Enrolled Users:")
                print("-" * 40)
                for user_id, label, pin in users:
                    has_face = "📷" if self.user_has_face(user_id) else "📝"
                    print(f"{has_face} {label} (PIN: {pin})")
            else:
                print("\n📭 No users enrolled yet")
        except Exception as e:
            print(f"❌ Error listing users: {e}")
    
    def user_has_face(self, user_id):
        """Check if user has face embedding"""
        try:
            conn = sqlite3.connect(self.face_auth.db_path)
            c = conn.cursor()
            c.execute("SELECT embedding FROM users WHERE id=?", (user_id,))
            result = c.fetchone()
            conn.close()
            return result and result[0] is not None
        except:
            return False
    
    def test_recognition(self, label=None):
        """Test face recognition with live camera"""
        print(f"\n🧪 Testing face recognition...")
        print("Position your face in the camera and press 'r' to test recognition")
        print("Press 'q' to quit")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Error: Could not access camera")
            return
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)
            
            cv2.putText(frame, "Press 'r' to test recognition, 'q' to quit", (10, 450), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            cv2.imshow('Face Recognition Test', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('r'):
                user = self.face_auth.match_face(frame)
                if user:
                    print(f"✅ Recognized: {user['label']} (Score: {user['score']:.3f})")
                else:
                    print("❌ Face not recognized")
            elif key == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='Guardia AI Face Enrollment')
    parser.add_argument('--label', type=str, help='Name/label for the user')
    parser.add_argument('--pin', type=str, help='PIN for the user (optional)')
    parser.add_argument('--list', action='store_true', help='List enrolled users')
    parser.add_argument('--test', action='store_true', help='Test face recognition')
    
    args = parser.parse_args()
    
    enrollment = FaceEnrollment()
    
    if args.list:
        enrollment.list_users()
    elif args.test:
        enrollment.test_recognition()
    elif args.label:
        enrollment.capture_face(args.label, args.pin)
    else:
        # Interactive mode
        print("\n🎯 Face Enrollment Options:")
        print("1. Enroll new user")
        print("2. List users")
        print("3. Test recognition")
        print("4. Exit")
        
        while True:
            choice = input("\nSelect option (1-4): ").strip()
            
            if choice == '1':
                label = input("Enter user name/label: ").strip()
                if label:
                    enrollment.capture_face(label)
            elif choice == '2':
                enrollment.list_users()
            elif choice == '3':
                enrollment.test_recognition()
            elif choice == '4':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1-4.")

if __name__ == "__main__":
    main()
