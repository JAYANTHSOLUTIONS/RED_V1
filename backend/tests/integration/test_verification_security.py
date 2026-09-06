"""Security and authorization tests for Preliminary Property Verification API."""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.property import Property
from app.models.user import User


@pytest.fixture
async def sample_property():
    ref_code = f"SEC-PROP-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Security Test Plot",
                property_type="PLOT",
                transaction_type="SALE",
                price=Decimal("4000000.00"),
                district="Chennai",
                city="Chennai",
                taluk="Guindy",
                locality="Guindy",
                pincode="600032",
                status="PUBLISHED",
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id
    return prop_id


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    email = f"consultant-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantSecurePass123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Chief Consultant",
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
async def non_consultant_auth(client: AsyncClient):
    """User with a non-consultant role."""
    email = f"guest-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "GuestSecurePass123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Guest User",
                role="GUEST",
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
async def test_unauthenticated_requests_blocked(client: AsyncClient, sample_property: uuid.UUID):
    """Verify all preliminary verification endpoints reject unauthenticated requests with 401."""
    fake_id = uuid.uuid4()

    res = await client.post(f"/api/v1/properties/{sample_property}/verification", json={})
    assert res.status_code == 401

    res = await client.get(f"/api/v1/properties/{sample_property}/verification")
    assert res.status_code == 401

    res = await client.get(f"/api/v1/verifications/{fake_id}")
    assert res.status_code == 401

    res = await client.get("/api/v1/verifications")
    assert res.status_code == 401

    res = await client.patch(f"/api/v1/verifications/{fake_id}", json={})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_non_consultant_role_forbidden(
    client: AsyncClient, non_consultant_auth: dict, sample_property: uuid.UUID
):
    """Verify non-consultant users receive 403 Forbidden on verification endpoints."""
    fake_id = uuid.uuid4()

    res = await client.post(
        f"/api/v1/properties/{sample_property}/verification",
        json={},
        headers=non_consultant_auth,
    )
    assert res.status_code == 403

    res = await client.get(
        f"/api/v1/properties/{sample_property}/verification",
        headers=non_consultant_auth,
    )
    assert res.status_code == 403

    res = await client.get(
        f"/api/v1/verifications/{fake_id}",
        headers=non_consultant_auth,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_tamper_with_computed_risk_or_status(
    client: AsyncClient, consultant_auth: dict, sample_property: uuid.UUID
):
    """Verify client attempts to submit status='COMPLETED' and risk_level='LOW' are ignored.

    The backend MUST compute status and risk level deterministically from evidence.
    """
    tampered_payload = {
        "status": "COMPLETED",
        "risk_level": "LOW",
        "verified": True,
        # Property has NO deed, NO EC, NO patta, and NO survey number submitted
        "consultant_notes": "Attempting client tamper",
    }

    res = await client.post(
        f"/api/v1/properties/{sample_property}/verification",
        json=tampered_payload,
        headers=consultant_auth,
    )
    assert res.status_code == 201
    data = res.json()["data"]

    # Backend MUST determine HIGH risk and NEEDS_REVIEW due to missing critical documents
    assert data["risk_level"] == "HIGH"
    assert data["status"] == "NEEDS_REVIEW"
    assert "CRITICAL_REQUIRED_EVIDENCE_MISSING" in data["risk_flags"]


@pytest.mark.asyncio
async def test_evidence_traces_do_not_leak_raw_storage_keys(
    client: AsyncClient, consultant_auth: dict, sample_property: uuid.UUID
):
    """Verify check evidence items never leak raw filesystem paths or storage keys."""
    res = await client.post(
        f"/api/v1/properties/{sample_property}/verification",
        json={},
        headers=consultant_auth,
    )
    assert res.status_code == 201
    body_text = res.text

    # Verify no raw storage keys or system paths appear
    assert "storage_key" not in body_text
    assert "C:\\" not in body_text
    assert "s3://" not in body_text
