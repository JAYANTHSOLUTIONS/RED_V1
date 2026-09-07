"""Phase 14 Integration Scenario 13: Transaction Boundaries & Rollback Integrity.

Verifies that atomic transactions across business entities and audit records
behave correctly under failure:
1. Failed property transaction rolls back both property record and audit event.
2. Failed site visit mutation preserves prior state and writes no phantom success audit.
3. Rollback leaves no orphan records or inconsistent cross-module state.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory, transaction
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.lead import Lead
from app.models.property import Property
from app.models.site_visit import SiteVisit
from app.models.user import User
from app.models.verification import VerificationCase
from app.repositories.audit import AuditRepository
from app.repositories.property import PropertyRepository
from app.repositories.site_visit import SiteVisitRepository
from app.schemas.property import PropertyCreate
from app.services.property import PropertyService
from app.services.site_visit import SiteVisitService


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    """Authenticate a test consultant user."""
    email = f"consultant-p14-tx-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Phase 14 TX Consultant",
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
async def test_property_creation_audit_failure_rolls_back_entirely(consultant_auth: dict):
    """If audit recording fails during property creation, neither property nor audit persists."""
    actor_id = consultant_auth["user_id"]
    prop_service = PropertyService()

    prop_in = PropertyCreate(
        title="Rollback Test Farmland in Maduranthakam",
        description="Agricultural land tested for atomic transaction rollback",
        property_type="AGRICULTURAL_LAND",
        transaction_type="SALE",
        price=Decimal("4500000.00"),
        plot_area=Decimal("43560.00"),
        area_unit="sq.ft",
        district="Chengalpattu",
        city="Maduranthakam",
        locality="Acharapakkam",
        pincode="603301",
    )

    # We simulate a catastrophic failure when audit_repo.record is invoked
    with patch.object(
        AuditRepository, "record", side_effect=RuntimeError("Simulated downstream audit failure")
    ):
        async with AsyncSessionFactory() as session:
            with pytest.raises(RuntimeError, match="Simulated downstream audit failure"):
                await prop_service.create_property(
                    session=session,
                    data=prop_in,
                    actor_id=actor_id,
                )

    # Verify no orphan property was committed
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Property).where(Property.title == "Rollback Test Farmland in Maduranthakam")
        )
        orphaned_prop = result.scalars().first()
        assert orphaned_prop is None, "Failed transaction must not leave orphan property in DB"

        # Verify no phantom audit log exists
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "PROPERTY_CREATED",
                AuditLog.actor_id == actor_id,
            )
        )
        audits = audit_res.scalars().all()
        matching_audits = [
            a for a in audits if a.change_diff and a.change_diff.get("title") == "Rollback Test Farmland in Maduranthakam"
        ]
        assert len(matching_audits) == 0, "Failed transaction must not leave phantom audit log"


@pytest.mark.asyncio
async def test_site_visit_mutation_rollback_preserves_original_state(consultant_auth: dict):
    """When a site visit status mutation fails mid-transaction, the prior status is preserved."""
    actor_id = consultant_auth["user_id"]
    public_ref = f"PR-2026-{uuid.uuid4().int % 1000000:06d}"

    # 1. Setup committed property, client, and REQUESTED site visit
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=public_ref,
                title="Rollback Test Apartment in Porur",
                property_type="APARTMENT",
                transaction_type="SALE",
                price=Decimal("6500000.00"),
                district="Chennai",
                city="Chennai",
                locality="Porur",
                pincode="600116",
                status="PUBLISHED",
                is_archived=False,
            )
            client = Client(
                full_name="Karthikeyan Rollback Test",
                phone="+91 98400 88991",
                email="karthik.rollback@example.com",
                classification="BUYER",
                status="ACTIVE",
            )
            session.add_all([prop, client])
            await session.flush()

            visit = SiteVisit(
                property_id=prop.id,
                client_id=client.id,
                scheduled_at=datetime.now(timezone.utc) + timedelta(days=2),
                status="REQUESTED",
            )
            session.add(visit)
            await session.flush()
            visit_id = visit.id

    visit_service = SiteVisitService()

    # 2. Attempt confirm_visit, but simulate failure in audit recording
    with patch.object(
        AuditRepository, "record", side_effect=RuntimeError("Audit disk full / network crash")
    ):
        async with AsyncSessionFactory() as session:
            with pytest.raises(RuntimeError, match="Audit disk full / network crash"):
                await visit_service.confirm_visit(
                    session=session,
                    visit_id=visit_id,
                    actor_id=actor_id,
                )

    # 3. Verify site visit is still in REQUESTED status (did not partially commit CONFIRMED)
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(SiteVisit).where(SiteVisit.id == visit_id)
        )
        refreshed_visit = result.scalar_one()
        assert refreshed_visit.status == "REQUESTED", "Rolled back visit must retain REQUESTED status"

        # Verify no phantom SITE_VISIT_CONFIRMED audit entry
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == visit_id,
                AuditLog.action == "SITE_VISIT_CONFIRMED",
            )
        )
        assert audit_res.scalars().first() is None, "No phantom confirmation audit log on failure"


@pytest.mark.asyncio
async def test_atomic_transaction_helper_rollback_consistency():
    """Explicit test of app.db.session.transaction context manager ensuring multi-model atomicity."""
    prop_id = uuid.uuid4()
    client_id = uuid.uuid4()
    public_ref = f"PR-2026-{uuid.uuid4().int % 1000000:06d}"

    # Attempt to insert Property + Client in a single transaction that raises midway
    try:
        async with AsyncSessionFactory() as session:
            async with transaction(session):
                prop = Property(
                    id=prop_id,
                    public_reference=public_ref,
                    title="Atomic Rollback Check",
                    property_type="PLOTS_LAND",
                    transaction_type="SALE",
                    price=Decimal("3000000.00"),
                    district="Kanchipuram",
                    city="Sriperumbudur",
                    locality="Vallam",
                    pincode="602105",
                    status="DRAFT",
                    is_archived=False,
                )
                session.add(prop)
                await session.flush()

                client = Client(
                    id=client_id,
                    full_name="Atomic Client Check",
                    phone="+91 97900 12345",
                    classification="BUYER",
                    status="ACTIVE",
                )
                session.add(client)
                await session.flush()

                # Trigger intentional failure before committing
                raise ValueError("Intentional business constraint check failure")
    except ValueError:
        pass

    # Verify neither prop nor client persisted in DB
    async with AsyncSessionFactory() as session:
        prop_check = (await session.execute(select(Property).where(Property.id == prop_id))).scalar_one_or_none()
        client_check = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none()
        assert prop_check is None, "Property must be rolled back"
        assert client_check is None, "Client must be rolled back"
