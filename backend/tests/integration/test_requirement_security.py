"""Security tests for Property Requirement Management and Matching API.

Verifies:
- Unauthenticated requests are rejected (401)
- Non-consultant roles are forbidden (403)
- No public requirement endpoints exist (404)
- Zero leakage of client PII or sensitive owner/seller data in matching results
"""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.client import Client
from app.models.property import Property
from app.models.requirement import PropertyRequirement
from app.models.user import User


@pytest.fixture
async def regular_user_headers(client: AsyncClient):
    email = f"regular-user-req-{uuid.uuid4().hex[:8]}@example.com"
    password = "UserPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Regular User",
                role="USER",
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
async def consultant_headers(client: AsyncClient):
    email = f"consultant-sec-req-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant Sec",
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
async def test_unauthenticated_requests_rejected(client: AsyncClient):
    random_id = uuid.uuid4()
    endpoints = [
        ("GET", "/api/v1/property-requirements"),
        ("POST", "/api/v1/property-requirements"),
        ("GET", f"/api/v1/property-requirements/{random_id}"),
        ("PATCH", f"/api/v1/property-requirements/{random_id}"),
        ("POST", f"/api/v1/property-requirements/{random_id}/fulfill"),
        ("POST", f"/api/v1/property-requirements/{random_id}/cancel"),
        ("POST", f"/api/v1/property-requirements/{random_id}/archive"),
        ("GET", f"/api/v1/property-requirements/{random_id}/matches"),
    ]

    for method, endpoint in endpoints:
        res = await client.request(method, endpoint)
        assert res.status_code == 401, f"{method} {endpoint} did not return 401"
        assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_non_consultant_forbidden(
    client: AsyncClient, regular_user_headers: dict
):
    random_id = uuid.uuid4()
    endpoints = [
        ("GET", "/api/v1/property-requirements"),
        ("POST", "/api/v1/property-requirements"),
        ("GET", f"/api/v1/property-requirements/{random_id}"),
        ("PATCH", f"/api/v1/property-requirements/{random_id}"),
        ("POST", f"/api/v1/property-requirements/{random_id}/fulfill"),
        ("POST", f"/api/v1/property-requirements/{random_id}/cancel"),
        ("POST", f"/api/v1/property-requirements/{random_id}/archive"),
        ("GET", f"/api/v1/property-requirements/{random_id}/matches"),
    ]

    for method, endpoint in endpoints:
        res = await client.request(method, endpoint, headers=regular_user_headers)
        assert res.status_code == 403, f"{method} {endpoint} did not return 403"
        assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_no_public_requirement_endpoints(client: AsyncClient):
    res = await client.get("/api/v1/public/property-requirements")
    assert res.status_code == 404

    res2 = await client.post("/api/v1/public/property-requirements")
    assert res2.status_code == 404


@pytest.mark.asyncio
async def test_matching_data_isolation(
    client: AsyncClient, consultant_headers: dict
):
    ref_code = f"REF-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            c = Client(
                full_name="Secret Buyer",
                phone="+91 9123456780",
                email="secret.buyer@example.com",
                notes="Confidential high-net-worth client",
            )
            session.add(c)
            await session.flush()

            p = Property(
                public_reference=ref_code,
                title="Private Villa with Internal Notes",
                description="Public description",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("10000000"),
                built_up_area=Decimal("2500"),
                area_unit="sq.ft",
                district="Chennai",
                city="Chennai",
                locality="ECR",
                pincode="600119",
                owner_name="Confidential Owner",
                owner_phone="+91 9999999999",
                owner_email="owner@confidential.com",
                internal_notes="Secret seller notes",
                status="PUBLISHED",
                is_archived=False,
            )
            session.add(p)
            await session.flush()

            req = PropertyRequirement(
                client_id=c.id,
                transaction_type="BUY",
                property_types="RESIDENTIAL_VILLA",
                min_budget=Decimal("9000000"),
                max_budget=Decimal("12000000"),
                status="ACTIVE",
            )
            session.add(req)
            await session.flush()
            req_id = req.id

    res = await client.get(
        f"/api/v1/property-requirements/{req_id}/matches",
        headers=consultant_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]["items"]
    assert len(data) >= 1

    # Verify no leak of client PII or private owner data in matching candidate object
    match_item = data[0]
    assert "property" in match_item
    matched_prop = match_item["property"]

    # Verify expected sanitized fields only
    expected_fields = {
        "id", "public_reference", "title", "property_type", "transaction_type",
        "price", "price_negotiable", "built_up_area", "plot_area", "area_unit",
        "bedrooms", "bathrooms", "facing", "furnishing_state", "parking_spaces",
        "district", "city", "locality", "status"
    }
    assert set(matched_prop.keys()) == expected_fields
    assert "client" not in match_item
    assert "owner_name" not in matched_prop
    assert "owner_phone" not in matched_prop
    assert "owner_email" not in matched_prop
    assert "internal_notes" not in matched_prop
