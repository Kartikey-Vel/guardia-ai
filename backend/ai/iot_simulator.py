"""
TASK-043: IoT Sensor Simulator
================================
Generates synthetic auxiliary sensor readings to enrich the FusionController
context. Simulates sensors that might exist in a real deployment:

  - Sound level meter (dB)
  - Door/window contact sensors
  - PIR motion sensors (zone-based)
  - Temperature / smoke detector (environmental)
  - Vibration sensor

The readings are intentionally correlated with threat scenarios so the
FusionController can use them as additional signals.
"""

import random
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SensorReading:
    sensor_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    alert_triggered: bool = False
    zone: str = "general"


@dataclass
class IoTSnapshot:
    """Combined snapshot of all sensor readings at a point in time."""
    timestamp: str
    readings: List[SensorReading]
    anomaly_score: float   # 0.0–1.0
    summary: str           # Human-readable summary for the LLM prompt

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "anomaly_score": round(self.anomaly_score, 3),
            "summary": self.summary,
            "sensors": [
                {
                    "id": r.sensor_id,
                    "type": r.sensor_type,
                    "value": r.value,
                    "unit": r.unit,
                    "zone": r.zone,
                    "alert": r.alert_triggered,
                }
                for r in self.readings
            ],
        }


# ---------------------------------------------------------------------------
# Sensor Simulator
# ---------------------------------------------------------------------------

class IoTSensorSimulator:
    """
    Simulates a network of IoT sensors installed in a building.

    Readings drift over time and can be spiked to simulate an incident.
    """

    ZONES = ["entrance", "lobby", "warehouse", "parking", "server_room", "corridor"]

    def __init__(self) -> None:
        self._base_noise = 0.0     # 0.0 = calm, 1.0 = high alert
        self._last_spike = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_snapshot(self, threat_scenario: str = "normal") -> IoTSnapshot:
        """Return a full sensor snapshot.

        Parameters
        ----------
        threat_scenario : str
            One of "normal", "fight", "intrusion", "fall", "fire" —
            used to bias the simulated readings.
        """
        self._update_noise(threat_scenario)
        readings = self._generate_readings(threat_scenario)
        anomaly_score = self._compute_anomaly_score(readings)
        summary = self._build_summary(readings, anomaly_score, threat_scenario)

        return IoTSnapshot(
            timestamp=datetime.utcnow().isoformat() + "Z",
            readings=readings,
            anomaly_score=anomaly_score,
            summary=summary,
        )

    def get_for_fusion(self, threat_scenario: str = "normal") -> dict:
        """Return a compact dict suitable for injecting into the Groq prompt."""
        snap = self.get_snapshot(threat_scenario)
        return snap.to_dict()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _update_noise(self, scenario: str) -> None:
        now = time.time()
        if scenario != "normal":
            self._base_noise = min(1.0, self._base_noise + 0.3)
            self._last_spike = now
        else:
            # Decay noise over 30 seconds
            elapsed = now - self._last_spike
            self._base_noise = max(0.0, self._base_noise - elapsed * 0.02)

    def _generate_readings(self, scenario: str) -> List[SensorReading]:
        noise = self._base_noise
        readings: List[SensorReading] = []

        # Sound level — dB
        base_db = 45 + noise * 40 + random.gauss(0, 3)
        sound_db = max(30.0, min(120.0, base_db))
        if scenario == "fight":
            sound_db = min(120.0, sound_db + random.uniform(15, 30))
        readings.append(SensorReading(
            sensor_id="SOUND_01",
            sensor_type="sound_level",
            value=round(sound_db, 1),
            unit="dB",
            zone="entrance",
            alert_triggered=sound_db > 85,
        ))

        # Door sensors (binary: 0=closed, 1=open)
        for i, zone in enumerate(["entrance", "warehouse", "server_room"]):
            is_open = random.random() < (0.05 + noise * 0.4)
            if scenario == "intrusion" and zone == "warehouse":
                is_open = True
            readings.append(SensorReading(
                sensor_id=f"DOOR_0{i+1}",
                sensor_type="door_contact",
                value=1.0 if is_open else 0.0,
                unit="binary",
                zone=zone,
                alert_triggered=is_open and zone in ["server_room", "warehouse"],
            ))

        # PIR motion sensors
        for i, zone in enumerate(["parking", "corridor", "lobby"]):
            pir_value = random.random() < (0.1 + noise * 0.7)
            readings.append(SensorReading(
                sensor_id=f"PIR_0{i+1}",
                sensor_type="pir_motion",
                value=1.0 if pir_value else 0.0,
                unit="binary",
                zone=zone,
                alert_triggered=False,
            ))

        # Temperature
        temp_c = 22.0 + noise * 8 + random.gauss(0, 0.5)
        if scenario == "fire":
            temp_c = min(80.0, temp_c + random.uniform(20, 40))
        readings.append(SensorReading(
            sensor_id="TEMP_01",
            sensor_type="temperature",
            value=round(temp_c, 1),
            unit="°C",
            zone="server_room",
            alert_triggered=temp_c > 35,
        ))

        # Vibration
        vibration = round(random.uniform(0, 0.3) + noise * 0.5, 3)
        if scenario in ["fight", "fall"]:
            vibration = min(1.0, vibration + random.uniform(0.3, 0.6))
        readings.append(SensorReading(
            sensor_id="VIB_01",
            sensor_type="vibration",
            value=vibration,
            unit="g",
            zone="entrance",
            alert_triggered=vibration > 0.6,
        ))

        return readings

    @staticmethod
    def _compute_anomaly_score(readings: List[SensorReading]) -> float:
        alerts = sum(1 for r in readings if r.alert_triggered)
        total = len(readings)
        return round(alerts / total if total > 0 else 0.0, 3)

    @staticmethod
    def _build_summary(readings: List[SensorReading], anomaly_score: float, scenario: str) -> str:
        alerts = [r for r in readings if r.alert_triggered]
        if not alerts:
            return "All sensors nominal. No anomalies detected."
        parts = []
        for a in alerts[:3]:
            parts.append(f"{a.sensor_type} in {a.zone} ({a.value}{a.unit})")
        base = f"IoT anomaly score: {anomaly_score:.2f}. Triggered: {', '.join(parts)}."
        return base


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

iot_simulator = IoTSensorSimulator()
