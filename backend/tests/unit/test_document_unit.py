"""Unit tests for Document validation, storage keys, and local storage backend."""
from pathlib import Path
import tempfile
import uuid
import pytest
from pydantic import ValidationError

from app.core.exceptions import StorageError, ValidationAppError
from app.schemas.document import (
    VALID_DOCUMENT_TYPES,
    DocumentUpdate,
    TamilNaduMetadata,
)
from app.services.document import (
    generate_storage_key,
    sanitize_filename,
    validate_file_content,
)
from app.storage.local import LocalStorageBackend


# ---------------------------------------------------------------------------
# File Validation & Sanitization Tests
# ---------------------------------------------------------------------------

def test_validate_file_content_valid_pdf():
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    filename, mime = validate_file_content(pdf_bytes, "sale_deed.pdf", max_mb=15)
    assert filename == "sale_deed.pdf"
    assert mime == "application/pdf"


def test_validate_file_content_valid_jpeg():
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    filename, mime = validate_file_content(jpeg_bytes, "patta_scan.jpg", max_mb=15)
    assert filename == "patta_scan.jpg"
    assert mime == "image/jpeg"


def test_validate_file_content_valid_png():
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    filename, mime = validate_file_content(png_bytes, "layout.png", max_mb=15)
    assert filename == "layout.png"
    assert mime == "image/png"


def test_validate_file_content_empty_file():
    with pytest.raises(ValidationAppError) as exc:
        validate_file_content(b"", "empty.pdf", max_mb=15)
    assert "empty" in str(exc.value).lower()


def test_validate_file_content_oversized_file():
    big_bytes = b"%PDF-" + b"0" * 1024 * 1024 * 2  # 2MB
    with pytest.raises(ValidationAppError) as exc:
        validate_file_content(big_bytes, "big.pdf", max_mb=1)
    assert "exceeds maximum allowed size" in str(exc.value)


def test_validate_file_content_invalid_extension():
    content = b"#!/bin/bash\necho hello"
    with pytest.raises(ValidationAppError) as exc:
        validate_file_content(content, "script.sh", max_mb=15)
    assert "not permitted" in str(exc.value)


def test_validate_file_content_forged_extension():
    fake_pdf = b"This is just plain text, not a real PDF document!"
    with pytest.raises(ValidationAppError) as exc:
        validate_file_content(fake_pdf, "fake.pdf", max_mb=15)
    assert "does not match expected format" in str(exc.value)


def test_sanitize_filename_traversal():
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("..\\..\\windows\\win.ini.jpg") == "win.ini.jpg"
    assert sanitize_filename("safe_document.pdf") == "safe_document.pdf"
    assert sanitize_filename("") == "unnamed_document"


# ---------------------------------------------------------------------------
# Storage Key Generation Tests
# ---------------------------------------------------------------------------

def test_generate_storage_key_property():
    prop_id = uuid.uuid4()
    key = generate_storage_key(property_id=prop_id, client_id=None, ext=".pdf")
    assert key.startswith(f"properties/{prop_id}/documents/")
    assert key.endswith(".pdf")
    # Verify UUID length in key
    filename_part = key.split("/")[-1]
    assert len(filename_part) == 32 + 4  # 32 hex chars + .pdf


def test_generate_storage_key_client():
    client_id = uuid.uuid4()
    key = generate_storage_key(property_id=None, client_id=client_id, ext=".jpg")
    assert key.startswith(f"clients/{client_id}/documents/")
    assert key.endswith(".jpg")


def test_generate_storage_key_general():
    key = generate_storage_key(property_id=None, client_id=None, ext=".png")
    assert key.startswith("general/documents/")
    assert key.endswith(".png")


# ---------------------------------------------------------------------------
# Local Storage Backend Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_storage_backend_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageBackend(base_dir=tmpdir)
        key = "properties/test-prop/documents/sample.pdf"
        data = b"%PDF-sample-content"

        # Store
        saved_key = await storage.store(key, data, "application/pdf")
        assert saved_key == key
        assert await storage.exists(key) is True

        # Retrieve
        retrieved = await storage.retrieve(key)
        assert retrieved == data

        # Stream
        stream, size, content_type = await storage.get_stream(key)
        assert size == len(data)
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)
        assert b"".join(chunks) == data

        # Delete
        assert await storage.delete(key) is True
        assert await storage.exists(key) is False


def test_local_storage_path_traversal_defense():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorageBackend(base_dir=tmpdir)
        with pytest.raises(StorageError) as exc:
            storage._resolve_safe_path("../../../etc/shadow")
        assert "path traversal" in str(exc.value)


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------

def test_document_types_validity():
    assert "EC" in VALID_DOCUMENT_TYPES
    assert "PATTA" in VALID_DOCUMENT_TYPES
    assert "SALE_DEED" in VALID_DOCUMENT_TYPES
    assert "RERA_DOCUMENT" in VALID_DOCUMENT_TYPES


def test_document_update_validation():
    update = DocumentUpdate(document_type="ec", notes="Updated notes")
    assert update.document_type == "EC"
    assert update.notes == "Updated notes"

    with pytest.raises(ValidationError):
        DocumentUpdate(document_type="INVALID_TYPE")


def test_tamil_nadu_metadata_schema():
    meta = TamilNaduMetadata(
        district="Chennai",
        taluk="Mylapore",
        village="Adyar",
        survey_number="123/4",
        subdivision_number="4A",
        sro_name="Adyar SRO",
        document_number="4567",
        document_year=2024,
    )
    assert meta.district == "Chennai"
    assert meta.document_year == 2024
