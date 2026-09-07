"""Tests for Operational Resilience, Health Probes, Sensitive Log Masking, and Bounded Rate Limiting."""
import logging
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.logging import SensitiveDataFilter
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.main import app, lifespan


@pytest.mark.asyncio
async def test_health_liveness_endpoints():
    """Liveness probe must return 200 with alive status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/health")
        assert r1.status_code == 200
        assert r1.json()["data"]["status"] == "alive"

        r2 = await client.get("/api/v1/health/live")
        assert r2.status_code == 200
        assert r2.json()["data"]["status"] == "alive"


@pytest.mark.asyncio
async def test_health_readiness_healthy():
    """Readiness probe must return 200 with database: ok when database is responsive."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data.get("database") == "ok"


@pytest.mark.asyncio
async def test_health_readiness_failure_returns_503_without_leaks():
    """When a readiness dependency fails, return 503 without leaking credentials or trace."""
    transport = ASGITransport(app=app)
    mock_db_check = AsyncMock(side_effect=RuntimeError("psql: connection refused to 10.0.0.1:5432 with pass=secret"))
    with patch.dict("app.api.v1.health.READINESS_CHECKS", {"database": mock_db_check}):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
            assert response.status_code == 503
            body = response.json()
            assert body["success"] is False
            assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
            assert "10.0.0.1" not in str(body)
            assert "pass=secret" not in str(body)


def test_sensitive_data_filter_redacts_tokens_and_passwords():
    """SensitiveDataFilter must redact bearer tokens, passwords, and JWTs."""
    filt = SensitiveDataFilter()

    # Bearer token redaction
    rec1 = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="Authorization header found: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        args=(), exc_info=None
    )
    filt.filter(rec1)
    assert "Bearer [REDACTED]" in rec1.msg
    assert "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c" not in rec1.msg

    # Password redaction
    rec2 = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg='Failed login attempt with payload: {"username": "admin", "password": "super_secret_password_123"}',
        args=(), exc_info=None
    )
    filt.filter(rec2)
    assert '"password": "[REDACTED]"' in rec2.msg
    assert "super_secret_password_123" not in rec2.msg


@pytest.mark.asyncio
async def test_rate_limiter_memory_bounding_and_stale_pruning():
    """SlidingWindowRateLimiter must bound tracked clients and prune stale entries."""
    limiter = SlidingWindowRateLimiter(max_tracked_clients=5)

    # Insert 5 clients with older timestamps (simulate past window)
    window = 10
    for i in range(5):
        await limiter.check_rate_limit(f"ip-{i}", max_attempts=5, window_seconds=window)

    assert len(limiter._requests) == 5

    # Wait or simulate window passage by directly modifying timestamp
    for q in limiter._requests.values():
        q[0] = q[0] - (window + 1)

    # Prune stale
    pruned = await limiter.prune_stale(window_seconds=window)
    assert pruned == 5
    assert len(limiter._requests) == 0

    # Test capacity ceiling enforcement when active entries saturate limiter
    small_limiter = SlidingWindowRateLimiter(max_tracked_clients=3)
    for i in range(3):
        await small_limiter.check_rate_limit(f"active-{i}", max_attempts=5, window_seconds=60)
    
    # Next unique client exceeds capacity limit
    from app.core.exceptions import RateLimitedError
    with pytest.raises(RateLimitedError) as exc_info:
        await small_limiter.check_rate_limit("active-overflow", max_attempts=5, window_seconds=60)
    assert "capacity reached" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown():
    """Lifespan must initialize logging and cleanly dispose database engine."""
    with patch("app.main.dispose_engine", new_callable=AsyncMock) as mock_dispose:
        async with lifespan(app):
            pass
        mock_dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check_log_suppression():
    """Health check endpoints must log at DEBUG to suppress log spam, while other routes log at INFO."""
    transport = ASGITransport(app=app)
    with patch("app.middleware.logging.logger") as mock_logger:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Healthy check probe
            resp_health = await client.get("/health")
            assert resp_health.status_code == 200
            assert mock_logger.debug.called
            # Ensure info was not called for routine healthy health check
            assert not mock_logger.info.called

            mock_logger.reset_mock()

            # 2. Non-health route
            resp_other = await client.get("/api/v1/properties")
            # Whether 200 or 401, non-health path logs at info or warning (not suppressed to debug)
            if resp_other.status_code < 400:
                assert mock_logger.info.called
            else:
                assert mock_logger.warning.called or mock_logger.info.called
            assert not mock_logger.debug.called
