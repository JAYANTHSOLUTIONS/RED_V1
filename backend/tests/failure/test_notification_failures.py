"""Failure and edge-case tests for Notification module."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.exceptions import NotFoundError
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
    email = f"consultant-fail-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Failure Test Consultant",
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
async def test_notification_not_found(client: AsyncClient, consultant_user: dict):
    """Ensure non-existent notification ID returns 404."""
    auth_headers = consultant_user["headers"]
    random_id = uuid.uuid4()

    res_get = await client.get(f"/api/v1/notifications/{random_id}", headers=auth_headers)
    assert res_get.status_code == 404
    assert "not found" in res_get.json()["error"]["message"].lower()

    res_read = await client.post(f"/api/v1/notifications/{random_id}/read", headers=auth_headers)
    assert res_read.status_code == 404

    res_unread = await client.post(f"/api/v1/notifications/{random_id}/unread", headers=auth_headers)
    assert res_unread.status_code == 404


@pytest.mark.asyncio
async def test_invalid_uuid_format(client: AsyncClient, consultant_user: dict):
    """Ensure malformed UUID path parameter returns 422."""
    auth_headers = consultant_user["headers"]
    res = await client.get("/api/v1/notifications/not-a-valid-uuid", headers=auth_headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_invalid_pagination_bounds(client: AsyncClient, consultant_user: dict):
    """Ensure pagination limits and negative offsets are rejected with 422."""
    auth_headers = consultant_user["headers"]

    # limit > 100
    res_high = await client.get("/api/v1/notifications?limit=101", headers=auth_headers)
    assert res_high.status_code == 422

    # limit < 1
    res_low = await client.get("/api/v1/notifications?limit=0", headers=auth_headers)
    assert res_low.status_code == 422

    # negative offset
    res_neg = await client.get("/api/v1/notifications?offset=-1", headers=auth_headers)
    assert res_neg.status_code == 422


@pytest.mark.asyncio
async def test_whatsapp_link_validation_failures(client: AsyncClient, consultant_user: dict):
    """Ensure invalid phone inputs are rejected with 422."""
    auth_headers = consultant_user["headers"]

    # Phone too short
    res_short = await client.post(
        "/api/v1/notifications/whatsapp-link",
        json={"phone": "123", "message": "Test"},
        headers=auth_headers,
    )
    assert res_short.status_code == 422

    # Empty message
    res_empty_msg = await client.post(
        "/api/v1/notifications/whatsapp-link",
        json={"phone": "9876543210", "message": "   "},
        headers=auth_headers,
    )
    assert res_empty_msg.status_code == 422


@pytest.mark.asyncio
async def test_service_create_notification_non_existent_user():
    """Ensure creating notification with invalid user_id raises NotFoundError."""
    service = NotificationService()
    fake_user_id = uuid.uuid4()

    async with AsyncSessionFactory() as session:
        async with session.begin():
            with pytest.raises(NotFoundError):
                await service.create_notification(
                    session=session,
                    data=NotificationCreateInternal(
                        user_id=fake_user_id,
                        title="Alert",
                        message="Msg",
                        channel="IN_APP",
                        notification_type="GENERAL",
                    ),
                )
