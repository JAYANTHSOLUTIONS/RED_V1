"""Tests for storage failure modes and compensation rollbacks."""
import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy import select

from app.core.exceptions import StorageError, NotFoundError
from app.db.session import AsyncSessionFactory
from app.models.document import Document
from app.services.document import DocumentService
from app.storage.local import LocalStorageBackend


@pytest.fixture
def temp_storage(tmp_path):
    return LocalStorageBackend(base_dir=str(tmp_path / "docs"))


async def test_storage_write_failure_aborts_operation_and_no_db_record(temp_storage):
    """If the storage backend fails during store(), no database record should be saved."""
    service = DocumentService(storage=temp_storage)

    # Valid PDF bytes
    valid_pdf = b"%PDF-1.4 test document content for failure simulation"

    with patch.object(temp_storage, "store", side_effect=OSError("Disk full")):
        async with AsyncSessionFactory() as session:
            with pytest.raises(StorageError):
                await service.upload_document(
                    session=session,
                    file_bytes=valid_pdf,
                    original_filename="sample.pdf",
                    document_type="SALE_DEED",
                )

    # Verify no document record was persisted in database
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Document).where(Document.original_filename == "sample.pdf")
        )
        assert result.scalar_one_or_none() is None


async def test_database_failure_triggers_storage_compensation_cleanup(temp_storage):
    """If DB persistence fails after storage write, the written file must be cleaned up."""
    service = DocumentService(storage=temp_storage)
    valid_pdf = b"%PDF-1.4 test document for compensation cleanup"

    # Track deleted keys
    deleted_keys = []
    original_delete = temp_storage.delete

    async def tracking_delete(key: str) -> bool:
        deleted_keys.append(key)
        return await original_delete(key)

    temp_storage.delete = tracking_delete

    # Simulate DB error during document metadata persistence
    with patch.object(service.doc_repo, "create", side_effect=RuntimeError("Simulated DB flush crash")):
        async with AsyncSessionFactory() as session:
            with pytest.raises(RuntimeError, match="Simulated DB flush crash"):
                await service.upload_document(
                    session=session,
                    file_bytes=valid_pdf,
                    original_filename="compensation_test.pdf",
                    document_type="SALE_DEED",
                )

    # Verify that compensation cleanup was triggered
    assert len(deleted_keys) == 1
    storage_key = deleted_keys[0]

    # Verify file does not exist on disk
    file_exists = await temp_storage.exists(storage_key)
    assert file_exists is False


async def test_storage_read_missing_file_raises_not_found(temp_storage):
    """Retrieving a non-existent storage key raises NotFoundError without leaking absolute paths."""
    with pytest.raises(NotFoundError) as exc_info:
        await temp_storage.retrieve("nonexistent/missing_file.pdf")

    assert "not found" in str(exc_info.value).lower()
    # Must not leak the base directory path
    assert str(temp_storage.base_dir) not in str(exc_info.value)


async def test_storage_path_traversal_prevention(temp_storage):
    """Attempting path traversal must be rejected with StorageError."""
    with pytest.raises(StorageError) as exc_info:
        temp_storage._resolve_safe_path("../../etc/passwd")

    assert "path traversal detected" in str(exc_info.value)
