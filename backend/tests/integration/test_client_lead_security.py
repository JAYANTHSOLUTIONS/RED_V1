"""Security tests for Client and Lead Management.

Verifies:
- Unauthenticated requests are rejected (401)
- Non-consultant roles are forbidden (403)
- No public client or lead endpoints exist (404)
- Zero leakage of client PII or lead metadata through public channels
"""
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def regular_user_headers(client: AsyncClient):
    """Create and authenticate a non-consultant user."""
    email = f"regular-user-{uuid.uuid4().hex[:8]}@example.com"
    password = "UserPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Regular User",
                role="USER",
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
async def consultant_headers(client: AsyncClient):
    email = f"consultant-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant Sec",
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


@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient):
    # Clients
    res_get_clients = await client.get("/api/v1/clients")
    assert res_get_clients.status_code == 401

    res_post_clients = await client.post("/api/v1/clients", json={"full_name": "Anon", "phone": "123"})
    assert res_post_clients.status_code == 401

    # Leads
    res_get_leads = await client.get("/api/v1/leads")
    assert res_get_leads.status_code == 401

    res_post_leads = await client.post("/api/v1/leads", json={"client_id": str(uuid.uuid4()), "source": "TEST"})
    assert res_post_leads.status_code == 401


@pytest.mark.asyncio
async def test_non_consultant_role_forbidden(client: AsyncClient, regular_user_headers: dict):
    res_clients = await client.get("/api/v1/clients", headers=regular_user_headers)
    assert res_clients.status_code == 403

    res_leads = await client.get("/api/v1/leads", headers=regular_user_headers)
    assert res_leads.status_code == 403


@pytest.mark.asyncio
async def test_no_public_client_or_lead_endpoints(client: AsyncClient):
    res_public_clients = await client.get("/api/v1/public/clients")
    assert res_public_clients.status_code == 404

    res_public_leads = await client.get("/api/v1/public/leads")
    assert res_public_leads.status_code == 404


@pytest.mark.asyncio
async def test_zero_client_data_leakage_to_public_endpoints(
    client: AsyncClient, consultant_headers: dict
):
    """Ensure client contact details and internal leads are NEVER serialized in public property responses."""
    # Create private client
    client_res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Private HighNetWorth Client",
            "phone": "+91 9111122222",
            "email": "hnw@private-domain.com",
            "notes": "Secret negotiation notes",
        },
        headers=consultant_headers,
    )
    client_id = client_res.json()["data"]["id"]

    # Create and publish property
    prop_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Luxury Penthouse",
            "property_type": "Apartment",
            "transaction_type": "SALE",
            "price": "25000000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Race Course",
            "pincode": "641018",
            "owner_name": "Secret Property Owner",
            "owner_phone": "+91 9888877777",
            "internal_notes": "Highly confidential property evaluation",
        },
        headers=consultant_headers,
    )
    prop_id = prop_res.json()["data"]["id"]
    public_ref = prop_res.json()["data"]["public_reference"]

    # Publish property
    await client.post(f"/api/v1/properties/{prop_id}/publish", headers=consultant_headers)

    # Attach a lead from the private client
    await client.post(
        "/api/v1/leads",
        json={
            "client_id": client_id,
            "property_id": prop_id,
            "source": "DIRECT_CALL",
            "notes": "Client offering 2.4 Cr",
        },
        headers=consultant_headers,
    )

    # Query public property listing
    public_list = await client.get("/api/v1/public/properties")
    assert public_list.status_code == 200
    public_list_text = public_list.text
    assert "Private HighNetWorth" not in public_list_text
    assert "+91 9111122222" not in public_list_text
    assert "hnw@private-domain.com" not in public_list_text
    assert "Secret negotiation notes" not in public_list_text
    assert "Client offering 2.4 Cr" not in public_list_text

    # Query public property detail
    public_detail = await client.get(f"/api/v1/public/properties/{public_ref}")
    assert public_detail.status_code == 200
    public_detail_text = public_detail.text
    assert "Private HighNetWorth" not in public_detail_text
    assert "+91 9111122222" not in public_detail_text
    assert "hnw@private-domain.com" not in public_detail_text
    assert "Client offering 2.4 Cr" not in public_detail_text
