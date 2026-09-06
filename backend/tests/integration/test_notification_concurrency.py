"""Concurrency tests for Notification status mutations under PostgreSQL row locks."""
import asyncio
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.main import create_app
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


@pytest.mark.asyncio
async def test_concurrent_mark_read_and_unread():
    """Ensure concurrent read and unread requests on the same notification resolve cleanly without deadlock."""
    email = f"consultant-conc-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Concurrency Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        data = login_res.json()["data"]
        token = data["access_token"]
        user_id = uuid.UUID(data["user"]["id"])
        headers = {"Authorization": f"Bearer {token}"}

        # Create target notification
        service = NotificationService()
        async with AsyncSessionFactory() as session:
            async with session.begin():
                notif = await service.create_notification(
                    session=session,
                    data=NotificationCreateInternal(
                        user_id=user_id,
                        title="High Priority Lead",
                        message="Call lead immediately",
                        channel="IN_APP",
                        notification_type="LEAD_STATUS_CHANGED",
                    ),
                )
                notif_id = str(notif.id)

        # Fire 6 concurrent requests (mix of read and unread)
        tasks = [
            client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers),
            client.post(f"/api/v1/notifications/{notif_id}/unread", headers=headers),
            client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers),
            client.post(f"/api/v1/notifications/{notif_id}/unread", headers=headers),
            client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers),
            client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers),
        ]

        responses = await asyncio.gather(*tasks)

        # Every single request must return 200 OK without deadlocks or server errors
        for r in responses:
            assert r.status_code == 200

        # Verify final record is valid
        res_final = await client.get(f"/api/v1/notifications/{notif_id}", headers=headers)
        assert res_final.status_code == 200
        assert isinstance(res_final.json()["data"]["is_read"], bool)
