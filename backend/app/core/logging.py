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

# Populated by RequestIdMiddleware for the lifetime of a single request.
request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injects the current request's correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx_var.get()
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
