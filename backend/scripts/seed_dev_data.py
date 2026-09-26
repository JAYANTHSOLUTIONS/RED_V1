"""Database seed script for local development and testing.

Creates initial consultant & admin users, sample Tamil Nadu properties,
clients, requirements, leads, and notifications.
"""
import asyncio
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select
from app.db.session import AsyncSessionFactory
from app.core.security import hash_password
from app.models.user import User
from app.models.property import Property, PropertyImage
from app.models.client import Client
from app.models.lead import Lead
from app.models.requirement import PropertyRequirement
from app.models.notification import Notification

async def seed():
    async with AsyncSessionFactory() as session:
        # 1. Seed Users
        existing_user = await session.execute(
            select(User).where(User.email == "consultant@red.tn")
        )
        if not existing_user.scalar_one_or_none():
            consultant = User(
                id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
                email="consultant@red.tn",
                hashed_password=hash_password("Consultant@123"),
                full_name="S. Jayanth (Chief Consultant)",
                phone="+91 98400 12345",
                role="CONSULTANT",
                is_active=True,
            )
            admin = User(
                id=uuid.UUID("22222222-3333-4444-5555-666666666666"),
                email="admin@red.tn",
                hashed_password=hash_password("Admin@12345"),
                full_name="Operations Administrator",
                phone="+91 98400 99999",
                role="ADMIN",
                is_active=True,
            )
            session.add_all([consultant, admin])
            await session.commit()
            print("Seeded users: consultant@red.tn / Consultant@123 and admin@red.tn / Admin@12345")
        else:
            print("Users already exist.")

        # 2. Seed Sample Properties
        existing_props = await session.execute(select(Property))
        if not existing_props.scalars().first():
            p1 = Property(
                public_reference="PROP-ADYAR-001",
                title="3 BHK Luxury Sea-Breeze Residence, Gandhinagar",
                description="Corner East-facing apartment with sea breeze, modular teak kitchen, 2 covered car parks, and 100% power backup. CMDA approved.",
                property_type="APARTMENT",
                transaction_type="BUY",
                status="AVAILABLE",
                price=Decimal("26500000.00"),
                price_negotiable=True,
                built_up_area=Decimal("1950.00"),
                plot_area=Decimal("2200.00"),
                area_unit="sq.ft",
                bedrooms=3,
                bathrooms=3,
                floor=4,
                total_floors=6,
                facing="EAST",
                furnishing_state="SEMI_FURNISHED",
                parking_spaces=2,
                property_age=2,
                district="Chennai",
                city="Chennai",
                taluk="Mylapore-Triplicane",
                locality="Adyar",
                pincode="600020",
                address="4th Main Road, Gandhi Nagar, Adyar, Chennai 600020",
                owner_name="K. Sundararajan",
                owner_phone="+91 94440 55667",
                owner_email="sundararajan.k@example.com",
                inventory_source="Direct Referral",
                advertisement_authorized=True,
                internal_notes="Clear title parent deed from 1982 verified with sub-registrar.",
            )

            p2 = Property(
                public_reference="PROP-OMR-002",
                title="Premium IT Corridor Commercial Office Space",
                description="Furnished plug-and-play office floor with 40 workstations, 2 conference rooms, server room, and high-speed fiber connectivity.",
                property_type="COMMERCIAL",
                transaction_type="RENT",
                status="AVAILABLE",
                price=Decimal("175000.00"),
                price_negotiable=False,
                built_up_area=Decimal("3200.00"),
                plot_area=Decimal("3200.00"),
                area_unit="sq.ft",
                floor=2,
                total_floors=8,
                facing="NORTH",
                furnishing_state="FULLY_FURNISHED",
                parking_spaces=4,
                property_age=4,
                district="Chennai",
                city="Chennai",
                taluk="Sholinganallur",
                locality="Perungudi OMR",
                pincode="600096",
                address="Rajiv Gandhi Salai, Perungudi, Chennai 600096",
                owner_name="Rajesh Varma",
                owner_phone="+91 98840 99881",
                inventory_source="Broker Network",
                advertisement_authorized=True,
                internal_notes="Lock-in period 3 years minimum.",
            )

            p3 = Property(
                public_reference="PROP-CBE-003",
                title="Exclusive 4 BHK Spanish Courtyard Villa",
                description="Independent modern villa in gated enclave with private landscaped lawn, solar rooftop installation, and DTCP approved layout.",
                property_type="VILLA",
                transaction_type="BUY",
                status="UNDER_OFFER",
                price=Decimal("39000000.00"),
                price_negotiable=True,
                built_up_area=Decimal("3800.00"),
                plot_area=Decimal("4356.00"),
                area_unit="sq.ft",
                bedrooms=4,
                bathrooms=5,
                floor=1,
                total_floors=2,
                facing="NORTH_EAST",
                furnishing_state="FULLY_FURNISHED",
                parking_spaces=3,
                property_age=1,
                district="Coimbatore",
                city="Coimbatore",
                taluk="Coimbatore North",
                locality="RS Puram",
                pincode="641002",
                address="West Club Road, RS Puram, Coimbatore 641002",
                owner_name="Dr. V. Meenakshisundaram",
                owner_phone="+91 98422 33441",
                inventory_source="Direct Owner",
                advertisement_authorized=True,
                internal_notes="Token advance received, legal verification in final phase.",
            )

            session.add_all([p1, p2, p3])
            await session.commit()
            print("Seeded 3 sample properties.")

        # 3. Seed Sample Clients
        existing_clients = await session.execute(select(Client))
        if not existing_clients.scalars().first():
            c1 = Client(
                full_name="K. Ravichandran",
                phone="+91 98401 22334",
                email="ravichandran.k@example.com",
                preferred_contact_method="WHATSAPP",
                postal_address="Flat 2B, Alwarpet, Chennai 600018",
                classification="BUYER",
                source="Referral",
                status="ACTIVE",
                notes="Looking for 3 BHK in South Chennai budget 2.5 - 3 Cr.",
            )
            c2 = Client(
                full_name="M. Anitha",
                phone="+91 97910 88776",
                email="anitha.m@example.com",
                preferred_contact_method="CALL",
                postal_address="Perungudi, Chennai 600096",
                classification="TENANT",
                source="Direct Enquiry",
                status="ACTIVE",
                notes="Tech lead looking for commercial space in OMR.",
            )
            session.add_all([c1, c2])
            await session.commit()
            print("Seeded 2 sample clients.")

            # 4. Seed Lead & Requirement
            lead = Lead(
                client_id=c1.id,
                source="DIRECT",
                status="CONTACTED",
                notes="Initial phone discussion completed. Shared Adyar brochure.",
            )
            session.add(lead)

            req = PropertyRequirement(
                client_id=c1.id,
                title="South Chennai 3 BHK Luxury Apartment",
                transaction_type="BUY",
                property_type="APARTMENT",
                district="Chennai",
                city="Chennai",
                preferred_localities="Adyar,Besant Nagar,Thiruvanmiyur",
                min_price=Decimal("20000000.00"),
                max_price=Decimal("30000000.00"),
                min_built_up_area=Decimal("1700.00"),
                max_built_up_area=Decimal("2400.00"),
                min_bedrooms=3,
                min_bathrooms=3,
                preferred_facing="EAST,NORTH_EAST",
                status="ACTIVE",
            )
            session.add(req)

            # 5. Notification
            notif = Notification(
                user_id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
                title="New High-Value Match Detected",
                message="Property PROP-ADYAR-001 matches requirement 'South Chennai 3 BHK Luxury Apartment' with 94% score.",
                notification_type="SYSTEM_ALERT",
                is_read=False,
            )
            session.add(notif)
            await session.commit()
            print("Seeded lead, requirement, and notification.")

    print("Seeding complete successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
