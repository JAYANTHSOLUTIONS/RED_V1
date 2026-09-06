"""Private Document Management and Secure Storage API endpoints.

All endpoints require authentication and consultant authorization.
Exposes multipart upload, metadata listing, streaming download, review transition,
and soft-archival.
"""
from typing import Optional
import urllib.parse
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.schemas.document import (
    DocumentFilterParams,
    DocumentResponse,
    DocumentUpdate,
)
from app.services.document import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents"])
document_service = DocumentService()


@router.post(
    "",
    response_model=SuccessEnvelope[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new private document",
)
async def upload_document(
    request: Request,
    file: UploadFile = File(..., description="Document file to upload (.pdf, .jpg, .png)"),
    document_type: str = Form(..., description="Document category (e.g. SALE_DEED, EC, PATTA)"),
    property_id: Optional[uuid.UUID] = Form(None, description="Optional associated property UUID"),
    client_id: Optional[uuid.UUID] = Form(None, description="Optional associated client UUID"),
    notes: Optional[str] = Form(None, description="Optional notes or registration details"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
    correlation_id: Optional[str] = Depends(get_request_id),
    ip_address: Optional[str] = Depends(get_ip_address),
) -> SuccessEnvelope[DocumentResponse]:
    """Upload a private property or client document with binary validation."""
    file_bytes = await file.read()
    filename = file.filename or "uploaded_file"

    doc = await document_service.upload_document(
        session=session,
        file_bytes=file_bytes,
        original_filename=filename,
        document_type=document_type,
        property_id=property_id,
        client_id=client_id,
        notes=notes,
        actor_id=current_user.id,
        ip_address=ip_address,
        correlation_id=correlation_id,
    )
    return success_envelope(
        data=DocumentResponse.model_validate(doc),
        message="Document uploaded successfully.",
    )


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[DocumentResponse]],
    summary="List documents with filtering and pagination",
)
async def list_documents(
    filters: DocumentFilterParams = Depends(),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[PaginatedResponse[DocumentResponse]]:
    """List documents filtered by property, client, document type, status, or archival state."""
    result = await document_service.list_documents(session, filters)
    return success_envelope(data=result)


@router.get(
    "/{document_id}",
    response_model=SuccessEnvelope[DocumentResponse],
    summary="Get document metadata",
)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[DocumentResponse]:
    """Retrieve document metadata by UUID."""
    doc = await document_service.get_document(session, document_id)
    return success_envelope(data=DocumentResponse.model_validate(doc))


@router.get(
    "/{document_id}/download",
    summary="Download private document file",
)
async def download_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
    correlation_id: Optional[str] = Depends(get_request_id),
    ip_address: Optional[str] = Depends(get_ip_address),
) -> StreamingResponse:
    """Stream private document binary safely with authorization and audit logging."""
    stream, size, content_type, filename = await document_service.download_document(
        session=session,
        doc_id=document_id,
        actor_id=current_user.id,
        ip_address=ip_address,
        correlation_id=correlation_id,
    )
    # RFC 5987 / safe filename encoding
    safe_filename = urllib.parse.quote(filename)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"; filename*=UTF-8\'\'{safe_filename}',
        "Content-Length": str(size),
    }
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers=headers,
    )


@router.patch(
    "/{document_id}",
    response_model=SuccessEnvelope[DocumentResponse],
    summary="Update document metadata",
)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
    correlation_id: Optional[str] = Depends(get_request_id),
    ip_address: Optional[str] = Depends(get_ip_address),
) -> SuccessEnvelope[DocumentResponse]:
    """Update document type or notes for an active document."""
    doc = await document_service.update_document(
        session=session,
        doc_id=document_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=ip_address,
        correlation_id=correlation_id,
    )
    return success_envelope(
        data=DocumentResponse.model_validate(doc),
        message="Document updated successfully.",
    )


@router.post(
    "/{document_id}/review",
    response_model=SuccessEnvelope[DocumentResponse],
    summary="Transition document status to UNDER_REVIEW",
)
async def review_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
    correlation_id: Optional[str] = Depends(get_request_id),
    ip_address: Optional[str] = Depends(get_ip_address),
) -> SuccessEnvelope[DocumentResponse]:
    """Transition document from UPLOADED to UNDER_REVIEW."""
    doc = await document_service.review_document(
        session=session,
        doc_id=document_id,
        actor_id=current_user.id,
        ip_address=ip_address,
        correlation_id=correlation_id,
    )
    return success_envelope(
        data=DocumentResponse.model_validate(doc),
        message="Document status transitioned to UNDER_REVIEW.",
    )


@router.post(
    "/{document_id}/archive",
    response_model=SuccessEnvelope[DocumentResponse],
    summary="Soft-archive a document",
)
async def archive_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
    correlation_id: Optional[str] = Depends(get_request_id),
    ip_address: Optional[str] = Depends(get_ip_address),
) -> SuccessEnvelope[DocumentResponse]:
    """Soft-archive a document, preserving physical file on storage."""
    doc = await document_service.archive_document(
        session=session,
        doc_id=document_id,
        actor_id=current_user.id,
        ip_address=ip_address,
        correlation_id=correlation_id,
    )
    return success_envelope(
        data=DocumentResponse.model_validate(doc),
        message="Document archived successfully.",
    )
