"""Failure mode and boundary tests for Preliminary Property Verification API."""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.property import Property
from app.models.user import User


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    email = f"consultant-fail-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantFailurePass123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Failure Tester Consultant",
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
async def archived_property():
    ref_code = f"ARC-PROP-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Archived Land Parcel",
                property_type="LAND",
                transaction_type="SALE",
                price=Decimal("3000000.00"),
                district="Madurai",
                city="Madurai",
                locality="KK Nagar",
                pincode="625020",
                status="ARCHIVED",
                is_archived=True,
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id
    return prop_id


@pytest.mark.asyncio
async def test_verification_on_nonexistent_property_404(
    client: AsyncClient, consultant_auth: dict
):
    """Verify executing verification on a non-existent property returns 404."""
    random_id = uuid.uuid4()
    res = await client.post(
        f"/api/v1/properties/{random_id}/verification",
        json={},
        headers=consultant_auth,
    )
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False
    assert "not found" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_verification_on_archived_property_404(
    client: AsyncClient, consultant_auth: dict, archived_property: uuid.UUID
):
    """Verify executing verification on an archived property returns 404."""
    res = await client.post(
        f"/api/v1/properties/{archived_property}/verification",
        json={},
        headers=consultant_auth,
    )
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False
    assert "archived" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_get_nonexistent_verification_404(
    client: AsyncClient, consultant_auth: dict
):
    """Verify requesting an unknown verification case returns 404."""
    random_id = uuid.uuid4()
    res = await client.get(
        f"/api/v1/verifications/{random_id}",
        headers=consultant_auth,
    )
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_get_latest_verification_for_unverified_property_404(
    client: AsyncClient, consultant_auth: dict
):
    """Verify fetching latest verification on a property that has none returns 404."""
    ref_code = f"NEW-PROP-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Unverified Property",
                property_type="APARTMENT",
                transaction_type="SALE",
                price=Decimal("7000000.00"),
                district="Chennai",
                city="Chennai",
                locality="Adyar",
                pincode="600020",
                status="DRAFT",
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id

    res = await client.get(
        f"/api/v1/properties/{prop_id}/verification",
        headers=consultant_auth,
    )
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_patch_nonexistent_verification_404(
    client: AsyncClient, consultant_auth: dict
):
    """Verify updating a non-existent verification case returns 404."""
    random_id = uuid.uuid4()
    res = await client.patch(
        f"/api/v1/verifications/{random_id}",
        json={"consultant_observations": "Trying to update nothing"},
        headers=consultant_auth,
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_invalid_uuid_path_parameter_422(
    client: AsyncClient, consultant_auth: dict
):
    """Verify invalid UUID string in path triggers 422 Unprocessable Entity."""
    res = await client.get(
        "/api/v1/verifications/not-a-valid-uuid",
        headers=consultant_auth,
    )
    assert res.status_code == 422
