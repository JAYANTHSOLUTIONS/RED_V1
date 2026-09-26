"""FMB Map Generation API endpoints.

Provides secure, server-side FMB map generation via the Tamil Nadu
CollabLand government GIS service. All government API implementation
details, credentials, and raw response data are handled exclusively
on the server — never exposed to the browser.

Routes:
  POST /fmb/properties/{property_id}/generate  — Generate FMB map PDF
  POST /fmb/properties/{property_id}/save      — Save generated PDF to Document Vault
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import SuccessEnvelope, success_envelope
from app.schemas.fmb import (
    FmbGenerateRequest,
    FmbGenerateResponse,
    FmbSaveRequest,
    FmbSaveResponse,
)
from app.services import fmb_service

router = APIRouter(prefix="/fmb", tags=["FMB Map Generation"])


@router.post(
    "/properties/{property_id}/generate",
    response_model=SuccessEnvelope[FmbGenerateResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate FMB map PDF from CollabLand",
)
async def generate_fmb_map(
    property_id: uuid.UUID,
    payload: FmbGenerateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[FmbGenerateResponse]:
    """Fetch property location, construct GIS code, call CollabLand FMB Map Service,
    decode and validate the returned PDF, and return it as Base64 for client preview/download.

    The user can then optionally save the result to the Document Vault via the /save endpoint.
    Raw government API internals and credentials are never forwarded to the browser.
    """
    result = await fmb_service.generate_fmb_map(
        session=session,
        property_id=property_id,
        survey_number=payload.survey_number,
        subdivision_number=payload.subdivision_number,
    )
    return success_envelope(
        data=FmbGenerateResponse(**result),
        message="FMB map generated successfully.",
    )


@router.post(
    "/properties/{property_id}/save",
    response_model=SuccessEnvelope[FmbSaveResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Save generated FMB map to Property Document Vault",
)
async def save_fmb_to_vault(
    property_id: uuid.UUID,
    payload: FmbSaveRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
    correlation_id: Optional[str] = Depends(get_request_id),
    ip_address: Optional[str] = Depends(get_ip_address),
) -> SuccessEnvelope[FmbSaveResponse]:
    """Decode the Base64 PDF received from the generate step, validate it,
    check for duplicates, and persist it to the Property Document Vault.

    Duplicate behaviour:
    - If an FMB map already exists for the same survey/subdivision and
      force_duplicate=False (default), returns HTTP 409.
    - If force_duplicate=True, saves a new copy regardless.
    """
    doc, duplicate_existed = await fmb_service.save_fmb_to_vault(
        session=session,
        property_id=property_id,
        survey_number=payload.survey_number,
        subdivision_number=payload.subdivision_number,
        pdf_base64=payload.pdf_base64,
        filename=payload.filename,
        actor_id=current_user.id,
        ip_address=ip_address,
        correlation_id=correlation_id,
        force_duplicate=payload.force_duplicate,
    )
    return success_envelope(
        data=FmbSaveResponse(
            document_id=doc.id,
            document_type=doc.document_type,
            original_filename=doc.original_filename,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            status=doc.status,
            notes=doc.notes,
            created_at=doc.created_at.isoformat(),
            duplicate_existed=duplicate_existed,
            source="CollabLand",
        ),
        message="FMB map saved to Document Vault successfully.",
    )
