#!/usr/bin/env python3
"""
Guardia AI Desktop Application Demo
Simple demonstration of camera feed and face detection
"""
import cv2
import time
from pathlib import Path

def demo_camera():
    """Demo basic camera functionality"""
    print("🎥 Guardia AI Camera Demo")
    print("=" * 30)
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        return
    
    # Initialize face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    print("✅ Camera initialized")
    print("📋 Controls:")
    print("   SPACE - Take screenshot")
    print("   ESC   - Exit")
    print("   'r'   - Toggle recording")
    
    # Setup recording
    is_recording = False
    video_writer = None
    
    frame_count = 0
    fps_start = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Calculate FPS
        frame_count += 1
        if frame_count % 30 == 0:
            fps = frame_count / (time.time() - fps_start)
            frame_count = 0
            fps_start = time.time()
        else:
            fps = 0
        
        # Face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        # Draw face rectangles
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, "Person Detected", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Add info overlay
        info_text = f"FPS: {fps:.1f} | Faces: {len(faces)}"
        if is_recording:
            info_text += " | REC"
        
        cv2.putText(frame, info_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Record frame if recording
        if is_recording and video_writer:
            video_writer.write(frame)
        
        # Display frame
        cv2.imshow('Guardia AI - Camera Demo', frame)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        
        if key == 27:  # ESC
            break
        elif key == ord(' '):  # SPACE - Screenshot
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            Path("screenshots").mkdir(exist_ok=True)
            screenshot_path = f"screenshots/demo_screenshot_{timestamp}.jpg"
            cv2.imwrite(screenshot_path, frame)
            print(f"📸 Screenshot saved: {screenshot_path}")
        elif key == ord('r'):  # R - Toggle recording
            if not is_recording:
                # Start recording
                Path("recordings").mkdir(exist_ok=True)
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                recording_path = f"recordings/demo_recording_{timestamp}.mp4"
                
                height, width = frame.shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(recording_path, fourcc, 20.0, (width, height))
                is_recording = True
                print(f"🔴 Recording started: {recording_path}")
            else:
                # Stop recording
                if video_writer:
                    video_writer.release()
                    video_writer = None
                is_recording = False
                print("⏹️ Recording stopped")
    
    # Cleanup
    if video_writer:
        video_writer.release()
    cap.release()
    cv2.destroyAllWindows()
    print("✅ Demo completed")

if __name__ == "__main__":
    try:
        demo_camera()
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo error: {e}")
