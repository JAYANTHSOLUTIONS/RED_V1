"""Phase 14 Integration Tests: Site Visit Coordination and Follow-up Management.

Scenarios Covered:
- Scenario 6: Property + Client -> Site Visit -> Confirm -> Complete (Lifecycle state machine, inactive property restrictions)
- Scenario 7: Site Visit -> Completed -> Follow-Up -> Completed / Missed (Downstream continuity, scheduling, audit trails)
"""
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
async def clean_visits_and_followups():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM follow_ups"))
            await session.execute(text("DELETE FROM site_visits"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM follow_ups"))
            await session.execute(text("DELETE FROM site_visits"))


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    email = f"consultant-p14-svfu-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Phase 14 SV-FU Consultant",
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
            "full_name": "S. Ramachandran",
            "phone": f"+91 96{uuid.uuid4().int % 100000000:08d}",
            "email": f"ramachandran-{uuid.uuid4().hex[:6]}@example.com",
            "classification": "BUYER",
        },
        headers=headers,
    )
    return client_res.json()["data"]["id"]


@pytest.fixture
async def sample_property():
    ref_code = f"SV-PROP-{uuid.uuid4().hex[:6].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Triplex Penthouse in ECR Injambakkam",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("12000000.00"),
                district="Chennai",
                city="Chennai",
                locality="Injambakkam",
                pincode="600115",
                status="PUBLISHED",
                is_archived=False,
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id
    return prop_id


@pytest.mark.asyncio
async def test_site_visit_lifecycle_to_follow_up_progression(
    client: AsyncClient, consultant_auth: dict, sample_client: str, sample_property: uuid.UUID
):
    """Scenarios 6 & 7: Site Visit (REQUESTED -> CONFIRMED -> COMPLETED) followed by Follow-Up (SCHEDULED -> COMPLETED)."""
    headers = consultant_auth["headers"]
    user_id = consultant_auth["user_id"]

    # 1. Schedule Site Visit for tomorrow
    visit_time = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    visit_payload = {
        "property_id": str(sample_property),
        "client_id": sample_client,
        "scheduled_at": visit_time.isoformat(),
        "notes": "Client requested afternoon site inspection with family",
    }
    create_visit_res = await client.post(
        "/api/v1/site-visits", json=visit_payload, headers=headers
    )
    assert create_visit_res.status_code == 201
    visit_data = create_visit_res.json()["data"]
    visit_id = visit_data["id"]
    assert visit_data["status"] == "REQUESTED"

    # 2. Confirm Site Visit
    confirm_res = await client.post(
        f"/api/v1/site-visits/{visit_id}/confirm",
        json={"notes": "Confirmed with property caretaker"},
        headers=headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["data"]["status"] == "CONFIRMED"

    # 3. Complete Site Visit
    complete_time = (datetime.now(timezone.utc) + timedelta(days=1, hours=2)).replace(microsecond=0)
    complete_visit_res = await client.post(
        f"/api/v1/site-visits/{visit_id}/complete",
        json={
            "feedback": "Buyer impressed with layout; wants to negotiate pricing",
            "outcome": "INTERESTED",
            "completed_at": complete_time.isoformat(),
        },
        headers=headers,
    )
    assert complete_visit_res.status_code == 200
    assert complete_visit_res.json()["data"]["status"] == "COMPLETED"

    # 4. Progress to Follow-Up task linked to Client and Property
    fu_time = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
    fu_payload = {
        "client_id": sample_client,
        "property_id": str(sample_property),
        "action_type": "CALL",
        "scheduled_at": fu_time.isoformat(),
        "notes": "Call buyer to discuss seller pricing counter-offer",
    }
    create_fu_res = await client.post(
        "/api/v1/follow-ups", json=fu_payload, headers=headers
    )
    assert create_fu_res.status_code == 201
    fu_data = create_fu_res.json()["data"]
    fu_id = fu_data["id"]
    assert fu_data["status"] == "SCHEDULED"
    assert fu_data["action_type"] == "CALL"

    # 5. Complete Follow-Up
    complete_fu_res = await client.post(
        f"/api/v1/follow-ups/{fu_id}/complete",
        json={"completion_notes": "Offer accepted; proceed with legal documents."},
        headers=headers,
    )
    assert complete_fu_res.status_code == 200
    assert complete_fu_res.json()["data"]["status"] == "COMPLETED"

    # 6. Verify Cross-Module Audit Events
    async with AsyncSessionFactory() as session:
        # Site visit events
        sv_audits = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.entity_id == uuid.UUID(visit_id),
                    AuditLog.action.in_(["SITE_VISIT_CREATED", "SITE_VISIT_CONFIRMED", "SITE_VISIT_COMPLETED"]),
                )
            )
        ).all()
        assert len(sv_audits) == 3

        # Follow-up events
        fu_audits = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.entity_id == uuid.UUID(fu_id),
                    AuditLog.action.in_(["FOLLOW_UP_CREATED", "FOLLOW_UP_COMPLETED"]),
                )
            )
        ).all()
        assert len(fu_audits) == 2


@pytest.mark.asyncio
async def test_site_visit_cannot_be_scheduled_for_archived_property(
    client: AsyncClient, consultant_auth: dict, sample_client: str
):
    """Scenario 6 Edge Case: Site visits must not be allowed on archived properties."""
    headers = consultant_auth["headers"]

    # Create and archive property
    archived_prop_ref = f"ARC-SV-{uuid.uuid4().hex[:6].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=archived_prop_ref,
                title="Archived Villa in Madipakkam",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("9000000.00"),
                district="Chennai",
                city="Chennai",
                locality="Madipakkam",
                pincode="600091",
                status="ARCHIVED",
                is_archived=True,
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id

    visit_time = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    res = await client.post(
        "/api/v1/site-visits",
        json={
            "property_id": str(prop_id),
            "client_id": sample_client,
            "scheduled_at": visit_time.isoformat(),
        },
        headers=headers,
    )
    assert res.status_code in (404, 422)


@pytest.mark.asyncio
async def test_follow_up_missed_lifecycle(
    client: AsyncClient, consultant_auth: dict, sample_client: str
):
    """Scenario 7: Follow-up marked as MISSED persists correctly with audit record."""
    headers = consultant_auth["headers"]

    fu_time = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    create_fu_res = await client.post(
        "/api/v1/follow-ups",
        json={
            "client_id": sample_client,
            "action_type": "SEND_DOCS",
            "scheduled_at": fu_time.isoformat(),
            "notes": "Email draft sale agreement",
        },
        headers=headers,
    )
    assert create_fu_res.status_code == 201
    fu_id = create_fu_res.json()["data"]["id"]

    # Mark as MISSED
    miss_res = await client.post(
        f"/api/v1/follow-ups/{fu_id}/miss",
        json={"notes": "Client phone switched off; reschedule tomorrow"},
        headers=headers,
    )
    assert miss_res.status_code == 200
    assert miss_res.json()["data"]["status"] == "MISSED"

    # Verify audit event
    async with AsyncSessionFactory() as session:
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(fu_id),
                AuditLog.action == "FOLLOW_UP_MISSED",
            )
        )
        assert audit is not None
