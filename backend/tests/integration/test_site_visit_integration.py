"""Integration tests for Site Visit Coordination API and database persistence."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.property import Property
from app.models.site_visit import SiteVisit
from app.models.user import User


@pytest.fixture(autouse=True)
async def clean_site_visits():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM site_visits"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM site_visits"))


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-visit-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Site Visit Consultant",
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
        "full_name": "Visit Prospective Buyer",
        "phone": f"+91 98{uuid.uuid4().int % 100000000:08d}",
        "email": f"visitbuyer-{uuid.uuid4().hex[:6]}@example.com",
        "classification": "BUYER",
    }
    res = await client.post("/api/v1/clients", json=payload, headers=auth_headers)
    assert res.status_code == 201
    return res.json()["data"]


@pytest.fixture
async def sample_property(auth_headers: dict, client: AsyncClient):
    payload = {
        "title": "Apartment in Anna Nagar",
        "property_type": "Apartment",
        "transaction_type": "SALE",
        "price": "8500000.00",
        "district": "Chennai",
        "city": "Chennai",
        "locality": "Anna Nagar",
        "pincode": "600040",
    }
    res = await client.post("/api/v1/properties", json=payload, headers=auth_headers)
    assert res.status_code == 201
    return res.json()["data"]


@pytest.mark.asyncio
async def test_full_site_visit_lifecycle(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
    sample_property: dict,
):
    """Test full cycle: Create -> Confirm -> Complete -> Audit logs verified."""
    visit_time = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)

    # 1. Create visit (Consultant)
    create_payload = {
        "client_id": sample_client["id"],
        "property_id": sample_property["id"],
        "scheduled_at": visit_time.isoformat(),
        "status": "REQUESTED",
        "notes": "Buyer interested in morning inspection",
    }
    res = await client.post("/api/v1/site-visits", json=create_payload, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["status"] == "REQUESTED"
    assert data["notes"] == "Buyer interested in morning inspection"
    assert data["client"]["id"] == sample_client["id"]
    assert data["property"]["id"] == sample_property["id"]
    assert "disclaimer" in data
    visit_id = data["id"]

    # 2. Confirm visit
    confirm_payload = {
        "notes": "Owner agreed for morning visit. Confirmed 10:00 AM.",
    }
    res_confirm = await client.post(
        f"/api/v1/site-visits/{visit_id}/confirm",
        json=confirm_payload,
        headers=auth_headers,
    )
    assert res_confirm.status_code == 200
    confirm_data = res_confirm.json()["data"]
    assert confirm_data["status"] == "CONFIRMED"
    assert "Confirmed" in confirm_data["notes"]

    # 3. Complete visit
    complete_payload = {
        "feedback": "Buyer liked the ventilation. Requested preliminary document review.",
        "notes": "Follow-up required next Monday.",
    }
    res_complete = await client.post(
        f"/api/v1/site-visits/{visit_id}/complete",
        json=complete_payload,
        headers=auth_headers,
    )
    assert res_complete.status_code == 200
    complete_data = res_complete.json()["data"]
    assert complete_data["status"] == "COMPLETED"
    assert complete_data["feedback"] == "Buyer liked the ventilation. Requested preliminary document review."

    # 4. Verify Audit Logs in Database
    async with AsyncSessionFactory() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_id == uuid.UUID(visit_id))
            .order_by(AuditLog.created_at.asc())
        )
        result = await session.execute(stmt)
        logs = list(result.scalars().all())
        actions = [log.action for log in logs]
        assert "SITE_VISIT_CREATED" in actions
        assert "SITE_VISIT_CONFIRMED" in actions
        assert "SITE_VISIT_COMPLETED" in actions


@pytest.mark.asyncio
async def test_public_visit_request_flow(
    client: AsyncClient,
    sample_client: dict,
    sample_property: dict,
    auth_headers: dict,
):
    """Verify customer public request creates a visit in REQUESTED status without leaking consultant data."""
    visit_time = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)

    payload = {
        "client_id": sample_client["id"],
        "property_id": sample_property["id"],
        "scheduled_at": visit_time.isoformat(),
        "notes": "Customer requesting evening plot inspection.",
    }

    # Public request (no auth headers required)
    res = await client.post("/api/v1/site-visits/request", json=payload)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["status"] == "REQUESTED"
    assert data["property_id"] == sample_property["id"]
    # Public response does NOT include client PII or internal notes
    assert "notes" not in data
    assert "client" not in data
    assert "disclaimer" in data
    visit_id = data["id"]

    # Public get status
    res_pub = await client.get(f"/api/v1/site-visits/{visit_id}/public")
    assert res_pub.status_code == 200
    pub_data = res_pub.json()["data"]
    assert pub_data["status"] == "REQUESTED"
    assert "notes" not in pub_data

    # Consultant can retrieve full private view
    res_priv = await client.get(f"/api/v1/site-visits/{visit_id}", headers=auth_headers)
    assert res_priv.status_code == 200
    priv_data = res_priv.json()["data"]
    assert priv_data["notes"] == "Customer requesting evening plot inspection."
    assert priv_data["client"]["id"] == sample_client["id"]


@pytest.mark.asyncio
async def test_cancellation_flow(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
    sample_property: dict,
):
    """Verify explicit cancellation with mandatory cancellation reason."""
    visit_time = (datetime.now(timezone.utc) + timedelta(days=4)).replace(microsecond=0)

    # 1. Create visit
    create_payload = {
        "client_id": sample_client["id"],
        "property_id": sample_property["id"],
        "scheduled_at": visit_time.isoformat(),
        "status": "REQUESTED",
    }
    res = await client.post("/api/v1/site-visits", json=create_payload, headers=auth_headers)
    visit_id = res.json()["data"]["id"]

    # 2. Cancel visit
    cancel_payload = {
        "cancellation_reason": "Owner unavailable due to travel outside Tamil Nadu",
        "notes": "Will re-contact next month",
    }
    res_cancel = await client.post(
        f"/api/v1/site-visits/{visit_id}/cancel",
        json=cancel_payload,
        headers=auth_headers,
    )
    assert res_cancel.status_code == 200
    cancel_data = res_cancel.json()["data"]
    assert cancel_data["status"] == "CANCELLED"
    assert cancel_data["cancellation_reason"] == "Owner unavailable due to travel outside Tamil Nadu"

    # Historical record is preserved in database (not deleted)
    async with AsyncSessionFactory() as session:
        visit_in_db = await session.get(SiteVisit, uuid.UUID(visit_id))
        assert visit_in_db is not None
        assert visit_in_db.status == "CANCELLED"


@pytest.mark.asyncio
async def test_rescheduling_preserves_history(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
    sample_property: dict,
):
    """Verify rescheduling marks original visit as RESCHEDULED and creates new linked visit."""
    original_time = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)
    new_time = (datetime.now(timezone.utc) + timedelta(days=6)).replace(microsecond=0)

    # 1. Create visit and confirm it
    create_payload = {
        "client_id": sample_client["id"],
        "property_id": sample_property["id"],
        "scheduled_at": original_time.isoformat(),
        "status": "REQUESTED",
    }
    res = await client.post("/api/v1/site-visits", json=create_payload, headers=auth_headers)
    visit_id = res.json()["data"]["id"]

    await client.post(f"/api/v1/site-visits/{visit_id}/confirm", headers=auth_headers)

    # 2. Reschedule visit
    reschedule_payload = {
        "new_scheduled_at": new_time.isoformat(),
        "reason": "Heavy rain in Chennai / flood alert",
        "notes": "Rescheduled with buyer agreement",
    }
    res_resched = await client.post(
        f"/api/v1/site-visits/{visit_id}/reschedule",
        json=reschedule_payload,
        headers=auth_headers,
    )
    assert res_resched.status_code == 200
    new_visit_data = res_resched.json()["data"]
    assert new_visit_data["status"] == "CONFIRMED"
    assert new_visit_data["rescheduled_from_id"] == visit_id

    # 3. Check original visit in database
    res_orig = await client.get(f"/api/v1/site-visits/{visit_id}", headers=auth_headers)
    orig_data = res_orig.json()["data"]
    assert orig_data["status"] == "RESCHEDULED"
    assert "Heavy rain in Chennai" in orig_data["notes"]


@pytest.mark.asyncio
async def test_list_site_visits_and_filters(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
    sample_property: dict,
):
    """Verify list endpoint with status and pagination filters."""
    base_time = (datetime.now(timezone.utc) + timedelta(days=10)).replace(microsecond=0)

    # Create 2 visits
    for i in range(2):
        payload = {
            "client_id": sample_client["id"],
            "property_id": sample_property["id"],
            "scheduled_at": (base_time + timedelta(hours=i * 2)).isoformat(),
            "status": "REQUESTED",
        }
        await client.post("/api/v1/site-visits", json=payload, headers=auth_headers)

    res = await client.get(
        f"/api/v1/site-visits?client_id={sample_client['id']}&status=REQUESTED",
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert all(item["status"] == "REQUESTED" for item in data["items"])


@pytest.mark.asyncio
async def test_patch_update_notes(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
    sample_property: dict,
):
    """Verify updating notes and feedback on a visit."""
    visit_time = (datetime.now(timezone.utc) + timedelta(days=7)).replace(microsecond=0)

    res = await client.post(
        "/api/v1/site-visits",
        json={
            "client_id": sample_client["id"],
            "property_id": sample_property["id"],
            "scheduled_at": visit_time.isoformat(),
        },
        headers=auth_headers,
    )
    visit_id = res.json()["data"]["id"]

    patch_res = await client.patch(
        f"/api/v1/site-visits/{visit_id}",
        json={"notes": "Updated notes: Buyer requested EC copy"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["notes"] == "Updated notes: Buyer requested EC copy"
