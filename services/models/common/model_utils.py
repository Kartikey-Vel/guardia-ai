"""
Common model utilities for Guardia AI
Shared inference wrapper and output formatting
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)


@dataclass
class ModelOutput:
    """Standardized model output format"""
    model: str
    timestamp: str
    camera_id: str
    camera_name: str
    sequence_id: str
    frame_number: int
    confidence: float
    class_label: Optional[str] = None
    class_id: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    bounding_boxes: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ONNXModelWrapper:
    """Wrapper for ONNX Runtime inference"""
    
    def __init__(self, model_path: str, model_name: str):
        self.model_name = model_name
        self.model_path = model_path
        self.session = None
        self.input_name = None
        self.output_names = None
        
    def load(self):
        """Load ONNX model"""
        try:
            # Create session options
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # Check for available providers (GPU/CPU)
            providers = ['CPUExecutionProvider']
            if 'CUDAExecutionProvider' in ort.get_available_providers():
                providers.insert(0, 'CUDAExecutionProvider')
                logger.info(f"CUDA available, using GPU for {self.model_name}")
            
            # Create inference session
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=sess_options,
                providers=providers
            )
            
            # Get input/output names
            self.input_name = self.session.get_inputs()[0].name
            self.output_names = [output.name for output in self.session.get_outputs()]
            
            logger.info(f"Loaded ONNX model: {self.model_name} from {self.model_path}")
            logger.info(f"Input: {self.input_name}, Outputs: {self.output_names}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load ONNX model {self.model_name}: {e}")
            return False
    
    def infer(self, input_data: np.ndarray) -> List[np.ndarray]:
        """Run inference"""
        if not self.session:
            raise RuntimeError(f"Model {self.model_name} not loaded")
        
        try:
            # Run inference
            outputs = self.session.run(
                self.output_names,
                {self.input_name: input_data}
            )
            return outputs
            
        except Exception as e:
            logger.error(f"Inference error in {self.model_name}: {e}")
            raise
    
    def get_input_shape(self) -> tuple:
        """Get expected input shape"""
        if self.session:
            return self.session.get_inputs()[0].shape
        return None


class FrameBuffer:
    """Buffer for temporal sequence processing"""
    
    def __init__(self, buffer_size: int = 16):
        self.buffer_size = buffer_size
        self.buffers: Dict[str, List] = {}  # camera_id -> frame list
    
    def add_frame(self, camera_id: str, frame: np.ndarray, metadata: Dict):
        """Add frame to buffer"""
        if camera_id not in self.buffers:
            self.buffers[camera_id] = []
        
        self.buffers[camera_id].append((frame, metadata))
        
        # Maintain buffer size
        if len(self.buffers[camera_id]) > self.buffer_size:
            self.buffers[camera_id].pop(0)
    
    def get_sequence(self, camera_id: str, length: int) -> Optional[tuple]:
        """Get sequence of frames"""
        if camera_id not in self.buffers:
            return None
        
        if len(self.buffers[camera_id]) < length:
            return None
        
        # Get last 'length' frames
        sequence = self.buffers[camera_id][-length:]
        frames = [item[0] for item in sequence]
        metadata = sequence[-1][1]  # Use latest metadata
        
        return np.array(frames), metadata
    
    def clear(self, camera_id: Optional[str] = None):
        """Clear buffer"""
        if camera_id:
            self.buffers[camera_id] = []
        else:
            self.buffers.clear()


def softmax(x: np.ndarray) -> np.ndarray:
    """Compute softmax"""
    exp_x = np.exp(x - np.max(x))
    return exp_x / exp_x.sum()


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Compute sigmoid"""
    return 1 / (1 + np.exp(-x))


def nms(boxes: List[Dict], iou_threshold: float = 0.5) -> List[Dict]:
    """Non-maximum suppression for bounding boxes"""
    if not boxes:
        return []
    
    # Sort by confidence
    boxes = sorted(boxes, key=lambda x: x['confidence'], reverse=True)
    
    selected = []
    
    while boxes:
        current = boxes.pop(0)
        selected.append(current)
        
        # Filter overlapping boxes
        boxes = [
            box for box in boxes
            if compute_iou(current, box) < iou_threshold
        ]
    
    return selected


def compute_iou(box1: Dict, box2: Dict) -> float:
    """Compute Intersection over Union"""
    x1 = max(box1['x'], box2['x'])
    y1 = max(box1['y'], box2['y'])
    x2 = min(box1['x'] + box1['width'], box2['x'] + box2['width'])
    y2 = min(box1['y'] + box1['height'], box2['y'] + box2['height'])
    
    if x2 < x1 or y2 < y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area1 = box1['width'] * box1['height']
    area2 = box2['width'] * box2['height']
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0


def generate_sequence_id(camera_id: str, timestamp: str) -> str:
    """Generate unique sequence ID"""
    return f"{camera_id}_{timestamp.replace(':', '').replace('.', '')}"
