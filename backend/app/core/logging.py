"""Structured application logging.

Every log line is tagged with the request's correlation ID (see
`app.middleware.request_id`), so a single request's activity can be traced
across the router, service, and repository layers.

Security baseline: never log passwords, JWT access/refresh tokens, other
secrets, full personal data, or document contents. Log identifiers
(user/entity IDs) instead of raw payloads.
"""
import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger import jsonlogger

from app.core.config import get_settings

import re

# Populated by RequestIdMiddleware for the lifetime of a single request.
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")

SENSITIVE_PATTERNS = [
    (re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r'(["\']?(?:password|token|access_token|refresh_token|secret|jwt_secret_key)["\']?\s*[:=]\s*["\'])([^"\']+)(["\'])', re.IGNORECASE), r"\1[REDACTED]\3"),
    (re.compile(r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]+"), r"[REDACTED_JWT]"),
]


class RequestIdFilter(logging.Filter):
    """Injects the current request's correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
        return True


class SensitiveDataFilter(logging.Filter):
    """Redacts potential secrets, credentials, and tokens from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern, repl in SENSITIVE_PATTERNS:
                msg = pattern.sub(repl, msg)
            record.msg = msg
        return True


def configure_logging() -> None:
    """Configure the root logger once, at application startup.

    Idempotent: safe to call multiple times (e.g. across test runs).
    """
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.addFilter(SensitiveDataFilter())

    if settings.LOG_FORMAT == "json":
        formatter: logging.Formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | request_id=%(request_id)s | %(message)s"
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    if not settings.DEBUG:
        # Keep noisy third-party loggers quiet in normal operation; SQL
        # statements and access logs can still contain data we don't want
        # to persist by default.
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
