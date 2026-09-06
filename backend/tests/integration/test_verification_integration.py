"""Integration tests for Tamil Nadu Preliminary Property Verification API."""
from datetime import date
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.document import Document
from app.models.property import Property
from app.models.user import User
from app.models.verification import VerificationCase


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Create and authenticate a consultant user."""
    email = f"consultant-verif-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Verification Consultant",
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
async def sample_plot():
    """Create a sample plot property in Chengalpattu with associated title and EC documents."""
    ref_code = f"VR-PROP-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Premium CMDA Approved Residential Plot in Tambaram",
                property_type="PLOT",
                transaction_type="SALE",
                price=Decimal("5500000.00"),
                plot_area=Decimal("2400.00"),
                area_unit="sq.ft",
                district="Chengalpattu",
                city="Tambaram",
                taluk="Tambaram",
                locality="Tambaram West",
                pincode="600045",
                owner_name="R. Kumar",
                status="PUBLISHED",
            )
            session.add(prop)
            await session.flush()

            doc_deed = Document(
                property_id=prop.id,
                document_type="SALE_DEED",
                storage_key=f"test/deed-{uuid.uuid4().hex}.pdf",
                original_filename="registered_sale_deed.pdf",
                mime_type="application/pdf",
                file_size=2048,
                checksum=f"chk-{uuid.uuid4().hex}",
                status="UPLOADED",
            )
            doc_ec = Document(
                property_id=prop.id,
                document_type="EC",
                storage_key=f"test/ec-{uuid.uuid4().hex}.pdf",
                original_filename="encumbrance_certificate_30yr.pdf",
                mime_type="application/pdf",
                file_size=4096,
                checksum=f"chk-{uuid.uuid4().hex}",
                status="UPLOADED",
            )
            doc_patta = Document(
                property_id=prop.id,
                document_type="PATTA",
                storage_key=f"test/patta-{uuid.uuid4().hex}.pdf",
                original_filename="patta_chitta.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum=f"chk-{uuid.uuid4().hex}",
                status="UPLOADED",
            )
            session.add_all([doc_deed, doc_ec, doc_patta])
            await session.flush()
            prop_id = prop.id

    return prop_id


@pytest.mark.asyncio
async def test_run_property_verification_success(
    client: AsyncClient, auth_headers: dict, sample_plot: uuid.UUID
):
    """Verify executing preliminary property verification returns complete explainable assessment."""
    payload = {
        "survey_number": "124/3A",
        "subdivision_number": "3A",
        "patta_number": "412",
        "ec_start_date": "1994-01-01",
        "ec_end_date": "2024-01-01",
        "ec_has_encumbrance_entries": False,
        "planning_approval_number": "CMDA/P/045/2019",
        "is_new_project_or_promoter_sale": False,
        "consultant_notes": "All initial documents inspected at Tambaram SRO.",
        "disclaimer_acknowledged": True,
    }

    res = await client.post(
        f"/api/v1/properties/{sample_plot}/verification",
        json=payload,
        headers=auth_headers,
    )
    assert res.status_code == 201
    data = res.json()["data"]

    assert data["property_id"] == str(sample_plot)
    assert data["status"] in ("COMPLETED", "NEEDS_REVIEW")
    assert "risk_level" in data
    assert data["completeness_score"] > 0
    assert data["planning_authority_type"] == "CMDA"
    assert "checks" in data
    assert len(data["checks"]) >= 10
    assert "preliminary property verification assessment" in data["disclaimer"]

    # Verify audit log recorded events
    async with AsyncSessionFactory() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id.in_([sample_plot, uuid.UUID(data["id"])])
            )
        )
        logs = audit_res.scalars().all()
        actions = [log.action for log in logs]
        assert "VERIFICATION_REQUESTED" in actions
        assert any("VERIFICATION_" in a for a in actions)


@pytest.mark.asyncio
async def test_get_latest_property_verification(
    client: AsyncClient, auth_headers: dict, sample_plot: uuid.UUID
):
    """Verify retrieving the latest verification assessment for a property."""
    # First trigger verification
    post_res = await client.post(
        f"/api/v1/properties/{sample_plot}/verification",
        json={"survey_number": "124/3A", "disclaimer_acknowledged": True},
        headers=auth_headers,
    )
    assert post_res.status_code == 201
    created_id = post_res.json()["data"]["id"]

    # Now get latest
    get_res = await client.get(
        f"/api/v1/properties/{sample_plot}/verification",
        headers=auth_headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == created_id


@pytest.mark.asyncio
async def test_get_verification_by_id(
    client: AsyncClient, auth_headers: dict, sample_plot: uuid.UUID
):
    """Verify retrieving a verification case directly by its UUID."""
    post_res = await client.post(
        f"/api/v1/properties/{sample_plot}/verification",
        json={"disclaimer_acknowledged": True},
        headers=auth_headers,
    )
    verif_id = post_res.json()["data"]["id"]

    get_res = await client.get(
        f"/api/v1/verifications/{verif_id}",
        headers=auth_headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == verif_id


@pytest.mark.asyncio
async def test_list_verifications_paginated(
    client: AsyncClient, auth_headers: dict, sample_plot: uuid.UUID
):
    """Verify listing verification cases with pagination and property filter."""
    # Create two verification runs
    await client.post(
        f"/api/v1/properties/{sample_plot}/verification",
        json={"survey_number": "124/3A", "disclaimer_acknowledged": True},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/properties/{sample_plot}/verification",
        json={"survey_number": "124/3A", "disclaimer_acknowledged": True},
        headers=auth_headers,
    )

    list_res = await client.get(
        f"/api/v1/verifications?property_id={sample_plot}&limit=10&offset=0",
        headers=auth_headers,
    )
    assert list_res.status_code == 200
    paginated = list_res.json()["data"]
    assert paginated["total"] >= 2
    assert len(paginated["items"]) >= 2
    assert paginated["items"][0]["property_id"] == str(sample_plot)


@pytest.mark.asyncio
async def test_patch_verification_observations(
    client: AsyncClient, auth_headers: dict, sample_plot: uuid.UUID
):
    """Verify consultant can update review observations and status."""
    post_res = await client.post(
        f"/api/v1/properties/{sample_plot}/verification",
        json={"disclaimer_acknowledged": True},
        headers=auth_headers,
    )
    verif_id = post_res.json()["data"]["id"]

    patch_res = await client.patch(
        f"/api/v1/verifications/{verif_id}",
        json={
            "consultant_observations": "Physical site inspection confirmed boundary stones match survey 124/3A.",
            "status": "COMPLETED",
        },
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    data = patch_res.json()["data"]
    assert data["consultant_observations"] == "Physical site inspection confirmed boundary stones match survey 124/3A."
    assert data["status"] == "COMPLETED"
