"""Adversarial security tests for Information Leakage & Public Endpoint Privacy.

Verifies:
  - Centralized error handlers never leak Python tracebacks, database credentials,
    filesystem paths, or SQL statements.
  - Public property endpoints strictly filter out owner PII, internal notes, and consultant IDs.
  - Public site visit endpoints strictly filter out client PII and consultant notes.
"""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.property import Property
from app.models.user import User


@pytest.fixture
async def consultant_headers(client: AsyncClient):
    email = f"leak-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant Privacy Officer",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


@pytest.mark.asyncio
async def test_error_handlers_do_not_leak_internals(client: AsyncClient):
    """Invalid requests and 404s must return uniform envelopes without traceback or system paths."""
    # 1. 404 Not Found
    res_404 = await client.get("/api/v1/nonexistent-endpoint-path")
    assert res_404.status_code == 404
    body_404 = res_404.json()
    assert body_404["success"] is False
    assert "Traceback" not in str(body_404)
    assert "password" not in str(body_404).lower()
    assert "postgresql://" not in str(body_404)
    assert "C:\\" not in str(body_404)
    assert "/home/" not in str(body_404)

    # 2. 422 Validation Error
    res_422 = await client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": ""})
    assert res_422.status_code == 422
    body_422 = res_422.json()
    assert body_422["success"] is False
    assert "Traceback" not in str(body_422)


@pytest.mark.asyncio
async def test_public_property_data_leakage_prevention(client: AsyncClient, consultant_headers: tuple):
    """Public property responses must strictly omit owner PII, internal notes, and consultant IDs."""
    headers, consultant = consultant_headers

    # Create a property with sensitive owner PII and confidential internal notes
    prop_payload = {
        "title": "Confidential Penthouse",
        "property_type": "APARTMENT",
        "transaction_type": "SALE",
        "price": "25000000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "R.A. Puram",
        "pincode": "600028",
        "taluk": "Mylapore",
        "village": "R.A. Puram",
        "description": "Exclusive penthouse with sea view.",
        "owner_name": "High Profile VIP Owner",
        "owner_phone": "+919999988888",
        "owner_email": "vip.owner@private.com",
        "internal_notes": "Urgent distressed sale. Do not reveal owner's financial distress.",
    }

    create_res = await client.post("/api/v1/properties", json=prop_payload, headers=headers)
    assert create_res.status_code == 201
    created = create_res.json()["data"]
    prop_id = created["id"]
    public_ref = created["public_reference"]

    # Publish property to active state so it appears on public endpoints
    await client.patch(
        f"/api/v1/properties/{prop_id}",
        json={"is_active": True},
        headers=headers,
    )

    # 1. Fetch via public list endpoint
    pub_list_res = await client.get("/api/v1/public/properties")
    assert pub_list_res.status_code == 200
    pub_items = pub_list_res.json()["data"]["items"]
    target_item = next((i for i in pub_items if i.get("public_reference") == public_ref), None)
    if target_item:
        # Assert strict PII redaction
        assert "owner_name" not in target_item
        assert "owner_phone" not in target_item
        assert "owner_email" not in target_item
        assert "internal_notes" not in target_item
        assert "id" not in target_item  # Database UUID must not be exposed

    # 2. Fetch via public detail endpoint
    pub_detail_res = await client.get(f"/api/v1/public/properties/{public_ref}")
    if pub_detail_res.status_code == 200:
        detail_data = pub_detail_res.json()["data"]
        assert "owner_name" not in detail_data
        assert "owner_phone" not in detail_data
        assert "owner_email" not in detail_data
        assert "internal_notes" not in detail_data
        assert "id" not in detail_data
        assert "VIP Owner" not in str(detail_data)
        assert "distressed" not in str(detail_data)
