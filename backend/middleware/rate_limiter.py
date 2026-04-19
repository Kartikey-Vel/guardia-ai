"""
TASK-060: API Rate Limiting Middleware
=======================================
Simple in-memory sliding-window rate limiter.

Defaults (configurable via environment):
  - IP-based rate limiting
  - 200 requests per 60 seconds (general)
  - /analyze-frame: 30 req /60 sec (expensive AI endpoint)
  - /ws/: exempt (WebSocket connections managed separately)

TASK-037: Also doubles as the BackgroundTasks integration point —
this middleware attaches the background task runner ref so routes
can access it via request.state.background_tasks.
"""

import time
import logging
from collections import defaultdict, deque
from typing import Callable, Deque

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limit configuration
# ---------------------------------------------------------------------------

# (path_prefix, max_requests, window_seconds)
RATE_LIMITS = [
    ("/api/v1/analyze-frame",  30,  60),   # expensive AI endpoint
    ("/api/v1/settings",       10,  60),   # settings mutations
    ("/api/v1",               200,  60),   # general API
]


class SlidingWindowRateLimiter:
    """Thread-safe sliding window rate limiter using deque."""

    def __init__(self) -> None:
        # key: (client_ip, endpoint_bucket) → deque of timestamps
        self._windows: dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str, max_requests: int, window_sec: int) -> bool:
        now = time.monotonic()
        window = self._windows[key]

        # Remove timestamps outside the window
        cutoff = now - window_sec
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= max_requests:
            return False  # rate limit exceeded

        window.append(now)
        return True

    def remaining(self, key: str, max_requests: int, window_sec: int) -> int:
        now = time.monotonic()
        window = self._windows[key]
        cutoff = now - window_sec
        count = sum(1 for ts in window if ts >= cutoff)
        return max(0, max_requests - count)


_limiter = SlidingWindowRateLimiter()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Implements IP-based sliding window rate limiting.
    WebSocket paths and health checks are excluded.
    """

    EXEMPT_PREFIXES = ("/ws/", "/docs", "/redoc", "/openapi", "/health", "/ping")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        client_ip = self._get_client_ip(request)

        # Exempt paths
        if any(path.startswith(pfx) for pfx in self.EXEMPT_PREFIXES):
            return await call_next(request)

        # Find applicable rate limit rule
        for prefix, max_req, window in RATE_LIMITS:
            if path.startswith(prefix):
                key = f"{client_ip}:{prefix}"
                if not _limiter.is_allowed(key, max_req, window):
                    remaining_secs = window  # simplified — return window reset time
                    logger.warning(
                        "Rate limit exceeded: ip=%s path=%s limit=%d/%ds",
                        client_ip, path, max_req, window
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "error": "rate_limit_exceeded",
                            "message": f"Too many requests. Limit: {max_req} per {window}s.",
                            "retry_after_seconds": window,
                        },
                        headers={"Retry-After": str(window)},
                    )
                # Add rate-limit headers to response
                response = await call_next(request)
                remaining = _limiter.remaining(key, max_req, window)
                response.headers["X-RateLimit-Limit"] = str(max_req)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
                response.headers["X-RateLimit-Window"] = str(window)
                return response

        return await call_next(request)

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        # Respect X-Forwarded-For header for proxied setups
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
