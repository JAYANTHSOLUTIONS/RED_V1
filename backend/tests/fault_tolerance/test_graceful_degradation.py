"""Tests for graceful degradation when non-critical external dependencies fail."""
from datetime import datetime, timezone
from decimal import Decimal
import uuid
from unittest.mock import patch
import pytest
from sqlalchemy import select

from app.db.session import AsyncSessionFactory
from app.models.client import Client
from app.schemas.notification import DeliveryStatus
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.email import EmailNotificationChannel


async def test_business_mutation_succeeds_when_email_notification_fails():
    """Client creation and business transaction must succeed even if notification dispatch fails."""
    client_name = f"Degradation Client {uuid.uuid4().hex[:6]}"
    phone = f"+9198{uuid.uuid4().int % 100000000:08d}"
    email = "client-fail@example.com"

    dispatcher = NotificationDispatcher(email_channel=EmailNotificationChannel(host="smtp.example.com"))

    # 1. Perform core business mutation
    async with AsyncSessionFactory() as session:
        async with session.begin():
            client = Client(
                full_name=client_name,
                phone=phone,
                email=email,
                classification="BUYER",
            )
            session.add(client)
            await session.flush()
            client_id = client.id

    # 2. Simulate email dispatch failure
    with patch("app.services.notifications.email._send_smtp_sync", side_effect=ConnectionRefusedError("SMTP unreachable")):
        delivery_result = await dispatcher.dispatch(
            channel_name="EMAIL",
            recipient=email,
            title="Registration Welcome",
            message="Welcome to RED_V1 real-estate consultancy.",
            notification_type="CLIENT_WELCOME",
            entity_type="CLIENT",
            entity_id=client_id,
        )

    # 3. Verify notification failed gracefully without raising an unhandled exception
    assert delivery_result.success is False
    assert delivery_result.status == DeliveryStatus.FAILED
    assert "SMTP dispatch error" in delivery_result.message

    # 4. Verify core business entity is preserved and intact in PostgreSQL
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Client).where(Client.id == client_id))
        persisted_client = result.scalar_one_or_none()
        assert persisted_client is not None
        assert persisted_client.full_name == client_name
        assert persisted_client.email == email


async def test_notification_delivery_failure_leaves_no_phantom_sent_status():
    """A failed delivery attempt must not record a success or phantom SENT status."""
    channel = EmailNotificationChannel(host="127.0.0.1", port=25)

    with patch("app.services.notifications.email._send_smtp_sync", side_effect=TimeoutError("Connection timed out")):
        res = await channel.send(
            recipient="buyer@example.com",
            title="Property Update",
            message="Price reduction on shortlisted property",
            notification_type="PRICE_DROP",
        )

    assert res.success is False
    assert res.status != DeliveryStatus.SENT
    assert res.status == DeliveryStatus.FAILED
