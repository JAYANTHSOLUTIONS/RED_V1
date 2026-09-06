"""Property Management service.

Enforces property business rules, lifecycle state machine transitions with
PostgreSQL row-level locking, image metadata orchestration, and immutable audit logs.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.session import transaction
from app.models.property import Property, PropertyImage
from app.repositories.audit import AuditRepository
from app.repositories.property import PropertyRepository
from app.schemas.property import (
    PaginatedResponse,
    PrivatePropertyResponse,
    PropertyCreate,
    PropertyFilterParams,
    PropertyImageCreate,
    PropertyImageUpdate,
    PropertyUpdate,
    PublicPropertyResponse,
)

# Valid lifecycle state transitions
VALID_TRANSITIONS = {
    "DRAFT": {"PUBLISHED", "ARCHIVED"},
    "PUBLISHED": {"PAUSED", "SOLD", "RENTED", "ARCHIVED"},
    "PAUSED": {"PUBLISHED", "ARCHIVED"},
    "SOLD": {"ARCHIVED"},
    "RENTED": {"ARCHIVED"},
    "ARCHIVED": set(),
}


class PropertyService:
    def __init__(
        self,
        property_repo: Optional[PropertyRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.property_repo = property_repo or PropertyRepository()
        self.audit_repo = audit_repo or AuditRepository()

    # -----------------------------------------------------------------------
    # CRUD Operations
    # -----------------------------------------------------------------------

    async def create_property(
        self,
        session: AsyncSession,
        data: PropertyCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Property:
        """Create a new property in DRAFT status with a sequence-generated public reference."""
        async with transaction(session):
            public_ref = await self.property_repo.generate_public_reference(session)
            prop_data = data.model_dump()
            prop = Property(
                public_reference=public_ref,
                status="DRAFT",
                is_archived=False,
                **prop_data,
            )
            await self.property_repo.create(session, prop)

            await self.audit_repo.record(
                session,
                action="PROPERTY_CREATED",
                entity_type="PROPERTY",
                entity_id=prop.id,
                actor_id=actor_id,
                change_diff={
                    "public_reference": public_ref,
                    "title": prop.title,
                    "property_type": prop.property_type,
                    "transaction_type": prop.transaction_type,
                    "price": str(prop.price),
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        # Reload with images eager-loaded
        return await self.property_repo.get_by_id(session, prop.id)

    async def get_property(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> Property:
        """Retrieve full private property details for consultant workspace."""
        prop = await self.property_repo.get_by_id(session, property_id)
        if prop is None:
            raise NotFoundError("Property not found.")
        return prop

    async def update_property(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        data: PropertyUpdate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Property:
        """Apply partial update to property attributes (excluding lifecycle and system fields)."""
        prop = await self.property_repo.get_by_id(session, property_id)
        if prop is None:
            raise NotFoundError("Property not found.")

        if prop.is_archived:
            raise ValidationAppError("Cannot update an archived property.")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return prop

        # Format diff for audit log
        diff = {}
        for k, v in update_data.items():
            old_val = getattr(prop, k, None)
            diff[k] = {
                "old": str(old_val) if isinstance(old_val, (Decimal, datetime)) else old_val,
                "new": str(v) if isinstance(v, (Decimal, datetime)) else v,
            }

        async with transaction(session):
            await self.property_repo.update(session, prop, update_data)
            await self.audit_repo.record(
                session,
                action="PROPERTY_UPDATED",
                entity_type="PROPERTY",
                entity_id=prop.id,
                actor_id=actor_id,
                change_diff=diff,
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return await self.property_repo.get_by_id(session, prop.id)

    async def list_private_properties(
        self, session: AsyncSession, filters: PropertyFilterParams
    ) -> PaginatedResponse[PrivatePropertyResponse]:
        """List properties for consultant workspace with filters and pagination."""
        items, total = await self.property_repo.list_properties(
            session, filters, is_public=False
        )
        responses = [PrivatePropertyResponse.model_validate(p) for p in items]
        return PaginatedResponse(
            items=responses,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def list_public_properties(
        self, session: AsyncSession, filters: PropertyFilterParams
    ) -> PaginatedResponse[PublicPropertyResponse]:
        """List strictly published, unarchived properties with filtered public schemas."""
        items, total = await self.property_repo.list_properties(
            session, filters, is_public=True
        )
        responses = [PublicPropertyResponse.model_validate(p) for p in items]
        return PaginatedResponse(
            items=responses,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get_public_property(
        self, session: AsyncSession, public_reference: str
    ) -> PublicPropertyResponse:
        """Retrieve single published property for public discovery, strictly omitting private data."""
        prop = await self.property_repo.get_by_public_reference(
            session, public_reference, published_only=True
        )
        if prop is None:
            raise NotFoundError("Property not found.")
        return PublicPropertyResponse.model_validate(prop)

    # -----------------------------------------------------------------------
    # Lifecycle Transitions (with Row-Level Locking)
    # -----------------------------------------------------------------------

    async def _transition_status(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        target_status: str,
        audit_action: str,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Property:
        async with transaction(session):
            # Row lock prevents race conditions in concurrent transition requests
            prop = await self.property_repo.get_by_id_for_update(session, property_id)
            if prop is None:
                raise NotFoundError("Property not found.")

            if prop.is_archived:
                if target_status == "ARCHIVED":
                    # Idempotent archive
                    return prop
                raise ValidationAppError("Cannot perform status transition on an archived property.")

            if prop.status == target_status:
                # Idempotent: already in target status
                return prop

            allowed_next = VALID_TRANSITIONS.get(prop.status, set())
            if target_status not in allowed_next:
                raise ValidationAppError(
                    f"Invalid status transition from '{prop.status}' to '{target_status}'."
                )

            old_status = prop.status
            prop.status = target_status
            if target_status == "ARCHIVED":
                prop.is_archived = True
                prop.archived_at = datetime.now(timezone.utc)

            await session.flush()
            await self.audit_repo.record(
                session,
                action=audit_action,
                entity_type="PROPERTY",
                entity_id=prop.id,
                actor_id=actor_id,
                change_diff={"old_status": old_status, "new_status": target_status},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return await self.property_repo.get_by_id(session, prop.id)

    async def publish_property(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Property:
        return await self._transition_status(
            session=session,
            property_id=property_id,
            target_status="PUBLISHED",
            audit_action="PROPERTY_PUBLISHED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def pause_property(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Property:
        return await self._transition_status(
            session=session,
            property_id=property_id,
            target_status="PAUSED",
            audit_action="PROPERTY_PAUSED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def archive_property(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Property:
        return await self._transition_status(
            session=session,
            property_id=property_id,
            target_status="ARCHIVED",
            audit_action="PROPERTY_ARCHIVED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def mark_property_sold(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Property:
        return await self._transition_status(
            session=session,
            property_id=property_id,
            target_status="SOLD",
            audit_action="PROPERTY_MARKED_SOLD",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def mark_property_rented(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Property:
        return await self._transition_status(
            session=session,
            property_id=property_id,
            target_status="RENTED",
            audit_action="PROPERTY_MARKED_RENTED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    # -----------------------------------------------------------------------
    # Image Operations
    # -----------------------------------------------------------------------

    async def add_image(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        data: PropertyImageCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PropertyImage:
        prop = await self.property_repo.get_by_id(session, property_id)
        if prop is None:
            raise NotFoundError("Property not found.")

        if prop.is_archived:
            raise ValidationAppError("Cannot add images to an archived property.")

        async with transaction(session):
            if data.is_primary:
                await self.property_repo.clear_primary_image(session, property_id)

            image = PropertyImage(
                property_id=property_id,
                uploaded_by=actor_id,
                **data.model_dump(),
            )
            await self.property_repo.add_image(session, image)
            await session.refresh(image)

            await self.audit_repo.record(
                session,
                action="PROPERTY_IMAGE_ADDED",
                entity_type="PROPERTY",
                entity_id=property_id,
                actor_id=actor_id,
                change_diff={
                    "image_id": str(image.id),
                    "storage_key": image.storage_key,
                    "is_primary": image.is_primary,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return image

    async def list_property_images(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
    ) -> list[PropertyImage]:
        prop = await self.property_repo.get_by_id(session, property_id)
        if prop is None:
            raise NotFoundError("Property not found.")
        return await self.property_repo.get_images_for_property(session, property_id)

    async def update_image(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        image_id: uuid.UUID,
        data: PropertyImageUpdate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PropertyImage:
        img = await self.property_repo.get_image(session, image_id)
        if img is None or img.property_id != property_id or img.is_archived:
            raise NotFoundError("Property image not found.")

        async with transaction(session):
            if data.is_primary is True:
                await self.property_repo.clear_primary_image(session, property_id)
                img.is_primary = True
            elif data.is_primary is False:
                img.is_primary = False

            if data.display_order is not None:
                img.display_order = data.display_order

            await session.flush()
            await session.refresh(img)
            await self.audit_repo.record(
                session,
                action="PROPERTY_IMAGE_UPDATED",
                entity_type="PROPERTY",
                entity_id=property_id,
                actor_id=actor_id,
                change_diff={
                    "image_id": str(image_id),
                    "is_primary": img.is_primary,
                    "display_order": img.display_order,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return img

    async def delete_image(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        image_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        img = await self.property_repo.get_image(session, image_id)
        if img is None or img.property_id != property_id or img.is_archived:
            raise NotFoundError("Property image not found.")

        async with transaction(session):
            await self.property_repo.delete_image(session, img, soft_delete=True)
            await self.audit_repo.record(
                session,
                action="PROPERTY_IMAGE_REMOVED",
                entity_type="PROPERTY",
                entity_id=property_id,
                actor_id=actor_id,
                change_diff={"image_id": str(image_id)},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
