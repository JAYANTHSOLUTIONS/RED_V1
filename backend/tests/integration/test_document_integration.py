"""Integration tests for Document Management and Secure Storage API."""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.document import Document
from app.models.property import Property
from app.models.user import User
from app.storage import get_storage_backend


SAMPLE_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-doc-test-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Doc Test Consultant",
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
async def sample_property():
    ref_code = f"DOC-PROP-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Document Test Villa",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("8500000"),
                district="Chennai",
                city="Chennai",
                locality="Besant Nagar",
                pincode="600090",
                status="PUBLISHED",
                is_archived=False,
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id
    return prop_id


@pytest.fixture
async def sample_client(auth_headers: dict, client: AsyncClient):
    payload = {
        "full_name": "Document Test Client",
        "phone": f"+91 98{uuid.uuid4().int % 100000000:08d}",
        "email": f"client-{uuid.uuid4().hex[:6]}@example.com",
        "classification": "BUYER",
    }
    res = await client.post("/api/v1/clients", json=payload, headers=auth_headers)
    assert res.status_code == 201
    return res.json()["data"]["id"]


@pytest.mark.asyncio
async def test_upload_and_get_document(
    client: AsyncClient, auth_headers: dict, sample_property: uuid.UUID
):
    files = {"file": ("sale_deed.pdf", SAMPLE_PDF, "application/pdf")}
    data = {
        "document_type": "SALE_DEED",
        "property_id": str(sample_property),
        "notes": "Original registered deed",
    }

    res = await client.post(
        "/api/v1/documents", files=files, data=data, headers=auth_headers
    )
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    doc_data = body["data"]
    doc_id = doc_data["id"]
    assert doc_data["property_id"] == str(sample_property)
    assert doc_data["document_type"] == "SALE_DEED"
    assert doc_data["original_filename"] == "sale_deed.pdf"
    assert doc_data["mime_type"] == "application/pdf"
    assert doc_data["status"] == "UPLOADED"
    assert doc_data["is_archived"] is False
    assert doc_data["file_size"] == len(SAMPLE_PDF)

    # Verify audit log was recorded
    async with AsyncSessionFactory() as session:
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(doc_id),
                AuditLog.action == "DOCUMENT_UPLOADED",
            )
        )
        assert audit is not None

    # Get document metadata
    get_res = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == doc_id


@pytest.mark.asyncio
async def test_client_document_upload(
    client: AsyncClient, auth_headers: dict, sample_client: str
):
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    files = {"file": ("id_proof.png", png_bytes, "image/png")}
    data = {
        "document_type": "IDENTITY_PROOF",
        "client_id": sample_client,
        "notes": "Aadhaar Card copy",
    }

    res = await client.post(
        "/api/v1/documents", files=files, data=data, headers=auth_headers
    )
    assert res.status_code == 201
    doc_data = res.json()["data"]
    assert doc_data["client_id"] == sample_client
    assert doc_data["document_type"] == "IDENTITY_PROOF"


@pytest.mark.asyncio
async def test_duplicate_document_rejection(
    client: AsyncClient, auth_headers: dict, sample_property: uuid.UUID
):
    # Upload first time
    files1 = {"file": ("ec_doc.pdf", SAMPLE_PDF, "application/pdf")}
    data1 = {"document_type": "EC", "property_id": str(sample_property)}
    res1 = await client.post("/api/v1/documents", files=files1, data=data1, headers=auth_headers)
    assert res1.status_code == 201

    # Upload identical content to the same property again -> 409
    files2 = {"file": ("ec_copy.pdf", SAMPLE_PDF, "application/pdf")}
    data2 = {"document_type": "EC", "property_id": str(sample_property)}
    res2 = await client.post("/api/v1/documents", files=files2, data=data2, headers=auth_headers)
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "RESOURCE_CONFLICT"
    assert "duplicate" in res2.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_list_and_filter_documents(
    client: AsyncClient, auth_headers: dict, sample_property: uuid.UUID
):
    pdf_content = b"%PDF-1.4 distinct content " + uuid.uuid4().bytes
    files = {"file": ("patta.pdf", pdf_content, "application/pdf")}
    data = {"document_type": "PATTA", "property_id": str(sample_property)}
    await client.post("/api/v1/documents", files=files, data=data, headers=auth_headers)

    # Filter by property_id
    res = await client.get(f"/api/v1/documents?property_id={sample_property}", headers=auth_headers)
    assert res.status_code == 200
    items = res.json()["data"]["items"]
    assert len(items) >= 1

    # Filter by document_type
    res_patta = await client.get(
        f"/api/v1/documents?property_id={sample_property}&document_type=PATTA",
        headers=auth_headers,
    )
    assert res_patta.status_code == 200
    assert all(d["document_type"] == "PATTA" for d in res_patta.json()["data"]["items"])


@pytest.mark.asyncio
async def test_download_document_stream(
    client: AsyncClient, auth_headers: dict, sample_property: uuid.UUID
):
    pdf_bytes = b"%PDF-1.4 download test " + uuid.uuid4().bytes
    files = {"file": ("deed.pdf", pdf_bytes, "application/pdf")}
    data = {"document_type": "SALE_DEED", "property_id": str(sample_property)}

    upload_res = await client.post("/api/v1/documents", files=files, data=data, headers=auth_headers)
    doc_id = upload_res.json()["data"]["id"]

    # Download
    download_res = await client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_headers)
    assert download_res.status_code == 200
    assert download_res.headers["content-type"] == "application/pdf"
    assert "attachment" in download_res.headers["content-disposition"]
    assert download_res.content == pdf_bytes

    # Verify audit log for download access
    async with AsyncSessionFactory() as session:
        audit = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(doc_id),
                AuditLog.action == "DOCUMENT_ACCESSED",
            )
        )
        assert audit is not None


@pytest.mark.asyncio
async def test_review_and_archive_lifecycle(
    client: AsyncClient, auth_headers: dict, sample_property: uuid.UUID
):
    pdf_bytes = b"%PDF-1.4 lifecycle test " + uuid.uuid4().bytes
    files = {"file": ("approval.pdf", pdf_bytes, "application/pdf")}
    data = {"document_type": "BUILDING_APPROVAL", "property_id": str(sample_property)}

    upload_res = await client.post("/api/v1/documents", files=files, data=data, headers=auth_headers)
    doc_id = upload_res.json()["data"]["id"]

    # Transition to UNDER_REVIEW
    review_res = await client.post(f"/api/v1/documents/{doc_id}/review", headers=auth_headers)
    assert review_res.status_code == 200
    assert review_res.json()["data"]["status"] == "UNDER_REVIEW"

    # Update metadata
    patch_res = await client.patch(
        f"/api/v1/documents/{doc_id}",
        json={"notes": "Approved by CMDA in 2023"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["notes"] == "Approved by CMDA in 2023"

    # Soft-archive
    archive_res = await client.post(f"/api/v1/documents/{doc_id}/archive", headers=auth_headers)
    assert archive_res.status_code == 200
    archive_data = archive_res.json()["data"]
    assert archive_data["is_archived"] is True
    assert archive_data["status"] == "ARCHIVED"

    # Verify underlying file is still preserved in storage (not deleted)
    async with AsyncSessionFactory() as session:
        doc = await session.scalar(select(Document).where(Document.id == uuid.UUID(doc_id)))
        storage = get_storage_backend()
        assert await storage.exists(doc.storage_key) is True
