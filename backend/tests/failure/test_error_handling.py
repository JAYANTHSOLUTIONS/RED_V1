"""Failure/fault-tolerance tests.

Verifies that both expected (`AppException`) and completely unexpected
exceptions are always translated into the standard, sanitized error
envelope — never a raw traceback, exception class name, or internal path.

Test-only routes are added directly to the per-test `app` fixture (see
tests/conftest.py) rather than to the production app, so no throwaway
endpoints ever ship in the real API surface.
"""
from fastapi import APIRouter

from app.core.exceptions import ConflictError, NotFoundError


def _add_fault_routes(app):
    router = APIRouter()

    @router.get("/boom/app-exception")
    async def boom_app_exception():
        raise ConflictError("Duplicate site visit booking.")

    @router.get("/boom/not-found")
    async def boom_not_found():
        raise NotFoundError("Property not found.")

    @router.get("/boom/unexpected")
    async def boom_unexpected():
        # Deliberately includes a fake "sensitive" detail to prove it never
        # reaches the client.
        raise RuntimeError("unexpected failure near /etc/passwd, secret=abc123")

    app.include_router(router, prefix="/_fault_test")


async def test_app_exception_returns_sanitized_envelope(app, client):
    _add_fault_routes(app)

    response = await client.get("/_fault_test/boom/app-exception")

    assert response.status_code == 409
    assert response.json() == {
        "success": False,
        "error": {"code": "RESOURCE_CONFLICT", "message": "Duplicate site visit booking."},
    }


async def test_not_found_error_returns_404_envelope(app, client):
    _add_fault_routes(app)

    response = await client.get("/_fault_test/boom/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {"code": "NOT_FOUND", "message": "Property not found."},
    }


async def test_unexpected_exception_is_sanitized(app, client):
    _add_fault_routes(app)

    response = await client.get("/_fault_test/boom/unexpected")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "An unexpected error occurred."

    assert "/etc/passwd" not in response.text
    assert "secret=abc123" not in response.text
    assert "RuntimeError" not in response.text
    assert "Traceback" not in response.text


async def test_unknown_route_returns_standard_not_found_envelope(client):
    response = await client.get("/api/v1/this-route-does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"
