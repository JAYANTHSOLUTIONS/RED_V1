"""Site visit repository for database access."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.site_visit import SiteVisit
from app.schemas.site_visit import SiteVisitFilterParams


class SiteVisitRepository:
    """Encapsulates database operations for SiteVisit entities."""

    async def create(self, session: AsyncSession, visit_obj: SiteVisit) -> SiteVisit:
        session.add(visit_obj)
        await session.flush()
        return visit_obj

    async def get_by_id(
        self, session: AsyncSession, visit_id: uuid.UUID
    ) -> Optional[SiteVisit]:
        """Fetch site visit with eager loaded relationships."""
        stmt = (
            select(SiteVisit)
            .where(SiteVisit.id == visit_id)
            .options(
                selectinload(SiteVisit.client),
                selectinload(SiteVisit.property),
                selectinload(SiteVisit.lead),
                selectinload(SiteVisit.rescheduled_from),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, visit_id: uuid.UUID
    ) -> Optional[SiteVisit]:
        """Fetch site visit with row-level locking (SELECT FOR UPDATE) for atomic state transitions."""
        stmt = (
            select(SiteVisit)
            .where(SiteVisit.id == visit_id)
            .with_for_update()
            .options(
                selectinload(SiteVisit.client),
                selectinload(SiteVisit.property),
                selectinload(SiteVisit.lead),
                selectinload(SiteVisit.rescheduled_from),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_conflicts(
        self,
        session: AsyncSession,
        scheduled_at: datetime,
        buffer_minutes: int = 60,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> List[SiteVisit]:
        """Find existing CONFIRMED site visits that overlap with the proposed interval.
        
        Touching boundaries are non-overlapping:
        [T - buffer, T + buffer] exclusive.
        """
        start_bound = scheduled_at - timedelta(minutes=buffer_minutes)
        end_bound = scheduled_at + timedelta(minutes=buffer_minutes)

        stmt = (
            select(SiteVisit)
            .where(
                SiteVisit.status == "CONFIRMED",
                SiteVisit.scheduled_at > start_bound,
                SiteVisit.scheduled_at < end_bound,
            )
            .options(
                selectinload(SiteVisit.property),
                selectinload(SiteVisit.client),
            )
        )

        if exclude_id is not None:
            stmt = stmt.where(SiteVisit.id != exclude_id)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def list_visits(
        self,
        session: AsyncSession,
        filters: SiteVisitFilterParams,
    ) -> Tuple[List[SiteVisit], int]:
        """Query site visits with filters, sorting, and pagination."""
        stmt = (
            select(SiteVisit)
            .options(
                selectinload(SiteVisit.client),
                selectinload(SiteVisit.property),
                selectinload(SiteVisit.lead),
                selectinload(SiteVisit.rescheduled_from),
            )
        )
        count_stmt = select(func.count(SiteVisit.id))

        conditions = []

        if filters.status:
            conditions.append(SiteVisit.status == filters.status)

        if filters.property_id:
            conditions.append(SiteVisit.property_id == filters.property_id)

        if filters.client_id:
            conditions.append(SiteVisit.client_id == filters.client_id)

        if filters.lead_id:
            conditions.append(SiteVisit.lead_id == filters.lead_id)

        if filters.date_from:
            conditions.append(SiteVisit.scheduled_at >= filters.date_from)

        if filters.date_to:
            conditions.append(SiteVisit.scheduled_at <= filters.date_to)

        if filters.upcoming_only:
            now_utc = datetime.now(timezone.utc)
            conditions.append(SiteVisit.scheduled_at >= now_utc)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        count_res = await session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        # Sort chronologically by schedule
        stmt = stmt.order_by(SiteVisit.scheduled_at.asc(), SiteVisit.id.asc())

        # Pagination
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await session.execute(stmt)
        visits = list(result.scalars().all())
        return visits, total_count

    async def update(
        self, session: AsyncSession, visit_obj: SiteVisit, update_dict: dict
    ) -> SiteVisit:
        for key, value in update_dict.items():
            setattr(visit_obj, key, value)
        await session.flush()
        return visit_obj
