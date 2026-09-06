"""Client repository for database access."""
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.client import Client
from app.models.lead import Lead
from app.schemas.client import ClientFilterParams


class ClientRepository:
    async def create(self, session: AsyncSession, client_obj: Client) -> Client:
        session.add(client_obj)
        await session.flush()
        return client_obj

    async def get_by_id(
        self,
        session: AsyncSession,
        client_id: uuid.UUID,
        include_leads: bool = False,
    ) -> Optional[Client]:
        stmt = select(Client).where(Client.id == client_id)
        if include_leads:
            stmt = stmt.options(selectinload(Client.leads))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, client_id: uuid.UUID
    ) -> Optional[Client]:
        """Fetch client with row-level locking (SELECT FOR UPDATE)."""
        stmt = select(Client).where(Client.id == client_id).with_for_update()
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_clients(
        self,
        session: AsyncSession,
        filters: ClientFilterParams,
    ) -> Tuple[List[Client], int]:
        """Query clients with parameterized filtering and database-level pagination."""
        stmt = select(Client)
        count_stmt = select(func.count(Client.id))

        conditions = []

        if filters.is_archived is not None:
            conditions.append(Client.is_archived.is_(filters.is_archived))

        if filters.status:
            conditions.append(Client.status == filters.status.strip().upper())

        if filters.classification:
            conditions.append(Client.classification == filters.classification.strip().upper())

        if filters.phone:
            conditions.append(Client.phone.ilike(f"%{filters.phone.strip()}%"))

        if filters.email:
            conditions.append(Client.email.ilike(f"%{filters.email.strip()}%"))

        if filters.search:
            s = filters.search.strip()
            conditions.append(
                or_(
                    Client.full_name.ilike(f"%{s}%"),
                    Client.phone.ilike(f"%{s}%"),
                    Client.email.ilike(f"%{s}%"),
                )
            )

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        # Count total
        count_res = await session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        # Sorting
        sort_attr = getattr(Client, filters.sort_by, Client.created_at)
        if filters.sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_attr.asc(), Client.id.asc())
        else:
            stmt = stmt.order_by(sort_attr.desc(), Client.id.desc())

        # Pagination
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await session.execute(stmt)
        clients = list(result.scalars().all())
        return clients, total_count

    async def update(
        self, session: AsyncSession, client_obj: Client, update_dict: dict
    ) -> Client:
        for key, value in update_dict.items():
            setattr(client_obj, key, value)
        await session.flush()
        return client_obj

    async def archive(
        self, session: AsyncSession, client_obj: Client
    ) -> Client:
        client_obj.is_archived = True
        client_obj.status = "ARCHIVED"
        await session.flush()
        return client_obj
