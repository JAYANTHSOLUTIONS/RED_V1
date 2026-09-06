"""Public Property Discovery API endpoints.

Unauthenticated endpoints allowing public visitors to search, filter,
and view published properties by their human-readable public reference.
All private owner data and internal notes are strictly excluded server-side.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.common import SuccessEnvelope, success_envelope
from app.schemas.property import (
    PaginatedResponse,
    PropertyFilterParams,
    PublicPropertyResponse,
)
from app.services.property import PropertyService

router = APIRouter(prefix="/public/properties", tags=["Public Properties"])
property_service = PropertyService()


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[PublicPropertyResponse]],
    status_code=status.HTTP_200_OK,
    summary="Search and filter published properties",
)
async def list_public_properties(
    filters: PropertyFilterParams = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public search and discovery for live (PUBLISHED) properties only."""
    paginated = await property_service.list_public_properties(
        session=db, filters=filters
    )
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Published properties retrieved successfully.",
    )


@router.get(
    "/{public_reference}",
    response_model=SuccessEnvelope[PublicPropertyResponse],
    status_code=status.HTTP_200_OK,
    summary="View public property details by public reference",
)
async def get_public_property(
    public_reference: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve public property details by reference ID (e.g. PR-2026-000123)."""
    prop = await property_service.get_public_property(
        session=db, public_reference=public_reference
    )
    return success_envelope(
        data=prop.model_dump(mode="json"),
        message="Property retrieved successfully.",
    )
