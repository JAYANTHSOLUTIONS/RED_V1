"""Tests for Request ID correlation and sanitization.

Verifies that incoming request IDs are sanitized, validated against malicious payloads
or memory exhaustion, and that valid correlation IDs are preserved end-to-end.
"""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.middleware.request_id import is_valid_request_id


def test_is_valid_request_id():
    """Direct unit tests on request ID pattern validator."""
    assert is_valid_request_id("valid-request-id-1234") is True
    assert is_valid_request_id("corr_id:999.abc") is True
    assert is_valid_request_id(str(uuid.uuid4())) is True
    assert is_valid_request_id("") is False
    assert is_valid_request_id(None) is False
    # Characters outside allowed pattern
    assert is_valid_request_id("bad id with spaces") is False
    assert is_valid_request_id("<script>alert(1)</script>") is False
    assert is_valid_request_id("req_id\ninjection") is False
    assert is_valid_request_id("id_with_special!@#$") is False
    # Length limit: 64 chars max
    assert is_valid_request_id("a" * 64) is True
    assert is_valid_request_id("a" * 65) is False


@pytest.mark.asyncio
async def test_valid_request_id_preserved():
    """Valid correlation ID from client/proxy is retained on response."""
    transport = ASGITransport(app=app)
    custom_id = "trace-req-chennai-2026-09-07_abc:01"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": custom_id})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == custom_id


@pytest.mark.asyncio
async def test_missing_request_id_auto_generated():
    """When client provides no X-Request-ID, the server generates a valid UUID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        rid = response.headers.get("X-Request-ID")
        assert rid is not None
        # Verify it parses as UUID
        parsed = uuid.UUID(rid)
        assert str(parsed) == rid


@pytest.mark.asyncio
async def test_malformed_request_id_sanitized():
    """When client sends malicious or invalid characters, server replaces with fresh UUID."""
    transport = ASGITransport(app=app)
    malicious_id = "<script>alert('xss')</script>"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": malicious_id})
        assert response.status_code == 200
        rid = response.headers.get("X-Request-ID")
        assert rid != malicious_id
        assert "<script>" not in rid
        # Valid UUID was generated instead
        parsed = uuid.UUID(rid)
        assert str(parsed) == rid


@pytest.mark.asyncio
async def test_oversized_request_id_sanitized():
    """When client sends oversized request ID, server replaces with fresh UUID."""
    transport = ASGITransport(app=app)
    oversized_id = "x" * 200
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": oversized_id})
        assert response.status_code == 200
        rid = response.headers.get("X-Request-ID")
        assert rid != oversized_id
        assert len(rid) <= 64
        parsed = uuid.UUID(rid)
        assert str(parsed) == rid
