import cv2
import numpy as np
from typing import Optional
from models.schemas import YOLOResult

def annotate_frame(frame: np.ndarray, yolo_result: Optional[YOLOResult]) -> np.ndarray:
    """
    Overlays bounding boxes and labels onto the given frame if YOLO detections exist.
    
    Args:
        frame: The original image frame (numpy array).
        yolo_result: The YOLOResult object containing detections.
        
    Returns:
        A new annotated image frame.
    """
    # Create a copy so we don't modify the original frame
    annotated_frame = frame.copy()
    
    if not yolo_result or not yolo_result.detections:
        return annotated_frame

    for detection in yolo_result.detections:
        # Bounding box coordinates (x_min, y_min, x_max, y_max)
        x_min, y_min, x_max, y_max = [int(v) for v in detection.bbox_xyxy]
        label = detection.label
        confidence = detection.confidence

        # Draw the bounding box
        color = (0, 255, 0) # Green
        thickness = 2
        cv2.rectangle(annotated_frame, (x_min, y_min), (x_max, y_max), color, thickness)
        
        # Prepare the label text
        text = f"{label} {confidence:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        font_thickness = 2
        
        # Calculate text size and baseline
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, font_thickness)
        
        # Draw text background
        cv2.rectangle(
            annotated_frame, 
            (x_min, y_min - text_height - 10), 
            (x_min + text_width, y_min), 
            color, 
            -1
        )
        
        # Draw the text
        cv2.putText(
            annotated_frame, 
            text, 
            (x_min, y_min - 5), 
            font, 
            font_scale, 
            (0, 0, 0), # Black text 
            font_thickness
        )
        
    return annotated_frame
