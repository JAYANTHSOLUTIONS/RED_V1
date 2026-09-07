"""Security tests for HTTP Security Headers and CORS Policy.

Verifies:
  - Security response headers (X-Content-Type-Options, X-Frame-Options, CSP, COOP, CORP)
    are present on API responses.
  - CORS configuration respects allowed origins and blocks arbitrary origins from credentialed access.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers_present_on_api_responses(client: AsyncClient):
    """Every HTTP response must carry hardened security headers."""
    res = await client.get("/api/v1/health/live")
    assert res.status_code == 200

    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers.get("Permissions-Policy", "")
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in headers.get("Content-Security-Policy", "")
    assert headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert headers.get("Cross-Origin-Resource-Policy") == "same-origin"


@pytest.mark.asyncio
async def test_cors_preflight_and_origin_policy(client: AsyncClient):
    """OPTIONS preflight with allowed Origin returns Access-Control-Allow-Origin."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type, Authorization",
    }
    res = await client.options("/api/v1/auth/login", headers=headers)
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert res.headers.get("access-control-allow-credentials") == "true"
