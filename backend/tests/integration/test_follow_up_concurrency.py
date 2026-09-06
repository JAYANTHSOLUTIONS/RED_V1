"""Concurrency tests for Follow-up state transitions under PostgreSQL row locking."""
import asyncio
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.follow_up import FollowUp
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
async def auth_headers(client: AsyncClient):
    email = f"consultant-concur-fu-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Concurrency FU Consultant",
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
async def sample_client(auth_headers: dict, client: AsyncClient):
    res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Concurrency FU Client",
            "phone": f"+91 99{uuid.uuid4().int % 100000000:08d}",
            "classification": "BUYER",
        },
        headers=auth_headers,
    )
    return res.json()["data"]


@pytest.mark.asyncio
async def test_concurrent_competing_complete_and_miss(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
):
    """Two competing requests attempt to complete and miss the same follow-up simultaneously.
    
    Expected result:
    - Exactly one transition wins (200 OK)
    - The competing transition fails with 422 INVALID_FOLLOW_UP_STATE
    - Database row remains strictly consistent (never corrupted)
    """
    scheduled_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # 1. Create scheduled follow-up
    res = await client.post(
        "/api/v1/follow-ups",
        json={
            "client_id": sample_client["id"],
            "action_type": "CALL",
            "scheduled_at": scheduled_time,
            "notes": "Follow-up for competing concurrency test",
        },
        headers=auth_headers,
    )
    assert res.status_code == 201
    fu_id = res.json()["data"]["id"]

    # 2. Fire simultaneous complete and miss requests
    task_complete = client.post(
        f"/api/v1/follow-ups/{fu_id}/complete",
        json={"completion_notes": "Completed by winner"},
        headers=auth_headers,
    )
    task_miss = client.post(
        f"/api/v1/follow-ups/{fu_id}/miss",
        json={"notes": "Missed by contender"},
        headers=auth_headers,
    )

    resp_complete, resp_miss = await asyncio.gather(task_complete, task_miss)

    status_codes = sorted([resp_complete.status_code, resp_miss.status_code])
    assert status_codes == [200, 422], f"Expected [200, 422], got {status_codes}"

    # 3. Verify database consistency
    async with AsyncSessionFactory() as session:
        fu_in_db = await session.get(FollowUp, uuid.UUID(fu_id))
        assert fu_in_db is not None
        assert fu_in_db.status in {"COMPLETED", "MISSED"}
        if fu_in_db.status == "COMPLETED":
            assert resp_complete.status_code == 200
            assert resp_miss.status_code == 422
        else:
            assert resp_miss.status_code == 200
            assert resp_complete.status_code == 422
