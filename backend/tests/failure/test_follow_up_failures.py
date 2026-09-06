"""Failure scenario tests for Follow-up Management."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.client import Client
from app.models.property import Property
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
    email = f"consultant-fail-fu-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Failure FU Consultant",
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
async def active_client(auth_headers: dict, client: AsyncClient):
    res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Active FU Buyer",
            "phone": f"+91 93{uuid.uuid4().int % 100000000:08d}",
            "classification": "BUYER",
        },
        headers=auth_headers,
    )
    return res.json()["data"]


@pytest.fixture
async def active_property(auth_headers: dict, client: AsyncClient):
    res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Active FU Villa",
            "property_type": "Villa",
            "transaction_type": "SALE",
            "price": "12000000.00",
            "district": "Chennai",
            "city": "Chennai",
            "locality": "ECR",
            "pincode": "600115",
        },
        headers=auth_headers,
    )
    return res.json()["data"]


@pytest.mark.asyncio
async def test_nonexistent_entities_return_404(
    client: AsyncClient,
    auth_headers: dict,
    active_client: dict,
    active_property: dict,
):
    """Verify 404 with machine-readable error codes when references do not exist."""
    random_id = uuid.uuid4()
    scheduled_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # 1. Nonexistent client
    res1 = await client.post(
        "/api/v1/follow-ups",
        json={
            "client_id": str(random_id),
            "action_type": "CALL",
            "scheduled_at": scheduled_time,
        },
        headers=auth_headers,
    )
    assert res1.status_code == 404
    assert res1.json()["error"]["code"] == "CLIENT_NOT_FOUND"

    # 2. Nonexistent lead
    res2 = await client.post(
        "/api/v1/follow-ups",
        json={
            "lead_id": str(random_id),
            "action_type": "SEND_DOCS",
            "scheduled_at": scheduled_time,
        },
        headers=auth_headers,
    )
    assert res2.status_code == 404
    assert res2.json()["error"]["code"] == "LEAD_NOT_FOUND"

    # 3. Nonexistent property
    res3 = await client.post(
        "/api/v1/follow-ups",
        json={
            "client_id": active_client["id"],
            "property_id": str(random_id),
            "action_type": "ARRANGE_VISIT",
            "scheduled_at": scheduled_time,
        },
        headers=auth_headers,
    )
    assert res3.status_code == 404
    assert res3.json()["error"]["code"] == "PROPERTY_NOT_FOUND"

    # 4. Nonexistent follow-up retrieval
    res4 = await client.get(
        f"/api/v1/follow-ups/{random_id}",
        headers=auth_headers,
    )
    assert res4.status_code == 404
    assert res4.json()["error"]["code"] == "FOLLOW_UP_NOT_FOUND"


@pytest.mark.asyncio
async def test_missing_target_rejected(client: AsyncClient, auth_headers: dict):
    """Ensure creating a follow-up with neither client_id nor lead_id is rejected with 422."""
    res = await client.post(
        "/api/v1/follow-ups",
        json={
            "action_type": "CALL",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_archived_entities_rejected(
    client: AsyncClient,
    auth_headers: dict,
    active_property: dict,
):
    """Ensure follow-ups cannot be created for archived clients or associated with archived properties."""
    # 1. Create and archive a client
    c_res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Archived FU Client",
            "phone": f"+91 91{uuid.uuid4().int % 100000000:08d}",
            "classification": "BUYER",
        },
        headers=auth_headers,
    )
    client_id = c_res.json()["data"]["id"]
    arc_res = await client.post(f"/api/v1/clients/{client_id}/archive", headers=auth_headers)
    assert arc_res.status_code == 200

    # Attempt to create follow-up for archived client
    res1 = await client.post(
        "/api/v1/follow-ups",
        json={
            "client_id": client_id,
            "action_type": "CALL",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        },
        headers=auth_headers,
    )
    assert res1.status_code == 422
    assert "archived client" in res1.json()["error"]["message"]


@pytest.mark.asyncio
async def test_terminal_state_mutations_rejected(
    client: AsyncClient,
    auth_headers: dict,
    active_client: dict,
):
    """Ensure completed and missed follow-ups cannot be edited or cross-mutated."""
    scheduled_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # Create follow-up
    res = await client.post(
        "/api/v1/follow-ups",
        json={
            "client_id": active_client["id"],
            "action_type": "CALL",
            "scheduled_at": scheduled_time,
        },
        headers=auth_headers,
    )
    fu_id = res.json()["data"]["id"]

    # Mark as completed
    await client.post(f"/api/v1/follow-ups/{fu_id}/complete", headers=auth_headers)

    # 1. Attempt to update completed follow-up
    res_upd = await client.patch(
        f"/api/v1/follow-ups/{fu_id}",
        json={"notes": "Try updating completed task"},
        headers=auth_headers,
    )
    assert res_upd.status_code == 422
    assert res_upd.json()["error"]["code"] == "INVALID_FOLLOW_UP_STATE"

    # 2. Attempt to mark completed follow-up as missed
    res_miss = await client.post(f"/api/v1/follow-ups/{fu_id}/miss", headers=auth_headers)
    assert res_miss.status_code == 422
    assert res_miss.json()["error"]["code"] == "INVALID_FOLLOW_UP_STATE"


@pytest.mark.asyncio
async def test_cross_client_lead_mismatch_rejected(
    client: AsyncClient,
    auth_headers: dict,
    active_property: dict,
):
    """Verify that specifying a lead belonging to Client A together with Client B is rejected."""
    c1 = (await client.post("/api/v1/clients", json={"full_name": "FU Client 1", "phone": f"+91 97{uuid.uuid4().int % 100000000:08d}", "classification": "BUYER"}, headers=auth_headers)).json()["data"]
    c2 = (await client.post("/api/v1/clients", json={"full_name": "FU Client 2", "phone": f"+91 98{uuid.uuid4().int % 100000000:08d}", "classification": "BUYER"}, headers=auth_headers)).json()["data"]

    # Lead for Client 1
    lead_c1 = (await client.post("/api/v1/leads", json={"client_id": c1["id"], "property_id": active_property["id"], "source": "DIRECT_CALL"}, headers=auth_headers)).json()["data"]

    # Attempt to pair Client 2 with Client 1's lead
    res = await client.post(
        "/api/v1/follow-ups",
        json={
            "client_id": c2["id"],
            "lead_id": lead_c1["id"],
            "action_type": "CALL",
            "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert res.status_code == 422
    assert "Lead does not belong to the specified client" in res.json()["error"]["message"]
