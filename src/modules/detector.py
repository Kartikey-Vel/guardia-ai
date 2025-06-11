import numpy as np
import cv2
import os
from datetime import datetime

# Try to import face_recognition, fallback to basic detection if not available
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
    print("✅ Face recognition available")
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("⚠️ Face recognition not available - using basic motion detection")

def load_known_faces():
    if not FACE_RECOGNITION_AVAILABLE:
        print("Face recognition not available. Skipping face loading.")
        return [], []
        
    known_encodings = []
    known_names = []
    
    if not os.path.exists("encodings"):
        print("No encodings directory found. Please add family members first.")
        return known_encodings, known_names
    
    for file in os.listdir("encodings"):
        if file.endswith(".npy"):
            name = file.replace(".npy", "")
            try:
                encoding = np.load(f"encodings/{file}")
                known_encodings.append(encoding)
                known_names.append(name)
                print(f"Loaded encoding for: {name}")
            except Exception as e:
                print(f"Error loading encoding for {file}: {e}")
    
    return known_encodings, known_names

def save_detected_face(frame, face_location, name, is_known=True):
    """Save detected face to appropriate folder"""
    top, right, bottom, left = face_location
    
    # Extract face region with some padding
    padding = 20
    face_image = frame[max(0, top-padding):bottom+padding, max(0, left-padding):right+padding]
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Determine save directory
    if is_known:
        save_dir = "detected/known"
        filename = f"{name}_{timestamp}.jpg"
    else:
        save_dir = "detected/unknown"
        filename = f"unknown_{timestamp}.jpg"
    
    # Ensure directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Save the face
    save_path = os.path.join(save_dir, filename)
    cv2.imwrite(save_path, face_image)
    
    # Log the detection
    log_detection(name, is_known, save_path)
    
    return save_path

def log_detection(name, is_known, image_path):
    """Log detection events"""
    os.makedirs("logs", exist_ok=True)
    log_file = "logs/detection_log.txt"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "KNOWN" if is_known else "UNKNOWN"
    
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {status}: {name} - Image saved: {image_path}\n")

def basic_motion_detection(frame, background_subtractor):
    """Basic motion detection fallback when face recognition is not available"""
    # Apply background subtraction
    fg_mask = background_subtractor.apply(frame)
    
    # Find contours
    contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    motion_detected = False
    for contour in contours:
        if cv2.contourArea(contour) > 1000:  # Minimum area threshold
            motion_detected = True
            # Draw bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, "Motion Detected", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    return frame, motion_detected

def start_detection():
    if FACE_RECOGNITION_AVAILABLE:
        known_encodings, known_names = load_known_faces()
        
        if not known_encodings:
            print("No known faces loaded. Switching to motion detection mode.")
            FACE_RECOGNITION_AVAILABLE = False
    else:
        known_encodings, known_names = [], []
    
    # Initialize background subtractor for motion detection fallback
    background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
    
    # Try different camera indices
    cap = None
    for camera_index in [0, 1, 2]:
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            print(f"Using camera index: {camera_index}")
            break
        cap.release()
    
    if not cap or not cap.isOpened():
        print("Error: Could not open camera. Please check camera connection.")
        print("Note: In Docker, camera access might be limited.")
        return

    mode = "Face Recognition" if FACE_RECOGNITION_AVAILABLE and known_encodings else "Motion Detection"
    print(f"Running in {mode} mode...")
    print("Press ESC to exit surveillance...")
    print("Press 'q' to quit...")
    print("Press 's' to save current frame...")
    
    detection_count = {"known": 0, "unknown": 0, "motion": 0}
    save_counter = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame from camera.")
            break
        
        if FACE_RECOGNITION_AVAILABLE and known_encodings:
            # Face recognition mode
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Find faces and encodings
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                # Scale back up face locations since frame was scaled to 1/4 size
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                matches = face_recognition.compare_faces(known_encodings, face_encoding, tolerance=0.6)
                name = "Unknown"
                color = (0, 0, 255)  # Red for unknown
                is_known = False

                if True in matches:
                    match_index = matches.index(True)
                    name = known_names[match_index]
                    color = (0, 255, 0)  # Green for known
                    is_known = True
                    detection_count["known"] += 1
                else:
                    detection_count["unknown"] += 1

                # Save detected face every 60 frames to avoid spam
                save_counter += 1
                if save_counter % 60 == 0:
                    save_detected_face(frame, (top, right, bottom, left), name, is_known)

                # Draw rectangle and label
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 1)

            # Display detection counts
            cv2.putText(frame, f"Known: {detection_count['known']//60}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Unknown: {detection_count['unknown']//60}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            # Motion detection fallback mode
            frame, motion_detected = basic_motion_detection(frame, background_subtractor)
            if motion_detected:
                detection_count["motion"] += 1
            
            # Display motion count
            cv2.putText(frame, f"Motion Events: {detection_count['motion']}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, "Motion Detection Mode", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow("Smart Home Surveillance", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):  # ESC or 'q' key
            break
        elif key == ord('s'):  # Save current frame
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("detected", exist_ok=True)
            cv2.imwrite(f"detected/frame_{timestamp}.jpg", frame)
            print(f"Frame saved as detected/frame_{timestamp}.jpg")

    cap.release()
    cv2.destroyAllWindows()
    print("Surveillance stopped.")
    
    if FACE_RECOGNITION_AVAILABLE and known_encodings:
        print(f"Total detections - Known: {detection_count['known']//60}, Unknown: {detection_count['unknown']//60}")
    else:
        print(f"Total motion events: {detection_count['motion']}")
