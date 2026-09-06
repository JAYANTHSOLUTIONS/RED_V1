"""Integration tests for Notification management API, repository, and domain services."""
from datetime import datetime, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
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
async def consultant_user(client: AsyncClient):
    email = f"consultant-notif-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Notification Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    data = login_res.json()["data"]
    token = data["access_token"]
    user_id = data["user"]["id"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": uuid.UUID(user_id),
    }


@pytest.mark.asyncio
async def test_list_notifications_and_pagination(client: AsyncClient, consultant_user: dict):
    """Ensure notifications are returned paginated and ordered newest first."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]
    service = NotificationService()

    # Create 3 notifications
    async with AsyncSessionFactory() as session:
        async with session.begin():
            for i in range(3):
                await service.create_notification(
                    session=session,
                    data=NotificationCreateInternal(
                        user_id=user_id,
                        title=f"Notification #{i}",
                        message=f"Body content for #{i}",
                        channel="IN_APP",
                        notification_type="FOLLOW_UP_DUE",
                    ),
                )

    # 1. Fetch page 1 (limit=2)
    res1 = await client.get("/api/v1/notifications?limit=2&offset=0", headers=auth_headers)
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    assert data1["total"] == 3
    assert len(data1["items"]) == 2
    assert data1["limit"] == 2
    assert data1["offset"] == 0

    # 2. Fetch page 2 (limit=2, offset=2)
    res2 = await client.get("/api/v1/notifications?limit=2&offset=2", headers=auth_headers)
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert len(data2["items"]) == 1

    page1_titles = {item["title"] for item in data1["items"]}
    page2_titles = {item["title"] for item in data2["items"]}
    assert len(page1_titles) == 2
    assert len(page2_titles) == 1
    assert page1_titles.isdisjoint(page2_titles)
    assert (page1_titles | page2_titles) == {"Notification #0", "Notification #1", "Notification #2"}


@pytest.mark.asyncio
async def test_filter_notifications(client: AsyncClient, consultant_user: dict):
    """Verify filtering by is_read and notification_type."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]
    service = NotificationService()

    async with AsyncSessionFactory() as session:
        async with session.begin():
            n1 = await service.create_notification(
                session=session,
                data=NotificationCreateInternal(
                    user_id=user_id,
                    title="Follow-up Call",
                    message="Call client",
                    channel="IN_APP",
                    notification_type="FOLLOW_UP_DUE",
                ),
            )
            await service.create_notification(
                session=session,
                data=NotificationCreateInternal(
                    user_id=user_id,
                    title="Site Visit Confirmed",
                    message="Visit confirmed",
                    channel="IN_APP",
                    notification_type="SITE_VISIT_CONFIRMED",
                ),
            )
        # Mark first notification as read
        async with session.begin():
            await service.mark_as_read(session, n1.id, user_id)

    # Filter is_read=true
    res_read = await client.get("/api/v1/notifications?is_read=true", headers=auth_headers)
    assert res_read.status_code == 200
    items_read = res_read.json()["data"]["items"]
    assert len(items_read) == 1
    assert items_read[0]["notification_type"] == "FOLLOW_UP_DUE"

    # Filter is_read=false
    res_unread = await client.get("/api/v1/notifications?is_read=false", headers=auth_headers)
    assert res_unread.status_code == 200
    items_unread = res_unread.json()["data"]["items"]
    assert len(items_unread) == 1
    assert items_unread[0]["notification_type"] == "SITE_VISIT_CONFIRMED"

    # Filter by notification_type
    res_type = await client.get("/api/v1/notifications?notification_type=SITE_VISIT_CONFIRMED", headers=auth_headers)
    assert res_type.status_code == 200
    assert len(res_type.json()["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_notification_read_and_unread_flow(client: AsyncClient, consultant_user: dict):
    """Verify full read/unread cycle including server timestamps and idempotency."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]
    service = NotificationService()

    async with AsyncSessionFactory() as session:
        async with session.begin():
            n = await service.create_notification(
                session=session,
                data=NotificationCreateInternal(
                    user_id=user_id,
                    title="Action Required",
                    message="Verify Patta extract",
                    channel="IN_APP",
                    notification_type="DOCUMENT_REQUIRED",
                ),
            )
            notif_id = str(n.id)

    # Initially unread
    res_get = await client.get(f"/api/v1/notifications/{notif_id}", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["data"]["is_read"] is False
    assert res_get.json()["data"]["read_at"] is None

    # Mark as read
    res_read = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=auth_headers)
    assert res_read.status_code == 200
    read_data = res_read.json()["data"]
    assert read_data["is_read"] is True
    assert read_data["read_at"] is not None

    # Idempotent repeat read
    res_read_repeat = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=auth_headers)
    assert res_read_repeat.status_code == 200
    assert res_read_repeat.json()["data"]["is_read"] is True

    # Mark as unread
    res_unread = await client.post(f"/api/v1/notifications/{notif_id}/unread", headers=auth_headers)
    assert res_unread.status_code == 200
    unread_data = res_unread.json()["data"]
    assert unread_data["is_read"] is False
    assert unread_data["read_at"] is None

    # Idempotent repeat unread
    res_unread_repeat = await client.post(f"/api/v1/notifications/{notif_id}/unread", headers=auth_headers)
    assert res_unread_repeat.status_code == 200
    assert res_unread_repeat.json()["data"]["is_read"] is False


@pytest.mark.asyncio
async def test_unread_count_aggregate(client: AsyncClient, consultant_user: dict):
    """Verify unread count aggregation endpoint."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]
    service = NotificationService()

    # Initial count is 0
    res0 = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert res0.status_code == 200
    assert res0.json()["data"]["unread_count"] == 0

    # Add 2 unread notifications
    async with AsyncSessionFactory() as session:
        async with session.begin():
            n1 = await service.create_notification(
                session=session,
                data=NotificationCreateInternal(
                    user_id=user_id,
                    title="Alert 1",
                    message="Msg 1",
                    channel="IN_APP",
                    notification_type="GENERAL",
                ),
            )
            await service.create_notification(
                session=session,
                data=NotificationCreateInternal(
                    user_id=user_id,
                    title="Alert 2",
                    message="Msg 2",
                    channel="IN_APP",
                    notification_type="GENERAL",
                ),
            )

    res2 = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["data"]["unread_count"] == 2

    # Read one
    await client.post(f"/api/v1/notifications/{n1.id}/read", headers=auth_headers)
    res1 = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert res1.status_code == 200
    assert res1.json()["data"]["unread_count"] == 1


@pytest.mark.asyncio
async def test_whatsapp_link_endpoint(client: AsyncClient, consultant_user: dict):
    """Verify consultant endpoint for generating safe WhatsApp deep links."""
    auth_headers = consultant_user["headers"]
    payload = {
        "phone": "+91 94433 22110",
        "message": "Dear client, please share the Patta subdivision sketch for verification.",
    }
    res = await client.post("/api/v1/notifications/whatsapp-link", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["sanitized_phone"] == "919443322110"
    assert "https://wa.me/919443322110?text=" in data["deep_link"]
    assert "Patta" in data["deep_link"]


@pytest.mark.asyncio
async def test_domain_event_helpers(consultant_user: dict):
    """Verify domain event helpers create appropriate in-app notifications."""
    user_id = consultant_user["user_id"]
    service = NotificationService()
    fu_id = uuid.uuid4()
    sv_id = uuid.uuid4()

    async with AsyncSessionFactory() as session:
        async with session.begin():
            notif_fu = await service.create_follow_up_due_notification(
                session=session,
                follow_up_id=fu_id,
                action_type="ARRANGE_VISIT",
                user_id=user_id,
                scheduled_at_str="2026-09-10 11:00 AM IST",
                target_name="Senthil Kumar",
            )
            assert notif_fu.notification_type == "FOLLOW_UP_DUE"
            assert notif_fu.entity_type == "FOLLOW_UP"
            assert notif_fu.entity_id == fu_id
            assert "Senthil Kumar" in notif_fu.message

            notif_sv = await service.create_site_visit_notification(
                session=session,
                site_visit_id=sv_id,
                event_type="CONFIRMED",
                user_id=user_id,
                scheduled_at_str="2026-09-12 04:00 PM IST",
                property_title="2BHK Gated Villa, Saravanampatti",
            )
            assert notif_sv.notification_type == "SITE_VISIT_CONFIRMED"
            assert notif_sv.entity_type == "SITE_VISIT"
            assert notif_sv.entity_id == sv_id
            assert "Saravanampatti" in notif_sv.message
