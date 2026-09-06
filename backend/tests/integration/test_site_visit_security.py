"""Security and RBAC tests for Site Visit endpoints."""
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
async def consultant_headers(client: AsyncClient):
    email = f"consultant-sec-{uuid.uuid4().hex[:8]}@example.com"
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
    email = f"assistant-sec-{uuid.uuid4().hex[:8]}@example.com"
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
async def existing_visit(consultant_headers: dict, client: AsyncClient):
    # Create client
    c_res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Sec Client",
            "phone": f"+91 97{uuid.uuid4().int % 100000000:08d}",
            "classification": "BUYER",
        },
        headers=consultant_headers,
    )
    client_id = c_res.json()["data"]["id"]

    # Create property
    p_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Sec Property",
            "property_type": "Residential Plot",
            "transaction_type": "SALE",
            "price": "3500000.00",
            "plot_area": "1500.00",
            "district": "Chennai",
            "city": "Chennai",
            "locality": "Thoraipakkam",
            "pincode": "600096",
        },
        headers=consultant_headers,
    )
    prop_id = p_res.json()["data"]["id"]

    # Create visit
    visit_time = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)
    v_res = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": client_id,
            "property_id": prop_id,
            "scheduled_at": visit_time.isoformat(),
            "notes": "CONFIDENTIAL: Consultant private notes about price negotiation limit",
        },
        headers=consultant_headers,
    )
    return v_res.json()["data"]


@pytest.mark.asyncio
async def test_unauthenticated_private_endpoints_rejected(
    client: AsyncClient, existing_visit: dict
):
    """Ensure private endpoints reject requests without valid Bearer token with 401."""
    visit_id = existing_visit["id"]

    # List
    res_list = await client.get("/api/v1/site-visits")
    assert res_list.status_code == 401

    # Get
    res_get = await client.get(f"/api/v1/site-visits/{visit_id}")
    assert res_get.status_code == 401

    # Confirm
    res_conf = await client.post(f"/api/v1/site-visits/{visit_id}/confirm")
    assert res_conf.status_code == 401

    # Complete
    res_comp = await client.post(f"/api/v1/site-visits/{visit_id}/complete")
    assert res_comp.status_code == 401

    # Cancel
    res_canc = await client.post(
        f"/api/v1/site-visits/{visit_id}/cancel",
        json={"cancellation_reason": "No reason"},
    )
    assert res_canc.status_code == 401

    # Reschedule
    res_resc = await client.post(
        f"/api/v1/site-visits/{visit_id}/reschedule",
        json={"new_scheduled_at": datetime.now(timezone.utc).isoformat()},
    )
    assert res_resc.status_code == 401


@pytest.mark.asyncio
async def test_non_consultant_role_rejected(
    client: AsyncClient, assistant_headers: dict, existing_visit: dict
):
    """Ensure users without CONSULTANT role (e.g. ASSISTANT) receive 403 Forbidden."""
    visit_id = existing_visit["id"]

    res_list = await client.get("/api/v1/site-visits", headers=assistant_headers)
    assert res_list.status_code == 403
    assert res_list.json()["error"]["code"] == "FORBIDDEN"

    res_conf = await client.post(
        f"/api/v1/site-visits/{visit_id}/confirm",
        headers=assistant_headers,
    )
    assert res_conf.status_code == 403
    assert res_conf.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_public_endpoint_data_isolation(
    client: AsyncClient, existing_visit: dict
):
    """Ensure public view never exposes confidential consultant notes or client details."""
    visit_id = existing_visit["id"]

    res = await client.get(f"/api/v1/site-visits/{visit_id}/public")
    assert res.status_code == 200
    data = res.json()["data"]

    # Public fields present
    assert data["id"] == visit_id
    assert data["status"] == existing_visit["status"]
    assert "disclaimer" in data

    # Private fields STRICTLY absent
    assert "notes" not in data
    assert "CONFIDENTIAL" not in str(data)
    assert "client" not in data
    assert "client_id" not in data


@pytest.mark.asyncio
async def test_invalid_uuid_handling(client: AsyncClient, consultant_headers: dict):
    """Ensure malformed UUID path parameter returns 422 validation error."""
    res = await client.get("/api/v1/site-visits/not-a-valid-uuid", headers=consultant_headers)
    assert res.status_code == 422
