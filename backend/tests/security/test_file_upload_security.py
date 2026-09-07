"""Adversarial security tests for Document File Uploads & Storage Safety.

Verifies:
  - Dangerous extensions (.exe, .sh, .php, .html, .js) are strictly rejected.
  - Content spoofing (HTML or scripts renamed to .pdf/.png) is rejected via magic byte checks.
  - Oversized files (>15MB) and zero-byte empty files are rejected.
  - Path traversal in filenames (../../etc/passwd.pdf) is sanitized and neutralized.
  - User-supplied filenames do not dictate storage paths (unpredictable UUID keys used).
"""
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def consultant_headers():
    user_id = uuid.uuid4()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                id=user_id,
                email=f"upload-sec-{uuid.uuid4().hex[:8]}@example.com",
                hashed_password=hash_password("ValidPassword123!"),
                full_name="Consultant Uploader",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename, content, mime_type",
    [
        ("exploit.php", b"<?php echo 'malicious'; ?>", "application/x-php"),
        ("script.sh", b"#!/bin/bash\nrm -rf /", "application/x-sh"),
        ("malware.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/x-msdownload"),
        ("page.html", b"<html><script>alert(1)</script></html>", "text/html"),
        ("payload.js", b"console.log('pwned')", "application/javascript"),
        ("code.py", b"import os; os.system('calc')", "text/x-python"),
    ],
)
async def test_disallowed_extensions_rejected(
    client: AsyncClient, consultant_headers: dict, filename: str, content: bytes, mime_type: str
):
    """Dangerous and unpermitted file extensions must be rejected with 422 ValidationAppError."""
    files = {"file": (filename, content, mime_type)}
    data = {"document_type": "OTHER"}

    res = await client.post("/api/v1/documents", files=files, data=data, headers=consultant_headers)
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "not permitted" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_magic_byte_content_spoofing_rejected(client: AsyncClient, consultant_headers: dict):
    """Files with allowed extensions (.pdf) but spoofed content (HTML/text) must be rejected."""
    spoofed_content = b"<html><body><script>alert('XSS')</script></body></html>"
    files = {"file": ("harmless_looking.pdf", spoofed_content, "application/pdf")}
    data = {"document_type": "SALE_DEED"}

    res = await client.post("/api/v1/documents", files=files, data=data, headers=consultant_headers)
    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert "does not match expected format" in body["error"]["message"]


@pytest.mark.asyncio
async def test_empty_file_upload_rejected(client: AsyncClient, consultant_headers: dict):
    """Zero-byte file uploads must be rejected with 422 ValidationAppError."""
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    data = {"document_type": "PATTA"}

    res = await client.post("/api/v1/documents", files=files, data=data, headers=consultant_headers)
    assert res.status_code == 422
    assert "empty" in res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_oversized_file_upload_rejected(client: AsyncClient, consultant_headers: dict):
    """Uploads exceeding the 15 MB limit must be rejected with 422 ValidationAppError."""
    # 16 MB payload starting with PDF magic bytes
    oversized_content = b"%PDF-1.4\n" + (b"A" * (16 * 1024 * 1024))
    files = {"file": ("oversized.pdf", oversized_content, "application/pdf")}
    data = {"document_type": "SALE_DEED"}

    res = await client.post("/api/v1/documents", files=files, data=data, headers=consultant_headers)
    assert res.status_code == 422
    assert "exceeds maximum allowed size" in res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_path_traversal_filename_sanitized(client: AsyncClient, consultant_headers: dict):
    """Malicious filenames attempting path traversal (../../etc/passwd.pdf) must be sanitized."""
    valid_pdf = b"%PDF-1.4\n%unique-" + uuid.uuid4().hex.encode() + b"\n%%EOF"
    malicious_filename = "../../../../../etc/passwd.pdf"
    files = {"file": (malicious_filename, valid_pdf, "application/pdf")}
    data = {"document_type": "SALE_DEED"}

    res = await client.post("/api/v1/documents", files=files, data=data, headers=consultant_headers)
    assert res.status_code == 201
    doc_data = res.json()["data"]

    # Original filename should be cleaned of directory separators
    assert "/" not in doc_data["original_filename"]
    assert "\\" not in doc_data["original_filename"]
    assert ".." not in doc_data["original_filename"]
    assert doc_data["original_filename"] == "passwd.pdf"


@pytest.mark.asyncio
async def test_storage_key_uuid_isolation(client: AsyncClient, consultant_headers: dict):
    """Uploading two files with identical names must generate distinct, non-conflicting storage keys."""
    valid_pdf_1 = b"%PDF-1.4\n%doc-1-" + uuid.uuid4().hex.encode() + b"\n%%EOF"
    valid_pdf_2 = b"%PDF-1.4\n%doc-2-" + uuid.uuid4().hex.encode() + b"\n%%EOF"
    files1 = {"file": ("title_deed.pdf", valid_pdf_1, "application/pdf")}
    files2 = {"file": ("title_deed.pdf", valid_pdf_2, "application/pdf")}
    data = {"document_type": "SALE_DEED"}

    res1 = await client.post("/api/v1/documents", files=files1, data=data, headers=consultant_headers)
    res2 = await client.post("/api/v1/documents", files=files2, data=data, headers=consultant_headers)

    assert res1.status_code == 201
    assert res2.status_code == 201

    data1 = res1.json()["data"]
    data2 = res2.json()["data"]
    assert data1["id"] != data2["id"]
    # Internal storage_key must NOT leak to API client
    assert "storage_key" not in data1
    assert "storage_key" not in data2
    assert data1["original_filename"] == "title_deed.pdf"
    assert data2["original_filename"] == "title_deed.pdf"

    # Verify directly in DB that internal storage keys are distinct
    from app.models.document import Document
    async with AsyncSessionFactory() as session:
        doc1 = await session.get(Document, uuid.UUID(data1["id"]))
        doc2 = await session.get(Document, uuid.UUID(data2["id"]))
        assert doc1 is not None and doc2 is not None
        assert doc1.storage_key != doc2.storage_key
