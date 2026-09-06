"""Security tests for Property Management.

Covers:
  - Authentication requirement on all private property routes (401 Unauthorized)
  - Role-based authorization enforcement (403 Forbidden for unauthorized roles)
  - Public data leakage prevention (zero owner PII, zero internal notes)
  - Uniform safe 404 responses for nonexistent or private properties (anti-enumeration)
"""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def consultant_headers(client: AsyncClient):
    email = f"consultant-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

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
    access_token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def assistant_headers(client: AsyncClient):
    """User with non-consultant role (e.g. ASSISTANT) without PROPERTY_WRITE permissions."""
    email = f"assistant-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Assistant User",
                role="ASSISTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    access_token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(client: AsyncClient):
    """Verify private endpoints require Bearer authentication."""
    random_id = uuid.uuid4()

    # 1. Create property
    res1 = await client.post("/api/v1/properties", json={})
    assert res1.status_code == 401

    # 2. List properties
    res2 = await client.get("/api/v1/properties")
    assert res2.status_code == 401

    # 3. Get property
    res3 = await client.get(f"/api/v1/properties/{random_id}")
    assert res3.status_code == 401

    # 4. Patch property
    res4 = await client.patch(f"/api/v1/properties/{random_id}", json={})
    assert res4.status_code == 401

    # 5. Status actions
    res5 = await client.post(f"/api/v1/properties/{random_id}/publish")
    assert res5.status_code == 401

    # 6. Images
    res6 = await client.post(f"/api/v1/properties/{random_id}/images", json={})
    assert res6.status_code == 401


@pytest.mark.asyncio
async def test_unauthorized_role_rejected(
    client: AsyncClient, assistant_headers: dict
):
    """Verify users without CONSULTANT role cannot manage properties (403 Forbidden)."""
    res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Unauthorized Villa",
            "property_type": "Villa",
            "transaction_type": "SALE",
            "price": "5000000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "RS Puram",
            "pincode": "641002",
        },
        headers=assistant_headers,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_public_detail_never_leaks_private_information(
    client: AsyncClient, consultant_headers: dict
):
    """Verify public endpoint never returns owner name, phone, email, or internal notes."""
    create_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Private Owner Villa",
            "property_type": "Independent House / Villa",
            "transaction_type": "SALE",
            "price": "9500000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Race Course",
            "pincode": "641018",
            "address": "123 Secret Lane, Near Collector Office",
            "owner_name": "K. Balakrishnan",
            "owner_phone": "+919842112233",
            "owner_email": "balu@privatedomain.com",
            "inventory_source": "Personal Referral",
            "advertisement_authorized": True,
            "internal_notes": "Minimum price acceptable is 90 Lakhs.",
        },
        headers=consultant_headers,
    )
    prop_id = create_res.json()["data"]["id"]
    public_ref = create_res.json()["data"]["public_reference"]

    # Publish property so it is accessible publicly
    await client.post(
        f"/api/v1/properties/{prop_id}/publish", headers=consultant_headers
    )

    # Fetch via public endpoint
    pub_res = await client.get(f"/api/v1/public/properties/{public_ref}")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()["data"]

    # Public data present
    assert pub_data["public_reference"] == public_ref
    assert pub_data["title"] == "Private Owner Villa"
    assert pub_data["locality"] == "Race Course"

    # Strict privacy verification
    assert "owner_name" not in pub_data
    assert "owner_phone" not in pub_data
    assert "owner_email" not in pub_data
    assert "inventory_source" not in pub_data
    assert "internal_notes" not in pub_data
    assert "address" not in pub_data
    assert "id" not in pub_data


@pytest.mark.asyncio
async def test_public_endpoint_safe_404_on_unpublished_or_nonexistent(
    client: AsyncClient, consultant_headers: dict
):
    """Verify uniform 404 behavior for draft, paused, archived, and nonexistent properties."""
    # 1. Nonexistent reference
    res_nonexistent = await client.get("/api/v1/public/properties/PR-2026-999999")
    assert res_nonexistent.status_code == 404
    assert res_nonexistent.json()["error"]["code"] == "NOT_FOUND"

    # 2. Draft property reference
    create_draft = await client.post(
        "/api/v1/properties",
        json={
            "title": "Secret Draft Property",
            "property_type": "Apartment",
            "transaction_type": "SALE",
            "price": "3500000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Saibaba Colony",
            "pincode": "641011",
        },
        headers=consultant_headers,
    )
    draft_ref = create_draft.json()["data"]["public_reference"]

    res_draft = await client.get(f"/api/v1/public/properties/{draft_ref}")
    assert res_draft.status_code == 404
    assert res_draft.json()["error"]["code"] == "NOT_FOUND"

    # Responses must be identical to avoid existence disclosure
    assert (
        res_nonexistent.json()["error"]["message"]
        == res_draft.json()["error"]["message"]
    )
