from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    NotFoundError,
    RateLimitedError,
    ServiceUnavailableError,
    StorageError,
    ValidationAppError,
)


def test_app_exception_defaults():
    exc = AppException()
    assert exc.code == "INTERNAL_ERROR"
    assert exc.status_code == 500
    assert exc.message == "An unexpected error occurred."


def test_not_found_error_custom_message():
    exc = NotFoundError("Property not found.")
    assert exc.code == "NOT_FOUND"
    assert exc.status_code == 404
    assert exc.message == "Property not found."


def test_exception_details_default_to_empty_dict():
    exc = AppException()
    assert exc.details == {}


def test_exception_accepts_details():
    exc = ConflictError("Duplicate booking.", details={"slot_id": "abc-123"})
    assert exc.details == {"slot_id": "abc-123"}


def test_status_codes_match_spec_error_codes():
    assert ValidationAppError().code == "VALIDATION_ERROR"
    assert AuthenticationError().code == "UNAUTHORIZED"
    assert AuthorizationError().code == "FORBIDDEN"
    assert ConflictError().code == "RESOURCE_CONFLICT"
    assert RateLimitedError().code == "RATE_LIMITED"

    assert ValidationAppError().status_code == 422
    assert AuthenticationError().status_code == 401
    assert AuthorizationError().status_code == 403
    assert ConflictError().status_code == 409
    assert RateLimitedError().status_code == 429


def test_infrastructure_errors_do_not_leak_driver_details():
    exc = DatabaseError()
    assert "sql" not in exc.message.lower()
    assert exc.status_code == 500

    exc = StorageError()
    assert "s3" not in exc.message.lower()
    assert exc.status_code == 500


def test_service_unavailable_error():
    exc = ServiceUnavailableError()
    assert exc.code == "SERVICE_UNAVAILABLE"
    assert exc.status_code == 503
