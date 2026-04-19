"""
TASK-078: Structured Logging Setup with File Rotation
=======================================================
Configures a production-grade logger with:
  - Console (stdout) handler — colourised INFO level
  - Rotating file handler — guardia.log (10 MB max, 5 rotations)
  - Structured JSON log records for easy parsing / monitoring

Usage:
    from utils.logger import configure_logging
    configure_logging()  # call once in main.py startup
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# JSON formatter for structured log output
# ---------------------------------------------------------------------------

class JsonFormatter(logging.Formatter):
    """Outputs each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        # Extra fields from logger.info("foo", extra={"request_id": "..."})
        for key, value in record.__dict__.items():
            if key not in (
                "msg", "args", "levelname", "levelno", "pathname", "filename",
                "module", "exc_info", "exc_text", "stack_info", "lineno",
                "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process",
                "name", "message",
            ):
                payload[key] = value
        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# In-memory log buffer (last N lines — available at /api/v1/logs)
# ---------------------------------------------------------------------------

class MemoryLogHandler(logging.Handler):
    """Keeps the last ``maxlen`` log lines in memory."""

    def __init__(self, maxlen: int = 500) -> None:
        super().__init__()
        from collections import deque
        self._buffer: deque[dict] = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord) -> None:
        self._buffer.append({
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })

    def get_logs(self, n: int = 100) -> list:
        items = list(self._buffer)
        return items[-n:]


# Module-level memory handler (accessible from the system router)
memory_handler = MemoryLogHandler(maxlen=1000)


# ---------------------------------------------------------------------------
# Main configure function
# ---------------------------------------------------------------------------

def configure_logging(
    log_dir: str = "./logs",
    log_level: str = "INFO",
    enable_json_file: bool = True,
) -> None:
    """
    Set up the root logger with console + rotating file handlers.
    Call once at application startup.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # ── Console handler ──────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    root.addHandler(console)

    # ── Rotating file handler (plain text) ────────────────────────
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=str(log_path / "guardia.log"),
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    root.addHandler(file_handler)

    # ── Rotating JSON file handler (structured) ───────────────────
    if enable_json_file:
        json_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path / "guardia.json.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        json_handler.setLevel(level)
        json_handler.setFormatter(JsonFormatter())
        root.addHandler(json_handler)

    # ── In-memory buffer handler ──────────────────────────────────
    root.addHandler(memory_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    root.info("Logging configured — level=%s, log_dir=%s", log_level, log_dir)
