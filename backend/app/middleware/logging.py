"""Controlled request logging.

Logs method, path, status code, and duration for every request. Never logs
headers, request/response bodies, query strings, or auth tokens — those
can carry PII, credentials, or document contents that must not be
persisted in log storage.
"""
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import get_logger

logger = get_logger("app.request")

HEALTH_CHECK_PATHS = {
    "/health",
    "/ready",
    "/api/v1/health/live",
    "/api/v1/health/ready",
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        path = request.url.path
        status = response.status_code

        # Suppress routine health check log spam (emit at DEBUG if healthy)
        if path in HEALTH_CHECK_PATHS:
            if status < 400:
                logger.debug(
                    "%s %s -> %s (%.1fms)",
                    request.method,
                    path,
                    status,
                    duration_ms,
                )
            else:
                logger.warning(
                    "%s %s -> %s (%.1fms) - Health check failure",
                    request.method,
                    path,
                    status,
                    duration_ms,
                )
            return response

        # Routine HTTP request logging by status severity
        if status >= 500:
            logger.error(
                "%s %s -> %s (%.1fms)",
                request.method,
                path,
                status,
                duration_ms,
            )
        elif status >= 400:
            logger.warning(
                "%s %s -> %s (%.1fms)",
                request.method,
                path,
                status,
                duration_ms,
            )
        else:
            logger.info(
                "%s %s -> %s (%.1fms)",
                request.method,
                path,
                status,
                duration_ms,
            )
        return response
