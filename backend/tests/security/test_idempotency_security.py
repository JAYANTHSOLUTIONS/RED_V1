"""Adversarial security tests for Idempotency Key Abuse & Parameter Tampering.

Verifies:
  - Oversized idempotency keys (> 128 chars) and empty keys are rejected with 422 ValidationAppError.
  - Replaying an idempotency key with a tampered/different payload returns 409 Conflict.
  - Idempotency records enforce user isolation: User B reusing User A's key does not receive User A's cached response.
"""
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


async def create_consultant_helper(client: AsyncClient, prefix: str) -> tuple[dict, User]:
    email = f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=f"{prefix} Consultant",
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
async def test_oversized_idempotency_key_rejected(client: AsyncClient):
    """Idempotency-Key exceeding 128 characters must be rejected cleanly with 422."""
    headers, _ = await create_consultant_helper(client, "idemp-user")
    oversized_key = "K" * 150  # 150 chars > 128
    headers["Idempotency-Key"] = oversized_key

    payload = {
        "title": "Villa with Oversized Idemp Key",
        "property_type": "VILLA",
        "transaction_type": "SALE",
        "price": "10000000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "Tambaram",
        "pincode": "600045",
        "taluk": "Tambaram",
        "village": "Tambaram",
    }
    res = await client.post("/api/v1/properties", json=payload, headers=headers)
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"
    assert "128 characters" in body["error"]["message"]


@pytest.mark.asyncio
async def test_empty_idempotency_key_rejected(client: AsyncClient):
    """Empty or whitespace Idempotency-Key header must be rejected with 422."""
    headers, _ = await create_consultant_helper(client, "idemp-empty")
    headers["Idempotency-Key"] = "   "

    payload = {
        "title": "Villa with Empty Idemp Key",
        "property_type": "VILLA",
        "transaction_type": "SALE",
        "price": "10000000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "Tambaram",
        "pincode": "600045",
        "taluk": "Tambaram",
        "village": "Tambaram",
    }
    res = await client.post("/api/v1/properties", json=payload, headers=headers)
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"


@pytest.mark.asyncio
async def test_tampered_payload_idempotency_conflict(client: AsyncClient):
    """Reusing the same idempotency key with an altered payload must trigger 409 Conflict."""
    headers, _ = await create_consultant_helper(client, "idemp-tamper")
    key = str(uuid.uuid4())
    headers["Idempotency-Key"] = key

    payload1 = {
        "title": "Original Property Submission",
        "property_type": "APARTMENT",
        "transaction_type": "SALE",
        "price": "6000000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "Guindy",
        "pincode": "600032",
        "taluk": "Guindy",
        "village": "Guindy",
    }
    res1 = await client.post("/api/v1/properties", json=payload1, headers=headers)
    assert res1.status_code == 201

    # Tampered payload using the same key
    payload2 = {
        "title": "Tampered Property Submission",
        "property_type": "APARTMENT",
        "transaction_type": "SALE",
        "price": "9999999.00",  # Changed price
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "Guindy",
        "pincode": "600032",
        "taluk": "Guindy",
        "village": "Guindy",
    }
    res2 = await client.post("/api/v1/properties", json=payload2, headers=headers)
    assert res2.status_code == 409
    body2 = res2.json()
    assert body2["success"] is False
    assert body2["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"


@pytest.mark.asyncio
async def test_cross_user_idempotency_isolation(client: AsyncClient):
    """User B reusing User A's idempotency key must not receive User A's cached response."""
    headers_a, _ = await create_consultant_helper(client, "user-a")
    headers_b, _ = await create_consultant_helper(client, "user-b")

    shared_key = str(uuid.uuid4())
    headers_a["Idempotency-Key"] = shared_key
    headers_b["Idempotency-Key"] = shared_key

    payload = {
        "title": "Independent Property Submission",
        "property_type": "VILLA",
        "transaction_type": "SALE",
        "price": "8000000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "Velachery",
        "pincode": "600042",
        "taluk": "Velachery",
        "village": "Velachery",
    }

    # 1. User A creates property
    res_a = await client.post("/api/v1/properties", json=payload, headers=headers_a)
    assert res_a.status_code == 201
    prop_id_a = res_a.json()["data"]["id"]

    # 2. User B posts same payload with same key
    res_b = await client.post("/api/v1/properties", json=payload, headers=headers_b)
    assert res_b.status_code == 201
    prop_id_b = res_b.json()["data"]["id"]

    # Assert User B created a separate property, not receiving A's cached response
    assert prop_id_b != prop_id_a
    assert res_b.headers.get("Idempotent-Replay") is None

