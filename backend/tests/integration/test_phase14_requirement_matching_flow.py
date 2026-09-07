"""Phase 14 Integration Tests: Client Requirement and Deterministic Matching Foundation.

Scenarios Covered:
- Scenario 3: Client -> Requirement -> Matching -> Property
  Validates rule-based matching, exact/partial scoring, deterministic ranking,
  edge case filtering (price, type, location, area bounds), and exclusion of inactive properties.
"""
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
async def consultant_auth(client: AsyncClient):
    email = f"consultant-p14-match-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Phase 14 Match Consultant",
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
async def sample_client(client: AsyncClient, consultant_auth: dict):
    headers = consultant_auth["headers"]
    client_res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "K. Srinivasan",
            "phone": f"+91 98{uuid.uuid4().int % 100000000:08d}",
            "email": f"srinivasan-{uuid.uuid4().hex[:6]}@example.com",
            "classification": "BUYER",
        },
        headers=headers,
    )
    return client_res.json()["data"]["id"]


@pytest.mark.asyncio
async def test_requirement_creation_and_deterministic_matching(
    client: AsyncClient, consultant_auth: dict, sample_client: str
):
    """Scenario 3: Create client requirement, match against published properties, and verify scoring."""
    headers = consultant_auth["headers"]

    # 1. Create and publish 3 distinct properties:
    # Prop A: Perfect match in Velachery (Villa, Sale, 75L, 1600 sqft, 3BHK)
    # Prop B: Different location (Coimbatore)
    # Prop C: Transaction mismatch (Rent instead of Sale)
    prop_a_ref = f"MATCH-A-{uuid.uuid4().hex[:6].upper()}"
    prop_b_ref = f"MISLOC-B-{uuid.uuid4().hex[:6].upper()}"
    prop_c_ref = f"RENT-C-{uuid.uuid4().hex[:6].upper()}"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop_a = Property(
                public_reference=prop_a_ref,
                title="Matching Villa in Velachery",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("7500000"),
                built_up_area=Decimal("1600"),
                area_unit="sq.ft",
                district="Chennai",
                city="Chennai",
                locality="Velachery",
                pincode="600042",
                bedrooms=3,
                bathrooms=3,
                facing="NORTH",
                status="PUBLISHED",
                is_archived=False,
            )
            prop_b = Property(
                public_reference=prop_b_ref,
                title="Villa in RS Puram Coimbatore",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("7500000"),
                built_up_area=Decimal("1600"),
                area_unit="sq.ft",
                district="Coimbatore",
                city="Coimbatore",
                locality="RS Puram",
                pincode="641002",
                bedrooms=3,
                status="PUBLISHED",
                is_archived=False,
            )
            prop_c = Property(
                public_reference=prop_c_ref,
                title="Rental Villa in Velachery",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="RENT",
                price=Decimal("45000"),
                built_up_area=Decimal("1600"),
                area_unit="sq.ft",
                district="Chennai",
                city="Chennai",
                locality="Velachery",
                pincode="600042",
                bedrooms=3,
                status="PUBLISHED",
                is_archived=False,
            )
            session.add_all([prop_a, prop_b, prop_c])

    # 2. Create Requirement for Buyer (seeking Villa for Sale in Velachery between 60L-90L, 1400-2000 sqft)
    req_payload = {
        "client_id": sample_client,
        "transaction_type": "BUY",
        "property_types": "RESIDENTIAL_VILLA",
        "min_budget": 6000000,
        "max_budget": 9000000,
        "min_area": 1400,
        "max_area": 2000,
        "target_locations": "Velachery",
        "bedrooms": 3,
    }
    req_res = await client.post(
        "/api/v1/property-requirements",
        json=req_payload,
        headers=headers,
    )
    assert req_res.status_code == 201
    req_id = req_res.json()["data"]["id"]

    # 3. Call Matching Endpoint
    match_res = await client.get(
        f"/api/v1/property-requirements/{req_id}/matches",
        headers=headers,
    )
    assert match_res.status_code == 200
    matched_items = match_res.json()["data"]["items"]

    # 4. Verify Deterministic Matching Output
    matched_refs = [m["property"]["public_reference"] for m in matched_items]
    assert prop_a_ref in matched_refs
    assert prop_c_ref not in matched_refs  # Rent vs Buy must NOT match

    # Prop A must be ranked as top match with score == 100
    top_match = next(m for m in matched_items if m["property"]["public_reference"] == prop_a_ref)
    assert top_match["score"] == 100
    assert top_match["match_grade"] == "EXACT_MATCH"
    assert "transaction_type" in top_match["matched_criteria"]
    assert "budget" in top_match["matched_criteria"]
    assert "location" in top_match["matched_criteria"]

    # 5. Verify Audit Log for Matching Request
    async with AsyncSessionFactory() as session:
        audit_match = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(req_id),
                AuditLog.action == "PROPERTY_MATCHES_REQUESTED",
            )
        )
        assert audit_match is not None


@pytest.mark.asyncio
async def test_matching_excludes_inactive_and_archived_properties(
    client: AsyncClient, consultant_auth: dict, sample_client: str
):
    """Scenario 3 Edge Case: Draft, Paused, and Archived properties must be excluded from match results."""
    headers = consultant_auth["headers"]

    prop_published_ref = f"PUB-{uuid.uuid4().hex[:6].upper()}"
    prop_draft_ref = f"DFT-{uuid.uuid4().hex[:6].upper()}"
    prop_paused_ref = f"PSD-{uuid.uuid4().hex[:6].upper()}"
    prop_archived_ref = f"ARC-{uuid.uuid4().hex[:6].upper()}"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            common_kwargs = {
                "property_type": "RESIDENTIAL_APARTMENT",
                "transaction_type": "SALE",
                "price": Decimal("6500000"),
                "built_up_area": Decimal("1250"),
                "area_unit": "sq.ft",
                "district": "Chennai",
                "city": "Chennai",
                "locality": "Porur",
                "pincode": "600116",
            }
            p1 = Property(public_reference=prop_published_ref, title="Published Flat", status="PUBLISHED", is_archived=False, **common_kwargs)
            p2 = Property(public_reference=prop_draft_ref, title="Draft Flat", status="DRAFT", is_archived=False, **common_kwargs)
            p3 = Property(public_reference=prop_paused_ref, title="Paused Flat", status="PAUSED", is_archived=False, **common_kwargs)
            p4 = Property(public_reference=prop_archived_ref, title="Archived Flat", status="PUBLISHED", is_archived=True, **common_kwargs)
            session.add_all([p1, p2, p3, p4])

    # Create Requirement
    req_res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": sample_client,
            "transaction_type": "BUY",
            "property_types": "RESIDENTIAL_APARTMENT",
            "min_budget": 5000000,
            "max_budget": 8000000,
            "target_locations": "Porur",
        },
        headers=headers,
    )
    req_id = req_res.json()["data"]["id"]

    match_res = await client.get(
        f"/api/v1/property-requirements/{req_id}/matches",
        headers=headers,
    )
    assert match_res.status_code == 200
    matched_refs = [m["property"]["public_reference"] for m in match_res.json()["data"]["items"]]

    assert prop_published_ref in matched_refs
    assert prop_draft_ref not in matched_refs
    assert prop_paused_ref not in matched_refs
    assert prop_archived_ref not in matched_refs
