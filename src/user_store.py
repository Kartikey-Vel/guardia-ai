from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import os
import json
import base64
import hashlib
import hmac

USERS_FILE = os.path.abspath(os.path.join(os.getenv("GUARDIA_OUTPUTS_DIR", "outputs"), "users.json"))
PROFILES_DIR = os.path.abspath(os.path.join(os.getenv("GUARDIA_OUTPUTS_DIR", "outputs"), "profiles"))


def _ensure_dirs() -> None:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    os.makedirs(PROFILES_DIR, exist_ok=True)


def _load_users() -> Dict[str, Any]:
    _ensure_dirs()
    if not os.path.exists(USERS_FILE):
        return {"users": {}}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}


def _save_users(data: Dict[str, Any]) -> None:
    _ensure_dirs()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _hash_password(password: str, salt: Optional[bytes] = None) -> Dict[str, str]:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return {
        "salt": base64.b64encode(salt).decode("ascii"),
        "hash": base64.b64encode(dk).decode("ascii"),
    }


def register_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    if not username or not password:
        return False
    db = _load_users()
    if username in db.get("users", {}):
        return False
    cred = _hash_password(password)
    db.setdefault("users", {})[username] = {"salt": cred["salt"], "hash": cred["hash"]}
    _save_users(db)
    # create empty profile
    save_profile(username, {"purpose": "", "personalized": False})
    return True


def authenticate(username: str, password: str) -> bool:
    username = username.strip().lower()
    db = _load_users()
    rec = db.get("users", {}).get(username)
    if not rec:
        return False
    try:
        salt = base64.b64decode(rec["salt"])  # type: ignore[arg-type]
        expected = base64.b64decode(rec["hash"])  # type: ignore[arg-type]
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def profile_path(username: str) -> str:
    _ensure_dirs()
    return os.path.join(PROFILES_DIR, f"{username}.json")


def load_profile(username: str) -> Dict[str, Any]:
    p = profile_path(username)
    if not os.path.exists(p):
        return {"purpose": "", "personalized": False}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"purpose": "", "personalized": False}


def save_profile(username: str, data: Dict[str, Any]) -> None:
    _ensure_dirs()
    p = profile_path(username)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
