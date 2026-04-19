import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class KeyRotator:
    """
    Manages a list of API keys and handles rotation when a key is exhausted.
    
    Usage:
    rotator = KeyRotator(cfg.gemini_api_keys)
    current_key = rotator.current_key
    ...
    if error_is_quota_limit:
        rotator.rotate()
    """

    def __init__(self, keys_string: str) -> None:
        self._keys: List[str] = [k.strip() for k in keys_string.split(",") if k.strip()]
        self._index = 0
        if not self._keys:
            logger.warning("KeyRotator initialized with zero keys.")

    @property
    def current_key(self) -> Optional[str]:
        if not self._keys:
            return None
        return self._keys[self._index]

    def rotate(self) -> bool:
        """
        Switch to the next available key.
        Returns True if we rotated to a new key, False if we ran out of keys.
        """
        if not self._keys or len(self._keys) <= 1:
            logger.warning("No more alternative keys available for rotation.")
            return False
            
        self._index = (self._index + 1) % len(self._keys)
        logger.info(f"Rotated to next API key (Index {self._index}).")
        return True

    @property
    def has_keys(self) -> bool:
        return len(self._keys) > 0
