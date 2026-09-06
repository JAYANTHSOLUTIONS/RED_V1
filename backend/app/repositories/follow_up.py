"""Follow-up repository for database access."""
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.follow_up import FollowUp
from app.schemas.follow_up import FollowUpFilterParams


class FollowUpRepository:
    """Encapsulates database operations for FollowUp entities."""

    async def create(self, session: AsyncSession, follow_up_obj: FollowUp) -> FollowUp:
        session.add(follow_up_obj)
        await session.flush()
        return follow_up_obj

    async def get_by_id(
        self, session: AsyncSession, follow_up_id: uuid.UUID
    ) -> Optional[FollowUp]:
        """Fetch follow-up with eager loaded relationships."""
        stmt = (
            select(FollowUp)
            .where(FollowUp.id == follow_up_id)
            .options(
                selectinload(FollowUp.client),
                selectinload(FollowUp.lead),
                selectinload(FollowUp.property),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, follow_up_id: uuid.UUID
    ) -> Optional[FollowUp]:
        """Fetch follow-up with row-level locking (SELECT FOR UPDATE) for atomic state transitions."""
        stmt = (
            select(FollowUp)
            .where(FollowUp.id == follow_up_id)
            .with_for_update()
            .options(
                selectinload(FollowUp.client),
                selectinload(FollowUp.lead),
                selectinload(FollowUp.property),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_follow_ups(
        self,
        session: AsyncSession,
        filters: FollowUpFilterParams,
    ) -> Tuple[List[FollowUp], int]:
        """Query follow-ups with filters, sorting, and pagination."""
        stmt = (
            select(FollowUp)
            .options(
                selectinload(FollowUp.client),
                selectinload(FollowUp.lead),
                selectinload(FollowUp.property),
            )
        )
        count_stmt = select(func.count(FollowUp.id))

        conditions = []

        if filters.status:
            conditions.append(FollowUp.status == filters.status)

        if filters.action_type:
            conditions.append(FollowUp.action_type == filters.action_type)

        if filters.client_id:
            conditions.append(FollowUp.client_id == filters.client_id)

        if filters.lead_id:
            conditions.append(FollowUp.lead_id == filters.lead_id)

        if filters.property_id:
            conditions.append(FollowUp.property_id == filters.property_id)

        if filters.scheduled_from:
            conditions.append(FollowUp.scheduled_at >= filters.scheduled_from)

        if filters.scheduled_to:
            conditions.append(FollowUp.scheduled_at <= filters.scheduled_to)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        count_res = await session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        # Order chronologically by planned execution time
        stmt = stmt.order_by(FollowUp.scheduled_at.asc(), FollowUp.id.asc())

        # Pagination
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await session.execute(stmt)
        follow_ups = list(result.scalars().all())
        return follow_ups, total_count

    async def update(
        self, session: AsyncSession, follow_up_obj: FollowUp, update_dict: dict
    ) -> FollowUp:
        for key, value in update_dict.items():
            setattr(follow_up_obj, key, value)
        await session.flush()
        return follow_up_obj
