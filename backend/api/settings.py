"""Settings API — manage runtime configuration via DB-backed key-value store."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import get_settings
from database import Setting, get_db
from models.schemas import SettingsUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

_SENSITIVE_KEYS = {"groq_api_key", "gemini_api_key", "huggingface_api_key"}


def _redact(key: str, value: str) -> str:
    if key in _SENSITIVE_KEYS and len(value) > 8:
        return value[:4] + "****" + value[-4:]
    return value


@router.get("")
def get_all_settings(db: Session = Depends(get_db)):
    """Return all settings with sensitive values redacted."""
    settings = db.query(Setting).all()
    return {s.key: _redact(s.key, s.value) for s in settings}


@router.post("")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    """Persist updated settings and reinitialize AI clients if keys changed."""
    updates = payload.model_dump(exclude_none=True)
    keys_changed: list[str] = []

    for key, value in updates.items():
        existing = db.query(Setting).filter(Setting.key == key).first()
        if existing:
            existing.value = str(value)
            existing.updated_at = datetime.utcnow()
        else:
            db.add(Setting(key=key, value=str(value)))
        keys_changed.append(key)

    db.commit()

    # Clear cached settings singleton so env overrides re-read correctly
    get_settings.cache_clear()

    # Reinitialize AI if API keys were updated
    ai_keys = _SENSITIVE_KEYS.intersection(keys_changed)
    if ai_keys:
        try:
            from ai.pipeline import pipeline
            pipeline.initialize_ai()
            logger.info("AI clients reinitialized after key update: %s", ai_keys)
        except Exception as exc:
            logger.error("AI reinit failed: %s", exc)

    return {"status": "updated", "keys_updated": keys_changed}


@router.post("/test-connection")
async def test_connections():
    """Ping configured AI providers and return connection status."""
    cfg = get_settings()
    results: dict[str, str] = {}

    # --- Groq ---
    try:
        if cfg.groq_api_key:
            from groq import Groq  # type: ignore
            client = Groq(api_key=cfg.groq_api_key)
            client.chat.completions.create(
                model=cfg.groq_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            results["groq"] = "connected"
        else:
            results["groq"] = "no_key"
    except Exception as exc:
        results["groq"] = f"error: {str(exc)[:60]}"

    # --- Gemini ---
    try:
        if cfg.gemini_api_key:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=cfg.gemini_api_key)
            model = genai.GenerativeModel(cfg.gemini_model)
            model.generate_content("ping")
            results["gemini"] = "connected"
        else:
            results["gemini"] = "no_key"
    except Exception as exc:
        results["gemini"] = f"error: {str(exc)[:60]}"

    return results
