"""Unit tests for notification channel providers, dispatcher, and URL generators."""
from unittest.mock import MagicMock, patch
import uuid
import pytest

from app.schemas.notification import DeliveryStatus
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.email import EmailNotificationChannel
from app.services.notifications.in_app import InAppNotificationChannel
from app.services.notifications.whatsapp import (
    WhatsAppDeepLinkChannel,
    sanitize_phone_for_whatsapp,
)


@pytest.mark.asyncio
async def test_in_app_provider_ready():
    """InApp provider returns READY when no active session is provided."""
    provider = InAppNotificationChannel()
    res = await provider.send(
        recipient="consultant",
        title="Test Alert",
        message="Test Body",
        notification_type="FOLLOW_UP_DUE",
    )
    assert res.success is True
    assert res.status == DeliveryStatus.READY
    assert res.channel == "IN_APP"


@pytest.mark.asyncio
async def test_email_provider_unconfigured():
    """Email provider gracefully returns NOT_CONFIGURED when host is empty."""
    provider = EmailNotificationChannel(host="")
    res = await provider.send(
        recipient="client@example.com",
        title="Follow-up Reminder",
        message="Please check your documents.",
        notification_type="FOLLOW_UP_DUE",
    )
    assert res.success is False
    assert res.status == DeliveryStatus.NOT_CONFIGURED
    assert "not configured" in res.message


@pytest.mark.asyncio
async def test_email_provider_invalid_recipient():
    """Email provider rejects invalid email format without throwing unhandled exceptions."""
    provider = EmailNotificationChannel(host="smtp.example.com")
    res = await provider.send(
        recipient="invalid-email-string",
        title="Alert",
        message="Body",
        notification_type="GENERAL",
    )
    assert res.success is False
    assert res.status == DeliveryStatus.FAILED
    assert "Invalid or missing recipient" in res.message


@pytest.mark.asyncio
async def test_email_provider_mock_smtp_success():
    """Email provider sends email via mocked SMTP."""
    provider = EmailNotificationChannel(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pwd",
        from_addr="noreply@example.com",
        use_tls=True,
    )

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        res = await provider.send(
            recipient="test@example.com",
            title="Important Alert",
            message="Your site visit is confirmed.",
            notification_type="SITE_VISIT_CONFIRMED",
        )

        assert res.success is True
        assert res.status == DeliveryStatus.SENT
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pwd")
        mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_email_provider_mock_smtp_failure():
    """Email provider catches SMTP failures and returns FAILED without crashing."""
    provider = EmailNotificationChannel(
        host="smtp.example.com",
        port=587,
    )

    with patch("smtplib.SMTP", side_effect=OSError("Network unreachable")):
        res = await provider.send(
            recipient="test@example.com",
            title="Important Alert",
            message="Your site visit is confirmed.",
            notification_type="SITE_VISIT_CONFIRMED",
        )

        assert res.success is False
        assert res.status == DeliveryStatus.FAILED
        assert "Network unreachable" in res.message


def test_sanitize_phone_for_whatsapp():
    """Standard 10-digit Indian phone numbers receive 91 prefix."""
    assert sanitize_phone_for_whatsapp("9876543210") == "919876543210"
    assert sanitize_phone_for_whatsapp("+91 98765 43210") == "919876543210"
    assert sanitize_phone_for_whatsapp("919876543210") == "919876543210"
    assert sanitize_phone_for_whatsapp("14155552671") == "14155552671"


@pytest.mark.asyncio
async def test_whatsapp_deep_link_generation():
    """WhatsApp provider formats sanitized digits and safely URL-encodes message."""
    provider = WhatsAppDeepLinkChannel()
    res = await provider.send(
        recipient="9876543210",
        title="Site Visit Confirmed",
        message="Hello Mr. Ramanathan, your site visit at Coimbatore is confirmed for tomorrow 10:00 AM.",
        notification_type="SITE_VISIT_CONFIRMED",
    )
    assert res.success is True
    assert res.status == DeliveryStatus.READY
    assert res.channel == "WHATSAPP"
    assert res.deep_link is not None
    assert "https://wa.me/919876543210?text=" in res.deep_link
    assert "Ramanathan" in res.deep_link
    assert " " not in res.deep_link  # Spaces must be URL-encoded


@pytest.mark.asyncio
async def test_whatsapp_invalid_phone():
    """WhatsApp provider fails gracefully when phone number is too short."""
    provider = WhatsAppDeepLinkChannel()
    res = await provider.send(
        recipient="123",
        title="Title",
        message="Msg",
        notification_type="GENERAL",
    )
    assert res.success is False
    assert res.status == DeliveryStatus.FAILED
    assert "Invalid phone number format" in res.message


@pytest.mark.asyncio
async def test_notification_dispatcher():
    """Dispatcher routes correctly to registered providers and rejects unsupported channels."""
    dispatcher = NotificationDispatcher()

    # Route to WHATSAPP
    res_wa = await dispatcher.dispatch(
        channel_name="WHATSAPP",
        recipient="9876543210",
        title="Call Reminder",
        message="Please check paperwork",
        notification_type="FOLLOW_UP_DUE",
    )
    assert res_wa.channel == "WHATSAPP"
    assert res_wa.success is True

    # Unsupported channel
    res_unknown = await dispatcher.dispatch(
        channel_name="CARRIER_PIGEON",
        recipient="any",
        title="Title",
        message="Message",
        notification_type="GENERAL",
    )
    assert res_unknown.success is False
    assert res_unknown.status == DeliveryStatus.FAILED
    assert "not supported" in res_unknown.message
