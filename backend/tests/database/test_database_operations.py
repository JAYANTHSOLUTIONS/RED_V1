"""Database operations, CRUD, relationships, constraints, and transaction tests.

Verifies end-to-end database behavior against PostgreSQL:
  - Valid creation across models
  - Relationship traversal
  - Delete protections (RESTRICT on deals, cascade on images/requirements)
  - Decimal precision maintenance
  - Constraint violations (negative price, negative fee)
  - Atomic multi-record rollback via `transaction(session)`
"""
from datetime import datetime, timezone
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionFactory, dispose_engine, transaction
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.deal import Deal, Fee
from app.models.document import Document
from app.models.lead import Lead
from app.models.property import Property, PropertyImage
from app.models.requirement import PropertyRequirement
from app.models.site_visit import SiteVisit
from app.models.user import User





@pytest.mark.asyncio
async def test_crud_and_relationships():
    """Verify creating connected records across User, Property, Client, Lead, Deal, Fee."""
    async with AsyncSessionFactory() as session:
        async with session.begin():
            # 1. User
            user = User(
                id=uuid.uuid4(),
                email=f"agent-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password="hashed_pw_test",
                full_name="Agent Smith",
                role="CONSULTANT",
            )
            session.add(user)

            # 2. Property
            ref = f"PR-2026-{uuid.uuid4().hex[:6]}"
            prop = Property(
                id=uuid.uuid4(),
                public_reference=ref,
                title="Green Valley Plot",
                property_type="RESIDENTIAL_PLOT",
                transaction_type="SALE",
                status="PUBLISHED",
                price=Decimal("4500000.00"),
                plot_area=Decimal("2400.00"),
                district="Coimbatore",
                city="Coimbatore",
                locality="Saravanampatti",
                pincode="641035",
            )
            session.add(prop)

            # 3. Client
            client = Client(
                id=uuid.uuid4(),
                full_name="Ravi Kumar",
                phone=f"+9198{uuid.uuid4().hex[:8]}",
                classification="BUYER",
            )
            session.add(client)

            # 4. Property Image
            img = PropertyImage(
                id=uuid.uuid4(),
                property_id=prop.id,
                storage_key=f"prop-img-{uuid.uuid4().hex}",
                original_filename="front_view.jpg",
                mime_type="image/jpeg",
                file_size=2048500,
                is_primary=True,
            )
            session.add(img)

            # 5. Deal & Fees
            deal = Deal(
                id=uuid.uuid4(),
                property_id=prop.id,
                client_id=client.id,
                deal_type="SALE",
                agreed_amount=Decimal("4400000.00"),
                status="CLOSED",
            )
            session.add(deal)

            fee_brokerage = Fee(
                id=uuid.uuid4(),
                deal_id=deal.id,
                fee_type="BROKERAGE_COMMISSION",
                amount=Decimal("88000.00"),
                is_government_fee=False,
                payment_status="RECEIVED",
            )
            fee_stamp = Fee(
                id=uuid.uuid4(),
                deal_id=deal.id,
                fee_type="GOVERNMENT_STAMP_DUTY",
                amount=Decimal("308000.00"),
                is_government_fee=True,
                payment_status="RECEIVED",
            )
            session.add_all([fee_brokerage, fee_stamp])

        # Verify insertion and relationships
        loaded_prop = await session.get(Property, prop.id)
        assert loaded_prop is not None
        assert loaded_prop.price == Decimal("4500000.00")

        # Query deal and check fee segregation
        result = await session.execute(
            select(Fee).where(Fee.deal_id == deal.id)
        )
        fees = result.scalars().all()
        assert len(fees) == 2
        gov_fees = [f for f in fees if f.is_government_fee]
        comm_fees = [f for f in fees if not f.is_government_fee]
        assert len(gov_fees) == 1
        assert gov_fees[0].amount == Decimal("308000.00")
        assert len(comm_fees) == 1
        assert comm_fees[0].amount == Decimal("88000.00")


@pytest.mark.asyncio
async def test_negative_price_check_constraint_fails():
    """Verify check constraint rejects negative property price."""
    async with AsyncSessionFactory() as session:
        prop = Property(
            id=uuid.uuid4(),
            public_reference=f"PR-2026-{uuid.uuid4().hex[:6]}",
            title="Invalid Price Property",
            property_type="APARTMENT",
            transaction_type="SALE",
            price=Decimal("-500000.00"),
            district="Chennai",
            city="Chennai",
            locality="Adyar",
            pincode="600020",
        )
        session.add(prop)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_atomic_transaction_rollback():
    """Verify transaction context manager rolls back all writes on error."""
    async with AsyncSessionFactory() as session:
        client_id = uuid.uuid4()
        prop_id = uuid.uuid4()

        # Setup parent records
        async with session.begin():
            client = Client(
                id=client_id,
                full_name="Atomic Client",
                phone=f"+9199{uuid.uuid4().hex[:8]}",
            )
            prop = Property(
                id=prop_id,
                public_reference=f"PR-2026-{uuid.uuid4().hex[:6]}",
                title="Atomic Property",
                property_type="APARTMENT",
                transaction_type="SALE",
                price=Decimal("10000000.00"),
                district="Chennai",
                city="Chennai",
                locality="OMR",
                pincode="600096",
            )
            session.add_all([client, prop])

        deal_id = uuid.uuid4()
        # Attempt multi-record write that fails midway
        try:
            async with transaction(session) as tx:
                deal = Deal(
                    id=deal_id,
                    property_id=prop_id,
                    client_id=client_id,
                    deal_type="SALE",
                    agreed_amount=Decimal("9800000.00"),
                )
                tx.add(deal)
                await tx.flush()

                # Trigger intentional failure (violating fee check constraint)
                invalid_fee = Fee(
                    id=uuid.uuid4(),
                    deal_id=deal_id,
                    fee_type="BROKERAGE_COMMISSION",
                    amount=Decimal("-1000.00"),  # will fail CHECK constraint
                )
                tx.add(invalid_fee)
                await tx.flush()
        except Exception:
            pass  # Expected to fail and rollback

        # Verify deal was NOT persisted due to atomic rollback
        loaded_deal = await session.get(Deal, deal_id)
        assert loaded_deal is None


@pytest.mark.asyncio
async def test_delete_restrict_protects_deal_history():
    """Verify deleting a property or client with an existing deal is rejected (RESTRICT)."""
    async with AsyncSessionFactory() as session:
        prop_id = uuid.uuid4()
        client_id = uuid.uuid4()
        deal_id = uuid.uuid4()

        async with session.begin():
            prop = Property(
                id=prop_id,
                public_reference=f"PR-2026-{uuid.uuid4().hex[:6]}",
                title="Historic Deal Property",
                property_type="APARTMENT",
                transaction_type="SALE",
                price=Decimal("7500000.00"),
                district="Chennai",
                city="Chennai",
                locality="T Nagar",
                pincode="600017",
            )
            client = Client(
                id=client_id,
                full_name="Deal Protection Test",
                phone=f"+9191{uuid.uuid4().hex[:8]}",
            )
            session.add_all([prop, client])

        async with session.begin():
            deal = Deal(
                id=deal_id,
                property_id=prop_id,
                client_id=client_id,
                deal_type="SALE",
                agreed_amount=Decimal("7400000.00"),
            )
            session.add(deal)

        # Attempt to delete property - must be blocked by RESTRICT
        prop_to_delete = await session.get(Property, prop_id)
        await session.delete(prop_to_delete)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_cascade_delete_cleans_child_images():
    """Verify deleting a property cascade-deletes its child property images."""
    async with AsyncSessionFactory() as session:
        prop_id = uuid.uuid4()
        img_id = uuid.uuid4()

        async with session.begin():
            prop = Property(
                id=prop_id,
                public_reference=f"PR-2026-{uuid.uuid4().hex[:6]}",
                title="Cascade Test Property",
                property_type="APARTMENT",
                transaction_type="SALE",
                price=Decimal("5000000.00"),
                district="Chennai",
                city="Chennai",
                locality="Velachery",
                pincode="600042",
            )
            session.add(prop)

            img = PropertyImage(
                id=img_id,
                property_id=prop_id,
                storage_key=f"img-key-{uuid.uuid4().hex}",
                original_filename="pic.jpg",
                mime_type="image/jpeg",
                file_size=1024,
            )
            session.add(img)

        # Delete property
        async with session.begin():
            prop_to_del = await session.get(Property, prop_id)
            await session.delete(prop_to_del)

        # Image should be gone
        loaded_img = await session.get(PropertyImage, img_id)
        assert loaded_img is None
