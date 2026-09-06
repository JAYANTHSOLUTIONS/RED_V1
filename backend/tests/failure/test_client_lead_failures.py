"""Failure and boundary tests for Client and Lead Management."""
import asyncio
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-fail-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant Failures",
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
async def test_nonexistent_client_404(client: AsyncClient, auth_headers: dict):
    random_id = uuid.uuid4()
    res = await client.get(f"/api/v1/clients/{random_id}", headers=auth_headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_cannot_modify_archived_client(client: AsyncClient, auth_headers: dict):
    create_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Soon Archived", "phone": "+91 9333300001"},
        headers=auth_headers,
    )
    client_id = create_res.json()["data"]["id"]

    # Archive client
    await client.post(f"/api/v1/clients/{client_id}/archive", headers=auth_headers)

    # Attempt update
    update_res = await client.patch(
        f"/api/v1/clients/{client_id}",
        json={"full_name": "New Name Should Fail"},
        headers=auth_headers,
    )
    assert update_res.status_code == 422
    assert "Cannot modify an archived client" in update_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_cannot_create_lead_for_archived_client(client: AsyncClient, auth_headers: dict):
    create_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Archived For Lead", "phone": "+91 9333300002"},
        headers=auth_headers,
    )
    client_id = create_res.json()["data"]["id"]
    await client.post(f"/api/v1/clients/{client_id}/archive", headers=auth_headers)

    lead_res = await client.post(
        "/api/v1/leads",
        json={"client_id": client_id, "source": "PHONE"},
        headers=auth_headers,
    )
    assert lead_res.status_code == 422
    assert "Cannot create a lead for an archived client" in lead_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_create_lead_nonexistent_client(client: AsyncClient, auth_headers: dict):
    random_id = str(uuid.uuid4())
    lead_res = await client.post(
        "/api/v1/leads",
        json={"client_id": random_id, "source": "PHONE"},
        headers=auth_headers,
    )
    assert lead_res.status_code == 404
    assert "Client not found" in lead_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_create_lead_nonexistent_property(client: AsyncClient, auth_headers: dict):
    client_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Client Valid", "phone": "+91 9333300003"},
        headers=auth_headers,
    )
    client_id = client_res.json()["data"]["id"]

    random_prop_id = str(uuid.uuid4())
    lead_res = await client.post(
        "/api/v1/leads",
        json={"client_id": client_id, "property_id": random_prop_id, "source": "PHONE"},
        headers=auth_headers,
    )
    assert lead_res.status_code == 404
    assert "Property not found" in lead_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_create_lead_archived_property(client: AsyncClient, auth_headers: dict):
    client_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Client Valid", "phone": "+91 9333300004"},
        headers=auth_headers,
    )
    client_id = client_res.json()["data"]["id"]

    # Create and archive a property
    prop_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Property To Archive",
            "property_type": "Apartment",
            "transaction_type": "SALE",
            "price": "5000000.00",
            "district": "Chennai",
            "city": "Chennai",
            "locality": "Guindy",
            "pincode": "600032",
        },
        headers=auth_headers,
    )
    prop_id = prop_res.json()["data"]["id"]
    await client.post(f"/api/v1/properties/{prop_id}/archive", headers=auth_headers)

    lead_res = await client.post(
        "/api/v1/leads",
        json={"client_id": client_id, "property_id": prop_id, "source": "PHONE"},
        headers=auth_headers,
    )
    assert lead_res.status_code == 422
    assert "Cannot link an archived property" in lead_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_invalid_lifecycle_transition(client: AsyncClient, auth_headers: dict):
    client_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Lifecycle Client", "phone": "+91 9333300005"},
        headers=auth_headers,
    )
    client_id = client_res.json()["data"]["id"]

    lead_res = await client.post(
        "/api/v1/leads",
        json={"client_id": client_id, "source": "PHONE"},
        headers=auth_headers,
    )
    lead_id = lead_res.json()["data"]["id"]

    # Try illegal transition directly: NEW -> CONVERTED
    illegal_res = await client.post(f"/api/v1/leads/{lead_id}/convert", headers=auth_headers)
    assert illegal_res.status_code == 422
    assert "Invalid status transition" in illegal_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_terminal_lead_cannot_transition(client: AsyncClient, auth_headers: dict):
    client_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Terminal Client", "phone": "+91 9333300006"},
        headers=auth_headers,
    )
    client_id = client_res.json()["data"]["id"]

    lead_res = await client.post(
        "/api/v1/leads",
        json={"client_id": client_id, "source": "PHONE"},
        headers=auth_headers,
    )
    lead_id = lead_res.json()["data"]["id"]

    # Mark lost
    await client.post(
        f"/api/v1/leads/{lead_id}/lost",
        json={"lost_reason": "No longer looking"},
        headers=auth_headers,
    )

    # Try to contact again
    illegal_res = await client.post(f"/api/v1/leads/{lead_id}/contact", headers=auth_headers)
    assert illegal_res.status_code == 422
    assert "Cannot transition lead from terminal status" in illegal_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_lost_reason_required_for_lost_status(client: AsyncClient, auth_headers: dict):
    client_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Reason Client", "phone": "+91 9333300007"},
        headers=auth_headers,
    )
    client_id = client_res.json()["data"]["id"]

    lead_res = await client.post(
        "/api/v1/leads",
        json={"client_id": client_id, "source": "PHONE"},
        headers=auth_headers,
    )
    lead_id = lead_res.json()["data"]["id"]

    # Empty lost reason
    bad_res = await client.post(
        f"/api/v1/leads/{lead_id}/lost",
        json={"lost_reason": "   "},
        headers=auth_headers,
    )
    assert bad_res.status_code == 422


@pytest.mark.asyncio
async def test_concurrent_lead_lifecycle_transitions(client: AsyncClient, auth_headers: dict):
    """Verify that multiple concurrent transition requests are handled safely under row-level locking."""
    client_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Concurrent Client", "phone": "+91 9333300008"},
        headers=auth_headers,
    )
    client_id = client_res.json()["data"]["id"]

    lead_res = await client.post(
        "/api/v1/leads",
        json={"client_id": client_id, "source": "PHONE"},
        headers=auth_headers,
    )
    lead_id = lead_res.json()["data"]["id"]

    # Fire two concurrent requests: both calling /contact
    results = await asyncio.gather(
        client.post(f"/api/v1/leads/{lead_id}/contact", headers=auth_headers),
        client.post(f"/api/v1/leads/{lead_id}/contact", headers=auth_headers),
        return_exceptions=True,
    )

    statuses = [r.status_code for r in results if not isinstance(r, Exception)]
    assert all(s == 200 for s in statuses)

    final_lead = await client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers)
    assert final_lead.json()["data"]["status"] == "CONTACTED"
