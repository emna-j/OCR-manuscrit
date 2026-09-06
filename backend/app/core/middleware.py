"""Middleware : rate limiting (fenêtre glissante en mémoire) et logs de requêtes.

Le rate limiter est en mémoire : adapté au développement et à une
instance unique. En production multi-instances, le remplacer par une
solution partagée (Redis) — documenté dans docs/security.md.
"""
import time
from collections import defaultdict, deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limite le nombre de requêtes par adresse IP et par fenêtre."""

    _instances: list["RateLimitMiddleware"] = []

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        RateLimitMiddleware._instances.append(self)

    @classmethod
    def reset(cls) -> None:
        """Vide les compteurs de toutes les instances (utilisé par les tests)."""
        for instance in cls._instances:
            instance._hits.clear()

    async def dispatch(self, request: Request, call_next):
        # Les valeurs sont lues dynamiquement (testable par monkeypatch).
        max_requests = settings.rate_limit_max_requests
        window_seconds = settings.rate_limit_window_seconds

        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[key]
        while window and window[0] <= now - window_seconds:
            window.popleft()

        if len(window) >= max_requests:
            logger.warning(f"rate_limit_exceeded ip={key}")
            return JSONResponse(status_code=429, content={"detail": "Too many requests"})

        window.append(now)
        return await call_next(request)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log structuré (JSON) de chaque requête HTTP."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"http_request method={request.method} path={request.url.path} "
            f"status={response.status_code} duration_ms={duration_ms:.1f}"
        )
        return response