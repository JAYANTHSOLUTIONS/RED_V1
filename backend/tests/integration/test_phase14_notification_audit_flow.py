"""Phase 14 Integration Tests: Notification and Audit Cross-Module Integration.

Scenarios Covered:
- Scenario 8: Follow-Up -> Notification -> Read / Unread -> Audit
- Scenario 9: Site Visit events -> Notification helpers (persistence, unread count, audit)
- Scenario 24 & 25: Notification + Audit logical separation, WhatsApp deep link generation, and mock external providers
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreateInternal
from app.services.notification import NotificationService


@pytest.fixture(autouse=True)
async def clean_notifications():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM notifications"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM notifications"))


@pytest.fixture
async def consultant_a(client: AsyncClient):
    email = f"consultant-p14-notif-a-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Phase 14 Consultant A",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    user_id = login_res.json()["data"]["user"]["id"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": uuid.UUID(user_id),
    }


@pytest.fixture
async def consultant_b(client: AsyncClient):
    email = f"consultant-p14-notif-b-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Phase 14 Consultant B",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    user_id = login_res.json()["data"]["user"]["id"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": uuid.UUID(user_id),
    }


@pytest.mark.asyncio
async def test_follow_up_notification_lifecycle_and_audit(
    client: AsyncClient, consultant_a: dict
):
    """Scenario 8: Follow-up alert creates notification, updates unread count, transitions read/unread, and records audit."""
    headers = consultant_a["headers"]
    user_id = consultant_a["user_id"]
    service = NotificationService()
    fu_id = uuid.uuid4()

    # 1. Create in-app notification representing a follow-up due
    async with AsyncSessionFactory() as session:
        async with session.begin():
            notif = await service.create_follow_up_due_notification(
                session=session,
                follow_up_id=fu_id,
                action_type="CALL",
                user_id=user_id,
                scheduled_at_str="2026-09-08 14:00 IST",
                target_name="K. Ramanathan",
            )
            notif_id = str(notif.id)

    # 2. Check unread count
    count_res = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_res.status_code == 200
    assert count_res.json()["data"]["unread_count"] == 1

    # 3. Mark as read
    read_res = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)
    assert read_res.status_code == 200
    assert read_res.json()["data"]["is_read"] is True
    assert read_res.json()["data"]["read_at"] is not None

    # Verify unread count is now 0
    count_after_read = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_after_read.json()["data"]["unread_count"] == 0

    # 4. Mark as unread
    unread_res = await client.post(f"/api/v1/notifications/{notif_id}/unread", headers=headers)
    assert unread_res.status_code == 200
    assert unread_res.json()["data"]["is_read"] is False
    assert unread_res.json()["data"]["read_at"] is None

    # Verify unread count is restored to 1
    count_after_unread = await client.get("/api/v1/notifications/unread-count", headers=headers)
    assert count_after_unread.json()["data"]["unread_count"] == 1

    # 5. Verify audit logs for read and unread actions
    async with AsyncSessionFactory() as session:
        audits = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.entity_id == uuid.UUID(notif_id),
                    AuditLog.action.in_(["NOTIFICATION_READ", "NOTIFICATION_UNREAD"]),
                )
            )
        ).all()
        actions = [a.action for a in audits]
        assert "NOTIFICATION_READ" in actions
        assert "NOTIFICATION_UNREAD" in actions


@pytest.mark.asyncio
async def test_site_visit_notifications_and_cross_consultant_isolation(
    client: AsyncClient, consultant_a: dict, consultant_b: dict
):
    """Scenario 9 & 14: Site visit notification helpers and anti-IDOR cross-consultant isolation."""
    headers_a = consultant_a["headers"]
    user_a_id = consultant_a["user_id"]
    headers_b = consultant_b["headers"]
    service = NotificationService()
    visit_id = uuid.uuid4()

    # Create site visit confirmed notification for Consultant A
    async with AsyncSessionFactory() as session:
        async with session.begin():
            notif_a = await service.create_site_visit_notification(
                session=session,
                site_visit_id=visit_id,
                event_type="CONFIRMED",
                user_id=user_a_id,
                scheduled_at_str="2026-09-08 11:00 IST",
                property_title="Adyar Sea View Villa",
            )
            notif_a_id = str(notif_a.id)

    # Consultant A can access the notification
    get_res_a = await client.get(f"/api/v1/notifications/{notif_a_id}", headers=headers_a)
    assert get_res_a.status_code == 200
    assert get_res_a.json()["data"]["id"] == notif_a_id

    # Consultant B attempts to access Consultant A's notification -> 404 Not Found (Anti-IDOR)
    get_res_b = await client.get(f"/api/v1/notifications/{notif_a_id}", headers=headers_b)
    assert get_res_b.status_code == 404

    # Consultant B attempts to mark Consultant A's notification as read -> 404 Not Found
    read_res_b = await client.post(f"/api/v1/notifications/{notif_a_id}/read", headers=headers_b)
    assert read_res_b.status_code == 404


@pytest.mark.asyncio
async def test_whatsapp_link_generation_deterministic_and_safe(
    client: AsyncClient, consultant_a: dict
):
    """Scenario 25: WhatsApp deep link formatting with Indian phone sanitization and URL encoding."""
    headers = consultant_a["headers"]

    payload = {
        "phone": "+91 98401 54321",
        "message": "Hello Mr. Kumar, your site visit for Tambaram Plot is scheduled tomorrow at 10:00 AM IST.",
    }
    res = await client.post(
        "/api/v1/notifications/whatsapp-link",
        json=payload,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    deep_link = data["deep_link"]
    assert "wa.me/919840154321" in deep_link
    assert "Tambaram" in deep_link
    assert data["sanitized_phone"] == "919840154321"
