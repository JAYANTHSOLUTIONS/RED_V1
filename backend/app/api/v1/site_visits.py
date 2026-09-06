"""Site Visit Coordination API endpoints.

Exposes customer visit request submission, consultant schedule management,
conflict-checked confirmation, rescheduling, cancellation, and completion.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.schemas.site_visit import (
    SiteVisitCancel,
    SiteVisitComplete,
    SiteVisitConfirm,
    SiteVisitCreate,
    SiteVisitFilterParams,
    SiteVisitPrivateResponse,
    SiteVisitPublicRequest,
    SiteVisitPublicResponse,
    SiteVisitReschedule,
    SiteVisitUpdate,
)
from app.services.site_visit import SiteVisitService

router = APIRouter(prefix="/site-visits", tags=["Site Visits"])
site_visit_service = SiteVisitService()


# --- Public Customer Endpoints ---

@router.post(
    "/request",
    response_model=SuccessEnvelope[SiteVisitPublicResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Public / Customer request for a property visit",
)
async def request_site_visit(
    payload: SiteVisitPublicRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a customer visit request. Status is always initialised to REQUESTED."""
    visit = await site_visit_service.request_visit(
        session=db,
        data=payload,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=SiteVisitPublicResponse.model_validate(visit).model_dump(mode="json"),
        message="Site visit request submitted successfully. Awaiting consultant confirmation.",
    )


@router.get(
    "/{visit_id}/public",
    response_model=SuccessEnvelope[SiteVisitPublicResponse],
    status_code=status.HTTP_200_OK,
    summary="Public view of a site visit status",
)
async def get_public_site_visit(
    visit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve public status of a site visit without exposing internal consultant notes."""
    visit = await site_visit_service.get_visit(session=db, visit_id=visit_id)
    return success_envelope(
        data=SiteVisitPublicResponse.model_validate(visit).model_dump(mode="json"),
        message="Site visit details retrieved successfully.",
    )


# --- Private Consultant Endpoints ---

@router.post(
    "",
    response_model=SuccessEnvelope[SiteVisitPrivateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new site visit (Consultant)",
)
async def create_site_visit(
    payload: SiteVisitCreate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Consultant directly schedules a visit for a client in REQUESTED or CONFIRMED status."""
    visit = await site_visit_service.create_visit(
        session=db,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=SiteVisitPrivateResponse.model_validate(visit).model_dump(mode="json"),
        message=f"Site visit created successfully in {visit.status} status.",
    )


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[SiteVisitPrivateResponse]],
    status_code=status.HTTP_200_OK,
    summary="List site visits with filters and pagination (Consultant)",
)
async def list_site_visits(
    filters: SiteVisitFilterParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Query site visits with status, client, property, date range filters and pagination."""
    paginated = await site_visit_service.list_visits(session=db, filters=filters)
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Site visits retrieved successfully.",
    )


@router.get(
    "/{visit_id}",
    response_model=SuccessEnvelope[SiteVisitPrivateResponse],
    status_code=status.HTTP_200_OK,
    summary="Get full site visit details (Consultant)",
)
async def get_site_visit(
    visit_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve full visit details including consultant notes, client and property summaries."""
    visit = await site_visit_service.get_visit(session=db, visit_id=visit_id)
    return success_envelope(
        data=SiteVisitPrivateResponse.model_validate(visit).model_dump(mode="json"),
        message="Site visit retrieved successfully.",
    )


@router.patch(
    "/{visit_id}",
    response_model=SuccessEnvelope[SiteVisitPrivateResponse],
    status_code=status.HTTP_200_OK,
    summary="Update editable site visit fields (Consultant)",
)
async def update_site_visit(
    visit_id: uuid.UUID,
    payload: SiteVisitUpdate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update notes, feedback, or requested schedule."""
    visit = await site_visit_service.update_visit(
        session=db,
        visit_id=visit_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=SiteVisitPrivateResponse.model_validate(visit).model_dump(mode="json"),
        message="Site visit updated successfully.",
    )


@router.post(
    "/{visit_id}/confirm",
    response_model=SuccessEnvelope[SiteVisitPrivateResponse],
    status_code=status.HTTP_200_OK,
    summary="Confirm a requested site visit (Consultant)",
)
async def confirm_site_visit(
    visit_id: uuid.UUID,
    request: Request,
    payload: Optional[SiteVisitConfirm] = None,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Confirm a requested visit. Conflict checking is strictly enforced."""
    visit = await site_visit_service.confirm_visit(
        session=db,
        visit_id=visit_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=SiteVisitPrivateResponse.model_validate(visit).model_dump(mode="json"),
        message="Site visit confirmed successfully.",
    )


@router.post(
    "/{visit_id}/complete",
    response_model=SuccessEnvelope[SiteVisitPrivateResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark a confirmed site visit as completed (Consultant)",
)
async def complete_site_visit(
    visit_id: uuid.UUID,
    request: Request,
    payload: Optional[SiteVisitComplete] = None,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Transition a confirmed visit to completed status with optional feedback."""
    visit = await site_visit_service.complete_visit(
        session=db,
        visit_id=visit_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=SiteVisitPrivateResponse.model_validate(visit).model_dump(mode="json"),
        message="Site visit marked as completed.",
    )


@router.post(
    "/{visit_id}/cancel",
    response_model=SuccessEnvelope[SiteVisitPrivateResponse],
    status_code=status.HTTP_200_OK,
    summary="Cancel a site visit with mandatory reason (Consultant)",
)
async def cancel_site_visit(
    visit_id: uuid.UUID,
    payload: SiteVisitCancel,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a visit. Preserves historical records with mandatory cancellation reason."""
    visit = await site_visit_service.cancel_visit(
        session=db,
        visit_id=visit_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=SiteVisitPrivateResponse.model_validate(visit).model_dump(mode="json"),
        message="Site visit cancelled.",
    )


@router.post(
    "/{visit_id}/reschedule",
    response_model=SuccessEnvelope[SiteVisitPrivateResponse],
    status_code=status.HTTP_200_OK,
    summary="Reschedule a site visit to a new date/time (Consultant)",
)
async def reschedule_site_visit(
    visit_id: uuid.UUID,
    payload: SiteVisitReschedule,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Reschedule a visit. Marks the old visit as RESCHEDULED and creates a new linked confirmed visit."""
    new_visit = await site_visit_service.reschedule_visit(
        session=db,
        visit_id=visit_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=SiteVisitPrivateResponse.model_validate(new_visit).model_dump(mode="json"),
        message="Site visit rescheduled successfully.",
    )
