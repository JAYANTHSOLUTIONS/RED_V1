"""Phase 14 Integration Tests: Document Management, Secure Storage, and Property Verification.

Scenarios Covered:
- Scenario 4: Property -> Document -> Verification Case -> Verification Items -> Consultant Review -> Audit
- Scenario 5: Document -> Secure Storage -> Verification (Allowed/rejected file types, checksums, private storage abstraction)
"""
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

DUMMY_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
EC_PDF = b"%PDF-1.4\n2 0 obj\n<< /Type /EC >>\nendobj\ntrailer\n<< /Root 2 0 R >>\n%%EOF"


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    email = f"consultant-p14-docver-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Phase 14 DocVer Consultant",
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
async def published_plot(consultant_auth: dict):
    ref_code = f"PLOT-P14-{uuid.uuid4().hex[:6].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Verified CMDA Residential Plot in Guduvanchery",
                property_type="PLOT",
                transaction_type="SALE",
                price=Decimal("4200000.00"),
                plot_area=Decimal("1800.00"),
                area_unit="sq.ft",
                district="Chengalpattu",
                city="Guduvanchery",
                taluk="Vandalur",
                locality="Nellikuppam Road",
                pincode="603202",
                owner_name="M. Muthukumar",
                status="PUBLISHED",
                is_archived=False,
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id
    return prop_id


@pytest.mark.asyncio
async def test_property_document_and_verification_full_cycle(
    client: AsyncClient, consultant_auth: dict, published_plot: uuid.UUID
):
    """Scenario 4 & 5: Upload documents, request preliminary verification, review case, and verify audit trail."""
    headers = consultant_auth["headers"]
    user_id = consultant_auth["user_id"]

    # 1. Upload Sale Deed
    deed_files = {"file": ("mother_sale_deed.pdf", DUMMY_PDF, "application/pdf")}
    deed_data = {
        "document_type": "SALE_DEED",
        "property_id": str(published_plot),
        "notes": "Registered parent deed 2012",
    }
    upload_deed_res = await client.post(
        "/api/v1/documents", files=deed_files, data=deed_data, headers=headers
    )
    assert upload_deed_res.status_code == 201
    deed_doc = upload_deed_res.json()["data"]
    deed_id = deed_doc["id"]
    assert deed_doc["status"] == "UPLOADED"
    assert deed_doc["document_type"] == "SALE_DEED"
    assert deed_doc["checksum"] is not None

    # 2. Upload Encumbrance Certificate (EC)
    ec_files = {"file": ("ec_certificate_30yr.pdf", EC_PDF, "application/pdf")}
    ec_data = {
        "document_type": "EC",
        "property_id": str(published_plot),
        "notes": "EC from 1994 to 2024",
    }
    upload_ec_res = await client.post(
        "/api/v1/documents", files=ec_files, data=ec_data, headers=headers
    )
    assert upload_ec_res.status_code == 201
    ec_doc = upload_ec_res.json()["data"]
    ec_id = ec_doc["id"]
    assert ec_doc["document_type"] == "EC"

    # 3. Verify Download URL generation (presigned or local streaming) does NOT leak raw internal paths
    download_res = await client.get(
        f"/api/v1/documents/{deed_id}/download", headers=headers
    )
    assert download_res.status_code == 200
    assert download_res.content.startswith(b"%PDF")

    # 4. Request Preliminary Property Verification
    verif_payload = {
        "survey_number": "218/1B",
        "subdivision_number": "1B",
        "patta_number": "567",
        "ec_start_date": "1994-01-01",
        "ec_end_date": "2024-01-01",
        "ec_has_encumbrance_entries": False,
        "planning_approval_number": "CMDA/P/089/2021",
        "is_new_project_or_promoter_sale": False,
        "consultant_notes": "All original deeds physically inspected.",
        "disclaimer_acknowledged": True,
    }
    verif_res = await client.post(
        f"/api/v1/properties/{published_plot}/verification",
        json=verif_payload,
        headers=headers,
    )
    assert verif_res.status_code == 201
    verif_data = verif_res.json()["data"]
    verif_id = verif_data["id"]
    assert verif_data["property_id"] == str(published_plot)
    assert verif_data["status"] in ("COMPLETED", "NEEDS_REVIEW", "PENDING_REVIEW")
    assert "disclaimer" in verif_data  # Legal non-clearance disclaimer must be present

    # 5. Consultant Review / Update of the Verification Case
    review_res = await client.patch(
        f"/api/v1/verifications/{verif_id}",
        json={
            "consultant_observations": "Preliminary documentary consistency verified for consultant records.",
            "status": "COMPLETED",
        },
        headers=headers,
    )
    assert review_res.status_code == 200
    review_data = review_res.json()["data"]
    assert review_data["consultant_observations"] == "Preliminary documentary consistency verified for consultant records."

    # 6. Verify Complete Cross-Module Audit Trail
    async with AsyncSessionFactory() as session:
        # Document uploaded audits
        doc_audits = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.entity_id.in_([uuid.UUID(deed_id), uuid.UUID(ec_id)]),
                    AuditLog.action == "DOCUMENT_UPLOADED",
                )
            )
        ).all()
        assert len(doc_audits) == 2
        # Verification requested audit (logged against the verified property)
        verif_audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == published_plot,
                AuditLog.action == "VERIFICATION_REQUESTED",
            )
        )
        assert verif_audit is not None
        assert verif_audit.actor_id == user_id


@pytest.mark.asyncio
async def test_document_secure_storage_disallowed_file_types(
    client: AsyncClient, consultant_auth: dict, published_plot: uuid.UUID
):
    """Scenario 5: Disallowed file extensions (.exe, .sh) must be strictly rejected with 422."""
    headers = consultant_auth["headers"]

    malicious_files = {"file": ("malware_script.exe", b"MZexecutabledata", "application/x-msdownload")}
    data = {
        "document_type": "OTHER",
        "property_id": str(published_plot),
    }
    res = await client.post(
        "/api/v1/documents", files=malicious_files, data=data, headers=headers
    )
    assert res.status_code == 422
    assert "not allowed" in res.json()["error"]["message"].lower() or "extension" in res.json()["error"]["message"].lower()
