from __future__ import annotations
from typing import Dict, Any, List, Optional
import os
import json


DEFAULT_ENV_DIR = os.path.abspath(os.getenv("GUARDIA_OUTPUTS_DIR", "outputs"))
DEFAULT_ENV_FILE = os.path.join(DEFAULT_ENV_DIR, "environments.json")


def _user_env_file(username: Optional[str]) -> str:
    if not username:
        return DEFAULT_ENV_FILE
    safe = str(username).strip().lower().replace('/', '_').replace('\\', '_')
    base = os.path.join(DEFAULT_ENV_DIR, 'users', safe)
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'environments.json')


def _ensure_dir() -> None:
    os.makedirs(DEFAULT_ENV_DIR, exist_ok=True)


def load_all(username: Optional[str] = None) -> Dict[str, Any]:
    _ensure_dir()
    env_file = _user_env_file(username)
    if not os.path.exists(env_file):
        return {"active": None, "items": {}}
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"active": None, "items": {}}


def save_all(data: Dict[str, Any], username: Optional[str] = None) -> None:
    _ensure_dir()
    env_file = _user_env_file(username)
    with open(env_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_envs(username: Optional[str] = None) -> List[Dict[str, Any]]:
    data = load_all(username)
    items = data.get("items", {})
    active = data.get("active")
    out = []
    for name, cfg in items.items():
        out.append({"name": name, "config": cfg, "active": name == active})
    return out


def get_active(username: Optional[str] = None) -> Optional[Dict[str, Any]]:
    data = load_all(username)
    active = data.get("active")
    if not active:
        return None
    return {"name": active, "config": data.get("items", {}).get(active)}


def set_active(name: str, username: Optional[str] = None) -> bool:
    data = load_all(username)
    if name not in data.get("items", {}):
        return False
    data["active"] = name
    save_all(data, username)
    return True


def create_env(name: str, config: Dict[str, Any], username: Optional[str] = None) -> None:
    data = load_all(username)
    data.setdefault("items", {})[name] = config
    if not data.get("active"):
        data["active"] = name
    save_all(data, username)


def delete_env(name: str, username: Optional[str] = None) -> bool:
    data = load_all(username)
    items = data.get("items", {})
    if name not in items:
        return False
    del items[name]
    if data.get("active") == name:
        data["active"] = next(iter(items.keys()), None)
    data["items"] = items
    save_all(data, username)
    return True
