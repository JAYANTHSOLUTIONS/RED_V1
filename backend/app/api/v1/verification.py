"""API endpoints for Tamil Nadu Preliminary Property Verification.

All endpoints require authentication and consultant authorization.
Exposes preliminary verification assessment execution, historical retrieval,
and case management.
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.schemas.verification import (
    ConsultantActionItemSchema,
    EvidenceIntelligenceReport,
    PropertyVerificationInput,
    VerificationCaseResponse,
    VerificationCaseSummary,
    VerificationCaseUpdate,
    VerificationFilterParams,
    VerificationSummaryResponse,
)
from app.services.verification import VerificationService

router = APIRouter(tags=["Preliminary Property Verification"])
verification_service = VerificationService()


@router.post(
    "/properties/{property_id}/verification",
    response_model=SuccessEnvelope[VerificationCaseResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Execute preliminary Tamil Nadu property verification",
)
async def run_property_verification(
    property_id: uuid.UUID,
    request: Request,
    payload: Optional[PropertyVerificationInput] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[VerificationCaseResponse]:
    """Execute deterministic Tamil Nadu preliminary verification on a property.

    Evaluates survey & subdivision consistency, extent tolerance, owner name matching,
    EC period & entries, Patta & land records, CMDA/DTCP planning permissions, and TNRERA.
    """
    res = await verification_service.run_verification(
        session=session,
        property_id=property_id,
        payload=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=res,
        message="Preliminary property verification executed successfully.",
    )


@router.get(
    "/properties/{property_id}/verification",
    response_model=SuccessEnvelope[VerificationCaseResponse],
    summary="Get latest preliminary verification assessment for a property",
)
async def get_latest_property_verification(
    property_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[VerificationCaseResponse]:
    """Retrieve the most recent preliminary verification assessment for a property."""
    res = await verification_service.get_latest_for_property(
        session=session, property_id=property_id
    )
    return success_envelope(data=res)


@router.get(
    "/properties/{property_id}/verification/summary",
    response_model=SuccessEnvelope[VerificationSummaryResponse],
    summary="Get machine-readable summary metrics for property verification",
)
async def get_property_verification_summary(
    property_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[VerificationSummaryResponse]:
    """Retrieve high-level verification summary metrics, counts, and overall status."""
    res = await verification_service.get_verification_summary(
        session=session, property_id=property_id
    )
    return success_envelope(data=res)


@router.get(
    "/properties/{property_id}/verification/evidence",
    response_model=SuccessEnvelope[EvidenceIntelligenceReport],
    summary="Get detailed documentary evidence intelligence report",
)
async def get_property_verification_evidence(
    property_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[EvidenceIntelligenceReport]:
    """Retrieve detailed documentary evidence analysis including status, confidence, and missing documents."""
    res = await verification_service.get_verification_evidence(
        session=session, property_id=property_id
    )
    return success_envelope(data=res)


@router.get(
    "/properties/{property_id}/verification/actions",
    response_model=SuccessEnvelope[List[ConsultantActionItemSchema]],
    summary="Get prioritized consultant action recommendations",
)
async def get_property_verification_actions(
    property_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[List[ConsultantActionItemSchema]]:
    """Retrieve prioritized practical action steps recommended for the consultant."""
    res = await verification_service.get_verification_actions(
        session=session, property_id=property_id
    )
    return success_envelope(data=res)


@router.get(
    "/verifications/{verification_id}",
    response_model=SuccessEnvelope[VerificationCaseResponse],
    summary="Get specific verification case by ID",
)
@router.get(
    "/verification/{verification_id}",
    response_model=SuccessEnvelope[VerificationCaseResponse],
    include_in_schema=False,
)
async def get_verification_by_id(
    verification_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[VerificationCaseResponse]:
    """Retrieve detailed verification case by its UUID."""
    res = await verification_service.get_verification(
        session=session, verification_id=verification_id
    )
    return success_envelope(data=res)


@router.get(
    "/verifications",
    response_model=SuccessEnvelope[PaginatedResponse[VerificationCaseSummary]],
    summary="List verification cases with filtering and pagination",
)
async def list_verifications(
    filters: VerificationFilterParams = Depends(),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[PaginatedResponse[VerificationCaseSummary]]:
    """List historical verification assessments with optional status or property filter."""
    res = await verification_service.list_verifications(session=session, filters=filters)
    return success_envelope(data=res)


@router.patch(
    "/verifications/{verification_id}",
    response_model=SuccessEnvelope[VerificationCaseResponse],
    summary="Update verification case observations or disclaimer acknowledgement",
)
async def update_verification(
    verification_id: uuid.UUID,
    payload: VerificationCaseUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> SuccessEnvelope[VerificationCaseResponse]:
    """Update consultant observations, missing documents notes, or disclaimer acknowledgement."""
    res = await verification_service.update_verification(
        session=session,
        verification_id=verification_id,
        payload=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=res,
        message="Verification case updated successfully.",
    )
