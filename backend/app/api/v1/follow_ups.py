"""Follow-up Management API endpoints.

Exposes consultant follow-up task tracking, lifecycle state machine
(SCHEDULED -> COMPLETED / MISSED), filtering, and pagination.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.schemas.follow_up import (
    FollowUpComplete,
    FollowUpCreate,
    FollowUpFilterParams,
    FollowUpMiss,
    FollowUpResponse,
    FollowUpUpdate,
)
from app.services.follow_up import FollowUpService

router = APIRouter(prefix="/follow-ups", tags=["Follow-ups"])
follow_up_service = FollowUpService()


@router.post(
    "",
    response_model=SuccessEnvelope[FollowUpResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new follow-up task (Consultant)",
)
async def create_follow_up(
    payload: FollowUpCreate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new follow-up task in SCHEDULED status targeting a Client or Lead."""
    follow_up = await follow_up_service.create_follow_up(
        session=db,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=FollowUpResponse.model_validate(follow_up).model_dump(mode="json"),
        message="Follow-up task scheduled successfully.",
    )


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[FollowUpResponse]],
    status_code=status.HTTP_200_OK,
    summary="List follow-up tasks with filters and pagination (Consultant)",
)
async def list_follow_ups(
    filters: FollowUpFilterParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Query follow-up tasks with status, action_type, client, lead, property, and date range filters."""
    paginated = await follow_up_service.list_follow_ups(session=db, filters=filters)
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Follow-up tasks retrieved successfully.",
    )


@router.get(
    "/{follow_up_id}",
    response_model=SuccessEnvelope[FollowUpResponse],
    status_code=status.HTTP_200_OK,
    summary="Get follow-up task details (Consultant)",
)
async def get_follow_up(
    follow_up_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve full details of a specific follow-up task."""
    follow_up = await follow_up_service.get_follow_up(session=db, follow_up_id=follow_up_id)
    return success_envelope(
        data=FollowUpResponse.model_validate(follow_up).model_dump(mode="json"),
        message="Follow-up details retrieved successfully.",
    )


@router.patch(
    "/{follow_up_id}",
    response_model=SuccessEnvelope[FollowUpResponse],
    status_code=status.HTTP_200_OK,
    summary="Update editable follow-up fields (Consultant)",
)
async def update_follow_up(
    follow_up_id: uuid.UUID,
    payload: FollowUpUpdate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update follow-up metadata (action_type, scheduled_at, notes, property_id)."""
    follow_up = await follow_up_service.update_follow_up(
        session=db,
        follow_up_id=follow_up_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=FollowUpResponse.model_validate(follow_up).model_dump(mode="json"),
        message="Follow-up task updated successfully.",
    )


@router.post(
    "/{follow_up_id}/complete",
    response_model=SuccessEnvelope[FollowUpResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark follow-up as completed (Consultant)",
)
async def complete_follow_up(
    follow_up_id: uuid.UUID,
    request: Request,
    payload: Optional[FollowUpComplete] = None,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Transition a scheduled follow-up to COMPLETED status."""
    follow_up = await follow_up_service.complete_follow_up(
        session=db,
        follow_up_id=follow_up_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=FollowUpResponse.model_validate(follow_up).model_dump(mode="json"),
        message="Follow-up task marked as completed.",
    )


@router.post(
    "/{follow_up_id}/miss",
    response_model=SuccessEnvelope[FollowUpResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark follow-up as missed (Consultant)",
)
async def mark_missed_follow_up(
    follow_up_id: uuid.UUID,
    request: Request,
    payload: Optional[FollowUpMiss] = None,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Transition a scheduled follow-up to MISSED status."""
    follow_up = await follow_up_service.mark_missed_follow_up(
        session=db,
        follow_up_id=follow_up_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=FollowUpResponse.model_validate(follow_up).model_dump(mode="json"),
        message="Follow-up task marked as missed.",
    )
