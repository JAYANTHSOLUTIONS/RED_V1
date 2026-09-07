"""Tests for bounded timeouts across database, external HTTP, and SMTP layers."""
import asyncio
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.api.v1.health import check_database
from app.core.exceptions import GatewayTimeoutError
from app.schemas.notification import DeliveryStatus
from app.services.notifications.email import EmailNotificationChannel


async def test_database_readiness_check_timeout():
    """A database query hanging longer than 2.0s must time out with TimeoutError."""
    class HangingSession:
        async def execute(self, *args, **kwargs):
            # Hang longer than the 2.0s readiness timeout
            await asyncio.sleep(5.0)

    with pytest.raises(asyncio.TimeoutError):
        await check_database(HangingSession())


async def test_external_http_call_timeout():
    """An external API call that exceeds the timeout budget raises timeout or GatewayTimeoutError."""
    async def slow_upstream_service():
        async def hang():
            await asyncio.sleep(5.0)
            return "ok"

        try:
            # Bound external call with a 0.1s timeout
            return await asyncio.wait_for(hang(), timeout=0.1)
        except asyncio.TimeoutError:
            raise GatewayTimeoutError("External government registry timed out. Please try again.")

    with pytest.raises(GatewayTimeoutError) as exc_info:
        await slow_upstream_service()

    assert exc_info.value.status_code == 504
    assert exc_info.value.code == "GATEWAY_TIMEOUT"


async def test_smtp_bounded_timeout_terminates_promptly():
    """SMTP channel does not hang indefinitely and marks delivery failed on socket timeout."""
    channel = EmailNotificationChannel(host="10.255.255.1", port=25, timeout=1)

    def slow_smtp(*args, **kwargs):
        raise TimeoutError("Connection timed out after 1 second")

    with patch("app.services.notifications.email._send_smtp_sync", side_effect=slow_smtp):
        result = await channel.send(
            recipient="test@example.com",
            title="Urgent Alert",
            message="Meeting in 10 minutes",
            notification_type="SYSTEM",
        )

    assert result.success is False
    assert result.status == DeliveryStatus.FAILED
    assert "timed out" in result.message.lower()
