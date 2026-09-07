"""Application exception hierarchy.

Services and repositories raise these instead of leaking raw infrastructure
errors (SQLAlchemy exceptions, boto3 errors, etc.) up to the API boundary.
The centralized handlers registered in `app.main` translate every
`AppException` subclass into the project's standard error envelope and an
appropriate HTTP status code, without ever exposing internal details.

Business modules (Phase 2+) should raise these directly, e.g.:

    if property is None:
        raise NotFoundError("Property not found.")
"""
from typing import Any, Optional


class AppException(Exception):
    """Base class for all application-raised, user-facing errors."""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        if code is not None:
            self.code = code
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class ValidationAppError(AppException):
    """Raised for domain/business validation failures (distinct from
    Pydantic's own request-schema validation, which FastAPI handles via
    RequestValidationError)."""

    code = "VALIDATION_ERROR"
    status_code = 422
    default_message = "The provided data failed validation."


class AuthenticationError(AppException):
    code = "UNAUTHORIZED"
    status_code = 401
    default_message = "Authentication is required to access this resource."


class AuthorizationError(AppException):
    code = "FORBIDDEN"
    status_code = 403
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppException):
    code = "NOT_FOUND"
    status_code = 404
    default_message = "The requested resource was not found."


class ConflictError(AppException):
    """E.g. duplicate site-visit booking, double-submitted lead, unique
    constraint violation surfaced from the repository layer."""

    code = "RESOURCE_CONFLICT"
    status_code = 409
    default_message = "The request conflicts with the current state of the resource."


class RateLimitedError(AppException):
    code = "RATE_LIMITED"
    status_code = 429
    default_message = "Too many requests. Please try again later."


class DatabaseError(AppException):
    """Raised when a SQLAlchemy/PostgreSQL failure must be surfaced to the
    client without leaking the underlying driver error."""

    code = "DATABASE_ERROR"
    status_code = 500
    default_message = "A database error occurred. Please try again shortly."


class StorageError(AppException):
    """Raised when an object-storage (S3-compatible) failure must be
    surfaced to the client without leaking driver/provider internals."""

    code = "STORAGE_ERROR"
    status_code = 500
    default_message = "A storage error occurred. Please try again shortly."


class ServiceUnavailableError(DatabaseError):
    code = "SERVICE_UNAVAILABLE"
    status_code = 503
    default_message = "The service is temporarily unavailable."


class GatewayTimeoutError(AppException):
    """Raised when an external upstream dependency times out."""
    code = "GATEWAY_TIMEOUT"
    status_code = 504
    default_message = "An upstream service timed out. Please try again shortly."

