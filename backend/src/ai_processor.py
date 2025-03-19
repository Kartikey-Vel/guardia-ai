import asyncio
import numpy as np
import cv2
import time
import argparse
from datetime import datetime
from src.ai.video_processor import VideoProcessor, MotionDetector, WeaponDetector
from src.ai.audio_processor import AudioProcessor, GunshotDetector, ScreamDetector
from src.utils.tasmanian_logger import setup_logger
from src.api.bugs_notify import broadcast_security_alert
from src.config.yosemite_config import settings

logger = setup_logger(__name__)

# Global processors
video_proc = None
audio_proc = None

async def setup_processors():
    """Initialize and configure the AI processors."""
    global video_proc, audio_proc
    
    # Initialize video processor
    video_proc = VideoProcessor()
    
    # Add video detectors
    motion_detector = MotionDetector({"threshold": settings.MOTION_DETECTION_THRESHOLD})
    await video_proc.add_detector("motion", motion_detector)
    
    weapon_detector = WeaponDetector({"threshold": settings.WEAPON_DETECTION_THRESHOLD})
    await video_proc.add_detector("weapon", weapon_detector)
    
    # Initialize audio processor
    audio_proc = AudioProcessor()
    
    # Add audio detectors
    gunshot_detector = GunshotDetector({"threshold": 0.75})
    await audio_proc.add_detector("gunshot", gunshot_detector)
    
    scream_detector = ScreamDetector({"threshold": 0.7})
    await audio_proc.add_detector("scream", scream_detector)
    
    # Start processors
    await video_proc.start_processing()
    await audio_proc.start_processing()
    
    logger.info("AI processors initialized and ready")

async def process_video_source(source_id, source_url, interval=1.0):
    """Process frames from a video source at regular intervals."""
    global video_proc
    
    logger.info(f"Starting video processing for source {source_id}: {source_url}")
    
    try:
        # Open video source (could be a camera or video file)
        cap = cv2.VideoCapture(source_url)
        if not cap.isOpened():
            logger.error(f"Could not open video source {source_url}")
            return
        
        while True:
            # Read a frame
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Failed to read frame from source {source_id}")
                # Try to reconnect for live streams
                cap.release()
                await asyncio.sleep(5)
                cap = cv2.VideoCapture(source_url)
                continue
            
            # Process the frame
            results = await video_proc.process_frame(frame)
            
            # Check for detections that exceed thresholds
            for detector_name, detection in results["detections"].items():
                if detection.get("detected", False):
                    if detector_name == "motion" and detection.get("confidence", 0) > settings.MOTION_DETECTION_THRESHOLD:
                        await handle_detection("motion_detection", detection, source_id)
                    elif detector_name == "weapon" and detection.get("detections", []) and any(d["confidence"] > settings.WEAPON_DETECTION_THRESHOLD for d in detection["detections"]):
                        weapon_type = detection["detections"][0]["class"]
                        await handle_detection("weapon_detection", detection, source_id, weapon_type=weapon_type)
            
            # Wait before processing the next frame
            await asyncio.sleep(interval)
    
    except Exception as e:
        logger.error(f"Error processing video source {source_id}: {e}")
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()

async def process_audio_source(source_id, audio_data, interval=1.0):
    """Process audio chunks at regular intervals."""
    global audio_proc
    
    logger.info(f"Starting audio processing for source {source_id}")
    
    try:
        while True:
            # In a real application, you would capture audio in real-time
            # For this example, we'll simulate audio detection
            
            # Process the audio
            results = await audio_proc.process_audio(audio_data)
            
            # Check for detections
            for detector_name, detection in results["detections"].items():
                if detection.get("detected", False):
                    if detector_name == "gunshot" and detection.get("confidence", 0) > 0.75:
                        await handle_detection("gunshot_detection", detection, source_id)
                    elif detector_name == "scream" and detection.get("confidence", 0) > 0.7:
                        await handle_detection("scream_detection", detection, source_id)
            
            # Wait before processing the next audio chunk
            await asyncio.sleep(interval)
    
    except Exception as e:
        logger.error(f"Error processing audio source {source_id}: {e}")

async def handle_detection(event_type, detection, source_id, **extra_info):
    """Handle a positive detection by sending an alert."""
    # Determine threat level based on detection type and confidence
    threat_level = "low"
    confidence = detection.get("confidence", 0)
    
    if event_type == "weapon_detection" or event_type == "gunshot_detection":
        threat_level = "high"
    elif event_type == "scream_detection":
        threat_level = "medium"
    elif confidence > 0.85:
        threat_level = "medium"
    
    # Create alert description
    description = f"{event_type.replace('_', ' ').title()} detected"
    if event_type == "weapon_detection" and "weapon_type" in extra_info:
        description += f" - {extra_info['weapon_type']}"
    
    # Create alert event
    event = {
        "type": "security_alert",
        "event_type": event_type,
        "description": description,
        "threat_level": {
            "level": threat_level,
            "score": confidence
        },
        "location": f"Source {source_id}",
        "timestamp": datetime.now().isoformat()
    }
    
    # Add any extra detection info
    for key, value in extra_info.items():
        event[key] = value
    
    # Broadcast the alert
    logger.info(f"Security alert: {description} (Threat: {threat_level}, Confidence: {confidence:.2f})")
    await broadcast_security_alert(event)
    
    # In a real implementation, you would also store the event in the database
    # and potentially trigger other actions based on the threat level

async def main():
    """Main entry point for the AI processor."""
    parser = argparse.ArgumentParser(description='Guardia AI Processor')
    parser.add_argument('--video-sources', type=str, help='Comma-separated list of video source URLs')
    parser.add_argument('--interval', type=float, default=1.0, help='Processing interval in seconds')
    args = parser.parse_args()
    
    # Initialize processors
    await setup_processors()
    
    # Start processing video sources if provided
    if args.video_sources:
        video_sources = args.video_sources.split(',')
        tasks = []
        for i, source in enumerate(video_sources):
            tasks.append(asyncio.create_task(process_video_source(f"camera_{i+1}", source, args.interval)))
        
        # Also simulate some audio processing with dummy data
        dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence at 16kHz
        tasks.append(asyncio.create_task(process_audio_source("mic_1", dummy_audio, args.interval)))
        
        logger.info(f"Started processing {len(video_sources)} video sources")
        
        # Wait for all tasks
        await asyncio.gather(*tasks)
    else:
        logger.info("No video sources provided. Running in simulation mode.")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)  # Black frame
        dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence
        
        await asyncio.gather(
            process_video_source("sim_camera", dummy_frame, args.interval),
            process_audio_source("sim_mic", dummy_audio, args.interval)
        )

if __name__ == "__main__":
    asyncio.run(main())
