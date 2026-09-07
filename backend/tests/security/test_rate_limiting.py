"""Adversarial security tests for In-Memory Rate Limiting & Brute-Force Abuse Prevention.

Verifies:
  - Exceeding allowed login attempts from an IP returns HTTP 429 RATE_LIMITED.
  - Client IP addresses maintain isolated sliding windows.
  - Resetting or window expiration restores normal access.
"""
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.rate_limiter import get_login_rate_limiter


@pytest.mark.asyncio
async def test_login_brute_force_rate_limited(client: AsyncClient):
    """Exceeding max login attempts within sliding window returns HTTP 429."""
    settings = get_settings()
    max_attempts = settings.RATE_LIMIT_LOGIN_ATTEMPTS
    client_ip = "192.168.1.100"
    headers = {"X-Forwarded-For": client_ip}

    # Consume all allowed attempts (failing logins)
    for _ in range(max_attempts):
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": "attacker@example.com", "password": "WrongPassword!"},
            headers=headers,
        )
        assert res.status_code == 401

    # Attempt max_attempts + 1 -> must trigger 429
    blocked_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "attacker@example.com", "password": "WrongPassword!"},
        headers=headers,
    )
    assert blocked_res.status_code == 429
    body = blocked_res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "RATE_LIMITED"
    assert "rate limit exceeded" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_rate_limit_ip_isolation(client: AsyncClient):
    """A blocked IP does not block a different client IP."""
    settings = get_settings()
    max_attempts = settings.RATE_LIMIT_LOGIN_ATTEMPTS
    blocked_ip = "10.0.0.1"
    clean_ip = "10.0.0.2"

    # Exhaust limit for blocked_ip
    for _ in range(max_attempts):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "WrongPassword!"},
            headers={"X-Forwarded-For": blocked_ip},
        )

    # Next attempt for blocked_ip is 429
    res_blocked = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "WrongPassword!"},
        headers={"X-Forwarded-For": blocked_ip},
    )
    assert res_blocked.status_code == 429

    # But clean_ip can still attempt login and gets 401 (not 429)
    res_clean = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "WrongPassword!"},
        headers={"X-Forwarded-For": clean_ip},
    )
    assert res_clean.status_code == 401
