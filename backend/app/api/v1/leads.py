"""Private Lead Management API endpoints.

All endpoints require authentication and consultant authorization.
Exposes lead CRUD, search/filtering, pagination, and strict lifecycle status transitions.
"""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.schemas.lead import (
    LeadCreate,
    LeadFilterParams,
    LeadLostPayload,
    LeadResponse,
    LeadUpdate,
)
from app.services.lead import LeadService

router = APIRouter(prefix="/leads", tags=["Leads"])
lead_service = LeadService()


@router.post(
    "",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new sales lead",
)
async def create_lead(
    payload: LeadCreate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.create_lead(
        session=db,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead created successfully in NEW status.",
    )


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[LeadResponse]],
    status_code=status.HTTP_200_OK,
    summary="List leads with filters and pagination",
)
async def list_leads(
    filters: LeadFilterParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    paginated = await lead_service.list_leads(session=db, filters=filters)
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Leads retrieved successfully.",
    )


@router.get(
    "/{lead_id}",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Get lead details",
)
async def get_lead(
    lead_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.get_lead(session=db, lead_id=lead_id)
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead details retrieved successfully.",
    )


@router.patch(
    "/{lead_id}",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Update non-lifecycle lead fields",
)
async def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.update_lead(
        session=db,
        lead_id=lead_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead updated successfully.",
    )


# ---------------------------------------------------------------------------
# Lifecycle State Transition Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{lead_id}/contact",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition lead to CONTACTED",
)
async def contact_lead(
    lead_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.contact_lead(
        session=db,
        lead_id=lead_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead marked as CONTACTED.",
    )


@router.post(
    "/{lead_id}/mark-interested",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition lead to INTERESTED",
)
async def mark_interested(
    lead_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.mark_interested(
        session=db,
        lead_id=lead_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead marked as INTERESTED.",
    )


@router.post(
    "/{lead_id}/site-visit-stage",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition lead to SITE_VISIT stage",
)
async def schedule_site_visit_stage(
    lead_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.schedule_site_visit_stage(
        session=db,
        lead_id=lead_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead moved to SITE_VISIT stage.",
    )


@router.post(
    "/{lead_id}/negotiation",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition lead to NEGOTIATION stage",
)
async def move_to_negotiation(
    lead_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.move_to_negotiation(
        session=db,
        lead_id=lead_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead moved to NEGOTIATION stage.",
    )


@router.post(
    "/{lead_id}/convert",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition lead to CONVERTED (terminal)",
)
async def convert_lead(
    lead_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.convert_lead(
        session=db,
        lead_id=lead_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead marked as CONVERTED.",
    )


@router.post(
    "/{lead_id}/lost",
    response_model=SuccessEnvelope[LeadResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition lead to LOST with mandatory reason (terminal)",
)
async def mark_lost(
    lead_id: uuid.UUID,
    payload: LeadLostPayload,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    lead = await lead_service.mark_lost(
        session=db,
        lead_id=lead_id,
        lost_reason=payload.lost_reason,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=LeadResponse.model_validate(lead).model_dump(mode="json"),
        message="Lead marked as LOST.",
    )
