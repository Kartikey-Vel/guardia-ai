"""
FusionController - Decision Engine for Guardia AI
Aggregates model outputs and makes event classification decisions
"""

import asyncio
import logging
import os
import sqlite3
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
import zmq
import zmq.asyncio
from fastapi import FastAPI
import yaml
import json

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class EventDecision:
    """Event decision output"""
    event_id: str
    camera_id: str
    camera_name: str
    timestamp: str
    event_class: str
    severity: str  # low, medium, high, critical
    confidence: float
    contributing_models: List[Dict]
    suggested_action: str
    attribution: Dict
    metadata: Dict
    
    def to_dict(self) -> Dict:
        return asdict(self)


class DecisionEngine:
    """Rule-based + lightweight ensemble decision engine"""
    
    # Severity levels
    SEVERITY_CRITICAL = "critical"
    SEVERITY_HIGH = "high"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_LOW = "low"
    
    # Event classes
    EVENT_FIGHT = "fight"
    EVENT_FALL = "fall"
    EVENT_TRESPASS = "trespassing"
    EVENT_MOTION_ANOMALY = "motion_anomaly"
    EVENT_SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    EVENT_CROWD_STRESS = "crowd_stress"
    EVENT_NORMAL = "normal"
    
    def __init__(self):
        self.rules = self.load_rules()
        
    def load_rules(self) -> Dict:
        """Load decision rules"""
        return {
            # Fight detection rules
            "fight": {
                "required_models": ["skelegnn"],
                "optional_models": ["motionstream", "moodtiny"],
                "min_confidence": 0.75,
                "severity": self.SEVERITY_CRITICAL,
                "action": "alert_immediately",
                "weight": {
                    "skelegnn": 0.7,
                    "motionstream": 0.2,
                    "moodtiny": 0.1
                }
            },
            # Fall detection
            "fall": {
                "required_models": ["skelegnn"],
                "optional_models": ["motionstream"],
                "min_confidence": 0.7,
                "severity": self.SEVERITY_HIGH,
                "action": "alert_medical",
                "weight": {
                    "skelegnn": 0.8,
                    "motionstream": 0.2
                }
            },
            # Motion anomaly
            "motion_anomaly": {
                "required_models": ["motionstream"],
                "optional_models": [],
                "min_confidence": 0.75,
                "severity": self.SEVERITY_MEDIUM,
                "action": "record_and_review",
                "weight": {
                    "motionstream": 1.0
                }
            },
            # Suspicious behavior (combo)
            "suspicious_behavior": {
                "required_models": [],
                "optional_models": ["skelegnn", "motionstream", "moodtiny"],
                "min_confidence": 0.65,
                "severity": self.SEVERITY_MEDIUM,
                "action": "monitor_closely",
                "weight": {
                    "skelegnn": 0.4,
                    "motionstream": 0.3,
                    "moodtiny": 0.3
                }
            },
            # Crowd stress
            "crowd_stress": {
                "required_models": ["moodtiny"],
                "optional_models": ["motionstream"],
                "min_confidence": 0.7,
                "severity": self.SEVERITY_LOW,
                "action": "monitor",
                "weight": {
                    "moodtiny": 0.7,
                    "motionstream": 0.3
                }
            }
        }
    
    def compute_aggregated_confidence(
        self, 
        model_outputs: List[Dict],
        rule: Dict
    ) -> tuple:
        """
        Compute weighted confidence score
        Returns: (aggregated_confidence, attribution)
        """
        weights = rule.get("weight", {})
        total_weight = 0.0
        weighted_sum = 0.0
        attribution = {}
        
        for output in model_outputs:
            model_name = output.get("model")
            confidence = output.get("confidence", 0.0)
            
            if model_name in weights:
                weight = weights[model_name]
                weighted_sum += confidence * weight
                total_weight += weight
                
                attribution[model_name] = {
                    "confidence": confidence,
                    "weight": weight,
                    "contribution": confidence * weight
                }
        
        if total_weight == 0:
            return 0.0, {}
        
        aggregated = weighted_sum / total_weight
        return aggregated, attribution
    
    def match_event_class(self, model_outputs: List[Dict]) -> Optional[tuple]:
        """
        Match model outputs to event class
        Returns: (event_class, rule, matched_outputs)
        """
        # Build model output map
        output_map = {out["model"]: out for out in model_outputs}
        
        # Check each rule
        candidates = []
        
        for event_class, rule in self.rules.items():
            required_models = rule.get("required_models", [])
            
            # Check if all required models are present
            if not all(model in output_map for model in required_models):
                continue
            
            # Get relevant outputs
            matched_outputs = []
            for model_name in rule.get("weight", {}).keys():
                if model_name in output_map:
                    matched_outputs.append(output_map[model_name])
            
            if not matched_outputs:
                continue
            
            # Compute confidence
            agg_conf, attribution = self.compute_aggregated_confidence(
                matched_outputs, rule
            )
            
            # Check threshold
            if agg_conf >= rule.get("min_confidence", 0.5):
                candidates.append((event_class, rule, matched_outputs, agg_conf, attribution))
        
        if not candidates:
            return None
        
        # Return highest confidence match
        best_match = max(candidates, key=lambda x: x[3])
        return best_match
    
    def classify_severity(
        self, 
        event_class: str, 
        confidence: float, 
        rule: Dict,
        metadata: Dict
    ) -> str:
        """Determine event severity"""
        base_severity = rule.get("severity", self.SEVERITY_LOW)
        
        # Adjust based on time of day
        hour = metadata.get("hour_of_day", 12)
        if hour < 6 or hour > 22:  # Night time
            if base_severity == self.SEVERITY_MEDIUM:
                base_severity = self.SEVERITY_HIGH
            elif base_severity == self.SEVERITY_LOW:
                base_severity = self.SEVERITY_MEDIUM
        
        # Adjust based on confidence
        if confidence >= 0.9 and base_severity == self.SEVERITY_HIGH:
            base_severity = self.SEVERITY_CRITICAL
        
        return base_severity
    
    def decide(self, model_outputs: List[Dict], metadata: Dict) -> Optional[EventDecision]:
        """
        Main decision logic
        Returns EventDecision or None if no significant event
        """
        if not model_outputs:
            return None
        
        # Match to event class
        match = self.match_event_class(model_outputs)
        
        if not match:
            return None
        
        event_class, rule, matched_outputs, confidence, attribution = match
        
        # Classify severity
        severity = self.classify_severity(event_class, confidence, rule, metadata)
        
        # Determine action
        suggested_action = rule.get("action", "monitor")
        
        # Create event decision
        event_id = self.generate_event_id(metadata)
        
        decision = EventDecision(
            event_id=event_id,
            camera_id=metadata.get("camera_id", "unknown"),
            camera_name=metadata.get("camera_name", "unknown"),
            timestamp=metadata.get("timestamp", datetime.utcnow().isoformat()),
            event_class=event_class,
            severity=severity,
            confidence=confidence,
            contributing_models=[
                {
                    "model": out["model"],
                    "class_label": out.get("class_label"),
                    "confidence": out.get("confidence")
                }
                for out in matched_outputs
            ],
            suggested_action=suggested_action,
            attribution=attribution,
            metadata=metadata
        )
        
        return decision
    
    def generate_event_id(self, metadata: Dict) -> str:
        """Generate unique event ID"""
        timestamp = metadata.get("timestamp", datetime.utcnow().isoformat())
        camera_id = metadata.get("camera_id", "unknown")
        return f"evt_{camera_id}_{timestamp.replace(':', '').replace('.', '').replace('-', '')}"


class DatabaseManager:
    """Manages SQLite database for events"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
        
    def connect(self):
        """Connect to database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_tables()
        logger.info(f"Connected to database: {self.db_path}")
    
    def create_tables(self):
        """Create database schema"""
        cursor = self.connection.cursor()
        
        # Events table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            camera_id TEXT NOT NULL,
            camera_name TEXT,
            timestamp TEXT NOT NULL,
            event_class TEXT NOT NULL,
            severity TEXT NOT NULL,
            confidence REAL NOT NULL,
            suggested_action TEXT,
            attribution TEXT,
            metadata TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Model contributions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            model_name TEXT NOT NULL,
            class_label TEXT,
            confidence REAL,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
        """)
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_camera ON events(camera_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity)")
        
        self.connection.commit()
    
    def insert_event(self, decision: EventDecision):
        """Insert event into database"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
            INSERT INTO events (
                id, camera_id, camera_name, timestamp, event_class, 
                severity, confidence, suggested_action, attribution, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.event_id,
                decision.camera_id,
                decision.camera_name,
                decision.timestamp,
                decision.event_class,
                decision.severity,
                decision.confidence,
                decision.suggested_action,
                json.dumps(decision.attribution),
                json.dumps(decision.metadata)
            ))
            
            # Insert model contributions
            for contrib in decision.contributing_models:
                cursor.execute("""
                INSERT INTO model_contributions (event_id, model_name, class_label, confidence)
                VALUES (?, ?, ?, ?)
                """, (
                    decision.event_id,
                    contrib["model"],
                    contrib.get("class_label"),
                    contrib.get("confidence")
                ))
            
            self.connection.commit()
            logger.info(f"Inserted event: {decision.event_id}")
            
        except Exception as e:
            logger.error(f"Error inserting event: {e}")
            self.connection.rollback()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()


class FusionControllerService:
    """Main Fusion Controller service"""
    
    def __init__(self):
        self.decision_engine = DecisionEngine()
        self.db_manager = None
        self.zmq_context = zmq.asyncio.Context()
        self.zmq_subscribers = {}
        self.zmq_publisher = None
        self.running = False
        self.event_count = 0
        self.model_buffer = {}  # Buffer for collecting model outputs
        self.buffer_timeout = 2.0  # seconds
        
    async def initialize(self):
        """Initialize service"""
        try:
            # Initialize database
            db_path = os.getenv("DB_PATH", "/app/data/guardia.db")
            self.db_manager = DatabaseManager(db_path)
            self.db_manager.connect()
            
            # Subscribe to model outputs
            model_services = [
                ("skelegnn", "5557"),
                ("motionstream", "5558"),
                ("moodtiny", "5559")
            ]
            
            for model_name, port in model_services:
                subscriber = self.zmq_context.socket(zmq.SUB)
                host = os.getenv(f"{model_name.upper()}_HOST", model_name)
                subscriber.connect(f"tcp://{host}:{port}")
                subscriber.setsockopt_string(zmq.SUBSCRIBE, f"{model_name}_output")
                self.zmq_subscribers[model_name] = subscriber
                logger.info(f"Subscribed to {model_name}")
            
            # Bind publisher for events
            pub_port = os.getenv("ZMQ_PUB_PORT", "5560")
            self.zmq_publisher = self.zmq_context.socket(zmq.PUB)
            self.zmq_publisher.bind(f"tcp://*:{pub_port}")
            logger.info(f"Publisher bound to port {pub_port}")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise
    
    async def collect_model_outputs(self):
        """Collect outputs from all model services"""
        self.running = True
        
        while self.running:
            try:
                # Poll all subscribers
                for model_name, subscriber in self.zmq_subscribers.items():
                    try:
                        # Non-blocking receive
                        message = await asyncio.wait_for(
                            subscriber.recv_multipart(),
                            timeout=0.1
                        )
                        
                        if len(message) != 2:
                            continue
                        
                        topic, data_bytes = message
                        model_output = yaml.safe_load(data_bytes.decode('utf-8'))
                        
                        # Add to buffer
                        camera_id = model_output.get("camera_id")
                        timestamp = model_output.get("timestamp")
                        
                        key = f"{camera_id}_{timestamp[:19]}"  # Group by second
                        
                        if key not in self.model_buffer:
                            self.model_buffer[key] = {
                                "outputs": [],
                                "timestamp": datetime.utcnow(),
                                "metadata": {
                                    "camera_id": camera_id,
                                    "camera_name": model_output.get("camera_name"),
                                    "timestamp": timestamp
                                }
                            }
                        
                        self.model_buffer[key]["outputs"].append(model_output)
                        
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error receiving from {model_name}: {e}")
                
                # Process buffered outputs
                await self.process_buffer()
                
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(0.1)
    
    async def process_buffer(self):
        """Process buffered model outputs"""
        current_time = datetime.utcnow()
        keys_to_remove = []
        
        for key, buffer_data in self.model_buffer.items():
            # Check if buffer is ready
            time_diff = (current_time - buffer_data["timestamp"]).total_seconds()
            
            if time_diff >= self.buffer_timeout:
                # Process this buffer
                decision = self.decision_engine.decide(
                    buffer_data["outputs"],
                    buffer_data["metadata"]
                )
                
                if decision:
                    # Save to database
                    self.db_manager.insert_event(decision)
                    
                    # Publish event
                    await self.zmq_publisher.send_multipart([
                        b"event",
                        yaml.dump(decision.to_dict()).encode('utf-8')
                    ])
                    
                    self.event_count += 1
                    logger.info(f"Event created: {decision.event_class} (severity: {decision.severity})")
                
                keys_to_remove.append(key)
        
        # Clean up processed buffers
        for key in keys_to_remove:
            del self.model_buffer[key]
    
    async def stop(self):
        """Stop service"""
        self.running = False
        for subscriber in self.zmq_subscribers.values():
            subscriber.close()
        if self.zmq_publisher:
            self.zmq_publisher.close()
        self.zmq_context.term()
        if self.db_manager:
            self.db_manager.close()


# FastAPI application
app = FastAPI(title="Guardia FusionController", version="1.0.0")
service = FusionControllerService()


@app.on_event("startup")
async def startup_event():
    await service.initialize()
    asyncio.create_task(service.collect_model_outputs())


@app.on_event("shutdown")
async def shutdown_event():
    await service.stop()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "fusion-controller"}


@app.get("/status")
async def get_status():
    return {
        "service": "fusion-controller",
        "running": service.running,
        "event_count": service.event_count,
        "buffer_size": len(service.model_buffer),
        "connected_models": list(service.zmq_subscribers.keys())
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8006"))
    uvicorn.run(app, host="0.0.0.0", port=port)
