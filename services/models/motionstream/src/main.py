"""
MotionStream Model Service
Motion anomaly detection using optical flow and temporal convolutions
"""

import asyncio
import logging
import os
import sys
from typing import Dict, Optional, List
import numpy as np
import zmq
import zmq.asyncio
from fastapi import FastAPI
import yaml
import cv2

sys.path.append('/app')
from common.model_utils import ONNXModelWrapper, ModelOutput, FrameBuffer, sigmoid, generate_sequence_id

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MotionStreamService:
    """MotionStream model inference service"""
    
    def __init__(self):
        self.model = None
        self.frame_buffer = FrameBuffer(buffer_size=8)
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_subscriber = None
        self.zmq_publisher = None
        self.running = False
        self.inference_count = 0
        
        # Config
        self.sequence_length = 8
        self.anomaly_threshold = 0.7
        
    async def initialize(self):
        """Initialize service"""
        try:
            model_path = os.getenv("MODEL_PATH", "/app/weights/motionstream.onnx")
            
            if not os.path.exists(model_path):
                logger.warning(f"Model not found, using placeholder")
                self.model = None
            else:
                self.model = ONNXModelWrapper(model_path, "MotionStream")
                if not self.model.load():
                    self.model = None
            
            # Connect subscriber
            preproc_host = os.getenv("PREPROCESSING_HOST", "preprocessing")
            preproc_port = os.getenv("PREPROCESSING_ZMQ_PORT", "5556")
            self.zmq_subscriber = self.zmq_context.socket(zmq.SUB)
            self.zmq_subscriber.connect(f"tcp://{preproc_host}:{preproc_port}")
            self.zmq_subscriber.setsockopt_string(zmq.SUBSCRIBE, "motion_input")
            logger.info(f"Subscribed to preprocessing")
            
            # Bind publisher
            pub_port = os.getenv("ZMQ_PUB_PORT", "5558")
            self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
            self.zmq_publisher.bind(f"tcp://*:{pub_port}")
            logger.info(f"Publisher bound to port {pub_port}")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    def compute_motion_features(self, optical_flow: np.ndarray) -> Dict:
        """Extract motion features from optical flow"""
        if optical_flow is None or optical_flow.size == 0:
            return {
                "magnitude_mean": 0.0,
                "magnitude_max": 0.0,
                "direction_variance": 0.0,
                "motion_density": 0.0
            }
        
        # Compute magnitude and angle
        magnitude = np.sqrt(optical_flow[..., 0]**2 + optical_flow[..., 1]**2)
        angle = np.arctan2(optical_flow[..., 1], optical_flow[..., 0])
        
        features = {
            "magnitude_mean": float(np.mean(magnitude)),
            "magnitude_max": float(np.max(magnitude)),
            "magnitude_std": float(np.std(magnitude)),
            "direction_variance": float(np.var(angle)),
            "motion_density": float(np.sum(magnitude > 2.0) / magnitude.size)
        }
        
        return features
    
    def detect_anomaly(self, motion_sequence: List[Dict]) -> tuple:
        """
        Detect motion anomalies
        Returns: (anomaly_score, is_anomaly, motion_mask, details)
        """
        if self.model:
            try:
                # Prepare input features
                feature_array = np.array([
                    [m["magnitude_mean"], m["magnitude_max"], m["direction_variance"], m["motion_density"]]
                    for m in motion_sequence
                ]).astype(np.float32)
                
                input_data = feature_array.reshape(1, -1, 4)
                
                # Run inference
                outputs = self.model.infer(input_data)
                anomaly_score = float(sigmoid(outputs[0][0]))
                
                is_anomaly = anomaly_score > self.anomaly_threshold
                
                # Create motion mask (placeholder)
                motion_mask = None
                
                details = {
                    "raw_score": float(outputs[0][0]),
                    "threshold": self.anomaly_threshold
                }
                
                return anomaly_score, is_anomaly, motion_mask, details
                
            except Exception as e:
                logger.error(f"Inference error: {e}")
                return 0.0, False, None, {}
        else:
            # Dummy inference
            avg_magnitude = np.mean([m["magnitude_mean"] for m in motion_sequence])
            
            # Simple heuristic: high motion = higher anomaly score
            anomaly_score = min(avg_magnitude / 10.0, 1.0)
            
            # Add some randomness for demo
            anomaly_score = float(np.clip(anomaly_score + np.random.uniform(-0.2, 0.2), 0, 1))
            
            is_anomaly = anomaly_score > self.anomaly_threshold
            
            details = {
                "avg_magnitude": avg_magnitude,
                "threshold": self.anomaly_threshold
            }
            
            return anomaly_score, is_anomaly, None, details
    
    async def process_frames(self):
        """Main processing loop"""
        self.running = True
        logger.info("Starting frame processing loop")
        
        while self.running:
            try:
                message = await self.zmq_subscriber.recv_multipart()
                
                if len(message) != 4:
                    continue
                
                topic, metadata_bytes, frame_bytes, flow_bytes = message
                metadata = yaml.safe_load(metadata_bytes.decode('utf-8'))
                
                camera_id = metadata['camera_id']
                
                # Decode optical flow if available
                optical_flow = None
                if flow_bytes and metadata.get('has_optical_flow'):
                    flow_shape = tuple(metadata.get('optical_flow_shape', []))
                    if flow_shape:
                        optical_flow = np.frombuffer(flow_bytes, dtype=np.float32).reshape(flow_shape)
                
                # Compute motion features
                motion_features = self.compute_motion_features(optical_flow)
                
                # Add to buffer
                self.frame_buffer.add_frame(camera_id, motion_features, metadata)
                
                # Get sequence
                sequence_data = self.frame_buffer.get_sequence(camera_id, self.sequence_length)
                
                if sequence_data is None:
                    continue
                
                motion_sequence, latest_metadata = sequence_data
                
                # Detect anomaly
                anomaly_score, is_anomaly, motion_mask, details = self.detect_anomaly(
                    motion_sequence.tolist()
                )
                
                # Only publish anomalies
                if not is_anomaly:
                    continue
                
                # Create output
                output = ModelOutput(
                    model="motionstream",
                    timestamp=latest_metadata['timestamp'],
                    camera_id=camera_id,
                    camera_name=latest_metadata['camera_name'],
                    sequence_id=generate_sequence_id(camera_id, latest_metadata['timestamp']),
                    frame_number=latest_metadata['frame_number'],
                    confidence=anomaly_score,
                    class_label="motion_anomaly",
                    data={
                        "anomaly_score": anomaly_score,
                        "motion_features": motion_features,
                        "sequence_length": self.sequence_length,
                        "details": details
                    }
                )
                
                # Publish
                await self.zmq_publisher.send_multipart([
                    b"motionstream_output",
                    yaml.dump(output.to_dict()).encode('utf-8')
                ])
                
                self.inference_count += 1
                logger.info(f"Motion anomaly detected: {anomaly_score:.3f}")
                
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
app = FastAPI(title="MotionStream Model Service", version="1.0.0")
service = MotionStreamService()


@app.on_event("startup")
async def startup_event():
    await service.initialize()
    asyncio.create_task(service.process_frames())


@app.on_event("shutdown")
async def shutdown_event():
    await service.stop()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": "motionstream"}


@app.get("/status")
async def get_status():
    return {
        "model": "motionstream",
        "running": service.running,
        "inference_count": service.inference_count,
        "sequence_length": service.sequence_length,
        "anomaly_threshold": service.anomaly_threshold,
        "model_loaded": service.model is not None
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
