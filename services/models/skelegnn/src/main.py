"""
SkeleGNN Model Service
Skeleton-based action recognition using Graph Neural Networks
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Optional
import numpy as np
import zmq
import zmq.asyncio
from fastapi import FastAPI
import yaml
import cv2

# Add common utilities to path
sys.path.append('/app')
from common.model_utils import ONNXModelWrapper, ModelOutput, FrameBuffer, softmax, generate_sequence_id

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SkeleGNNService:
    """SkeleGNN model inference service"""
    
    # Action classes
    ACTION_CLASSES = [
        "normal",
        "fight",
        "fall",
        "running",
        "trespassing",
        "threatening_pose",
        "suspicious_movement"
    ]
    
    def __init__(self):
        self.model = None
        self.frame_buffer = FrameBuffer(buffer_size=16)
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_subscriber = None
        self.zmq_publisher = None
        self.running = False
        self.inference_count = 0
        
        # Model config
        self.sequence_length = 16  # Number of frames for temporal analysis
        self.confidence_threshold = 0.5
        
    async def initialize(self):
        """Initialize service and load model"""
        try:
            # Load ONNX model
            model_path = os.getenv("MODEL_PATH", "/app/weights/skelegnn.onnx")
            
            if not os.path.exists(model_path):
                logger.warning(f"Model not found at {model_path}, using placeholder")
                self.model = None  # Will use dummy inference
            else:
                self.model = ONNXModelWrapper(model_path, "SkeleGNN")
                if not self.model.load():
                    logger.error("Failed to load model")
                    self.model = None
            
            # Connect ZeroMQ subscriber
            preproc_host = os.getenv("PREPROCESSING_HOST", "preprocessing")
            preproc_port = os.getenv("PREPROCESSING_ZMQ_PORT", "5556")
            self.zmq_subscriber = self.zmq_context.socket(zmq.SUB)
            self.zmq_subscriber.connect(f"tcp://{preproc_host}:{preproc_port}")
            self.zmq_subscriber.setsockopt_string(zmq.SUBSCRIBE, "skele_input")
            logger.info(f"Subscribed to preprocessing at {preproc_host}:{preproc_port}")
            
            # Bind ZeroMQ publisher
            pub_port = os.getenv("ZMQ_PUB_PORT", "5557")
            self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
            self.zmq_publisher.bind(f"tcp://*:{pub_port}")
            logger.info(f"Publisher bound to port {pub_port}")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    def extract_skeleton(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract skeleton keypoints from frame
        In production, use MediaPipe or OpenPose
        For now, return placeholder
        """
        # Placeholder: 17 keypoints with (x, y, confidence)
        # Format: COCO keypoint format
        # In production, integrate MediaPipe Pose or similar
        
        # Dummy keypoints for demo
        h, w = frame.shape[:2]
        keypoints = np.random.rand(17, 3)  # 17 joints, (x, y, conf)
        keypoints[:, 0] *= w  # Scale x to frame width
        keypoints[:, 1] *= h  # Scale y to frame height
        keypoints[:, 2] = 0.8  # Confidence
        
        return keypoints
    
    def classify_action(self, skeleton_sequence: np.ndarray) -> tuple:
        """
        Classify action from skeleton sequence
        Returns: (class_label, class_id, confidence, logits)
        """
        if self.model:
            try:
                # Prepare input: (1, sequence_length, num_joints, features)
                input_data = skeleton_sequence.reshape(1, -1, 17, 3).astype(np.float32)
                
                # Run inference
                outputs = self.model.infer(input_data)
                logits = outputs[0][0]  # (num_classes,)
                
                # Apply softmax
                probs = softmax(logits)
                class_id = int(np.argmax(probs))
                confidence = float(probs[class_id])
                class_label = self.ACTION_CLASSES[class_id]
                
                return class_label, class_id, confidence, probs.tolist()
                
            except Exception as e:
                logger.error(f"Inference error: {e}")
                return "unknown", -1, 0.0, []
        else:
            # Dummy inference for demo
            class_id = np.random.choice(len(self.ACTION_CLASSES), p=[0.7, 0.1, 0.05, 0.05, 0.05, 0.03, 0.02])
            class_label = self.ACTION_CLASSES[class_id]
            confidence = np.random.uniform(0.6, 0.95)
            
            # Create dummy probabilities
            probs = np.random.rand(len(self.ACTION_CLASSES))
            probs[class_id] = confidence * 2
            probs = probs / probs.sum()
            
            return class_label, int(class_id), float(confidence), probs.tolist()
    
    async def process_frames(self):
        """Main processing loop"""
        self.running = True
        logger.info("Starting frame processing loop")
        
        while self.running:
            try:
                # Receive frame
                message = await self.zmq_subscriber.recv_multipart()
                
                if len(message) != 4:
                    continue
                
                topic, metadata_bytes, frame_bytes, flow_bytes = message
                metadata = yaml.safe_load(metadata_bytes.decode('utf-8'))
                
                # Decode frame
                frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                
                if frame is None:
                    continue
                
                camera_id = metadata['camera_id']
                
                # Extract skeleton from current frame
                skeleton = self.extract_skeleton(frame)
                
                # Add to buffer
                self.frame_buffer.add_frame(camera_id, skeleton, metadata)
                
                # Check if we have enough frames for sequence
                sequence_data = self.frame_buffer.get_sequence(camera_id, self.sequence_length)
                
                if sequence_data is None:
                    continue  # Not enough frames yet
                
                skeleton_sequence, latest_metadata = sequence_data
                
                # Classify action
                class_label, class_id, confidence, probs = self.classify_action(skeleton_sequence)
                
                # Only publish if confidence exceeds threshold
                if confidence < self.confidence_threshold:
                    continue
                
                # Create output
                output = ModelOutput(
                    model="skelegnn",
                    timestamp=latest_metadata['timestamp'],
                    camera_id=camera_id,
                    camera_name=latest_metadata['camera_name'],
                    sequence_id=generate_sequence_id(camera_id, latest_metadata['timestamp']),
                    frame_number=latest_metadata['frame_number'],
                    confidence=confidence,
                    class_label=class_label,
                    class_id=class_id,
                    data={
                        "skeleton_keypoints": skeleton.tolist(),
                        "action_probabilities": probs,
                        "sequence_length": self.sequence_length
                    }
                )
                
                # Publish result
                await self.zmq_publisher.send_multipart([
                    b"skelegnn_output",
                    yaml.dump(output.to_dict()).encode('utf-8')
                ])
                
                self.inference_count += 1
                
                if self.inference_count % 10 == 0:
                    logger.debug(f"Processed {self.inference_count} sequences")
                
            except Exception as e:
                logger.error(f"Error processing frame: {e}")
                await asyncio.sleep(0.1)
    
    async def stop(self):
        """Stop service"""
        self.running = False
        if self.zmq_subscriber:
            self.zmq_subscriber.close()
        if self.zmq_publisher:
            self.zmq_publisher.close()
        self.zmq_context.term()


# FastAPI application
app = FastAPI(title="SkeleGNN Model Service", version="1.0.0")
service = SkeleGNNService()


@app.on_event("startup")
async def startup_event():
    await service.initialize()
    asyncio.create_task(service.process_frames())


@app.on_event("shutdown")
async def shutdown_event():
    await service.stop()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": "skelegnn"}


@app.get("/status")
async def get_status():
    return {
        "model": "skelegnn",
        "running": service.running,
        "inference_count": service.inference_count,
        "sequence_length": service.sequence_length,
        "confidence_threshold": service.confidence_threshold,
        "action_classes": service.ACTION_CLASSES,
        "model_loaded": service.model is not None
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)
