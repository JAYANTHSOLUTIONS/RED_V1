"""Private Property Management API endpoints.

All endpoints require authentication and consultant authorization.
Exposes full property CRUD, lifecycle status actions, and image metadata management.
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.core.idempotency import IdempotencyService
from app.models.user import User
from app.schemas.common import SuccessEnvelope, success_envelope
from app.schemas.property import (
    PaginatedResponse,
    PrivatePropertyImageResponse,
    PrivatePropertyResponse,
    PropertyCreate,
    PropertyFilterParams,
    PropertyImageCreate,
    PropertyImageUpdate,
    PropertyUpdate,
)
from app.services.property import PropertyService

router = APIRouter(prefix="/properties", tags=["Properties"])
property_service = PropertyService()
idempotency_service = IdempotencyService()


@router.post(
    "",
    response_model=SuccessEnvelope[PrivatePropertyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new property listing",
)
async def create_property(
    payload: PropertyCreate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> dict:
    record_id = None
    if idempotency_key:
        cached_resp, record_id = await idempotency_service.check_or_reserve(
            session=db,
            key=idempotency_key,
            user_id=current_user.id,
            endpoint=request.url.path,
            payload=payload.model_dump(mode="json"),
        )
        if cached_resp:
            return cached_resp

    try:
        prop = await property_service.create_property(
            session=db,
            data=payload,
            actor_id=current_user.id,
            ip_address=get_ip_address(request),
            correlation_id=get_request_id(request),
        )
        resp = success_envelope(
            data=PrivatePropertyResponse.model_validate(prop).model_dump(mode="json"),
            message="Property created successfully in DRAFT status.",
        )
        if idempotency_key and record_id:
            await idempotency_service.finalize(db, record_id, status.HTTP_201_CREATED, resp)
        return resp
    except Exception:
        if idempotency_key and record_id:
            await idempotency_service.abort(db, record_id)
        raise


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[PrivatePropertyResponse]],
    status_code=status.HTTP_200_OK,
    summary="List properties with filters and pagination",
)
async def list_properties(
    filters: PropertyFilterParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    paginated = await property_service.list_private_properties(session=db, filters=filters)
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Properties retrieved successfully.",
    )


@router.get(
    "/{property_id}",
    response_model=SuccessEnvelope[PrivatePropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get property detail for consultant workspace",
)
async def get_property(
    property_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    prop = await property_service.get_property(session=db, property_id=property_id)
    return success_envelope(
        data=PrivatePropertyResponse.model_validate(prop).model_dump(mode="json"),
        message="Property retrieved successfully.",
    )


@router.patch(
    "/{property_id}",
    response_model=SuccessEnvelope[PrivatePropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Update property fields",
)
async def update_property(
    property_id: uuid.UUID,
    payload: PropertyUpdate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    prop = await property_service.update_property(
        session=db,
        property_id=property_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PrivatePropertyResponse.model_validate(prop).model_dump(mode="json"),
        message="Property updated successfully.",
    )


# ---------------------------------------------------------------------------
# Lifecycle Status Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{property_id}/publish",
    response_model=SuccessEnvelope[PrivatePropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Publish property to public discovery",
)
async def publish_property(
    property_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    prop = await property_service.publish_property(
        session=db,
        property_id=property_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PrivatePropertyResponse.model_validate(prop).model_dump(mode="json"),
        message="Property published successfully.",
    )


@router.post(
    "/{property_id}/pause",
    response_model=SuccessEnvelope[PrivatePropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Pause property listing from public discovery",
)
async def pause_property(
    property_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    prop = await property_service.pause_property(
        session=db,
        property_id=property_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PrivatePropertyResponse.model_validate(prop).model_dump(mode="json"),
        message="Property paused successfully.",
    )


@router.post(
    "/{property_id}/archive",
    response_model=SuccessEnvelope[PrivatePropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Soft-delete / archive property",
)
async def archive_property(
    property_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    prop = await property_service.archive_property(
        session=db,
        property_id=property_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PrivatePropertyResponse.model_validate(prop).model_dump(mode="json"),
        message="Property archived successfully.",
    )


@router.post(
    "/{property_id}/mark-sold",
    response_model=SuccessEnvelope[PrivatePropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark published property as sold",
)
async def mark_sold(
    property_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    prop = await property_service.mark_property_sold(
        session=db,
        property_id=property_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PrivatePropertyResponse.model_validate(prop).model_dump(mode="json"),
        message="Property marked as sold.",
    )


@router.post(
    "/{property_id}/mark-rented",
    response_model=SuccessEnvelope[PrivatePropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark published property as rented",
)
async def mark_rented(
    property_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    prop = await property_service.mark_property_rented(
        session=db,
        property_id=property_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PrivatePropertyResponse.model_validate(prop).model_dump(mode="json"),
        message="Property marked as rented.",
    )


# ---------------------------------------------------------------------------
# Image Metadata Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{property_id}/images",
    response_model=SuccessEnvelope[PrivatePropertyImageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add image metadata for a property",
)
async def add_image(
    property_id: uuid.UUID,
    payload: PropertyImageCreate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    image = await property_service.add_image(
        session=db,
        property_id=property_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PrivatePropertyImageResponse.model_validate(image).model_dump(mode="json"),
        message="Property image added successfully.",
    )


@router.get(
    "/{property_id}/images",
    response_model=SuccessEnvelope[List[PrivatePropertyImageResponse]],
    status_code=status.HTTP_200_OK,
    summary="List image metadata for a property",
)
async def list_images(
    property_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    images = await property_service.list_property_images(
        session=db, property_id=property_id
    )
    data = [
        PrivatePropertyImageResponse.model_validate(img).model_dump(mode="json")
        for img in images
    ]
    return success_envelope(data=data, message="Property images retrieved successfully.")


@router.patch(
    "/{property_id}/images/{image_id}",
    response_model=SuccessEnvelope[PrivatePropertyImageResponse],
    status_code=status.HTTP_200_OK,
    summary="Update property image metadata (order, primary)",
)
async def update_image(
    property_id: uuid.UUID,
    image_id: uuid.UUID,
    payload: PropertyImageUpdate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    image = await property_service.update_image(
        session=db,
        property_id=property_id,
        image_id=image_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=PrivatePropertyImageResponse.model_validate(image).model_dump(mode="json"),
        message="Property image updated successfully.",
    )


@router.delete(
    "/{property_id}/images/{image_id}",
    response_model=SuccessEnvelope[None],
    status_code=status.HTTP_200_OK,
    summary="Remove property image metadata",
)
async def delete_image(
    property_id: uuid.UUID,
    image_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await property_service.delete_image(
        session=db,
        property_id=property_id,
        image_id=image_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(data=None, message="Property image removed successfully.")
