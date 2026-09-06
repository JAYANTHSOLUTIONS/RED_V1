"""Integration tests for Property Requirement Management and Matching API."""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.property import Property
from app.models.user import User


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-req-test-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Req Test Consultant",
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
async def sample_client(auth_headers: dict, client: AsyncClient):
    payload = {
        "full_name": "Requirement Buyer",
        "phone": f"+91 99{uuid.uuid4().int % 100000000:08d}",
        "email": f"buyer-{uuid.uuid4().hex[:6]}@example.com",
        "classification": "BUYER",
    }
    res = await client.post("/api/v1/clients", json=payload, headers=auth_headers)
    assert res.status_code == 201
    return res.json()["data"]


@pytest.mark.asyncio
async def test_create_and_get_requirement(
    client: AsyncClient, auth_headers: dict, sample_client: dict
):
    payload = {
        "client_id": sample_client["id"],
        "transaction_type": "BUY",
        "property_types": "RESIDENTIAL_APARTMENT",
        "min_budget": 4500000,
        "max_budget": 6000000,
        "min_area": 900,
        "max_area": 1300,
        "target_locations": "Velachery, Chennai",
        "bedrooms": 2,
        "bathrooms": 2,
        "facing": "EAST",
        "furnishing_state": "SEMI_FURNISHED",
        "notes": "Near railway station preferred",
    }
    create_res = await client.post(
        "/api/v1/property-requirements", json=payload, headers=auth_headers
    )
    assert create_res.status_code == 201
    body = create_res.json()
    assert body["success"] is True
    data = body["data"]
    req_id = data["id"]
    assert data["client_id"] == sample_client["id"]
    assert data["transaction_type"] == "BUY"
    assert data["property_types"] == "RESIDENTIAL_APARTMENT"
    assert data["status"] == "ACTIVE"
    assert data["client"]["full_name"] == sample_client["full_name"]

    # Verify audit log was recorded
    async with AsyncSessionFactory() as session:
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(req_id),
                AuditLog.action == "PROPERTY_REQUIREMENT_CREATED",
            )
        )
        assert audit is not None

    # Retrieve by ID
    get_res = await client.get(
        f"/api/v1/property-requirements/{req_id}", headers=auth_headers
    )
    assert get_res.status_code == 200
    get_data = get_res.json()["data"]
    assert get_data["id"] == req_id
    assert get_data["target_locations"] == "Velachery, Chennai"


@pytest.mark.asyncio
async def test_list_and_filter_requirements(
    client: AsyncClient, auth_headers: dict, sample_client: dict
):
    # Create requirement 1 (BUY, RESIDENTIAL_APARTMENT)
    await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": sample_client["id"],
            "transaction_type": "BUY",
            "property_types": "RESIDENTIAL_APARTMENT",
            "min_budget": 3000000,
            "max_budget": 5000000,
        },
        headers=auth_headers,
    )

    # Create requirement 2 (RENT, COMMERCIAL_OFFICE)
    await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": sample_client["id"],
            "transaction_type": "RENT",
            "property_types": "COMMERCIAL_OFFICE",
            "min_budget": 20000,
            "max_budget": 40000,
        },
        headers=auth_headers,
    )

    # List all for client
    res = await client.get(
        f"/api/v1/property-requirements?client_id={sample_client['id']}",
        headers=auth_headers,
    )
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    assert len(items) >= 2

    # Filter by transaction_type=RENT
    rent_res = await client.get(
        f"/api/v1/property-requirements?client_id={sample_client['id']}&transaction_type=RENT",
        headers=auth_headers,
    )
    assert rent_res.status_code == 200
    rent_items = rent_res.json()["data"]["items"]
    assert len(rent_items) == 1
    assert rent_items[0]["transaction_type"] == "RENT"


@pytest.mark.asyncio
async def test_update_requirement(
    client: AsyncClient, auth_headers: dict, sample_client: dict
):
    create_res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": sample_client["id"],
            "transaction_type": "BUY",
            "property_types": "RESIDENTIAL_LAND",
            "min_budget": 2000000,
            "max_budget": 3000000,
        },
        headers=auth_headers,
    )
    req_id = create_res.json()["data"]["id"]

    # Update budget & location
    update_res = await client.patch(
        f"/api/v1/property-requirements/{req_id}",
        json={
            "min_budget": 2500000,
            "max_budget": 3500000,
            "target_locations": "Tambaram, Chennai",
        },
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert Decimal(updated_data["min_budget"]) == Decimal("2500000")
    assert Decimal(updated_data["max_budget"]) == Decimal("3500000")
    assert updated_data["target_locations"] == "Tambaram, Chennai"

    # Verify audit log
    async with AsyncSessionFactory() as session:
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(req_id),
                AuditLog.action == "PROPERTY_REQUIREMENT_UPDATED",
            )
        )
        assert audit is not None


@pytest.mark.asyncio
async def test_lifecycle_fulfill_cancel_archive(
    client: AsyncClient, auth_headers: dict, sample_client: dict
):
    # Test Fulfill
    res1 = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": sample_client["id"],
            "transaction_type": "BUY",
            "property_types": "RESIDENTIAL_APARTMENT",
        },
        headers=auth_headers,
    )
    req1_id = res1.json()["data"]["id"]

    fulfill_res = await client.post(
        f"/api/v1/property-requirements/{req1_id}/fulfill", headers=auth_headers
    )
    assert fulfill_res.status_code == 200
    assert fulfill_res.json()["data"]["status"] == "FULFILLED"

    # Test Cancel
    res2 = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": sample_client["id"],
            "transaction_type": "BUY",
            "property_types": "RESIDENTIAL_APARTMENT",
        },
        headers=auth_headers,
    )
    req2_id = res2.json()["data"]["id"]

    cancel_res = await client.post(
        f"/api/v1/property-requirements/{req2_id}/cancel", headers=auth_headers
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "CANCELLED"

    # Test Archive
    res3 = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": sample_client["id"],
            "transaction_type": "BUY",
            "property_types": "RESIDENTIAL_APARTMENT",
        },
        headers=auth_headers,
    )
    req3_id = res3.json()["data"]["id"]

    archive_res = await client.post(
        f"/api/v1/property-requirements/{req3_id}/archive", headers=auth_headers
    )
    assert archive_res.status_code == 200
    data3 = archive_res.json()["data"]
    assert data3["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_requirement_matching_endpoint(
    client: AsyncClient, auth_headers: dict, sample_client: dict
):
    # Create properties:
    # 1. Published matching property
    # 2. Draft property (must be excluded even if matching)
    matching_ref = f"REF-{uuid.uuid4().hex[:8].upper()}"
    draft_ref = f"REF-{uuid.uuid4().hex[:8].upper()}"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            matching_prop = Property(
                public_reference=matching_ref,
                title="Matching Adyar Villa",
                description="Luxury villa in Adyar",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("7000000"),
                built_up_area=Decimal("1500"),
                area_unit="sq.ft",
                district="Chennai",
                city="Chennai",
                locality="Adyar",
                pincode="600020",
                bedrooms=3,
                bathrooms=3,
                facing="EAST",
                furnishing_state="SEMI_FURNISHED",
                status="PUBLISHED",
                is_archived=False,
            )
            draft_prop = Property(
                public_reference=draft_ref,
                title="Draft Adyar Villa",
                description="Draft villa",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("7000000"),
                built_up_area=Decimal("1500"),
                area_unit="sq.ft",
                district="Chennai",
                city="Chennai",
                locality="Adyar",
                pincode="600020",
                bedrooms=3,
                bathrooms=3,
                facing="EAST",
                furnishing_state="SEMI_FURNISHED",
                status="DRAFT",
                is_archived=False,
            )
            session.add_all([matching_prop, draft_prop])

    # Create requirement
    req_res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": sample_client["id"],
            "transaction_type": "BUY",
            "property_types": "RESIDENTIAL_VILLA",
            "min_budget": 6000000,
            "max_budget": 8000000,
            "min_area": 1200,
            "max_area": 1800,
            "target_locations": "Adyar",
            "bedrooms": 3,
            "bathrooms": 3,
            "facing": "EAST",
            "furnishing_state": "SEMI_FURNISHED",
        },
        headers=auth_headers,
    )
    req_id = req_res.json()["data"]["id"]

    # Call matching endpoint
    matches_res = await client.get(
        f"/api/v1/property-requirements/{req_id}/matches",
        headers=auth_headers,
    )
    assert matches_res.status_code == 200
    matches_body = matches_res.json()
    assert matches_body["success"] is True
    paginated_data = matches_body["data"]
    items = paginated_data["items"]

    # The matching_prop must be in items, draft_prop must NOT
    refs = [m["property"]["public_reference"] for m in items]
    assert matching_ref in refs
    assert draft_ref not in refs

    # Inspect the exact match
    top_match = next(m for m in items if m["property"]["public_reference"] == matching_ref)
    assert top_match["score"] == 100
    assert top_match["match_grade"] == "EXACT_MATCH"
    assert "transaction_type" in top_match["matched_criteria"]
    assert "budget" in top_match["matched_criteria"]
    assert "area" in top_match["matched_criteria"]
    assert "location" in top_match["matched_criteria"]
    assert len(top_match["unmatched_criteria"]) == 0

    # Verify audit log for matches requested
    async with AsyncSessionFactory() as session:
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(req_id),
                AuditLog.action == "PROPERTY_MATCHES_REQUESTED",
            )
        )
        assert audit is not None
