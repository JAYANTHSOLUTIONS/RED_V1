"""Client Management service.

Enforces client business rules, soft-archival safeguards, and audit logging.
"""
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.session import transaction
from app.models.client import Client
from app.repositories.audit import AuditRepository
from app.repositories.client import ClientRepository
from app.schemas.client import (
    ClientCreate,
    ClientFilterParams,
    ClientResponse,
    ClientUpdate,
    ClientWithLeadsResponse,
)
from app.schemas.common import PaginatedResponse


class ClientService:
    def __init__(
        self,
        client_repo: Optional[ClientRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.client_repo = client_repo or ClientRepository()
        self.audit_repo = audit_repo or AuditRepository()

    async def create_client(
        self,
        session: AsyncSession,
        data: ClientCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Client:
        """Create a new client and record audit log."""
        async with transaction(session):
            client = Client(
                full_name=data.full_name,
                phone=data.phone,
                email=data.email,
                preferred_contact_method=data.preferred_contact_method,
                postal_address=data.postal_address,
                classification=data.classification,
                source=data.source,
                status="ACTIVE",
                notes=data.notes,
                is_archived=False,
            )
            await self.client_repo.create(session, client)

            await self.audit_repo.record(
                session,
                action="CLIENT_CREATED",
                entity_type="CLIENT",
                entity_id=client.id,
                actor_id=actor_id,
                change_diff={
                    "full_name": client.full_name,
                    "phone": client.phone,
                    "email": client.email,
                    "classification": client.classification,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return await self.get_client(session, client.id, include_leads=False)

    async def get_client(
        self,
        session: AsyncSession,
        client_id: uuid.UUID,
        include_leads: bool = True,
    ) -> Client:
        """Retrieve client record or raise NotFoundError."""
        client = await self.client_repo.get_by_id(
            session, client_id, include_leads=include_leads
        )
        if client is None:
            raise NotFoundError("Client not found.")
        return client

    async def update_client(
        self,
        session: AsyncSession,
        client_id: uuid.UUID,
        data: ClientUpdate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Client:
        """Update client fields with row-level lock and audit log."""
        async with transaction(session):
            client = await self.client_repo.get_by_id_for_update(session, client_id)
            if client is None:
                raise NotFoundError("Client not found.")

            if client.is_archived:
                raise ValidationAppError("Cannot modify an archived client.")

            update_dict = data.model_dump(exclude_unset=True)
            if update_dict:
                await self.client_repo.update(session, client, update_dict)
                await self.audit_repo.record(
                    session,
                    action="CLIENT_UPDATED",
                    entity_type="CLIENT",
                    entity_id=client.id,
                    actor_id=actor_id,
                    change_diff={k: str(v) for k, v in update_dict.items()},
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )

            await session.refresh(client)

        return await self.get_client(session, client.id, include_leads=True)

    async def list_clients(
        self,
        session: AsyncSession,
        filters: ClientFilterParams,
    ) -> PaginatedResponse[ClientResponse]:
        """List clients with filtering and database-level pagination."""
        clients, total = await self.client_repo.list_clients(session, filters)
        items = [ClientResponse.model_validate(c) for c in clients]
        return PaginatedResponse[ClientResponse](
            items=items,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def archive_client(
        self,
        session: AsyncSession,
        client_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Client:
        """Soft-archive a client (idempotent if already archived)."""
        async with transaction(session):
            client = await self.client_repo.get_by_id_for_update(session, client_id)
            if client is None:
                raise NotFoundError("Client not found.")

            if not client.is_archived:
                old_status = client.status
                await self.client_repo.archive(session, client)

                await self.audit_repo.record(
                    session,
                    action="CLIENT_ARCHIVED",
                    entity_type="CLIENT",
                    entity_id=client.id,
                    actor_id=actor_id,
                    change_diff={
                        "old_status": old_status,
                        "new_status": "ARCHIVED",
                        "is_archived": True,
                    },
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )
                await session.refresh(client)

        return await self.get_client(session, client_id, include_leads=True)
