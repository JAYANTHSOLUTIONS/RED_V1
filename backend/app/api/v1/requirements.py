"""Private Property Requirements and Matching API endpoints.

All endpoints require authentication and consultant authorization.
Exposes requirement CRUD, lifecycle actions, and deterministic matching.
"""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.schemas.requirement import (
    PropertyMatchItem,
    PropertyRequirementCreate,
    PropertyRequirementResponse,
    PropertyRequirementUpdate,
    RequirementFilterParams,
    RequirementMatchParams,
)
from app.services.requirement import PropertyRequirementService

router = APIRouter(prefix="/property-requirements", tags=["Property Requirements"])
requirement_service = PropertyRequirementService()


@router.post(
    "",
    response_model=SuccessEnvelope[PropertyRequirementResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer property requirement",
)
async def create_requirement(
    payload: PropertyRequirementCreate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await requirement_service.create_requirement(
        session=db,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PropertyRequirementResponse.model_validate(req).model_dump(mode="json"),
        message="Property requirement created successfully in ACTIVE status.",
    )


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[PropertyRequirementResponse]],
    status_code=status.HTTP_200_OK,
    summary="List property requirements with filters and pagination",
)
async def list_requirements(
    filters: RequirementFilterParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    paginated = await requirement_service.list_requirements(session=db, filters=filters)
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Property requirements retrieved successfully.",
    )


@router.get(
    "/{requirement_id}",
    response_model=SuccessEnvelope[PropertyRequirementResponse],
    status_code=status.HTTP_200_OK,
    summary="Get property requirement details",
)
async def get_requirement(
    requirement_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await requirement_service.get_requirement(session=db, req_id=requirement_id)
    return success_envelope(
        data=PropertyRequirementResponse.model_validate(req).model_dump(mode="json"),
        message="Property requirement retrieved successfully.",
    )


@router.patch(
    "/{requirement_id}",
    response_model=SuccessEnvelope[PropertyRequirementResponse],
    status_code=status.HTTP_200_OK,
    summary="Update property requirement fields",
)
async def update_requirement(
    requirement_id: uuid.UUID,
    payload: PropertyRequirementUpdate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await requirement_service.update_requirement(
        session=db,
        req_id=requirement_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PropertyRequirementResponse.model_validate(req).model_dump(mode="json"),
        message="Property requirement updated successfully.",
    )


# ---------------------------------------------------------------------------
# Lifecycle Transition Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{requirement_id}/fulfill",
    response_model=SuccessEnvelope[PropertyRequirementResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition requirement to FULFILLED",
)
async def fulfill_requirement(
    requirement_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await requirement_service.fulfill_requirement(
        session=db,
        req_id=requirement_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PropertyRequirementResponse.model_validate(req).model_dump(mode="json"),
        message="Property requirement marked as FULFILLED.",
    )


@router.post(
    "/{requirement_id}/cancel",
    response_model=SuccessEnvelope[PropertyRequirementResponse],
    status_code=status.HTTP_200_OK,
    summary="Transition requirement to CANCELLED",
)
async def cancel_requirement(
    requirement_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await requirement_service.cancel_requirement(
        session=db,
        req_id=requirement_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PropertyRequirementResponse.model_validate(req).model_dump(mode="json"),
        message="Property requirement marked as CANCELLED.",
    )


@router.post(
    "/{requirement_id}/archive",
    response_model=SuccessEnvelope[PropertyRequirementResponse],
    status_code=status.HTTP_200_OK,
    summary="Soft-archive requirement",
)
async def archive_requirement(
    requirement_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    req = await requirement_service.archive_requirement(
        session=db,
        req_id=requirement_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PropertyRequirementResponse.model_validate(req).model_dump(mode="json"),
        message="Property requirement archived successfully.",
    )


# ---------------------------------------------------------------------------
# Matching Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/{requirement_id}/matches",
    response_model=SuccessEnvelope[PaginatedResponse[PropertyMatchItem]],
    status_code=status.HTTP_200_OK,
    summary="Evaluate and return matching properties with explainability",
)
async def find_matches(
    requirement_id: uuid.UUID,
    request: Request,
    params: RequirementMatchParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    paginated = await requirement_service.find_matches(
        session=db,
        req_id=requirement_id,
        params=params,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Matching properties evaluated successfully.",
    )
