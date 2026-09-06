"""PropertyRequirement repository for database access."""
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.property import Property
from app.models.requirement import PropertyRequirement
from app.schemas.requirement import RequirementFilterParams


class PropertyRequirementRepository:
    async def create(
        self, session: AsyncSession, req_obj: PropertyRequirement
    ) -> PropertyRequirement:
        session.add(req_obj)
        await session.flush()
        return req_obj

    async def get_by_id(
        self, session: AsyncSession, req_id: uuid.UUID
    ) -> Optional[PropertyRequirement]:
        stmt = (
            select(PropertyRequirement)
            .where(PropertyRequirement.id == req_id)
            .options(selectinload(PropertyRequirement.client))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, req_id: uuid.UUID
    ) -> Optional[PropertyRequirement]:
        """Fetch requirement with row-level locking (SELECT FOR UPDATE) and eager loaded client."""
        stmt = (
            select(PropertyRequirement)
            .where(PropertyRequirement.id == req_id)
            .options(selectinload(PropertyRequirement.client))
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_requirements(
        self,
        session: AsyncSession,
        filters: RequirementFilterParams,
    ) -> Tuple[List[PropertyRequirement], int]:
        """Query requirements with parameterized filtering and database-level pagination."""
        stmt = (
            select(PropertyRequirement)
            .options(selectinload(PropertyRequirement.client))
        )
        count_stmt = select(func.count(PropertyRequirement.id))

        conditions = []

        if filters.client_id:
            conditions.append(PropertyRequirement.client_id == filters.client_id)

        if filters.transaction_type:
            conditions.append(
                PropertyRequirement.transaction_type == filters.transaction_type.strip().upper()
            )

        if filters.property_type:
            conditions.append(
                PropertyRequirement.property_types.ilike(f"%{filters.property_type.strip()}%")
            )

        if filters.status:
            conditions.append(
                PropertyRequirement.status == filters.status.strip().upper()
            )

        if filters.search:
            s = filters.search.strip()
            conditions.append(
                or_(
                    PropertyRequirement.target_locations.ilike(f"%{s}%"),
                    PropertyRequirement.notes.ilike(f"%{s}%"),
                )
            )

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        count_res = await session.execute(count_stmt)
        total_count = count_res.scalar() or 0

        # Sorting
        sort_attr = getattr(PropertyRequirement, filters.sort_by, PropertyRequirement.created_at)
        if filters.sort_order.lower() == "asc":
            stmt = stmt.order_by(sort_attr.asc(), PropertyRequirement.id.asc())
        else:
            stmt = stmt.order_by(sort_attr.desc(), PropertyRequirement.id.desc())

        # Pagination
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await session.execute(stmt)
        requirements = list(result.scalars().all())
        return requirements, total_count

    async def update(
        self, session: AsyncSession, req_obj: PropertyRequirement, update_dict: dict
    ) -> PropertyRequirement:
        for key, value in update_dict.items():
            setattr(req_obj, key, value)
        await session.flush()
        return req_obj

    async def get_candidate_properties(
        self, session: AsyncSession, transaction_type: str
    ) -> List[Property]:
        """Query published, unarchived properties matching the target transaction type."""
        normalized_tx = "SALE" if transaction_type.upper() in ("BUY", "SALE") else transaction_type.upper()

        stmt = (
            select(Property)
            .where(
                Property.status == "PUBLISHED",
                Property.is_archived.is_(False),
                Property.transaction_type == normalized_tx,
            )
            .order_by(Property.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
