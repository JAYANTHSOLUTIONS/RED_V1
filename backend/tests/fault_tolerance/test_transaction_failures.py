"""Tests for transaction atomicity and rollback under failure."""
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import AsyncSessionFactory, transaction
from app.models.client import Client
from app.models.property import Property
from decimal import Decimal


async def test_atomic_transaction_rolls_back_all_writes_on_failure():
    """Verify that if an error occurs within a transaction, all inserted records are rolled back."""
    client_name = f"Atomic Test {uuid.uuid4().hex[:6]}"
    prop_ref = f"ATOM-{uuid.uuid4().hex[:6].upper()}"

    with pytest.raises(RuntimeError, match="Simulated mid-transaction failure"):
        async with AsyncSessionFactory() as session:
            async with transaction(session):
                # 1. Insert client
                client = Client(
                    full_name=client_name,
                    phone=f"+9198{uuid.uuid4().int % 100000000:08d}",
                    classification="BUYER",
                )
                session.add(client)
                await session.flush()

                # 2. Insert property
                prop = Property(
                    public_reference=prop_ref,
                    title="Transaction Rollback Test Plot",
                    property_type="LAND",
                    transaction_type="SALE",
                    price=Decimal("2500000.00"),
                    district="Chennai",
                    city="Chennai",
                    locality="Guindy",
                    pincode="600032",
                )
                session.add(prop)
                await session.flush()

                # 3. Simulate failure before commit
                raise RuntimeError("Simulated mid-transaction failure")

    # Verify neither record exists in the database
    async with AsyncSessionFactory() as session:
        client_res = await session.execute(select(Client).where(Client.full_name == client_name))
        assert client_res.scalar_one_or_none() is None

        prop_res = await session.execute(select(Property).where(Property.public_reference == prop_ref))
        assert prop_res.scalar_one_or_none() is None


async def test_transaction_rollback_on_unique_constraint_violation():
    """Verify that an integrity constraint failure rolls back the transaction safely."""
    duplicate_ref = f"DUP-{uuid.uuid4().hex[:6].upper()}"

    # First insert succeeds
    async with AsyncSessionFactory() as session:
        async with transaction(session):
            prop1 = Property(
                public_reference=duplicate_ref,
                title="First Unique Property",
                property_type="LAND",
                transaction_type="SALE",
                price=Decimal("1500000.00"),
                district="Coimbatore",
                city="Coimbatore",
                locality="Gandhipuram",
                pincode="641012",
            )
            session.add(prop1)

    # Second insert with duplicate public_reference fails
    with pytest.raises(Exception):
        async with AsyncSessionFactory() as session:
            async with transaction(session):
                prop2 = Property(
                    public_reference=duplicate_ref,
                    title="Duplicate Property",
                    property_type="LAND",
                    transaction_type="SALE",
                    price=Decimal("1500000.00"),
                    district="Coimbatore",
                    city="Coimbatore",
                    locality="Gandhipuram",
                    pincode="641012",
                )
                session.add(prop2)

    # Verify only the first record exists
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Property).where(Property.public_reference == duplicate_ref))
        records = result.scalars().all()
        assert len(records) == 1
        assert records[0].title == "First Unique Property"
