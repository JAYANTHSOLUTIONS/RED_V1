"""Failure and edge-case tests for Property Management.

Covers:
  - Rejection of invalid lifecycle transitions (e.g. DRAFT -> SOLD)
  - Prohibition of mutating archived properties
  - Invalid pagination parameter validation
  - Nonexistent property and image references (404 errors)
  - Concurrency resilience on property status transitions
"""
import asyncio
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


@pytest.mark.asyncio
async def test_invalid_lifecycle_transitions_rejected(
    client: AsyncClient, consultant_headers: dict
):
    """Verify disallowed transitions fail with 422 VALIDATION_ERROR."""
    # Create DRAFT property
    create_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Transition Test Villa",
            "property_type": "Villa",
            "transaction_type": "SALE",
            "price": "5000000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "RS Puram",
            "pincode": "641002",
        },
        headers=consultant_headers,
    )
    prop_id = create_res.json()["data"]["id"]

    # 1. DRAFT -> SOLD (must fail: must be PUBLISHED first)
    res_sold = await client.post(
        f"/api/v1/properties/{prop_id}/mark-sold", headers=consultant_headers
    )
    assert res_sold.status_code == 422
    assert res_sold.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "invalid status transition" in res_sold.json()["error"]["message"].lower()

    # 2. DRAFT -> RENTED (must fail)
    res_rented = await client.post(
        f"/api/v1/properties/{prop_id}/mark-rented", headers=consultant_headers
    )
    assert res_rented.status_code == 422

    # 3. Publish it, then mark as sold
    await client.post(f"/api/v1/properties/{prop_id}/publish", headers=consultant_headers)
    sold_ok = await client.post(
        f"/api/v1/properties/{prop_id}/mark-sold", headers=consultant_headers
    )
    assert sold_ok.status_code == 200

    # 4. SOLD -> PUBLISHED (must fail: terminal state)
    res_repub = await client.post(
        f"/api/v1/properties/{prop_id}/publish", headers=consultant_headers
    )
    assert res_repub.status_code == 422
    assert "invalid status transition" in res_repub.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_archived_property_cannot_be_mutated(
    client: AsyncClient, consultant_headers: dict
):
    """Archived properties cannot undergo further status transitions or field updates."""
    create_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "To Be Archived",
            "property_type": "Apartment",
            "transaction_type": "RENT",
            "price": "15000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Gandhipuram",
            "pincode": "641012",
        },
        headers=consultant_headers,
    )
    prop_id = create_res.json()["data"]["id"]

    # Archive property
    arch_res = await client.post(
        f"/api/v1/properties/{prop_id}/archive", headers=consultant_headers
    )
    assert arch_res.status_code == 200

    # Attempt PATCH update on archived property
    patch_res = await client.patch(
        f"/api/v1/properties/{prop_id}",
        json={"price": "18000.00"},
        headers=consultant_headers,
    )
    assert patch_res.status_code == 422
    assert "archived" in patch_res.json()["error"]["message"].lower()

    # Attempt to publish archived property
    pub_res = await client.post(
        f"/api/v1/properties/{prop_id}/publish", headers=consultant_headers
    )
    assert pub_res.status_code == 422
    assert "archived" in pub_res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_invalid_pagination_parameters(
    client: AsyncClient, consultant_headers: dict
):
    """Verify limit and offset bounds."""
    # 1. Oversized limit (> 100)
    res1 = await client.get("/api/v1/properties?limit=150", headers=consultant_headers)
    assert res1.status_code == 422

    # 2. Limit < 1
    res2 = await client.get("/api/v1/properties?limit=0", headers=consultant_headers)
    assert res2.status_code == 422

    # 3. Negative offset
    res3 = await client.get("/api/v1/properties?offset=-5", headers=consultant_headers)
    assert res3.status_code == 422


@pytest.mark.asyncio
async def test_nonexistent_property_and_image_operations(
    client: AsyncClient, consultant_headers: dict
):
    """Verify 404 behavior for invalid UUID lookups."""
    fake_id = uuid.uuid4()

    # 1. Get nonexistent property
    res1 = await client.get(f"/api/v1/properties/{fake_id}", headers=consultant_headers)
    assert res1.status_code == 404

    # 2. Add image to nonexistent property
    res2 = await client.post(
        f"/api/v1/properties/{fake_id}/images",
        json={
            "storage_key": "some-key.jpg",
            "original_filename": "some.jpg",
            "mime_type": "image/jpeg",
            "file_size": 1000,
        },
        headers=consultant_headers,
    )
    assert res2.status_code == 404

    # 3. Delete nonexistent image
    res3 = await client.delete(
        f"/api/v1/properties/{fake_id}/images/{uuid.uuid4()}",
        headers=consultant_headers,
    )
    assert res3.status_code == 404


@pytest.mark.asyncio
async def test_concurrent_status_transitions_safe(
    client: AsyncClient, consultant_headers: dict
):
    """Verify concurrent transition requests handle row locks cleanly without data corruption."""
    create_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Concurrency Test Plot",
            "property_type": "Residential Plot / Layout Land",
            "transaction_type": "SALE",
            "price": "3000000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Kovaipudur",
            "pincode": "641042",
        },
        headers=consultant_headers,
    )
    prop_id = create_res.json()["data"]["id"]

    # First publish
    await client.post(f"/api/v1/properties/{prop_id}/publish", headers=consultant_headers)

    # Concurrently attempt: mark-sold AND pause
    req1 = client.post(f"/api/v1/properties/{prop_id}/mark-sold", headers=consultant_headers)
    req2 = client.post(f"/api/v1/properties/{prop_id}/pause", headers=consultant_headers)

    res1, res2 = await asyncio.gather(req1, req2)

    # One must succeed (200), and the other must either succeed or return 422 if transition became invalid
    status_codes = {res1.status_code, res2.status_code}
    assert 200 in status_codes
    assert status_codes.issubset({200, 422})
