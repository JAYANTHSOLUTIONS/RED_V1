"""Integration tests for Lead Management API endpoints."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.user import User


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-lead-test-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Lead Test Consultant",
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
async def test_client_id(client: AsyncClient, auth_headers: dict) -> str:
    res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Lead Test Client", "phone": "+91 9555500001"},
        headers=auth_headers,
    )
    return res.json()["data"]["id"]


@pytest.fixture
async def test_property_id(client: AsyncClient, auth_headers: dict) -> str:
    res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Lead Test Property",
            "property_type": "Apartment",
            "transaction_type": "SALE",
            "price": "7500000.00",
            "district": "Chennai",
            "city": "Chennai",
            "locality": "Adyar",
            "pincode": "600020",
        },
        headers=auth_headers,
    )
    return res.json()["data"]["id"]


@pytest.mark.asyncio
async def test_create_and_get_lead(
    client: AsyncClient, auth_headers: dict, test_client_id: str, test_property_id: str
):
    payload = {
        "client_id": test_client_id,
        "property_id": test_property_id,
        "source": "WEBSITE",
        "notes": "Enquired through website property listing",
    }
    create_res = await client.post("/api/v1/leads", json=payload, headers=auth_headers)
    assert create_res.status_code == 201
    data = create_res.json()["data"]
    lead_id = data["id"]
    assert data["status"] == "NEW"
    assert data["client_id"] == test_client_id
    assert data["property_id"] == test_property_id
    assert data["client"]["full_name"] == "Lead Test Client"
    assert data["property"]["title"] == "Lead Test Property"

    # Verify client detail includes this lead
    client_res = await client.get(f"/api/v1/clients/{test_client_id}", headers=auth_headers)
    assert client_res.status_code == 200
    leads_list = client_res.json()["data"]["leads"]
    assert any(ld["id"] == lead_id for ld in leads_list)

    # Verify audit log
    async with AsyncSessionFactory() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(lead_id),
                AuditLog.action == "LEAD_CREATED",
            )
        )
        assert audit_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_lead_full_lifecycle_conversion(
    client: AsyncClient, auth_headers: dict, test_client_id: str
):
    """Verify progressive lifecycle: NEW -> CONTACTED -> INTERESTED -> SITE_VISIT -> NEGOTIATION -> CONVERTED."""
    create_res = await client.post(
        "/api/v1/leads",
        json={"client_id": test_client_id, "source": "DIRECT_CALL"},
        headers=auth_headers,
    )
    lead_id = create_res.json()["data"]["id"]
    assert create_res.json()["data"]["status"] == "NEW"

    # NEW -> CONTACTED
    r1 = await client.post(f"/api/v1/leads/{lead_id}/contact", headers=auth_headers)
    assert r1.status_code == 200
    assert r1.json()["data"]["status"] == "CONTACTED"

    # Idempotent re-contact
    r1_repeat = await client.post(f"/api/v1/leads/{lead_id}/contact", headers=auth_headers)
    assert r1_repeat.status_code == 200
    assert r1_repeat.json()["data"]["status"] == "CONTACTED"

    # CONTACTED -> INTERESTED
    r2 = await client.post(f"/api/v1/leads/{lead_id}/mark-interested", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["data"]["status"] == "INTERESTED"

    # INTERESTED -> SITE_VISIT
    r3 = await client.post(f"/api/v1/leads/{lead_id}/site-visit-stage", headers=auth_headers)
    assert r3.status_code == 200
    assert r3.json()["data"]["status"] == "SITE_VISIT"

    # SITE_VISIT -> NEGOTIATION
    r4 = await client.post(f"/api/v1/leads/{lead_id}/negotiation", headers=auth_headers)
    assert r4.status_code == 200
    assert r4.json()["data"]["status"] == "NEGOTIATION"

    # NEGOTIATION -> CONVERTED
    r5 = await client.post(f"/api/v1/leads/{lead_id}/convert", headers=auth_headers)
    assert r5.status_code == 200
    assert r5.json()["data"]["status"] == "CONVERTED"

    # Verify audit log for CONVERTED
    async with AsyncSessionFactory() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(lead_id),
                AuditLog.action == "LEAD_CONVERTED",
            )
        )
        assert audit_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_lead_lost_lifecycle(
    client: AsyncClient, auth_headers: dict, test_client_id: str
):
    """Verify marking lead as lost with required reason from any non-terminal stage."""
    create_res = await client.post(
        "/api/v1/leads",
        json={"client_id": test_client_id, "source": "WHATSAPP"},
        headers=auth_headers,
    )
    lead_id = create_res.json()["data"]["id"]

    lost_res = await client.post(
        f"/api/v1/leads/{lead_id}/lost",
        json={"lost_reason": "Client bought property in Bangalore"},
        headers=auth_headers,
    )
    assert lost_res.status_code == 200
    data = lost_res.json()["data"]
    assert data["status"] == "LOST"
    assert data["lost_reason"] == "Client bought property in Bangalore"

    # Verify audit log
    async with AsyncSessionFactory() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(lead_id),
                AuditLog.action == "LEAD_MARKED_LOST",
            )
        )
        assert audit_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_list_and_filter_leads(
    client: AsyncClient, auth_headers: dict, test_client_id: str
):
    # Create leads with different sources
    await client.post(
        "/api/v1/leads",
        json={"client_id": test_client_id, "source": "UNIQUE_SOURCE_X"},
        headers=auth_headers,
    )

    res = await client.get("/api/v1/leads?source=UNIQUE_SOURCE_X", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    assert len(items) >= 1
    assert all(ld["source"] == "UNIQUE_SOURCE_X" for ld in items)


@pytest.mark.asyncio
async def test_update_lead(
    client: AsyncClient, auth_headers: dict, test_client_id: str
):
    create_res = await client.post(
        "/api/v1/leads",
        json={"client_id": test_client_id, "source": "PHONE", "notes": "Initial note"},
        headers=auth_headers,
    )
    lead_id = create_res.json()["data"]["id"]

    patch_res = await client.patch(
        f"/api/v1/leads/{lead_id}",
        json={"source": "WHATSAPP", "notes": "Updated discussion details"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()["data"]
    assert patched_data["source"] == "WHATSAPP"
    assert patched_data["notes"] == "Updated discussion details"

    # Verify audit log
    async with AsyncSessionFactory() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(lead_id),
                AuditLog.action == "LEAD_UPDATED",
            )
        )
        assert audit_res.scalar_one_or_none() is not None
