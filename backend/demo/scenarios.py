"""
TASK-045: Demo Scenarios — Pre-scripted Threat Sequences
=========================================================
Provides scripted event sequences for the demo:
  - FIGHT (high severity physical altercation escalation)
  - INTRUSION (door breach → unauthorized access)
  - FALL (person falls, slow severity build)
  - LOITERING (medium severity sustained)
  - CROWD_SURGE (mass gathering scenario)

Triggered via POST /api/v1/demo/trigger
"""

import asyncio
import logging
import random
import uuid
from datetime import datetime
from typing import List

from database import Event, SessionLocal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS: dict = {
    "fight": [
        {"classification": "suspicious_loitering", "severity": 3, "confidence": 0.65,
         "description": "Two individuals behaving erratically near entrance.", "delay": 0},
        {"classification": "unauthorized_access", "severity": 5, "confidence": 0.72,
         "description": "Subjects moving aggressively toward restricted area.", "delay": 3},
        {"classification": "physical_altercation", "severity": 9, "confidence": 0.94,
         "description": "CRITICAL: Physical altercation in progress — security response required immediately.", "delay": 5},
        {"classification": "physical_altercation", "severity": 8, "confidence": 0.91,
         "description": "Altercation continuing — medical assistance may be needed.", "delay": 8},
    ],
    "intrusion": [
        {"classification": "suspicious_loitering", "severity": 4, "confidence": 0.71,
         "description": "Unknown individual surveying perimeter.", "delay": 0},
        {"classification": "unauthorized_access", "severity": 7, "confidence": 0.88,
         "description": "ALERT: Perimeter breach detected at warehouse door.", "delay": 4},
        {"classification": "unauthorized_access", "severity": 8, "confidence": 0.93,
         "description": "Intruder confirmed inside restricted zone — lock down in progress.", "delay": 7},
    ],
    "fall": [
        {"classification": "normal_activity", "severity": 1, "confidence": 0.97,
         "description": "Routine movement detected in corridor.", "delay": 0},
        {"classification": "suspicious_loitering", "severity": 5, "confidence": 0.78,
         "description": "Person appears unsteady — potential medical incident.", "delay": 5},
        {"classification": "abandoned_object", "severity": 8, "confidence": 0.89,
         "description": "MEDICAL ALERT: Person has fallen — first responder notification sent.", "delay": 8},
    ],
    "loitering": [
        {"classification": "suspicious_loitering", "severity": 4, "confidence": 0.74,
         "description": "Individual loitering near ATM for over 5 minutes.", "delay": 0},
        {"classification": "suspicious_loitering", "severity": 5, "confidence": 0.80,
         "description": "Continued loitering — possible surveillance of facility.", "delay": 10},
        {"classification": "suspicious_loitering", "severity": 6, "confidence": 0.85,
         "description": "NOTICE: Loitering exceeds 15 minutes — security requested to investigate.", "delay": 20},
    ],
    "crowd_surge": [
        {"classification": "normal_activity", "severity": 2, "confidence": 0.90,
         "description": "Regular crowd movement at main entrance.", "delay": 0},
        {"classification": "crowd_formation", "severity": 5, "confidence": 0.76,
         "description": "Crowd density increasing rapidly at gate 1.", "delay": 3},
        {"classification": "crowd_formation", "severity": 8, "confidence": 0.88,
         "description": "CROWD SURGE: Dangerous density threshold exceeded — barrier protocols activate.", "delay": 6},
    ],
}


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

class DemoScenarioRunner:
    """
    Runs a scripted scenario by emitting events at defined intervals
    and broadcasting them over WebSocket (TASK-045).
    """

    def __init__(self) -> None:
        self._active: bool = False
        self._current_task: asyncio.Task = None

    async def trigger(self, scenario_name: str, camera_id: str = "CAM_001") -> dict:
        """
        Start a scenario sequence. Returns immediately; scenario runs
        as a background asyncio task.
        """
        if scenario_name not in SCENARIOS:
            available = list(SCENARIOS.keys())
            return {"error": f"Unknown scenario '{scenario_name}'. Available: {available}"}

        if self._active:
            if self._current_task and not self._current_task.done():
                self._current_task.cancel()

        self._active = True
        self._current_task = asyncio.create_task(
            self._run_sequence(scenario_name, camera_id)
        )
        logger.info("Demo scenario '%s' started for camera %s.", scenario_name, camera_id)
        steps = len(SCENARIOS[scenario_name])
        total_duration = SCENARIOS[scenario_name][-1].get("delay", 0) + 2
        return {
            "status": "started",
            "scenario": scenario_name,
            "camera_id": camera_id,
            "steps": steps,
            "estimated_duration_seconds": total_duration,
        }

    async def _run_sequence(self, scenario_name: str, camera_id: str) -> None:
        from websocket.manager import manager  # lazy to avoid circular

        steps = SCENARIOS[scenario_name]
        start = asyncio.get_event_loop().time()

        for i, step in enumerate(steps):
            target_time = start + step["delay"]
            now = asyncio.get_event_loop().time()
            wait = max(0.0, target_time - now)
            await asyncio.sleep(wait)

            event = _persist_step(step, camera_id)
            await manager.broadcast_alert({
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat() + "Z",
                "camera_id": camera_id,
                "classification": event.classification,
                "severity": event.severity,
                "confidence": event.confidence,
                "description": event.description,
                "frame_base64": None,
                "attribution": {"motion": 0.35, "vision_ai": 0.45, "audio": 0.20},
                "demo": True,
                "demo_scenario": scenario_name,
                "demo_step": i + 1,
            })
            logger.info(
                "Demo step %d/%d: cls=%s sev=%d", i + 1, len(steps),
                step["classification"], step["severity"]
            )

        self._active = False
        logger.info("Demo scenario '%s' completed.", scenario_name)

    @property
    def is_active(self) -> bool:
        return self._active


def _persist_step(step: dict, camera_id: str) -> Event:
    db = SessionLocal()
    try:
        event = Event(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            camera_id=camera_id,
            classification=step["classification"],
            severity=step["severity"],
            confidence=step["confidence"],
            description=step["description"],
            attribution={"motion": 0.35, "vision_ai": 0.45, "audio": 0.20},
            ai_model="demo-scenario",
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

demo_runner = DemoScenarioRunner()
