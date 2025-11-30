"""
MoodTiny Model Service
Privacy-first micro-expression and mood analysis
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

sys.path.append('/app')
from common.model_utils import ONNXModelWrapper, ModelOutput, softmax, generate_sequence_id

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MoodTinyService:
    """MoodTiny model inference service"""
    
    # Mood classes
    MOOD_CLASSES = [
        "neutral",
        "stress",
        "aggression",
        "sadness",
        "fear",
        "anxiety"
    ]
    
    def __init__(self):
        self.model = None
        self.face_cascade = None
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_subscriber = None
        self.zmq_publisher = None
        self.running = False
        self.inference_count = 0
        
        # Config
        self.privacy_mode = os.getenv("PRIVACY_MODE", "true").lower() == "true"
        self.confidence_threshold = 0.6
        self.min_face_size = 48  # Minimum face size for analysis
        
    async def initialize(self):
        """Initialize service"""
        try:
            model_path = os.getenv("MODEL_PATH", "/app/weights/moodtiny.onnx")
            
            if not os.path.exists(model_path):
                logger.warning(f"Model not found, using placeholder")
                self.model = None
            else:
                self.model = ONNXModelWrapper(model_path, "MoodTiny")
                if not self.model.load():
                    self.model = None
            
            # Load face detector
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                logger.info("Face detection loaded")
            except Exception as e:
                logger.warning(f"Face detector failed: {e}")
            
            # Connect subscriber
            preproc_host = os.getenv("PREPROCESSING_HOST", "preprocessing")
            preproc_port = os.getenv("PREPROCESSING_ZMQ_PORT", "5556")
            self.zmq_subscriber = self.zmq_context.socket(zmq.SUB)
            self.zmq_subscriber.connect(f"tcp://{preproc_host}:{preproc_port}")
            self.zmq_subscriber.setsockopt_string(zmq.SUBSCRIBE, "mood_input")
            logger.info(f"Subscribed to preprocessing")
            
            # Bind publisher
            pub_port = os.getenv("ZMQ_PUB_PORT", "5559")
            self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
            self.zmq_publisher.bind(f"tcp://*:{pub_port}")
            logger.info(f"Publisher bound to port {pub_port}")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    def detect_faces(self, frame: np.ndarray) -> list:
        """Detect faces in frame"""
        if not self.face_cascade:
            return []
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(self.min_face_size, self.min_face_size)
            )
            
            return [{"x": int(x), "y": int(y), "width": int(w), "height": int(h)} 
                    for x, y, w, h in faces]
            
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return []
    
    def extract_face_roi(self, frame: np.ndarray, face: Dict) -> Optional[np.ndarray]:
        """Extract and preprocess face ROI"""
        try:
            x, y, w, h = face['x'], face['y'], face['width'], face['height']
            face_roi = frame[y:y+h, x:x+w]
            
            # Resize to model input size (e.g., 48x48)
            face_roi = cv2.resize(face_roi, (48, 48))
            face_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            # Normalize
            face_roi = face_roi.astype(np.float32) / 255.0
            
            return face_roi
            
        except Exception as e:
            logger.error(f"Face ROI extraction error: {e}")
            return None
    
    def classify_mood(self, face_roi: np.ndarray) -> tuple:
        """
        Classify mood from face ROI
        Returns: (mood_label, mood_id, confidence, probabilities)
        """
        if self.model:
            try:
                # Prepare input: (1, 1, 48, 48)
                input_data = face_roi.reshape(1, 1, 48, 48).astype(np.float32)
                
                # Run inference
                outputs = self.model.infer(input_data)
                logits = outputs[0][0]
                
                # Apply softmax
                probs = softmax(logits)
                mood_id = int(np.argmax(probs))
                confidence = float(probs[mood_id])
                mood_label = self.MOOD_CLASSES[mood_id]
                
                return mood_label, mood_id, confidence, probs.tolist()
                
            except Exception as e:
                logger.error(f"Inference error: {e}")
                return "neutral", 0, 0.0, []
        else:
            # Dummy inference
            # Bias towards neutral for most cases
            weights = [0.6, 0.15, 0.1, 0.08, 0.05, 0.02]
            mood_id = np.random.choice(len(self.MOOD_CLASSES), p=weights)
            mood_label = self.MOOD_CLASSES[mood_id]
            confidence = np.random.uniform(0.65, 0.92)
            
            # Create dummy probabilities
            probs = np.random.rand(len(self.MOOD_CLASSES))
            probs[mood_id] = confidence * 2
            probs = probs / probs.sum()
            
            return mood_label, int(mood_id), float(confidence), probs.tolist()
    
    def aggregate_moods(self, mood_results: list) -> Dict:
        """Aggregate mood from multiple faces (privacy-preserving)"""
        if not mood_results:
            return {
                "dominant_mood": "neutral",
                "mood_distribution": {},
                "face_count": 0,
                "avg_confidence": 0.0
            }
        
        # Count moods
        mood_counts = {}
        total_confidence = 0.0
        
        for mood_label, confidence in mood_results:
            mood_counts[mood_label] = mood_counts.get(mood_label, 0) + 1
            total_confidence += confidence
        
        # Find dominant mood
        dominant_mood = max(mood_counts.items(), key=lambda x: x[1])[0]
        
        # Compute distribution
        total_faces = len(mood_results)
        mood_distribution = {k: v / total_faces for k, v in mood_counts.items()}
        
        return {
            "dominant_mood": dominant_mood,
            "mood_distribution": mood_distribution,
            "face_count": total_faces,
            "avg_confidence": total_confidence / total_faces if total_faces > 0 else 0.0
        }
    
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
                
                # Decode frame
                frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
                frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                
                if frame is None:
                    continue
                
                camera_id = metadata['camera_id']
                
                # Detect faces
                faces = self.detect_faces(frame)
                
                if not faces:
                    continue
                
                # Analyze each face
                mood_results = []
                face_moods = []
                
                for i, face in enumerate(faces):
                    face_roi = self.extract_face_roi(frame, face)
                    if face_roi is None:
                        continue
                    
                    mood_label, mood_id, confidence, probs = self.classify_mood(face_roi)
                    
                    if confidence < self.confidence_threshold:
                        continue
                    
                    mood_results.append((mood_label, confidence))
                    
                    # Store per-face data (privacy mode excludes identity)
                    face_moods.append({
                        "face_index": i if not self.privacy_mode else None,
                        "mood": mood_label,
                        "confidence": confidence,
                        "probabilities": probs if not self.privacy_mode else None
                    })
                
                if not mood_results:
                    continue
                
                # Aggregate moods (privacy-preserving)
                aggregated = self.aggregate_moods(mood_results)
                
                # Create output
                output_data = {
                    "aggregated_mood": aggregated,
                    "privacy_mode": self.privacy_mode
                }
                
                # Include individual face moods only if not in privacy mode
                if not self.privacy_mode:
                    output_data["face_moods"] = face_moods
                
                output = ModelOutput(
                    model="moodtiny",
                    timestamp=metadata['timestamp'],
                    camera_id=camera_id,
                    camera_name=metadata['camera_name'],
                    sequence_id=generate_sequence_id(camera_id, metadata['timestamp']),
                    frame_number=metadata['frame_number'],
                    confidence=aggregated['avg_confidence'],
                    class_label=aggregated['dominant_mood'],
                    data=output_data
                )
                
                # Publish
                await self.zmq_publisher.send_multipart([
                    b"moodtiny_output",
                    yaml.dump(output.to_dict()).encode('utf-8')
                ])
                
                self.inference_count += 1
                
                if self.inference_count % 10 == 0:
                    logger.debug(f"Processed {self.inference_count} frames")
                
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
app = FastAPI(title="MoodTiny Model Service", version="1.0.0")
service = MoodTinyService()


@app.on_event("startup")
async def startup_event():
    await service.initialize()
    asyncio.create_task(service.process_frames())


@app.on_event("shutdown")
async def shutdown_event():
    await service.stop()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": "moodtiny"}


@app.get("/status")
async def get_status():
    return {
        "model": "moodtiny",
        "running": service.running,
        "inference_count": service.inference_count,
        "privacy_mode": service.privacy_mode,
        "confidence_threshold": service.confidence_threshold,
        "mood_classes": service.MOOD_CLASSES,
        "model_loaded": service.model is not None
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8005"))
    uvicorn.run(app, host="0.0.0.0", port=port)
