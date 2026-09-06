"""Security tests for Notification management (RBAC, Anti-IDOR, authentication)."""
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


async def _create_consultant(client: AsyncClient, prefix: str):
    email = f"{prefix}-{uuid.uuid4().hex[:6]}@example.com"
    password = "SecurePassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=f"{prefix.title()} User",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    data = login_res.json()["data"]
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user_id": uuid.UUID(data["user"]["id"]),
    }


@pytest.mark.asyncio
async def test_unauthenticated_endpoints_rejected(client: AsyncClient):
    """Ensure all notification endpoints return 401 without Bearer token."""
    fake_id = uuid.uuid4()
    assert (await client.get("/api/v1/notifications")).status_code == 401
    assert (await client.get("/api/v1/notifications/unread-count")).status_code == 401
    assert (await client.get(f"/api/v1/notifications/{fake_id}")).status_code == 401
    assert (await client.post(f"/api/v1/notifications/{fake_id}/read")).status_code == 401
    assert (await client.post(f"/api/v1/notifications/{fake_id}/unread")).status_code == 401
    assert (await client.post("/api/v1/notifications/whatsapp-link", json={"phone": "9876543210", "message": "Hi"})).status_code == 401


@pytest.mark.asyncio
async def test_anti_idor_cross_user_isolation(client: AsyncClient):
    """Ensure Consultant A cannot access or mutate Consultant B's notifications (Anti-IDOR)."""
    consultant_a = await _create_consultant(client, "consultant-a")
    consultant_b = await _create_consultant(client, "consultant-b")

    service = NotificationService()

    # Create notification for Consultant A
    async with AsyncSessionFactory() as session:
        async with session.begin():
            notif_a = await service.create_notification(
                session=session,
                data=NotificationCreateInternal(
                    user_id=consultant_a["user_id"],
                    title="Confidential Lead Alert",
                    message="Important buyer information for Consultant A.",
                    channel="IN_APP",
                    notification_type="LEAD_STATUS_CHANGED",
                ),
            )
            notif_a_id = str(notif_a.id)

    # 1. Consultant A can view it
    res_a = await client.get(f"/api/v1/notifications/{notif_a_id}", headers=consultant_a["headers"])
    assert res_a.status_code == 200
    assert res_a.json()["data"]["title"] == "Confidential Lead Alert"

    # 2. Consultant B CANNOT view it (Strict 404 Anti-IDOR)
    res_b_get = await client.get(f"/api/v1/notifications/{notif_a_id}", headers=consultant_b["headers"])
    assert res_b_get.status_code == 404

    # 3. Consultant B CANNOT mark it as read
    res_b_read = await client.post(f"/api/v1/notifications/{notif_a_id}/read", headers=consultant_b["headers"])
    assert res_b_read.status_code == 404

    # 4. Consultant B CANNOT mark it as unread
    res_b_unread = await client.post(f"/api/v1/notifications/{notif_a_id}/unread", headers=consultant_b["headers"])
    assert res_b_unread.status_code == 404

    # 5. Consultant B listing does NOT contain Consultant A's notification
    res_b_list = await client.get("/api/v1/notifications", headers=consultant_b["headers"])
    assert res_b_list.status_code == 200
    assert res_b_list.json()["data"]["total"] == 0

    # 6. Consultant B unread count remains 0
    res_b_count = await client.get("/api/v1/notifications/unread-count", headers=consultant_b["headers"])
    assert res_b_count.status_code == 200
    assert res_b_count.json()["data"]["unread_count"] == 0
