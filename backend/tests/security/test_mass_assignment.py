"""Adversarial security tests for Mass Assignment & Parameter Tampering.

Verifies:
  - System-managed fields (id, status, public_reference, created_at, role) cannot
    be forced or escalated by client-supplied payload parameters.
  - Pydantic models sanitize and ignore or reject unauthorized privilege flags.
"""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def consultant_headers(client: AsyncClient):
    email = f"mass-assign-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant Mass Assign",
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
async def test_property_creation_mass_assignment_defense(client: AsyncClient, consultant_headers: dict):
    """Client cannot inject status='VERIFIED', custom public_reference, or forged id on creation."""
    forged_id = str(uuid.uuid4())
    forged_ref = "RED-FORGED-9999"
    payload = {
        "id": forged_id,
        "public_reference": forged_ref,
        "title": "Mass Assignment Test Villa",
        "property_type": "VILLA",
        "transaction_type": "SALE",
        "price": "12000000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "Adyar",
        "pincode": "600020",
        "taluk": "Guindy",
        "village": "Adyar",
        "status": "VERIFIED",  # Malicious attempt to bypass verification
        "is_active": False,
        "created_at": "2020-01-01T00:00:00Z",
    }

    res = await client.post("/api/v1/properties", json=payload, headers=consultant_headers)
    assert res.status_code == 201
    data = res.json()["data"]

    # 1. ID must be generated server-side, NOT the client's forged ID
    assert data["id"] != forged_id
    # 2. Public reference must follow server sequence pattern, NOT forged
    assert data["public_reference"] != forged_ref
    assert data["public_reference"].startswith("PR-")
    # 3. Status must start as DRAFT (or initial state), not client-forced VERIFIED
    assert data["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_property_update_mass_assignment_defense(client: AsyncClient, consultant_headers: dict):
    """Client cannot alter property id, public_reference, or status via property update."""
    # Create valid property
    create_payload = {
        "title": "Initial Property",
        "property_type": "APARTMENT",
        "transaction_type": "SALE",
        "price": "7500000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "Mylapore",
        "pincode": "600004",
        "taluk": "Mylapore",
        "village": "Mylapore",
    }
    create_res = await client.post("/api/v1/properties", json=create_payload, headers=consultant_headers)
    prop_id = create_res.json()["data"]["id"]
    orig_ref = create_res.json()["data"]["public_reference"]

    # Attempt malicious update with forged system fields
    tamper_payload = {
        "id": str(uuid.uuid4()),
        "public_reference": "RED-TAMPERED-REF",
        "status": "VERIFIED",
        "title": "Updated Title",
    }
    update_res = await client.patch(f"/api/v1/properties/{prop_id}", json=tamper_payload, headers=consultant_headers)
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]

    assert updated_data["id"] == prop_id
    assert updated_data["public_reference"] == orig_ref
    assert updated_data["status"] == "DRAFT"
    assert updated_data["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_client_creation_mass_assignment_defense(client: AsyncClient, consultant_headers: dict):
    """Client cannot inject is_archived=True or forged id on client creation."""
    forged_id = str(uuid.uuid4())
    payload = {
        "id": forged_id,
        "full_name": "Test Client Mass Assign",
        "phone": "+919876543299",
        "email": "testclient@example.com",
        "client_type": "INDIVIDUAL",
        "is_archived": True,  # Maliciously attempting to create already archived client
    }
    res = await client.post("/api/v1/clients", json=payload, headers=consultant_headers)
    assert res.status_code == 201
    data = res.json()["data"]

    assert data["id"] != forged_id
    assert data["is_archived"] is False
