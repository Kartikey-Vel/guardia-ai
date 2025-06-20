import cv2 # Keep for camera access if needed locally
import os
import time
import numpy as np
from datetime import datetime
# from google.cloud import videointelligence_v1p3beta1 as videointelligence # Moved to google_cloud_utils
from .google_cloud_utils import (
    get_video_client,
    analyze_video_from_gcs,
    upload_video_to_gcs,
    # get_analysis_results, # This might be handled differently
    detect_fire,
    detect_burglary,
    detect_unauthorized_access
)

# Global client for Google Cloud Video Intelligence
VIDEO_INTELLIGENCE_CLIENT = None

def initialize_cloud_detector():
    """Initializes the Google Cloud Video Intelligence client."""
    global VIDEO_INTELLIGENCE_CLIENT
    if VIDEO_INTELLIGENCE_CLIENT is None:
        VIDEO_INTELLIGENCE_CLIENT = get_video_client()
    return VIDEO_INTELLIGENCE_CLIENT is not None

def check_camera_access():
    """Check if a system camera is available."""
    try:
        cap = cv2.VideoCapture(0)  # Try to access default camera
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                print("✅ System camera detected and accessible")
                return True
            else:
                print("⚠️ Camera opened but failed to capture frame")
                return False
        else:
            print("❌ No camera detected or camera access denied")
            return False
    except Exception as e:
        print(f"❌ Error accessing camera: {e}")
        return False

def capture_video_segment(duration_seconds=10, output_path="temp_video.mp4"):
    """
    Capture a video segment from the system camera.
    
    Args:
        duration_seconds (int): Duration to record in seconds
        output_path (str): Path to save the video file
    
    Returns:
        str: Path to the saved video file, or None if failed
    """
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera for video capture")
            return None
        
        # Get camera properties
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 20  # Default to 20 FPS if can't detect
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"📹 Recording video: {width}x{height} at {fps} FPS for {duration_seconds} seconds")
        
        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        start_time = time.time()
        frame_count = 0
        
        while (time.time() - start_time) < duration_seconds:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
                frame_count += 1
                
                # Optional: Display frame (comment out for headless operation)
                # cv2.imshow('Recording...', frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break
            else:
                print("⚠️ Failed to capture frame")
                break
        
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        
        print(f"✅ Video captured: {frame_count} frames saved to {output_path}")
        return output_path
        
    except Exception as e:
        print(f"❌ Error during video capture: {e}")
        return None

def log_detection_event(event_type, details, image_path=None):
    """Log detection events from Cloud Video Intelligence or other sources."""
    os.makedirs("logs", exist_ok=True)
    log_file = "logs/cloud_detection_log.txt"
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = f"[{timestamp}] Event: {event_type} - Details: {details}"
    if image_path:
        log_entry += f" - Associated Image: {image_path}"
    log_entry += "\\n"
        
    with open(log_file, "a") as f:
        f.write(log_entry)

def basic_motion_detection():
    """
    Basic motion detection using OpenCV background subtraction.
    This provides a simple local surveillance option.
    """
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera for motion detection")
            return False
        
        print("🎥 Starting motion detection... Press 'q' to quit")
        
        # Create background subtractor
        background_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        
        motion_threshold = 1000  # Minimum contour area to consider as motion
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Failed to capture frame")
                break
            
            # Apply background subtraction
            fg_mask = background_subtractor.apply(frame)
            
            # Find contours
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            motion_detected = False
            for contour in contours:
                if cv2.contourArea(contour) > motion_threshold:
                    motion_detected = True
                    # Draw bounding rectangle
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, "Motion Detected", (x, y - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if motion_detected:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"🚨 Motion detected at {timestamp}")
                log_detection_event("MotionDetected", f"Local motion detection at {timestamp}")
            
            # Display the frame (comment out for headless operation)
            cv2.imshow('Motion Detection - Press q to quit', frame)
            cv2.imshow('Motion Mask', fg_mask)
            
            # Break on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
        return True
        
    except Exception as e:
        print(f"❌ Error during motion detection: {e}")
        return False

def process_video_with_cloud_ai(gcs_uri, features_to_analyze):
    """
    Processes a video using Google Cloud Video Intelligence API.

    Args:
        gcs_uri (str): The GCS URI of the video to analyze.
        features_to_analyze (list): List of videointelligence.Feature enums.
                                     e.g., [videointelligence.Feature.PERSON_DETECTION,
                                            videointelligence.Feature.LABEL_DETECTION]
    Returns:
        dict: A dictionary containing detected events.
    """
    if not VIDEO_INTELLIGENCE_CLIENT:
        print("🔴 Cloud Video Intelligence client not initialized. Call initialize_cloud_detector() first.")
        return None

    print(f"🎬 Processing video: {gcs_uri} with features: {features_to_analyze}")
    operation = analyze_video_from_gcs(gcs_uri, features_to_analyze, client=VIDEO_INTELLIGENCE_CLIENT)

    if not operation:
        log_detection_event("CloudAnalysisError", f"Failed to start analysis for {gcs_uri}")
        return None

    print(f"⏳ Waiting for analysis of {gcs_uri} to complete... This can take a while.")
    
    try:
        # The timeout should be appropriate for your video length and features.
        # For very long videos, consider asynchronous handling or breaking them into chunks.
        results = operation.result(timeout=900) # Timeout e.g., 15 minutes
        print(f"✅ Analysis complete for {gcs_uri}")
        
        detected_events = {
            "fire": [],
            "burglary": [],
            "unauthorized_access": [],
            "other_labels": [],
            "persons": [],
            "objects": []
        }

        # --- Parse results for different features ---
        # Note: The structure of `results.annotation_results` depends on the features requested.
        # You'll need to iterate through them and call the appropriate parsing functions.

        if not results.annotation_results:
            print("No annotation results found.")
            log_detection_event("CloudAnalysisWarning", f"No annotation results for {gcs_uri}")
            return detected_events # Return empty events

        for annotation_result in results.annotation_results:
            # Fire Detection (using label detection as an example)
            # You might have specific fire detection features or rely on labels.
            # This is a simplified example; `detect_fire` was a placeholder.
            # We'll refine this based on actual API capabilities for fire.
            # For now, let's assume detect_fire can take the full annotation_result.
            
            # Example for Label Detection
            if annotation_result.segment_label_annotations:
                for label_annotation in annotation_result.segment_label_annotations:
                    desc = label_annotation.entity.description.lower()
                    event_detail = {
                        "description": desc,
                        "segments": [{"start": seg.segment.start_time_offset.total_seconds(), 
                                      "end": seg.segment.end_time_offset.total_seconds()} 
                                     for seg in label_annotation.segments],
                        "confidence": getattr(label_annotation.entity, 'confidence', None) # if available
                    }
                    detected_events["other_labels"].append(event_detail)
                    if desc in ["fire", "smoke", "flame"]:
                         detected_events["fire"].append(event_detail)
                         log_detection_event("FireDetected", f"Label: {desc}", gcs_uri)
              # Example for Person Detection
            if annotation_result.person_detection_annotations:
                for person_annotation in annotation_result.person_detection_annotations:
                    for track in person_annotation.tracks:
                        person_event = {
                            "track_id": getattr(track, 'track_id', None) or getattr(track, 'id', 'unknown'),
                            "segments": [{"start": ts_segment.segment.start_time_offset.total_seconds(),
                                          "end": ts_segment.segment.end_time_offset.total_seconds()}
                                         for ts_segment in track.timestamped_objects],
                            # Potentially add bounding box info if needed and available
                        }
                        detected_events["persons"].append(person_event)
                        # Further logic for "unauthorized access" would go here,
                        # possibly comparing against known individuals if the API supports it
                        # or if you implement a secondary check.
                        # For now, any person detected could be logged.
                        track_id = getattr(track, 'track_id', None) or getattr(track, 'id', 'unknown')
                        log_detection_event("PersonDetected", f"Track ID: {track_id}", gcs_uri)


            # Example for Object Tracking
            if annotation_result.object_annotations:
                for object_annotation in annotation_result.object_annotations:
                    desc = object_annotation.entity.description.lower()
                    object_event = {
                        "description": desc,
                        "start": object_annotation.segment.start_time_offset.total_seconds(),
                        "end": object_annotation.segment.end_time_offset.total_seconds(),
                        "confidence": object_annotation.confidence,
                        # Bounding box info can be extracted from object_annotation.frames
                    }
                    detected_events["objects"].append(object_event)
                    log_detection_event("ObjectDetected", f"Object: {desc}", gcs_uri)
                    # Burglary detection logic could check for specific objects or patterns here
                    if desc in ["crowbar", "broken glass", "forced entry"]: # Example keywords
                        detected_events["burglary"].append(object_event)
                        log_detection_event("BurglaryIndicator", f"Object: {desc}", gcs_uri)
        
        # Call more specific parsing functions if they are more detailed
        # fire_events = detect_fire(results) # detect_fire needs to be adapted for the new structure
        # if fire_events:
        #     detected_events["fire"].extend(fire_events)
        #     for fe in fire_events:
        #         log_detection_event("FireDetected", fe, gcs_uri)

        # burglary_events = detect_burglary(results) # adapt detect_burglary
        # if burglary_events:
        #     detected_events["burglary"].extend(burglary_events)
        #     for be in burglary_events:
        #         log_detection_event("BurglaryIndicator", be, gcs_uri)
          # unauthorized_events = detect_unauthorized_access(results) # adapt detect_unauthorized_access
        # if unauthorized_events:
        #     detected_events["unauthorized_access"].extend(unauthorized_events)
        #     for ue in unauthorized_events:
        #         log_detection_event("UnauthorizedAccess", ue, gcs_uri)

        return detected_events

    except Exception as e:
        print(f"❌ Error processing or retrieving results for {gcs_uri}: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        log_detection_event("CloudAnalysisError", f"Error during result processing for {gcs_uri}: {e}")
        return None


def start_surveillance_loop():
    """
    Main loop for capturing video (or watching a directory for new videos)
    and sending it for cloud analysis.
    This is a placeholder and needs to be adapted based on how video is acquired.
    """
    if not initialize_cloud_detector():
        print("🔴 Cannot start surveillance: Cloud detector initialization failed.")
        return

    print("👁️ Guardia AI Surveillance (Cloud Mode) Started...")
    print("   Waiting for video input (e.g., new file in a monitored GCS bucket or local capture)...")

    # --- Example: Monitoring a local directory for video files to upload to GCS ---
    # This is a simplified example. A robust solution would use GCS event triggers (e.g., Cloud Functions)
    # or a more sophisticated local file watcher.

    # monitored_local_folder = "data/videos_to_process" # Example
    # gcs_bucket_name = "your-guardia-ai-bucket" # Replace with your bucket
    # os.makedirs(monitored_local_folder, exist_ok=True)

    # while True:
    #     for filename in os.listdir(monitored_local_folder):
    #         if filename.lower().endswith((".mp4", ".avi", ".mov")): # Add other video formats
    #             local_file_path = os.path.join(monitored_local_folder, filename)
    #             gcs_file_path = f"videos/{filename}" # Path within the bucket
    #             gcs_uri = f"gs://{gcs_bucket_name}/{gcs_file_path}"
                
    #             print(f"Found new video: {local_file_path}. Uploading to {gcs_uri}...")
                # --- Add GCS Upload Logic Here ---
                # Example: from google.cloud import storage
                # storage_client = storage.Client()
                # bucket = storage_client.bucket(gcs_bucket_name)
                # blob = bucket.blob(gcs_file_path)
                # try:
                #    blob.upload_from_filename(local_file_path)
                #    print(f"Successfully uploaded to {gcs_uri}")
                #    os.remove(local_file_path) # Remove after successful upload
                # except Exception as e:
                #    print(f"Failed to upload {local_file_path}: {e}")
                #    continue # Skip processing if upload failed

                # Define features for analysis
    #             features = [
    #                 videointelligence.Feature.LABEL_DETECTION,
    #                 videointelligence.Feature.PERSON_DETECTION,
    #                 videointelligence.Feature.OBJECT_TRACKING,
    #                 videointelligence.Feature.EXPLICIT_CONTENT_DETECTION,
    #                 # Add other relevant features like SHOT_CHANGE_DETECTION if useful
    #             ]
                
    #             events = process_video_with_cloud_ai(gcs_uri, features)
    #             if events:
    #                 print(f"🚨 Detected Events for {gcs_uri}:")
    #                 for event_type, event_list in events.items():
    #                     if event_list:
    #                         print(f"  -> {event_type.replace('_', ' ').title()}: {len(event_list)} instance(s)")
    #                         for event_item in event_list:
    #                             print(f"     - {event_item}")
    #                 # Here, you would trigger your alert system based on these events.
    #             else:
    #                 print(f"No significant events detected or analysis failed for {gcs_uri}.")
            
        # time.sleep(10) # Check for new videos every 10 seconds


# This replaces the old start_detection() which was based on local camera feed and local processing.
# The actual video acquisition (camera stream -> GCS or direct API stream) needs to be implemented.
# For live streaming, the Video Intelligence API has different methods (StreamingAnnotateVideo).
# The current `analyze_video_from_gcs` is for batch processing of videos already in GCS.

if __name__ == '__main__':
    # Example of how to use the detector module with a GCS video
    # Ensure GOOGLE_APPLICATION_CREDENTIALS is set in your environment.
    
    print("Testing Cloud Detector Module...")
    if not initialize_cloud_detector():
        print("Exiting test: Client initialization failed.")
        exit()

    # Replace with your actual GCS URI
    test_video_gcs_uri = "gs://your-bucket-name/your-video.mp4" 
    
    if "your-bucket-name" in test_video_gcs_uri:
        print(f"SKIPPING analysis: Please replace placeholder GCS URI \'{test_video_gcs_uri}\' with a real one for testing.")
    else:
        # Define features for analysis
        # You need to import videointelligence from google.cloud
        from google.cloud import videointelligence_v1p3beta1 as videointelligence
        test_features = [
            videointelligence.Feature.LABEL_DETECTION,
            videointelligence.Feature.PERSON_DETECTION,
            videointelligence.Feature.OBJECT_TRACKING,
            # videointelligence.Feature.SPEECH_TRANSCRIPTION, # If you need audio
        ]
        
        detected_events = process_video_with_cloud_ai(test_video_gcs_uri, test_features)

        if detected_events:
            print("\\n--- Test Analysis Results ---")
            for event_type, event_details in detected_events.items():
                if event_details: # Only print if there are events of this type
                    print(f"Event Type: {event_type}")
                    for detail in event_details:
                        print(f"  - {detail}")
            print("---------------------------")
        else:
            print("No events detected or analysis failed during the test.")
    
    print("Cloud Detector Module test finished.")

def start_detection():
    """
    Start detection using available camera and provide basic motion detection.
    This function is called by main_minimal.py for local surveillance.
    """
    print("🎥 Starting Camera-Based Detection...")
    
    # Check if camera is available
    if not check_camera_access():
        print("❌ No camera available. Cannot start detection.")
        print("Ensure a camera is connected and accessible.")
        return False
    
    print("\n📋 Available Detection Modes:")
    print("1. Basic Motion Detection (real-time)")
    print("2. Video Capture Test (10-second recording)")
    print("3. Capture & Cloud Analysis (record + upload + analyze)")
    print("4. Exit")
    
    while True:
        try:
            choice = input("\nSelect mode (1-4): ").strip()
            
            if choice == "1":
                print("\n🎯 Starting basic motion detection...")
                print("This will show live camera feed with motion detection.")
                print("Press 'q' in the camera window to stop.")
                if basic_motion_detection():
                    print("✅ Motion detection completed successfully")
                else:
                    print("❌ Motion detection failed")
                
            elif choice == "2":
                print("\n📹 Testing video capture...")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_path = f"captured_video_{timestamp}.mp4"
                
                if capture_video_segment(duration_seconds=10, output_path=video_path):
                    print(f"✅ Video saved to: {video_path}")
                else:
                    print("❌ Video capture failed")
                    
            elif choice == "3":
                print("\n🔄 Capture & Cloud Analysis...")
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_path = f"surveillance_{timestamp}.mp4"
                
                # Capture video
                print("📹 Capturing video for cloud analysis...")
                if capture_video_segment(duration_seconds=15, output_path=video_path):
                    print(f"✅ Video captured: {video_path}")
                    
                    # Upload to GCS
                    print("📤 Uploading to Google Cloud Storage...")
                    gcs_uri = upload_video_to_gcs(video_path)
                    
                    if gcs_uri:
                        print(f"✅ Video uploaded to: {gcs_uri}")
                        
                        # Initialize cloud detector and analyze
                        if initialize_cloud_detector():
                            print("🤖 Starting cloud analysis...")
                            try:
                                from google.cloud import videointelligence_v1p3beta1 as videointelligence
                                features = [
                                    videointelligence.Feature.LABEL_DETECTION,
                                    videointelligence.Feature.PERSON_DETECTION,
                                    videointelligence.Feature.OBJECT_TRACKING,
                                ]
                                
                                events = process_video_with_cloud_ai(gcs_uri, features)
                                if events:
                                    print("\n🚨 Cloud Analysis Results:")
                                    for event_type, event_list in events.items():
                                        if event_list:
                                            print(f"  {event_type}: {len(event_list)} detection(s)")
                                else:
                                    print("✅ Analysis complete - no significant events detected")
                                    
                            except ImportError:
                                print("❌ Google Cloud Video Intelligence not available")
                            except Exception as e:
                                print(f"❌ Analysis error: {e}")
                        else:
                            print("❌ Failed to initialize cloud detector")
                    else:
                        print("❌ Upload to GCS failed")
                        
                    # Clean up local file
                    try:
                        os.remove(video_path)
                        print(f"🗑️ Cleaned up local file: {video_path}")
                    except:
                        pass
                        
                else:
                    print("❌ Video capture failed")
                    
            elif choice == "4":
                print("👋 Exiting detection mode")
                break
                
            else:
                print("❌ Invalid choice. Please select 1, 2, 3, or 4.")
                
        except KeyboardInterrupt:
            print("\n🛑 Detection stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    return True

def capture_user_face(name, save_dir="images/users"):
    """
    Capture a user's face for registration with real-time face detection guide.
    
    Args:
        name (str): User name for file naming
        save_dir (str): Directory to save the captured image
    
    Returns:
        str: Path to the saved image, or None if failed
    """
    try:
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot access camera for face capture")
            return None
        
        # Load OpenCV's face detection cascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        print("📸 Face Capture Mode")
        print("=" * 30)
        print("Position your face in the camera view")
        print("A green rectangle will appear when face is detected")
        print("Press SPACE to capture when ready, or 'q' to cancel")
        print("=" * 30)
        
        captured_image = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Failed to capture frame")
                break
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(100, 100)
            )
            
            # Draw rectangles around detected faces
            face_detected = False
            for (x, y, w, h) in faces:
                # Draw green rectangle for detected face
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Add instruction text
                cv2.putText(frame, "Face Detected - Press SPACE to capture", 
                           (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                face_detected = True
            
            if not face_detected:
                # Add instruction when no face is detected
                cv2.putText(frame, "Position your face in the camera", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.putText(frame, "Make sure you're well lit and facing camera", 
                           (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Add general instructions
            cv2.putText(frame, "Press SPACE to capture | Press Q to cancel", 
                       (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Display frame
            cv2.imshow('Guardia AI - Face Capture', frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord(' '):  # Space bar to capture
                if face_detected:
                    # Save the current frame
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{name.replace(' ', '_')}_{timestamp}.jpg"
                    filepath = os.path.join(save_dir, filename)
                    
                    cv2.imwrite(filepath, frame)
                    captured_image = filepath
                    
                    print(f"✅ Face captured successfully: {filepath}")
                    
                    # Show capture confirmation for 2 seconds
                    confirmation_frame = frame.copy()
                    cv2.putText(confirmation_frame, "CAPTURED! ✓", 
                               (frame.shape[1]//2 - 100, frame.shape[0]//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                    cv2.imshow('Guardia AI - Face Capture', confirmation_frame)
                    cv2.waitKey(2000)  # Show for 2 seconds
                    break
                else:
                    print("⚠️ No face detected. Please position your face properly.")
            
            elif key == ord('q'):  # Q to cancel
                print("❌ Face capture cancelled")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        return captured_image
        
    except Exception as e:
        print(f"❌ Error during face capture: {e}")
        return None

def capture_family_member_face(name, relation, save_dir="images/family"):
    """
    Capture a family member's face for registration.
    
    Args:
        name (str): Family member name
        relation (str): Relation to owner (Father, Mother, etc.)
        save_dir (str): Directory to save the captured image
    
    Returns:
        str: Path to the saved image, or None if failed
    """
    try:
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        print(f"📸 Capturing face for {name} ({relation})")
        
        # Use the same face capture logic but with family-specific directory
        family_save_dir = os.path.join(save_dir, relation.lower().replace(' ', '_'))
        return capture_user_face(name, family_save_dir)
        
    except Exception as e:
        print(f"❌ Error during family member face capture: {e}")
        return None
