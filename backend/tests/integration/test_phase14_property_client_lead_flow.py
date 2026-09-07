"""Phase 14 Integration Tests: Property, Client, and Lead cross-module workflows.

Scenarios Covered:
- Scenario 1: Consultant -> Property -> Audit (Creation, mutation, diffs, audit trail)
- Scenario 2: Property + Client -> Lead (Relationship integrity, orphan prevention, invalid associations)
"""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.lead import Lead
from app.models.property import Property
from app.models.user import User


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    """Authenticate a test consultant user."""
    email = f"consultant-p14-pcl-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Phase 14 PCL Consultant",
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


@pytest.mark.asyncio
async def test_consultant_creates_and_updates_property_with_audit_trail(
    client: AsyncClient, consultant_auth: dict
):
    """Scenario 1: Authenticated consultant creates property, updates it, and verifies audit events."""
    headers = consultant_auth["headers"]
    user_id = consultant_auth["user_id"]
    correlation_id = f"corr-prop-{uuid.uuid4().hex[:8]}"

    # 1. Create Property
    prop_payload = {
        "title": "Luxury 3BHK Apartment in OMR Sholinganallur",
        "description": "Modern apartment near IT corridor",
        "property_type": "RESIDENTIAL_APARTMENT",
        "transaction_type": "SALE",
        "price": 8500000.00,
        "built_up_area": 1450.00,
        "carpet_area": 1200.00,
        "area_unit": "sq.ft",
        "district": "Chennai",
        "city": "Chennai",
        "locality": "Sholinganallur",
        "pincode": "600119",
        "bedrooms": 3,
        "bathrooms": 3,
        "facing": "EAST",
        "owner_name": "K. Balachander",
        "owner_phone": "+91 9840112233",
        "notes": "Direct owner mandate",
    }
    create_res = await client.post(
        "/api/v1/properties",
        json=prop_payload,
        headers={**headers, "X-Request-ID": correlation_id},
    )
    assert create_res.status_code == 201
    prop_data = create_res.json()["data"]
    prop_id = prop_data["id"]
    assert prop_data["title"] == prop_payload["title"]
    assert prop_data["status"] == "DRAFT"
    assert prop_data["is_archived"] is False

    # 2. Verify Audit Log for Creation
    async with AsyncSessionFactory() as session:
        audit_create = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(prop_id),
                AuditLog.action == "PROPERTY_CREATED",
            )
        )
        assert audit_create is not None
        assert audit_create.actor_id == user_id
        assert audit_create.entity_type == "PROPERTY"
        assert audit_create.correlation_id == correlation_id
        assert "title" in (audit_create.change_diff or "")
        assert "price" in (audit_create.change_diff or "")

    # 3. Update Property (Price & Title revision)
    update_res = await client.patch(
        f"/api/v1/properties/{prop_id}",
        json={
            "price": 8200000.00,
            "title": "Revised Luxury 3BHK Apartment in OMR Sholinganallur",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert float(updated_data["price"]) == 8200000.00

    # 4. Verify Audit Log for Update reflects mutation diff
    async with AsyncSessionFactory() as session:
        audit_update = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(prop_id),
                AuditLog.action == "PROPERTY_UPDATED",
            )
        )
        assert audit_update is not None
        assert audit_update.actor_id == user_id
        assert "price" in (audit_update.change_diff or "")


@pytest.mark.asyncio
async def test_property_client_lead_relationship_flow(
    client: AsyncClient, consultant_auth: dict
):
    """Scenario 2: Property + Client -> Lead end-to-end relationship verification."""
    headers = consultant_auth["headers"]
    user_id = consultant_auth["user_id"]

    # 1. Create Property
    prop_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Independent House in Anna Nagar West",
            "property_type": "RESIDENTIAL_VILLA",
            "transaction_type": "SALE",
            "price": 17500000.00,
            "district": "Chennai",
            "city": "Chennai",
            "locality": "Anna Nagar",
            "pincode": "600040",
        },
        headers=headers,
    )
    assert prop_res.status_code == 201
    prop_id = prop_res.json()["data"]["id"]

    # 2. Create Client
    client_res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Dr. R. Natarajan",
            "phone": f"+91 94{uuid.uuid4().int % 100000000:08d}",
            "email": f"natarajan-{uuid.uuid4().hex[:6]}@example.com",
            "classification": "BUYER",
            "notes": "Senior consultant seeking residential house in Anna Nagar",
        },
        headers=headers,
    )
    assert client_res.status_code == 201
    client_id = client_res.json()["data"]["id"]

    # 3. Create Lead linking Client and Property
    lead_res = await client.post(
        "/api/v1/leads",
        json={
            "client_id": client_id,
            "property_id": prop_id,
            "source": "DIRECT_CALL",
            "notes": "Enquired specifically about Anna Nagar house",
        },
        headers=headers,
    )
    assert lead_res.status_code == 201
    lead_data = lead_res.json()["data"]
    lead_id = lead_data["id"]
    assert lead_data["client_id"] == client_id
    assert lead_data["property_id"] == prop_id
    assert lead_data["status"] == "NEW"

    # 4. Fetch Lead details and verify relations without orphans
    get_lead_res = await client.get(f"/api/v1/leads/{lead_id}", headers=headers)
    assert get_lead_res.status_code == 200
    lead_detail = get_lead_res.json()["data"]
    assert lead_detail["client"]["id"] == client_id
    assert lead_detail["client"]["full_name"] == "Dr. R. Natarajan"
    assert lead_detail["property"]["id"] == prop_id
    assert lead_detail["property"]["locality"] == "Anna Nagar"

    # 5. Fetch Client details and verify associated leads list
    get_client_res = await client.get(f"/api/v1/clients/{client_id}", headers=headers)
    assert get_client_res.status_code == 200
    client_detail = get_client_res.json()["data"]
    lead_ids_in_client = [l["id"] for l in client_detail.get("leads", [])]
    assert lead_id in lead_ids_in_client

    # 6. Verify audit records for all entities
    async with AsyncSessionFactory() as session:
        lead_audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(lead_id),
                AuditLog.action == "LEAD_CREATED",
            )
        )
        assert lead_audit is not None
        assert lead_audit.actor_id == user_id


@pytest.mark.asyncio
async def test_property_client_lead_invalid_associations(
    client: AsyncClient, consultant_auth: dict
):
    """Scenario 2 Edge Cases: Rejection of nonexistent and archived entity associations."""
    headers = consultant_auth["headers"]

    # Create active client
    client_res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Valid Buyer Client",
            "phone": f"+91 97{uuid.uuid4().int % 100000000:08d}",
            "classification": "BUYER",
        },
        headers=headers,
    )
    valid_client_id = client_res.json()["data"]["id"]

    # Create active property
    prop_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Valid Property For Associations",
            "property_type": "COMMERCIAL_RETAIL",
            "transaction_type": "LEASE",
            "price": 120000.00,
            "district": "Chennai",
            "city": "Chennai",
            "locality": "T. Nagar",
            "pincode": "600017",
        },
        headers=headers,
    )
    valid_prop_id = prop_res.json()["data"]["id"]

    # 1. Nonexistent property_id -> 404
    res_bad_prop = await client.post(
        "/api/v1/leads",
        json={
            "client_id": valid_client_id,
            "property_id": str(uuid.uuid4()),
            "source": "WEBSITE",
        },
        headers=headers,
    )
    assert res_bad_prop.status_code == 404

    # 2. Nonexistent client_id -> 404
    res_bad_client = await client.post(
        "/api/v1/leads",
        json={
            "client_id": str(uuid.uuid4()),
            "property_id": valid_prop_id,
            "source": "WEBSITE",
        },
        headers=headers,
    )
    assert res_bad_client.status_code == 404

    # 3. Archive property and attempt linking -> 422
    archive_prop_res = await client.post(
        f"/api/v1/properties/{valid_prop_id}/archive",
        headers=headers,
    )
    assert archive_prop_res.status_code == 200

    res_archived_prop = await client.post(
        "/api/v1/leads",
        json={
            "client_id": valid_client_id,
            "property_id": valid_prop_id,
            "source": "WEBSITE",
        },
        headers=headers,
    )
    assert res_archived_prop.status_code == 422
    assert "archived" in res_archived_prop.json()["error"]["message"].lower()

    # 4. Archive client and attempt linking -> 422
    archive_client_res = await client.post(
        f"/api/v1/clients/{valid_client_id}/archive",
        headers=headers,
    )
    assert archive_client_res.status_code == 200

    res_archived_client = await client.post(
        "/api/v1/leads",
        json={
            "client_id": valid_client_id,
            "source": "WEBSITE",
        },
        headers=headers,
    )
    assert res_archived_client.status_code == 422
    assert "archived" in res_archived_client.json()["error"]["message"].lower()
