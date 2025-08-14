from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
import json


DEFAULT_DIR = os.path.abspath(os.getenv("GUARDIA_OUTPUTS_DIR", "outputs"))
DEFAULT_FILE = os.path.join(DEFAULT_DIR, "trusted.json")


def _user_trusted_file(username: Optional[str]) -> str:
    if not username:
        return DEFAULT_FILE
    safe = str(username).strip().lower().replace('/', '_').replace('\\', '_')
    base = os.path.join(DEFAULT_DIR, 'users', safe)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'trusted.json')


def _ensure_dir() -> None:
    os.makedirs(DEFAULT_DIR, exist_ok=True)


def load(username: Optional[str] = None) -> Dict[str, Any]:
    _ensure_dir()
    tf = _user_trusted_file(username)
    if not os.path.exists(tf):
        return {"trusted": [], "suppress_labels": ["knife", "gun"]}
    try:
        with open(tf, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"trusted": [], "suppress_labels": ["knife", "gun"]}


def save(data: Dict[str, Any], username: Optional[str] = None) -> None:
    _ensure_dir()
    tf = _user_trusted_file(username)
    with open(tf, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_trusted(username: Optional[str] = None) -> List[str]:
    return list(load(username).get("trusted", []))


def add_trusted(name: str, username: Optional[str] = None) -> None:
    data = load(username)
    t = set(data.get("trusted", []))
    t.add(name)
    data["trusted"] = sorted(t)
    save(data, username)


def remove_trusted(name: str, username: Optional[str] = None) -> None:
    data = load(username)
    data["trusted"] = [n for n in data.get("trusted", []) if n != name]
    save(data, username)


def get_suppress_labels(username: Optional[str] = None) -> List[str]:
    return list(load(username).get("suppress_labels", []))


def set_suppress_labels(labels: List[str], username: Optional[str] = None) -> None:
    data = load(username)
    data["suppress_labels"] = labels
    save(data, username)
