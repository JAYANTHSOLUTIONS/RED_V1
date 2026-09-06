"""Document Management service.

Enforces document validation, magic bytes verification, checksum generation,
duplicate detection, storage/database transactional consistency, soft-archival safeguards,
and comprehensive audit logging.
"""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import AsyncIterator, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    StorageError,
    ValidationAppError,
)
from app.db.session import transaction
from app.models.document import Document
from app.repositories.audit import AuditRepository
from app.repositories.client import ClientRepository
from app.repositories.document import DocumentRepository
from app.repositories.property import PropertyRepository
from app.schemas.common import PaginatedResponse
from app.schemas.document import (
    VALID_DOCUMENT_TYPES,
    DocumentFilterParams,
    DocumentResponse,
    DocumentUpdate,
)
from app.storage import StorageBackend, get_storage_backend

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

MAGIC_BYTE_SIGNATURES = {
    ".pdf": b"%PDF-",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
    ".png": b"\x89PNG\r\n\x1a\n",
}

MIME_TYPE_MAPPING = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def sanitize_filename(filename: str) -> str:
    """Normalize and clean user-provided filename to prevent path traversal."""
    base_name = os.path.basename(filename).strip()
    clean_name = "".join(c for c in base_name if c.isalnum() or c in "._- ")
    return clean_name or "unnamed_document"


def validate_file_content(content: bytes, filename: str, max_mb: int) -> Tuple[str, str]:
    """Validate size, extension whitelist, and magic byte signatures.

    Returns (clean_filename, canonical_mime_type).
    """
    if not content or len(content) == 0:
        raise ValidationAppError("Uploaded file is empty (zero bytes).")

    max_bytes = max_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValidationAppError(
            f"Uploaded file exceeds maximum allowed size of {max_mb} MB."
        )

    clean_name = sanitize_filename(filename)
    ext = Path(clean_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValidationAppError(
            f"File extension '{ext}' is not permitted. Allowed formats: {allowed}"
        )

    expected_magic = MAGIC_BYTE_SIGNATURES.get(ext)
    if expected_magic and not content.startswith(expected_magic):
        raise ValidationAppError(
            f"File content does not match expected format for extension '{ext}'."
        )

    canonical_mime = MIME_TYPE_MAPPING.get(ext, "application/octet-stream")
    return clean_name, canonical_mime


def generate_storage_key(
    property_id: Optional[uuid.UUID],
    client_id: Optional[uuid.UUID],
    ext: str,
) -> str:
    """Generate a collision-free UUID-based storage key, isolating from user filenames."""
    doc_uuid = uuid.uuid4().hex
    clean_ext = ext.lower()

    if property_id is not None:
        return f"properties/{property_id}/documents/{doc_uuid}{clean_ext}"
    elif client_id is not None:
        return f"clients/{client_id}/documents/{doc_uuid}{clean_ext}"
    return f"general/documents/{doc_uuid}{clean_ext}"


class DocumentService:
    """Domain service managing private document operations."""

    def __init__(
        self,
        document_repo: Optional[DocumentRepository] = None,
        property_repo: Optional[PropertyRepository] = None,
        client_repo: Optional[ClientRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
        storage: Optional[StorageBackend] = None,
        settings: Optional[Settings] = None,
    ):
        self.doc_repo = document_repo or DocumentRepository()
        self.property_repo = property_repo or PropertyRepository()
        self.client_repo = client_repo or ClientRepository()
        self.audit_repo = audit_repo or AuditRepository()
        self.settings = settings or get_settings()
        self.storage = storage or get_storage_backend(self.settings)

    async def upload_document(
        self,
        session: AsyncSession,
        file_bytes: bytes,
        original_filename: str,
        document_type: str,
        property_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Document:
        """Validate, store binary data, persist metadata, and record audit log.

        Includes compensation rollback: if DB commit fails after file write, the
        stored file is immediately deleted from storage.
        """
        # 1. Validate document type
        doc_type_upper = document_type.strip().upper()
        if doc_type_upper not in VALID_DOCUMENT_TYPES:
            allowed = ", ".join(sorted(VALID_DOCUMENT_TYPES))
            raise ValidationAppError(
                f"Invalid document_type '{document_type}'. Allowed types: {allowed}"
            )

        # 2. Validate file bytes and signatures
        clean_filename, canonical_mime = validate_file_content(
            content=file_bytes,
            filename=original_filename,
            max_mb=self.settings.MAX_DOCUMENT_SIZE_MB,
        )
        file_size = len(file_bytes)
        ext = Path(clean_filename).suffix.lower()

        # 3. Validate associations
        if property_id is not None:
            prop = await self.property_repo.get_by_id(session, property_id)
            if prop is None:
                raise NotFoundError("Property not found.")
            if prop.is_archived:
                raise ValidationAppError("Cannot attach document to an archived property.")

        if client_id is not None:
            client = await self.client_repo.get_by_id(session, client_id)
            if client is None:
                raise NotFoundError("Client not found.")
            if client.is_archived:
                raise ValidationAppError("Cannot attach document to an archived client.")

        # 4. Compute Checksum and Detect Duplicates
        checksum = hashlib.sha256(file_bytes).hexdigest()
        duplicate = await self.doc_repo.find_duplicate(
            session=session,
            checksum=checksum,
            property_id=property_id,
            client_id=client_id,
        )
        if duplicate is not None:
            raise ConflictError(
                "Duplicate document detected: an identical file has already been uploaded for this resource."
            )

        # 5. Generate Safe Storage Key
        storage_key = generate_storage_key(property_id, client_id, ext)

        # 6. Store File Binary in Storage Backend
        try:
            await self.storage.store(storage_key, file_bytes, canonical_mime)
        except Exception as exc:
            raise StorageError("Document storage is temporarily unavailable. Please try again later.") from exc

        # 7. Persist Metadata in PostgreSQL with Compensation Cleanup
        try:
            async with transaction(session):
                doc = Document(
                    property_id=property_id,
                    client_id=client_id,
                    document_type=doc_type_upper,
                    storage_key=storage_key,
                    original_filename=clean_filename,
                    mime_type=canonical_mime,
                    file_size=file_size,
                    checksum=checksum,
                    status="UPLOADED",
                    notes=notes,
                    is_archived=False,
                    uploaded_by=actor_id,
                )
                await self.doc_repo.create(session, doc)

                await self.audit_repo.record(
                    session,
                    action="DOCUMENT_UPLOADED",
                    entity_type="DOCUMENT",
                    entity_id=doc.id,
                    actor_id=actor_id,
                    change_diff={
                        "document_type": doc_type_upper,
                        "original_filename": clean_filename,
                        "file_size": file_size,
                        "property_id": str(property_id) if property_id else None,
                        "client_id": str(client_id) if client_id else None,
                    },
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )
        except Exception:
            # Compensation: delete written storage file so no orphaned files remain
            try:
                await self.storage.delete(storage_key)
            except Exception:
                pass
            raise

        return doc

    async def get_document(
        self, session: AsyncSession, doc_id: uuid.UUID
    ) -> Document:
        """Fetch document metadata by primary key."""
        doc = await self.doc_repo.get_by_id(session, doc_id)
        if doc is None:
            raise NotFoundError("Document not found.")
        return doc

    async def download_document(
        self,
        session: AsyncSession,
        doc_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Tuple[AsyncIterator[bytes], int, str, str]:
        """Verify access, log access event, and return download stream.

        Returns (stream_generator, file_size, content_type, original_filename).
        """
        doc = await self.get_document(session, doc_id)

        # Audit access event
        async with transaction(session):
            await self.audit_repo.record(
                session,
                action="DOCUMENT_ACCESSED",
                entity_type="DOCUMENT",
                entity_id=doc.id,
                actor_id=actor_id,
                change_diff={
                    "original_filename": doc.original_filename,
                    "is_archived": doc.is_archived,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        stream, size, content_type = await self.storage.get_stream(doc.storage_key)
        return stream, size, content_type, doc.original_filename

    async def list_documents(
        self,
        session: AsyncSession,
        filters: DocumentFilterParams,
    ) -> PaginatedResponse[DocumentResponse]:
        """Query documents with filtering and database-level pagination."""
        docs, total = await self.doc_repo.list_documents(session, filters)
        items = [DocumentResponse.model_validate(d) for d in docs]
        return PaginatedResponse[DocumentResponse](
            items=items,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update_document(
        self,
        session: AsyncSession,
        doc_id: uuid.UUID,
        data: DocumentUpdate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Document:
        """Update editable document metadata fields (document_type, notes)."""
        async with transaction(session):
            doc = await self.doc_repo.get_by_id_for_update(session, doc_id)
            if doc is None:
                raise NotFoundError("Document not found.")

            if doc.is_archived:
                raise ValidationAppError("Cannot update an archived document.")

            update_dict = data.model_dump(exclude_unset=True)
            if update_dict:
                await self.doc_repo.update(session, doc, update_dict)
                await self.audit_repo.record(
                    session,
                    action="DOCUMENT_UPDATED",
                    entity_type="DOCUMENT",
                    entity_id=doc.id,
                    actor_id=actor_id,
                    change_diff={k: str(v) for k, v in update_dict.items()},
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )

        return await self.get_document(session, doc_id)

    async def review_document(
        self,
        session: AsyncSession,
        doc_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Document:
        """Transition document status from UPLOADED to UNDER_REVIEW."""
        async with transaction(session):
            doc = await self.doc_repo.get_by_id_for_update(session, doc_id)
            if doc is None:
                raise NotFoundError("Document not found.")

            if doc.is_archived:
                raise ValidationAppError("Cannot transition status of an archived document.")

            if doc.status == "UNDER_REVIEW":
                raise ValidationAppError("Document is already under review.")

            if doc.status != "UPLOADED":
                raise ValidationAppError(
                    f"Cannot transition document from '{doc.status}' to 'UNDER_REVIEW'."
                )

            old_status = doc.status
            doc.status = "UNDER_REVIEW"
            await session.flush()

            await self.audit_repo.record(
                session,
                action="DOCUMENT_STATUS_CHANGED",
                entity_type="DOCUMENT",
                entity_id=doc.id,
                actor_id=actor_id,
                change_diff={"old_status": old_status, "new_status": "UNDER_REVIEW"},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return await self.get_document(session, doc_id)

    async def archive_document(
        self,
        session: AsyncSession,
        doc_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Document:
        """Soft-archive a document while preserving physical storage file."""
        async with transaction(session):
            doc = await self.doc_repo.get_by_id_for_update(session, doc_id)
            if doc is None:
                raise NotFoundError("Document not found.")

            if doc.is_archived:
                raise ValidationAppError("Document is already archived.")

            old_status = doc.status
            doc.is_archived = True
            doc.archived_at = datetime.now(timezone.utc)
            doc.status = "ARCHIVED"
            await session.flush()

            await self.audit_repo.record(
                session,
                action="DOCUMENT_ARCHIVED",
                entity_type="DOCUMENT",
                entity_id=doc.id,
                actor_id=actor_id,
                change_diff={"old_status": old_status, "is_archived": True},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return await self.get_document(session, doc_id)
