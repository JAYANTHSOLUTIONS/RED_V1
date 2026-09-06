"""Lead repository for database access."""
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lead import Lead
from app.schemas.lead import LeadFilterParams


class LeadRepository:
    async def create(self, session: AsyncSession, lead_obj: Lead) -> Lead:
        session.add(lead_obj)
        await session.flush()
        return lead_obj

    async def get_by_id(
        self, session: AsyncSession, lead_id: uuid.UUID
    ) -> Optional[Lead]:
        stmt = (
            select(Lead)
            .where(Lead.id == lead_id)
            .options(
                selectinload(Lead.client),
                selectinload(Lead.property),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, lead_id: uuid.UUID
    ) -> Optional[Lead]:
        """Fetch lead with row-level locking (SELECT FOR UPDATE) for atomic state transitions."""
        stmt = select(Lead).where(Lead.id == lead_id).with_for_update()
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_leads(
        self,
        session: AsyncSession,
        filters: LeadFilterParams,
    ) -> Tuple[List[Lead], int]:
        """Query leads with parameterized filtering and database-level pagination."""
        stmt = (
            select(Lead)
            .options(
                selectinload(Lead.client),
                selectinload(Lead.property),
            )
        )
        count_stmt = select(func.count(Lead.id))

        conditions = []

        if filters.status:
            conditions.append(Lead.status == filters.status.strip().upper())

        if filters.client_id:
            conditions.append(Lead.client_id == filters.client_id)

        if filters.property_id:
            conditions.append(Lead.property_id == filters.property_id)

        if filters.source:
            conditions.append(Lead.source.ilike(f"%{filters.source.strip()}%"))

        if filters.search:
            s = filters.search.strip()
            conditions.append(
                or_(
                    Lead.notes.ilike(f"%{s}%"),
                    Lead.lost_reason.ilike(f"%{s}%"),
                )
            )

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        # Count total
        count_res = await session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        # Sorting
        sort_attr = getattr(Lead, filters.sort_by, Lead.created_at)
        if filters.sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_attr.asc(), Lead.id.asc())
        else:
            stmt = stmt.order_by(sort_attr.desc(), Lead.id.desc())

        # Pagination
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await session.execute(stmt)
        leads = list(result.scalars().all())
        return leads, total_count

    async def update(
        self, session: AsyncSession, lead_obj: Lead, update_dict: dict
    ) -> Lead:
        for key, value in update_dict.items():
            setattr(lead_obj, key, value)
        await session.flush()
        return lead_obj

    async def list_leads_for_client(
        self, session: AsyncSession, client_id: uuid.UUID
    ) -> List[Lead]:
        stmt = (
            select(Lead)
            .where(Lead.client_id == client_id)
            .order_by(Lead.created_at.desc(), Lead.id.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
