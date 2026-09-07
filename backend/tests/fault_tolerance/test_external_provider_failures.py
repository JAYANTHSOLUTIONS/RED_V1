"""Tests for external provider failure handling and bounded retry logic."""
import asyncio
import httpx
import pytest

from app.core.retry import retry_async, is_transient_network_or_5xx


async def test_retry_async_succeeds_after_transient_failure():
    """Operation failing once with 503 succeeds on second attempt."""
    attempts = 0

    async def flaky_call():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            req = httpx.Request("GET", "https://api.external.tn.gov/rera/verify")
            resp = httpx.Response(503, request=req)
            raise httpx.HTTPStatusError("Service Unavailable", request=req, response=resp)
        return {"status": "ACTIVE", "rera_id": "TN/01/Building/0001/2024"}

    result = await retry_async(
        flaky_call,
        max_attempts=3,
        initial_delay=0.01,
        backoff_factor=1.5,
        retryable_check=is_transient_network_or_5xx,
    )

    assert result["status"] == "ACTIVE"
    assert attempts == 2


async def test_retry_async_does_not_retry_permanent_4xx():
    """400 Bad Request or 404 Not Found must NOT be retried."""
    attempts = 0

    async def client_error_call():
        nonlocal attempts
        attempts += 1
        req = httpx.Request("GET", "https://api.external.tn.gov/patta/view")
        resp = httpx.Response(404, request=req)
        raise httpx.HTTPStatusError("Not Found", request=req, response=resp)

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await retry_async(
            client_error_call,
            max_attempts=3,
            initial_delay=0.01,
            retryable_check=is_transient_network_or_5xx,
        )

    assert exc_info.value.response.status_code == 404
    assert attempts == 1  # No retries on 404


async def test_retry_async_retries_429_rate_limit():
    """429 Too Many Requests is transient and should be retried."""
    attempts = 0

    async def rate_limited_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            req = httpx.Request("GET", "https://api.external.tn.gov/guideline-value")
            resp = httpx.Response(429, request=req)
            raise httpx.HTTPStatusError("Too Many Requests", request=req, response=resp)
        return {"guideline_value": 4500}

    result = await retry_async(
        rate_limited_call,
        max_attempts=3,
        initial_delay=0.01,
        retryable_check=is_transient_network_or_5xx,
    )

    assert result["guideline_value"] == 4500
    assert attempts == 3


async def test_retry_async_exhausts_retries_on_persistent_timeout():
    """Persistent connection timeout stops after max_attempts."""
    attempts = 0

    async def timeout_call():
        nonlocal attempts
        attempts += 1
        req = httpx.Request("GET", "https://api.external.tn.gov/slow-service")
        raise httpx.ConnectTimeout("Connection timed out after 10s", request=req)

    with pytest.raises(httpx.ConnectTimeout):
        await retry_async(
            timeout_call,
            max_attempts=3,
            initial_delay=0.01,
            retryable_check=is_transient_network_or_5xx,
        )

    assert attempts == 3


async def test_retry_async_does_not_retry_non_network_exceptions():
    """Standard exceptions like ValueError must never be retried."""
    attempts = 0

    async def bad_data_call():
        nonlocal attempts
        attempts += 1
        raise ValueError("Invalid payload encoding")

    with pytest.raises(ValueError, match="Invalid payload encoding"):
        await retry_async(
            bad_data_call,
            max_attempts=3,
            initial_delay=0.01,
            retryable_check=is_transient_network_or_5xx,
        )

    assert attempts == 1
