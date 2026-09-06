"""Integration tests for cross-cutting middleware behavior."""
from app.middleware.request_id import REQUEST_ID_HEADER


async def test_security_headers_present_on_every_response(client):
    response = await client.get("/api/v1/health/live")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


async def test_request_id_is_generated_when_absent(client):
    response = await client.get("/api/v1/health/live")

    assert REQUEST_ID_HEADER in response.headers
    assert len(response.headers[REQUEST_ID_HEADER]) > 0


async def test_request_id_is_echoed_back_when_provided(client):
    custom_id = "test-correlation-id-123"

    response = await client.get(
        "/api/v1/health/live", headers={REQUEST_ID_HEADER: custom_id}
    )

    assert response.headers[REQUEST_ID_HEADER] == custom_id


async def test_cors_preflight_allows_configured_origin(client):
    response = await client.options(
        "/api/v1/health/live",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


async def test_cors_preflight_rejects_unconfigured_origin(client):
    response = await client.options(
        "/api/v1/health/live",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" not in response.headers
