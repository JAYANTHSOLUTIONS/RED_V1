"""Tests for mutation idempotency, duplicate prevention, and response replays."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.exceptions import ConflictError
from app.core.idempotency import IdempotencyService, compute_request_hash
from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.property import Property
from app.models.user import User


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    email = f"consultant-idemp-{uuid.uuid4().hex[:8]}@example.com"
    password = "IdempPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Idempotency Consultant",
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


def test_compute_request_hash_determinism():
    """Hash should be identical regardless of dictionary key ordering."""
    payload1 = {"title": "Villa", "price": 1000000, "locality": "Anna Nagar"}
    payload2 = {"locality": "Anna Nagar", "title": "Villa", "price": 1000000}
    assert compute_request_hash(payload1) == compute_request_hash(payload2)


async def test_idempotency_service_lifecycle():
    """Verify check_or_reserve -> finalize -> replay lifecycle."""
    service = IdempotencyService()
    key = f"key-{uuid.uuid4().hex}"
    user_id = None
    endpoint = "/api/v1/properties"
    payload = {"title": "Plot in OMR", "price": 5000000}

    async with AsyncSessionFactory() as session:
        # 1. First reservation
        cached_resp, record_id = await service.check_or_reserve(
            session=session,
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            payload=payload,
        )
        assert cached_resp is None
        assert record_id is not None

        # 2. In-flight collision raises ConflictError
        with pytest.raises(ConflictError) as exc_info:
            await service.check_or_reserve(
                session=session,
                key=key,
                user_id=user_id,
                endpoint=endpoint,
                payload=payload,
            )
        assert exc_info.value.code == "IDEMPOTENCY_IN_PROGRESS"

        # 3. Finalize reservation
        resp_data = {"success": True, "data": {"id": str(uuid.uuid4())}}
        await service.finalize(
            session=session,
            record_id=record_id,
            status_code=201,
            response_body=resp_data,
        )

        # 4. Replay with identical payload returns cached response
        cached_resp2, record_id2 = await service.check_or_reserve(
            session=session,
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            payload=payload,
        )
        assert cached_resp2 is not None
        assert record_id2 is None
        assert cached_resp2.status_code == 201
        assert cached_resp2.headers.get("Idempotent-Replay") == "true"

        # 5. Collision with differing payload raises payload mismatch
        different_payload = {"title": "Different Plot", "price": 6000000}
        with pytest.raises(ConflictError) as exc_info2:
            await service.check_or_reserve(
                session=session,
                key=key,
                user_id=user_id,
                endpoint=endpoint,
                payload=different_payload,
            )
        assert exc_info2.value.code == "IDEMPOTENCY_PAYLOAD_MISMATCH"


async def test_idempotency_service_abort_allows_retry():
    """If an operation fails and aborts, the key can be reserved again."""
    service = IdempotencyService()
    key = f"key-abort-{uuid.uuid4().hex}"
    user_id = None
    endpoint = "/api/v1/properties"
    payload = {"title": "Failing Op", "price": 100000}

    async with AsyncSessionFactory() as session:
        cached_resp, record_id = await service.check_or_reserve(
            session=session,
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            payload=payload,
        )
        assert record_id is not None

        # Abort
        await service.abort(session, record_id)

        # Retry should succeed in reserving again
        cached_resp2, record_id2 = await service.check_or_reserve(
            session=session,
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            payload=payload,
        )
        assert cached_resp2 is None
        assert record_id2 is not None


async def test_api_property_creation_idempotent_replay(client: AsyncClient, consultant_auth: dict):
    """Calling POST /api/v1/properties with same Idempotency-Key replays response without creating duplicate."""
    idemp_key = f"idem-prop-{uuid.uuid4().hex}"
    headers = {**consultant_auth, "Idempotency-Key": idemp_key}

    unique_title = f"Idempotent Prime Land {uuid.uuid4().hex[:6]}"
    payload = {
        "title": unique_title,
        "property_type": "LAND",
        "transaction_type": "SALE",
        "price": "3500000.00",
        "district": "Coimbatore",
        "city": "Coimbatore",
        "locality": "RS Puram",
        "pincode": "641002",
        "address": "DB Road",
    }

    # 1. First submission
    resp1 = await client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp1.status_code == 201
    body1 = resp1.json()
    prop_id = body1["data"]["id"]
    assert "Idempotent-Replay" not in resp1.headers

    # 2. Second submission with exact same key and payload
    resp2 = await client.post("/api/v1/properties", json=payload, headers=headers)
    assert resp2.status_code == 201
    body2 = resp2.json()
    assert body2["data"]["id"] == prop_id
    assert resp2.headers.get("Idempotent-Replay") == "true"

    # 3. Third submission with same key but altered payload -> 409 Conflict
    altered_payload = {**payload, "price": "4000000.00"}
    resp3 = await client.post("/api/v1/properties", json=altered_payload, headers=headers)
    assert resp3.status_code == 409
    body3 = resp3.json()
    assert body3["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"

    # 4. Verify only ONE property was created in the database
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Property).where(Property.title == unique_title)
        )
        props = result.scalars().all()
        assert len(props) == 1
