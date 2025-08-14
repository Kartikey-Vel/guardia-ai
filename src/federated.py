from __future__ import annotations
from typing import Dict, Any, List
import os
import json

FED_DIR = os.path.abspath(os.path.join(os.getenv("GUARDIA_OUTPUTS_DIR", "outputs"), "federated"))
UPDATES_FILE = os.path.join(FED_DIR, "updates.json")
GLOBAL_FILE = os.path.join(FED_DIR, "global.json")

def _ensure():
    os.makedirs(FED_DIR, exist_ok=True)


def submit_update(username: str, profile: Dict[str, Any]) -> None:
    _ensure()
    updates: List[Dict[str, Any]] = []
    if os.path.exists(UPDATES_FILE):
        try:
            with open(UPDATES_FILE, "r", encoding="utf-8") as f:
                updates = json.load(f)
        except Exception:
            updates = []
    updates.append({"user": username, "profile": profile})
    with open(UPDATES_FILE, "w", encoding="utf-8") as f:
        json.dump(updates, f, ensure_ascii=False, indent=2)


def aggregate() -> Dict[str, Any]:
    _ensure()
    updates: List[Dict[str, Any]] = []
    if os.path.exists(UPDATES_FILE):
        try:
            with open(UPDATES_FILE, "r", encoding="utf-8") as f:
                updates = json.load(f)
        except Exception:
            updates = []
    # Very naive aggregation: choose most recent config and purpose as global suggestion
    global_model: Dict[str, Any] = {}
    if updates:
        last = updates[-1].get("profile", {})
        if isinstance(last, dict):
            global_model = {
                "config": last.get("config", {}),
                "purpose": last.get("purpose", "")
            }
    with open(GLOBAL_FILE, "w", encoding="utf-8") as f:
        json.dump(global_model, f, ensure_ascii=False, indent=2)
    return global_model
