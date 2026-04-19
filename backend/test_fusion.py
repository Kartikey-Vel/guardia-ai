import sys
import numpy as np

# Add backend to path so we can run directly
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.gemini_vision import gemini_analyzer
from ai.groq_fusion import groq_fusion
from ai.yolo_detector import yolo_detector
from models.schemas import MotionResult

def test_groq_gemini_fusion():
    print("Testing Gemini + Groq Fusion...")
    
    # 1. Create a mock frame (e.g., solid gray but with some noise so it's not empty)
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # 2. Mock a MotionResult
    motion = MotionResult(
        motion_detected=True,
        motion_score=0.85,
        contour_count=3,
        frame_delta_mean=45.0,
        should_analyze=True
    )
    
    # 3. Optional YOLO
    yolo = yolo_detector.detect(frame, "test-cam")
    
    # 4. Gemini Vision
    print("\n--- Running Gemini Vision ---")
    vision_result = gemini_analyzer.analyze_frame(
        frame=frame,
        camera_id="test-cam",
        motion_score=motion.motion_score
    )
    print(f"Gemini output: {vision_result}")
    
    # 5. Groq Fusion
    print("\n--- Running Groq Fusion ---")
    fusion_result = groq_fusion.fuse(
        motion=motion,
        vision=vision_result,
        yolo=yolo,
        zone="test-zone",
        risk_level=3,
        camera_id="test-cam"
    )
    
    print("\n--- Final Fusion Result ---")
    print(fusion_result.model_dump_json(indent=2))

if __name__ == "__main__":
    test_groq_gemini_fusion()
