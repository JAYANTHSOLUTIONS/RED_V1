"""Concurrency test for Site Visit confirmation conflict protection.

Verifies that when two concurrent requests attempt to confirm overlapping visits,
PostgreSQL transactional locking and conflict guards ensure exactly one succeeds (200)
and the competing request is rejected with a conflict error (409 RESOURCE_CONFLICT).
"""
import asyncio
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.site_visit import SiteVisit
from app.models.user import User


@pytest.fixture(autouse=True)
async def clean_site_visits():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM site_visits"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM site_visits"))


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-concur-{uuid.uuid4().hex[:8]}@example.com"
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
            "full_name": "Concurrency Client",
            "phone": f"+91 95{uuid.uuid4().int % 100000000:08d}",
            "classification": "BUYER",
        },
        headers=auth_headers,
    )
    return res.json()["data"]


@pytest.fixture
async def sample_property(auth_headers: dict, client: AsyncClient):
    res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Concurrency Plot in Tambaram",
            "property_type": "Residential Plot",
            "transaction_type": "SALE",
            "price": "4000000.00",
            "plot_area": "1800.00",
            "district": "Chengalpattu",
            "city": "Chennai",
            "locality": "Tambaram",
            "pincode": "600045",
        },
        headers=auth_headers,
    )
    assert res.status_code == 201
    return res.json()["data"]


@pytest.mark.asyncio
async def test_concurrent_overlapping_confirmations(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
    sample_property: dict,
):
    """Two competing requests attempt to confirm overlapping site visits simultaneously.
    
    Expected result:
    - Exactly one returns 200 OK (CONFIRMED)
    - The other returns 409 Conflict (RESOURCE_CONFLICT)
    - Database state remains strictly consistent (only 1 confirmed visit)
    """
    base_time = (datetime.now(timezone.utc) + timedelta(days=7)).replace(minute=0, second=0, microsecond=0)

    # 1. Create Visit 1 at 10:00 AM
    res1 = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": sample_client["id"],
            "property_id": sample_property["id"],
            "scheduled_at": base_time.isoformat(),
            "status": "REQUESTED",
            "notes": "Visit 1 candidate",
        },
        headers=auth_headers,
    )
    assert res1.status_code == 201
    visit_1_id = res1.json()["data"]["id"]

    # 2. Create Visit 2 at 10:20 AM (overlapping with Visit 1)
    overlap_time = base_time + timedelta(minutes=20)
    res2 = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": sample_client["id"],
            "property_id": sample_property["id"],
            "scheduled_at": overlap_time.isoformat(),
            "status": "REQUESTED",
            "notes": "Visit 2 candidate",
        },
        headers=auth_headers,
    )
    assert res2.status_code == 201
    visit_2_id = res2.json()["data"]["id"]

    # 3. Fire concurrent confirmation requests
    task1 = client.post(f"/api/v1/site-visits/{visit_1_id}/confirm", headers=auth_headers)
    task2 = client.post(f"/api/v1/site-visits/{visit_2_id}/confirm", headers=auth_headers)

    resp1, resp2 = await asyncio.gather(task1, task2)

    status_codes = sorted([resp1.status_code, resp2.status_code])
    assert status_codes == [200, 409], f"Expected exactly [200, 409], got {status_codes}"

    # Verify conflict error payload
    conflict_resp = resp1 if resp1.status_code == 409 else resp2
    assert conflict_resp.json()["error"]["code"] == "RESOURCE_CONFLICT"

    # 4. Verify database consistency
    async with AsyncSessionFactory() as session:
        v1 = await session.get(SiteVisit, uuid.UUID(visit_1_id))
        v2 = await session.get(SiteVisit, uuid.UUID(visit_2_id))

        assert v1 is not None and v2 is not None
        statuses = {v1.status, v2.status}
        assert statuses == {"CONFIRMED", "REQUESTED"}, f"Expected one CONFIRMED and one REQUESTED, got {statuses}"
