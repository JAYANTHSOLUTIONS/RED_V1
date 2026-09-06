"""Property and PropertyImage repository for database access."""
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import Sequence, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.sequence import format_property_reference, property_ref_seq
from app.models.property import Property, PropertyImage
from app.schemas.property import PropertyFilterParams


class PropertyRepository:
    async def generate_public_reference(self, session: AsyncSession) -> str:
        """Fetch next sequence value and format standard public reference (e.g. PR-2026-000001)."""
        seq_val = await session.scalar(property_ref_seq.next_value())
        return format_property_reference(seq_val)

    async def create(self, session: AsyncSession, property_obj: Property) -> Property:
        session.add(property_obj)
        await session.flush()
        return property_obj

    async def get_by_id(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> Optional[Property]:
        stmt = (
            select(Property)
            .where(Property.id == property_id)
            .options(
                selectinload(Property.images.and_(PropertyImage.is_archived.is_(False)))
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> Optional[Property]:
        """Fetch property with row-level locking (SELECT FOR UPDATE) for safe state transitions."""
        stmt = (
            select(Property)
            .where(Property.id == property_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_reference(
        self,
        session: AsyncSession,
        public_reference: str,
        published_only: bool = False,
    ) -> Optional[Property]:
        stmt = (
            select(Property)
            .where(Property.public_reference == public_reference.strip())
            .options(
                selectinload(Property.images.and_(PropertyImage.is_archived.is_(False)))
            )
        )
        if published_only:
            stmt = stmt.where(
                Property.status == "PUBLISHED", Property.is_archived.is_(False)
            )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_properties(
        self,
        session: AsyncSession,
        filters: PropertyFilterParams,
        is_public: bool = False,
    ) -> Tuple[List[Property], int]:
        """Query properties with parameterized filtering and database-level pagination."""
        stmt = select(Property)
        count_stmt = select(func.count(Property.id))

        conditions = []

        if is_public:
            conditions.append(Property.status == "PUBLISHED")
            conditions.append(Property.is_archived.is_(False))
        else:
            if filters.status:
                conditions.append(Property.status == filters.status.upper())
            if filters.is_archived is not None:
                conditions.append(Property.is_archived.is_(filters.is_archived))

        if filters.property_type:
            conditions.append(Property.property_type.ilike(f"%{filters.property_type.strip()}%"))
        if filters.transaction_type:
            conditions.append(Property.transaction_type == filters.transaction_type.strip().upper())
        if filters.district:
            conditions.append(Property.district.ilike(f"%{filters.district.strip()}%"))
        if filters.city:
            conditions.append(Property.city.ilike(f"%{filters.city.strip()}%"))
        if filters.locality:
            conditions.append(Property.locality.ilike(f"%{filters.locality.strip()}%"))
        if filters.min_price is not None:
            conditions.append(Property.price >= filters.min_price)
        if filters.max_price is not None:
            conditions.append(Property.price <= filters.max_price)
        if filters.min_area is not None:
            conditions.append(
                or_(
                    Property.built_up_area >= filters.min_area,
                    Property.plot_area >= filters.min_area,
                )
            )
        if filters.max_area is not None:
            conditions.append(
                or_(
                    Property.built_up_area <= filters.max_area,
                    Property.plot_area <= filters.max_area,
                )
            )
        if filters.bedrooms is not None:
            conditions.append(Property.bedrooms == filters.bedrooms)
        if filters.search:
            pattern = f"%{filters.search.strip()}%"
            conditions.append(
                or_(
                    Property.title.ilike(pattern),
                    Property.description.ilike(pattern),
                    Property.locality.ilike(pattern),
                    Property.public_reference.ilike(pattern),
                )
            )

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        # Count total matching rows
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()

        # Determine sorting column
        sort_col_map = {
            "created_at": Property.created_at,
            "price": Property.price,
            "built_up_area": Property.built_up_area,
            "title": Property.title,
        }
        sort_col = sort_col_map.get(filters.sort_by, Property.created_at)
        sort_expression = sort_col.desc() if filters.sort_order == "desc" else sort_col.asc()

        stmt = (
            stmt.order_by(sort_expression)
            .limit(filters.limit)
            .offset(filters.offset)
            .options(
                selectinload(Property.images.and_(PropertyImage.is_archived.is_(False)))
            )
        )

        result = await session.execute(stmt)
        items = result.scalars().all()
        return list(items), total

    async def update(
        self, session: AsyncSession, property_obj: Property, values: dict
    ) -> Property:
        for key, val in values.items():
            setattr(property_obj, key, val)
        await session.flush()
        return property_obj

    # -----------------------------------------------------------------------
    # Image Operations
    # -----------------------------------------------------------------------

    async def add_image(
        self, session: AsyncSession, image: PropertyImage
    ) -> PropertyImage:
        session.add(image)
        await session.flush()
        return image

    async def get_image(
        self, session: AsyncSession, image_id: uuid.UUID
    ) -> Optional[PropertyImage]:
        return await session.get(PropertyImage, image_id)

    async def get_images_for_property(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        include_archived: bool = False,
    ) -> List[PropertyImage]:
        stmt = (
            select(PropertyImage)
            .where(PropertyImage.property_id == property_id)
            .order_by(PropertyImage.display_order.asc(), PropertyImage.created_at.asc())
        )
        if not include_archived:
            stmt = stmt.where(PropertyImage.is_archived.is_(False))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def clear_primary_image(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> None:
        """Reset is_primary=False on all images for this property before setting a new primary."""
        await session.execute(
            update(PropertyImage)
            .where(
                PropertyImage.property_id == property_id,
                PropertyImage.is_primary.is_(True),
            )
            .values(is_primary=False)
        )
        await session.flush()

    async def delete_image(
        self, session: AsyncSession, image: PropertyImage, soft_delete: bool = True
    ) -> None:
        if soft_delete:
            image.is_archived = True
            await session.flush()
        else:
            await session.delete(image)
            await session.flush()
