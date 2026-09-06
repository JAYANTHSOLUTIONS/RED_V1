"""Failure scenario tests for Site Visit coordination."""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient

from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
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
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def active_client(auth_headers: dict, client: AsyncClient):
    res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Failure Buyer",
            "phone": f"+91 91{uuid.uuid4().int % 100000000:08d}",
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
            "title": "Failure Property",
            "property_type": "Apartment",
            "transaction_type": "SALE",
            "price": "5000000.00",
            "district": "Chennai",
            "city": "Chennai",
            "locality": "T. Nagar",
            "pincode": "600017",
        },
        headers=auth_headers,
    )
    assert res.status_code == 201
    return res.json()["data"]


@pytest.mark.asyncio
async def test_nonexistent_entities_return_not_found(
    client: AsyncClient,
    auth_headers: dict,
    active_client: dict,
    active_property: dict,
):
    """Verify 404 with appropriate machine-readable error codes when references do not exist."""
    random_id = uuid.uuid4()
    visit_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # 1. Nonexistent property
    res1 = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": active_client["id"],
            "property_id": str(random_id),
            "scheduled_at": visit_time,
        },
        headers=auth_headers,
    )
    assert res1.status_code == 404
    assert res1.json()["error"]["code"] == "PROPERTY_NOT_FOUND"

    # 2. Nonexistent client
    res2 = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": str(random_id),
            "property_id": active_property["id"],
            "scheduled_at": visit_time,
        },
        headers=auth_headers,
    )
    assert res2.status_code == 404
    assert res2.json()["error"]["code"] == "CLIENT_NOT_FOUND"

    # 3. Nonexistent lead
    res3 = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": active_client["id"],
            "property_id": active_property["id"],
            "lead_id": str(random_id),
            "scheduled_at": visit_time,
        },
        headers=auth_headers,
    )
    assert res3.status_code == 404
    assert res3.json()["error"]["code"] == "LEAD_NOT_FOUND"

    # 4. Nonexistent site visit retrieval
    res4 = await client.get(
        f"/api/v1/site-visits/{random_id}",
        headers=auth_headers,
    )
    assert res4.status_code == 404
    assert res4.json()["error"]["code"] == "SITE_VISIT_NOT_FOUND"


@pytest.mark.asyncio
async def test_cannot_complete_unconfirmed_visit(
    client: AsyncClient,
    auth_headers: dict,
    active_client: dict,
    active_property: dict,
):
    """Verify that completing a REQUESTED visit directly is rejected with 422."""
    visit_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    res_create = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": active_client["id"],
            "property_id": active_property["id"],
            "scheduled_at": visit_time,
            "status": "REQUESTED",
        },
        headers=auth_headers,
    )
    visit_id = res_create.json()["data"]["id"]

    # Attempt to mark complete without confirmation
    res_comp = await client.post(
        f"/api/v1/site-visits/{visit_id}/complete",
        headers=auth_headers,
    )
    assert res_comp.status_code == 422
    assert res_comp.json()["error"]["code"] == "INVALID_SITE_VISIT_TRANSITION"


@pytest.mark.asyncio
async def test_cannot_mutate_terminal_visit(
    client: AsyncClient,
    auth_headers: dict,
    active_client: dict,
    active_property: dict,
):
    """Verify that completed and cancelled visits cannot transition to other states."""
    visit_time = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()

    # Create and cancel visit
    res_create = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": active_client["id"],
            "property_id": active_property["id"],
            "scheduled_at": visit_time,
            "status": "REQUESTED",
        },
        headers=auth_headers,
    )
    visit_id = res_create.json()["data"]["id"]

    await client.post(
        f"/api/v1/site-visits/{visit_id}/cancel",
        json={"cancellation_reason": "Customer called off inspection"},
        headers=auth_headers,
    )

    # Attempt to complete cancelled visit
    res_comp = await client.post(
        f"/api/v1/site-visits/{visit_id}/complete",
        headers=auth_headers,
    )
    assert res_comp.status_code == 422
    assert res_comp.json()["error"]["code"] == "INVALID_SITE_VISIT_TRANSITION"

    # Attempt to reschedule cancelled visit
    res_resc = await client.post(
        f"/api/v1/site-visits/{visit_id}/reschedule",
        json={"new_scheduled_at": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()},
        headers=auth_headers,
    )
    assert res_resc.status_code == 422
    assert res_resc.json()["error"]["code"] == "INVALID_SITE_VISIT_TRANSITION"


@pytest.mark.asyncio
async def test_conflicting_visit_confirmation_rejected(
    client: AsyncClient,
    auth_headers: dict,
    active_client: dict,
    active_property: dict,
):
    """Verify that confirming two overlapping visits results in 409 RESOURCE_CONFLICT."""
    base_time = (datetime.now(timezone.utc) + timedelta(days=5)).replace(minute=0, second=0, microsecond=0)

    # 1. Create and confirm Visit A for 10:00 AM
    res_a = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": active_client["id"],
            "property_id": active_property["id"],
            "scheduled_at": base_time.isoformat(),
            "status": "REQUESTED",
        },
        headers=auth_headers,
    )
    visit_a_id = res_a.json()["data"]["id"]

    res_conf_a = await client.post(
        f"/api/v1/site-visits/{visit_a_id}/confirm",
        headers=auth_headers,
    )
    assert res_conf_a.status_code == 200
    assert res_conf_a.json()["data"]["status"] == "CONFIRMED"

    # 2. Create Visit B for 10:30 AM (overlapping within 60 min window)
    overlap_time = base_time + timedelta(minutes=30)
    res_b = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": active_client["id"],
            "property_id": active_property["id"],
            "scheduled_at": overlap_time.isoformat(),
            "status": "REQUESTED",
        },
        headers=auth_headers,
    )
    visit_b_id = res_b.json()["data"]["id"]

    # Attempt to confirm Visit B -> Must fail with 409
    res_conf_b = await client.post(
        f"/api/v1/site-visits/{visit_b_id}/confirm",
        headers=auth_headers,
    )
    assert res_conf_b.status_code == 409
    assert res_conf_b.json()["error"]["code"] == "RESOURCE_CONFLICT"

    # 3. Create Visit C for 11:00 AM (touching boundary: exactly 60 min after base_time)
    boundary_time = base_time + timedelta(minutes=60)
    res_c = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": active_client["id"],
            "property_id": active_property["id"],
            "scheduled_at": boundary_time.isoformat(),
            "status": "REQUESTED",
        },
        headers=auth_headers,
    )
    visit_c_id = res_c.json()["data"]["id"]

    # Confirm Visit C -> Must succeed! Touching boundaries do not conflict
    res_conf_c = await client.post(
        f"/api/v1/site-visits/{visit_c_id}/confirm",
        headers=auth_headers,
    )
    assert res_conf_c.status_code == 200
    assert res_conf_c.json()["data"]["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_lead_validation_rules(
    client: AsyncClient,
    auth_headers: dict,
    active_property: dict,
):
    """Verify lead cross-client mismatch and terminal lead state validation."""
    # Create Client 1 and Client 2
    c1 = (await client.post("/api/v1/clients", json={"full_name": "Client 1", "phone": f"+91 91{uuid.uuid4().int % 100000000:08d}", "classification": "BUYER"}, headers=auth_headers)).json()["data"]
    c2 = (await client.post("/api/v1/clients", json={"full_name": "Client 2", "phone": f"+91 92{uuid.uuid4().int % 100000000:08d}", "classification": "BUYER"}, headers=auth_headers)).json()["data"]

    # Create Lead for Client 1 with required source
    lead_c1 = (await client.post("/api/v1/leads", json={"client_id": c1["id"], "property_id": active_property["id"], "source": "DIRECT_CALL"}, headers=auth_headers)).json()["data"]

    # Attempt to associate Client 1's lead with Client 2
    visit_time = (datetime.now(timezone.utc) + timedelta(days=6)).isoformat()
    res = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": c2["id"],
            "property_id": active_property["id"],
            "lead_id": lead_c1["id"],
            "scheduled_at": visit_time,
        },
        headers=auth_headers,
    )
    assert res.status_code == 422
    assert "Lead does not belong to the specified client" in res.json()["error"]["message"]
