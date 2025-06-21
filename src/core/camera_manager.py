"""
Camera Manager - Handles all camera operations
Simplified camera management with face photo capture capabilities
"""
import cv2
import numpy as np
from typing import Optional, Tuple
from pathlib import Path
from src.utils.logger import get_logger
import config.settings as settings

logger = get_logger(__name__)

class CameraManager:
    """Manages camera operations for surveillance"""
    
    def __init__(self, camera_index: int = None):
        self.camera_index = camera_index or settings.CAMERA_INDEX
        self.cap = None
        self.is_initialized = False
        self._initialize_camera()
    
    def _initialize_camera(self):
        """Initialize the camera"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap.isOpened():
                raise Exception(f"Could not open camera {self.camera_index}")
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.FRAME_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.FRAME_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, settings.FPS)
            
            self.is_initialized = True
            logger.info(f"📷 Camera {self.camera_index} initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            self.is_initialized = False
            raise
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame from the camera"""
        if not self.is_initialized or self.cap is None:
            return None
        
        ret, frame = self.cap.read()
        if not ret:
            logger.warning("Failed to read frame from camera")
            return None
        
        return frame
    
    def display_frame(self, frame: np.ndarray, faces: list = None):
        """Display frame with optional face annotations"""
        if frame is None:
            return
        
        display_frame = frame.copy()
        
        # Draw face rectangles
        if faces:
            for face in faces:
                x, y, w, h = face.get("location", (0, 0, 0, 0))
                color = (0, 255, 0) if not face.get("is_unknown", True) else (0, 0, 255)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                
                # Add label
                label = face.get("name", "Unknown")
                cv2.putText(display_frame, label, (x, y - 10), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Add status text
        status_text = f"Guardia AI - Active | Faces: {len(faces) if faces else 0}"
        cv2.putText(display_frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow("Guardia AI Surveillance", display_frame)
        cv2.waitKey(1)
    
    def capture_face_photo(self, person_name: str) -> bool:
        """Capture a photo for face recognition training"""
        if not self.is_initialized:
            return False
        
        logger.info(f"Starting photo capture for {person_name}")
        
        # Create person directory
        person_dir = settings.FACES_DIR / person_name
        person_dir.mkdir(exist_ok=True)
        
        photo_count = 0
        target_photos = 5  # Capture multiple photos for better recognition
        
        print(f"📷 Capturing {target_photos} photos for {person_name}")
        print("Position yourself in front of the camera and press SPACE to capture each photo")
        print("Press 'q' to quit")
        
        while photo_count < target_photos:
            frame = self.get_frame()
            if frame is None:
                continue
            
            # Display preview
            preview = frame.copy()
            cv2.putText(preview, f"Photos: {photo_count}/{target_photos}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(preview, "Press SPACE to capture", 
                       (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow(f"Capturing photos for {person_name}", preview)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):  # Spacebar to capture
                photo_path = person_dir / f"{person_name}_{photo_count + 1}.jpg"
                cv2.imwrite(str(photo_path), frame)
                photo_count += 1
                logger.info(f"Captured photo {photo_count} for {person_name}")
                print(f"✅ Photo {photo_count} captured!")
                
            elif key == ord('q'):  # Quit
                break
        
        cv2.destroyWindow(f"Capturing photos for {person_name}")
        
        success = photo_count > 0
        if success:
            logger.info(f"Successfully captured {photo_count} photos for {person_name}")
        
        return success
    
    def get_camera_info(self) -> dict:
        """Get camera information"""
        if not self.is_initialized:
            return {"error": "Camera not initialized"}
        
        return {
            "index": self.camera_index,
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": int(self.cap.get(cv2.CAP_PROP_FPS)),
            "backend": self.cap.getBackendName()
        }
    
    def release(self):
        """Release camera resources"""
        if self.cap is not None:
            self.cap.release()
            cv2.destroyAllWindows()
            self.is_initialized = False
            logger.info("📷 Camera released")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.release()
