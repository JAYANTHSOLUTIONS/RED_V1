"""Security and RBAC tests for Follow-up Management endpoints."""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture(autouse=True)
async def clean_follow_ups():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM follow_ups"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM follow_ups"))


@pytest.fixture
async def consultant_headers(client: AsyncClient):
    email = f"consultant-sec-fu-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant User",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def assistant_headers(client: AsyncClient):
    """User with non-consultant role (ASSISTANT)."""
    email = f"assistant-sec-fu-{uuid.uuid4().hex[:8]}@example.com"
    password = "AssistantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Assistant Staff",
                role="ASSISTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def existing_follow_up(consultant_headers: dict, client: AsyncClient):
    # Create client
    c_res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Sec FU Client",
            "phone": f"+91 94{uuid.uuid4().int % 100000000:08d}",
            "classification": "BUYER",
        },
        headers=consultant_headers,
    )
    client_id = c_res.json()["data"]["id"]

    # Create follow-up
    fu_res = await client.post(
        "/api/v1/follow-ups",
        json={
            "client_id": client_id,
            "action_type": "CALL",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
            "notes": "Confidential follow-up task notes",
        },
        headers=consultant_headers,
    )
    return fu_res.json()["data"]


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(client: AsyncClient, existing_follow_up: dict):
    """Ensure follow-up endpoints reject requests without valid Bearer token with 401."""
    fu_id = existing_follow_up["id"]

    # 1. List
    res_list = await client.get("/api/v1/follow-ups")
    assert res_list.status_code == 401

    # 2. Get
    res_get = await client.get(f"/api/v1/follow-ups/{fu_id}")
    assert res_get.status_code == 401

    # 3. Create
    res_create = await client.post("/api/v1/follow-ups", json={})
    assert res_create.status_code == 401

    # 4. Patch
    res_patch = await client.patch(f"/api/v1/follow-ups/{fu_id}", json={"notes": "new notes"})
    assert res_patch.status_code == 401

    # 5. Complete
    res_comp = await client.post(f"/api/v1/follow-ups/{fu_id}/complete")
    assert res_comp.status_code == 401

    # 6. Miss
    res_miss = await client.post(f"/api/v1/follow-ups/{fu_id}/miss")
    assert res_miss.status_code == 401


@pytest.mark.asyncio
async def test_non_consultant_role_rejected(
    client: AsyncClient, assistant_headers: dict, existing_follow_up: dict
):
    """Ensure users with non-consultant role (e.g. ASSISTANT) receive 403 Forbidden."""
    fu_id = existing_follow_up["id"]

    res_list = await client.get("/api/v1/follow-ups", headers=assistant_headers)
    assert res_list.status_code == 403
    assert res_list.json()["error"]["code"] == "FORBIDDEN"

    res_comp = await client.post(f"/api/v1/follow-ups/{fu_id}/complete", headers=assistant_headers)
    assert res_comp.status_code == 403
    assert res_comp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_invalid_uuid_handling(client: AsyncClient, consultant_headers: dict):
    """Ensure malformed UUID path parameter returns 422 validation error."""
    res = await client.get("/api/v1/follow-ups/not-a-valid-uuid", headers=consultant_headers)
    assert res.status_code == 422
