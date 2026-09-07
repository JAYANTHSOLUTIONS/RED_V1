"""Tests for database-level concurrency control, row locking, and conflict prevention."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select

from app.core.exceptions import ConflictError, ValidationAppError
from app.db.session import AsyncSessionFactory
from app.models.client import Client
from app.models.follow_up import FollowUp
from app.models.property import Property
from app.models.user import User
from app.schemas.follow_up import FollowUpCreate, FollowUpComplete
from app.schemas.property import PropertyCreate
from app.schemas.site_visit import SiteVisitCreate
from app.services.follow_up import FollowUpService
from app.services.property import PropertyService
from app.services.site_visit import SiteVisitService


@pytest.fixture
async def consultant_user():
    email = f"consultant-concur-{uuid.uuid4().hex[:8]}@example.com"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password="fakehashedpassword",
                full_name="Concurrency Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            user_id = user.id
    return user_id


@pytest.fixture
async def test_client_and_property(consultant_user):
    async with AsyncSessionFactory() as session:
        async with session.begin():
            client = Client(
                full_name="Concurrency Buyer",
                phone=f"+9198{uuid.uuid4().int % 100000000:08d}",
                classification="BUYER",
            )
            session.add(client)

            prop = Property(
                public_reference=f"CONCUR-{uuid.uuid4().hex[:6].upper()}",
                title="Concurrency Test Plot",
                property_type="LAND",
                transaction_type="SALE",
                price=Decimal("4500000.00"),
                district="Chennai",
                city="Chennai",
                locality="Velachery",
                pincode="600042",
                status="PUBLISHED",
            )
            session.add(prop)
            await session.flush()
            client_id = client.id
            prop_id = prop.id

    return client_id, prop_id


async def test_site_visit_conflict_detection(test_client_and_property, consultant_user):
    """Scheduling two confirmed visits within the conflict buffer raises ConflictError."""
    client_id, prop_id = test_client_and_property
    service = SiteVisitService()

    # Use an isolated far-future timestamp to avoid collisions with prior test runs
    random_offset_days = 100 + (uuid.uuid4().int % 500)
    visit_time = datetime.now(timezone.utc) + timedelta(days=random_offset_days)

    # 1. Schedule first confirmed visit
    async with AsyncSessionFactory() as session:
        visit1_data = SiteVisitCreate(
            client_id=client_id,
            property_id=prop_id,
            scheduled_at=visit_time,
            status="CONFIRMED",
            notes="First visit booking",
        )
        visit1 = await service.create_visit(session, visit1_data, actor_id=consultant_user)
        assert visit1.status == "CONFIRMED"

    # 2. Attempt overlapping visit (15 mins later, within 60 min buffer)
    async with AsyncSessionFactory() as session2:
        overlapping_time = visit_time + timedelta(minutes=15)
        visit2_data = SiteVisitCreate(
            client_id=client_id,
            property_id=prop_id,
            scheduled_at=overlapping_time,
            status="CONFIRMED",
            notes="Conflicting visit booking",
        )
        with pytest.raises(ConflictError) as exc_info:
            await service.create_visit(session2, visit2_data, actor_id=consultant_user)

        assert exc_info.value.code == "RESOURCE_CONFLICT"
        assert "conflicts with an existing confirmed visit" in exc_info.value.message


async def test_property_status_transition_concurrency_and_idempotency(consultant_user):
    """Property transition uses row locks and handles idempotent or invalid transitions."""
    service = PropertyService()

    # Create draft property
    async with AsyncSessionFactory() as session:
        prop_data = PropertyCreate(
            title="State Machine Property",
            property_type="LAND",
            transaction_type="SALE",
            price=Decimal("5000000.00"),
            district="Madurai",
            city="Madurai",
            locality="Tallakulam",
            pincode="625002",
        )
        prop = await service.create_property(session, prop_data, actor_id=consultant_user)
        prop_id = prop.id
        assert prop.status == "DRAFT"

    # Transition: DRAFT -> PUBLISHED
    async with AsyncSessionFactory() as session:
        published = await service.publish_property(session, prop_id, actor_id=consultant_user)
        assert published.status == "PUBLISHED"

    # Repeated transition to PUBLISHED is idempotent
    async with AsyncSessionFactory() as session:
        re_published = await service.publish_property(session, prop_id, actor_id=consultant_user)
        assert re_published.status == "PUBLISHED"

    # Invalid transition (PUBLISHED -> DRAFT is invalid in state machine)
    async with AsyncSessionFactory() as session:
        with pytest.raises(ValidationAppError):
            await service._transition_status(
                session,
                property_id=prop_id,
                target_status="DRAFT",
                audit_action="PROPERTY_UPDATED",
                actor_id=consultant_user,
            )


async def test_follow_up_completion_idempotency(test_client_and_property, consultant_user):
    """Completing a follow-up twice is strictly idempotent and concurrency safe."""
    client_id, prop_id = test_client_and_property
    service = FollowUpService()

    due_date = datetime.now(timezone.utc) + timedelta(days=1)

    # 1. Create scheduled follow-up
    async with AsyncSessionFactory() as session:
        fu_data = FollowUpCreate(
            client_id=client_id,
            property_id=prop_id,
            action_type="CALL",
            scheduled_at=due_date,
            description="Discuss token advance",
        )
        follow_up = await service.create_follow_up(session, fu_data, actor_id=consultant_user)
        fu_id = follow_up.id
        assert follow_up.status == "SCHEDULED"

    # 2. First completion
    async with AsyncSessionFactory() as session:
        completed = await service.complete_follow_up(
            session,
            follow_up_id=fu_id,
            data=FollowUpComplete(completion_notes="Client agreed to advance"),
            actor_id=consultant_user,
        )
        assert completed.status == "COMPLETED"
        assert completed.completed_at is not None

    # 3. Second concurrent/repeated completion
    async with AsyncSessionFactory() as session:
        completed_again = await service.complete_follow_up(
            session,
            follow_up_id=fu_id,
            data=FollowUpComplete(completion_notes="Repeated completion request"),
            actor_id=consultant_user,
        )
        assert completed_again.status == "COMPLETED"
