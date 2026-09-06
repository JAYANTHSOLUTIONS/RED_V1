"""Verification repository for database access."""
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.verification import VerificationCase, VerificationItem
from app.schemas.verification import VerificationFilterParams


class VerificationRepository:
    """Handles database persistence, queries, and eager loading for verification cases and items."""

    async def create(
        self, session: AsyncSession, case: VerificationCase
    ) -> VerificationCase:
        """Persist a new verification case along with cascade-associated checklist items."""
        session.add(case)
        await session.flush()
        return case

    async def get_by_id(
        self, session: AsyncSession, case_id: uuid.UUID
    ) -> Optional[VerificationCase]:
        """Fetch verification case by primary key with items, property, and reviewer eagerly loaded."""
        stmt = (
            select(VerificationCase)
            .where(VerificationCase.id == case_id)
            .options(
                selectinload(VerificationCase.items).selectinload(VerificationItem.document),
                selectinload(VerificationCase.property),
                selectinload(VerificationCase.reviewer),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, case_id: uuid.UUID
    ) -> Optional[VerificationCase]:
        """Fetch verification case with row-level locking (SELECT FOR UPDATE)."""
        stmt = (
            select(VerificationCase)
            .where(VerificationCase.id == case_id)
            .options(
                selectinload(VerificationCase.items).selectinload(VerificationItem.document),
                selectinload(VerificationCase.property),
                selectinload(VerificationCase.reviewer),
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_property_id(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> Optional[VerificationCase]:
        """Fetch the most recent verification case for a given property."""
        stmt = (
            select(VerificationCase)
            .where(VerificationCase.property_id == property_id)
            .options(
                selectinload(VerificationCase.items).selectinload(VerificationItem.document),
                selectinload(VerificationCase.property),
                selectinload(VerificationCase.reviewer),
            )
            .order_by(VerificationCase.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_cases(
        self, session: AsyncSession, filters: VerificationFilterParams
    ) -> Tuple[List[VerificationCase], int]:
        """List verification cases with filtering and pagination."""
        query = select(VerificationCase).options(
            selectinload(VerificationCase.items).selectinload(VerificationItem.document),
            selectinload(VerificationCase.property),
            selectinload(VerificationCase.reviewer),
        )

        if filters.property_id:
            query = query.where(VerificationCase.property_id == filters.property_id)
        if filters.status:
            query = query.where(VerificationCase.status == filters.status.upper())

        # Total count query
        count_stmt = select(func.count(VerificationCase.id))
        if filters.property_id:
            count_stmt = count_stmt.where(VerificationCase.property_id == filters.property_id)
        if filters.status:
            count_stmt = count_stmt.where(VerificationCase.status == filters.status.upper())

        total_res = await session.execute(count_stmt)
        total = total_res.scalar() or 0

        # Pagination & sorting
        query = query.order_by(VerificationCase.created_at.desc())
        query = query.offset(filters.offset).limit(filters.limit)

        result = await session.execute(query)
        cases = list(result.scalars().all())
        return cases, total
