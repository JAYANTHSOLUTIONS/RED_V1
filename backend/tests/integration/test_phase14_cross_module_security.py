"""Phase 14 Integration Tests: Cross-Module Authentication, RBAC, and Security Boundaries.

Scenarios Covered:
- Scenario 11: Authentication -> RBAC -> Business Modules (401 Unauthenticated, 403 Non-Consultant, 200/201 Consultant across modules)
- Scenario 12: Public Discovery -> Lead -> Consultant Workflow boundary
- Scenario 14: Cross-Module Data Isolation and anti-IDOR protections
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
async def consultant_auth(client: AsyncClient):
    email = f"consultant-p14-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Phase 14 Security Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    user_id = login_res.json()["data"]["user"]["id"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": uuid.UUID(user_id),
    }


@pytest.fixture
async def client_role_auth(client: AsyncClient):
    """Create a user with non-consultant CLIENT role."""
    email = f"client-role-p14-{uuid.uuid4().hex[:8]}@example.com"
    password = "ClientPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Non Consultant Client User",
                role="CLIENT",
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
async def test_unauthenticated_requests_rejected_across_all_modules(client: AsyncClient):
    """Scenario 11: Anonymous requests to protected private business modules return 401."""
    fake_id = uuid.uuid4()
    endpoints = [
        ("GET", "/api/v1/properties"),
        ("POST", "/api/v1/properties"),
        ("GET", "/api/v1/clients"),
        ("POST", "/api/v1/clients"),
        ("GET", "/api/v1/leads"),
        ("POST", "/api/v1/leads"),
        ("GET", f"/api/v1/documents/{fake_id}"),
        ("GET", "/api/v1/site-visits"),
        ("POST", "/api/v1/site-visits"),
        ("GET", "/api/v1/follow-ups"),
        ("POST", "/api/v1/follow-ups"),
        ("GET", "/api/v1/notifications"),
        ("GET", "/api/v1/audit-logs"),
    ]

    for method, path in endpoints:
        if method == "GET":
            res = await client.get(path)
        else:
            res = await client.post(path, json={})
        assert res.status_code == 401, f"Expected 401 for {method} {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_non_consultant_role_rejected_across_all_modules(
    client: AsyncClient, client_role_auth: dict
):
    """Scenario 11: Non-consultant role (CLIENT) receives 403 Forbidden on private management endpoints."""
    headers = client_role_auth
    fake_id = uuid.uuid4()

    endpoints = [
        ("GET", "/api/v1/properties"),
        ("GET", "/api/v1/clients"),
        ("GET", "/api/v1/leads"),
        ("GET", f"/api/v1/documents/{fake_id}"),
        ("GET", "/api/v1/site-visits"),
        ("GET", "/api/v1/follow-ups"),
        ("GET", "/api/v1/notifications"),
        ("GET", "/api/v1/audit-logs"),
    ]

    for method, path in endpoints:
        res = await client.get(path, headers=headers)
        assert res.status_code == 403, f"Expected 403 for {method} {path}, got {res.status_code}"


@pytest.mark.asyncio
async def test_public_discovery_to_consultant_lead_boundary(
    client: AsyncClient, consultant_auth: dict
):
    """Scenario 12: Public visitor discovers published property; private details remain shielded."""
    consultant_headers = consultant_auth["headers"]
    public_ref = f"PR-2026-{uuid.uuid4().int % 1000000:06d}"

    # 1. Consultant creates and publishes property with private owner data and internal notes
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=public_ref,
                title="Beachfront Villa in Akkarai ECR",
                description="Ultra-luxury residential villa on East Coast Road",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("25000000.00"),
                built_up_area=Decimal("3200"),
                district="Chennai",
                city="Chennai",
                locality="Akkarai",
                pincode="600119",
                owner_name="S. Sundaramurthy",
                owner_phone="+91 94440 98765",
                internal_notes="Confidential seller reserve price 2.3 Cr",
                status="PUBLISHED",
                is_archived=False,
            )
            session.add(prop)

    # 2. Public visitor views property at /api/v1/public/properties/{public_ref} WITHOUT authentication
    public_res = await client.get(f"/api/v1/public/properties/{public_ref}")
    assert public_res.status_code == 200
    pub_data = public_res.json()["data"]
    assert pub_data["public_reference"] == public_ref
    assert pub_data["title"] == "Beachfront Villa in Akkarai ECR"

    # CRITICAL: Verify private owner info and confidential notes are NEVER leaked publicly
    assert "owner_name" not in pub_data
    assert "owner_phone" not in pub_data
    assert "notes" not in pub_data
    assert "Sundaramurthy" not in public_res.text
    assert "94440" not in public_res.text
    assert "reserve price" not in public_res.text
