"""Tests for email delivery failure modes and non-duplication contracts."""
import socket
import smtplib
from unittest.mock import patch
import pytest

from app.schemas.notification import DeliveryStatus
from app.services.notifications.email import EmailNotificationChannel


async def test_email_unconfigured_host_returns_not_configured():
    """When SMTP_HOST is not set, channel gracefully returns NOT_CONFIGURED without crashing."""
    channel = EmailNotificationChannel(host="")
    result = await channel.send(
        recipient="client@example.com",
        title="Welcome",
        message="Your account is ready.",
        notification_type="SYSTEM",
    )

    assert result.success is False
    assert result.status == DeliveryStatus.NOT_CONFIGURED
    assert "not configured" in result.message.lower()


async def test_email_connection_refused_returns_failed():
    """When SMTP server is unreachable or refuses connection, return FAILED without crashing."""
    channel = EmailNotificationChannel(host="127.0.0.1", port=19999, timeout=1)

    with patch("app.services.notifications.email._send_smtp_sync", side_effect=ConnectionRefusedError("Connection refused")):
        result = await channel.send(
            recipient="client@example.com",
            title="Inspection Schedule",
            message="Visit scheduled for tomorrow.",
            notification_type="VISIT_SCHEDULED",
        )

    assert result.success is False
    assert result.status == DeliveryStatus.FAILED
    assert "SMTP dispatch error" in result.message


async def test_email_smtp_timeout_returns_failed():
    """When SMTP server hangs and times out, return FAILED cleanly."""
    channel = EmailNotificationChannel(host="10.255.255.1", port=25, timeout=1)

    with patch("app.services.notifications.email._send_smtp_sync", side_effect=TimeoutError("SMTP connection timed out")):
        result = await channel.send(
            recipient="client@example.com",
            title="Reminder",
            message="Follow up call today.",
            notification_type="FOLLOW_UP",
        )

    assert result.success is False
    assert result.status == DeliveryStatus.FAILED
    assert "timed out" in result.message.lower()


async def test_email_auth_failure_does_not_leak_password():
    """SMTP authentication failure reports error without exposing password."""
    channel = EmailNotificationChannel(
        host="smtp.example.com",
        username="consultant",
        password="SuperSecretPassword123!",
        timeout=2,
    )

    with patch("app.services.notifications.email._send_smtp_sync", side_effect=smtplib.SMTPAuthenticationError(535, b"Authentication failed")):
        result = await channel.send(
            recipient="client@example.com",
            title="Deal Update",
            message="Contract ready for review.",
            notification_type="DEAL_UPDATE",
        )

    assert result.success is False
    assert result.status == DeliveryStatus.FAILED
    assert "SuperSecretPassword123!" not in result.message


async def test_email_single_bounded_attempt_no_infinite_retry():
    """Verify email sending makes exactly one attempt to avoid sending duplicate emails."""
    call_count = 0

    def mock_send(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise socket.timeout("timed out")

    channel = EmailNotificationChannel(host="smtp.example.com", timeout=1)

    with patch("app.services.notifications.email._send_smtp_sync", side_effect=mock_send):
        result = await channel.send(
            recipient="client@example.com",
            title="Non-duplicate test",
            message="Testing single attempt policy",
            notification_type="TEST",
        )

    assert call_count == 1
    assert result.success is False
    assert result.status == DeliveryStatus.FAILED
