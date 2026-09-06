"""Private Client Management API endpoints.

All endpoints require authentication and consultant authorization.
Exposes client CRUD, search/filtering, pagination, and soft-archival.
"""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.client import (
    ClientCreate,
    ClientFilterParams,
    ClientResponse,
    ClientUpdate,
    ClientWithLeadsResponse,
)
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.services.client import ClientService

router = APIRouter(prefix="/clients", tags=["Clients"])
client_service = ClientService()


@router.post(
    "",
    response_model=SuccessEnvelope[ClientResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new client profile",
)
async def create_client(
    payload: ClientCreate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    client = await client_service.create_client(
        session=db,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=ClientResponse.model_validate(client).model_dump(mode="json"),
        message="Client profile created successfully.",
    )


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[ClientResponse]],
    status_code=status.HTTP_200_OK,
    summary="List clients with filters and pagination",
)
async def list_clients(
    filters: ClientFilterParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    paginated = await client_service.list_clients(session=db, filters=filters)
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Clients retrieved successfully.",
    )


@router.get(
    "/{client_id}",
    response_model=SuccessEnvelope[ClientWithLeadsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get client details with associated leads",
)
async def get_client(
    client_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    client = await client_service.get_client(session=db, client_id=client_id, include_leads=True)
    return success_envelope(
        data=ClientWithLeadsResponse.model_validate(client).model_dump(mode="json"),
        message="Client details retrieved successfully.",
    )


@router.patch(
    "/{client_id}",
    response_model=SuccessEnvelope[ClientWithLeadsResponse],
    status_code=status.HTTP_200_OK,
    summary="Update client details",
)
async def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    client = await client_service.update_client(
        session=db,
        client_id=client_id,
        data=payload,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=ClientWithLeadsResponse.model_validate(client).model_dump(mode="json"),
        message="Client updated successfully.",
    )


@router.post(
    "/{client_id}/archive",
    response_model=SuccessEnvelope[ClientWithLeadsResponse],
    status_code=status.HTTP_200_OK,
    summary="Archive client profile (soft-delete)",
)
async def archive_client(
    client_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    client = await client_service.archive_client(
        session=db,
        client_id=client_id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=ClientWithLeadsResponse.model_validate(client).model_dump(mode="json"),
        message="Client archived successfully.",
    )
