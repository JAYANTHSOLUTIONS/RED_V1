"""Site Visit Service.

Implements business logic for site visit coordination, state transitions,
interval conflict prevention, PostgreSQL concurrency safety, and audit logging.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import uuid

try:
    from zoneinfo import ZoneInfo
    KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.db.session import transaction
from app.models.site_visit import SiteVisit
from app.repositories.audit import AuditRepository
from app.repositories.client import ClientRepository
from app.repositories.lead import LeadRepository
from app.repositories.property import PropertyRepository
from app.repositories.site_visit import SiteVisitRepository
from app.schemas.common import PaginatedResponse
from app.schemas.site_visit import (
    SiteVisitCancel,
    SiteVisitComplete,
    SiteVisitConfirm,
    SiteVisitCreate,
    SiteVisitFilterParams,
    SiteVisitPrivateResponse,
    SiteVisitPublicRequest,
    SiteVisitReschedule,
    SiteVisitUpdate,
)

SITE_VISIT_ADVISORY_LOCK_ID = 8829910
CONFLICT_BUFFER_MINUTES = 60

VALID_TRANSITIONS = {
    "REQUESTED": {"CONFIRMED", "CANCELLED", "RESCHEDULED"},
    "CONFIRMED": {"COMPLETED", "CANCELLED", "RESCHEDULED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "RESCHEDULED": set(),
}


def normalize_datetime(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware and normalized to UTC for database storage.
    
    If a naive datetime is provided, it is assumed to be Indian Standard Time (Asia/Kolkata).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KOLKATA_TZ)
    return dt.astimezone(timezone.utc)


class SiteVisitService:
    def __init__(
        self,
        site_visit_repo: Optional[SiteVisitRepository] = None,
        property_repo: Optional[PropertyRepository] = None,
        client_repo: Optional[ClientRepository] = None,
        lead_repo: Optional[LeadRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.site_visit_repo = site_visit_repo or SiteVisitRepository()
        self.property_repo = property_repo or PropertyRepository()
        self.client_repo = client_repo or ClientRepository()
        self.lead_repo = lead_repo or LeadRepository()
        self.audit_repo = audit_repo or AuditRepository()

    async def _validate_related_entities(
        self,
        session: AsyncSession,
        client_id: uuid.UUID,
        property_id: uuid.UUID,
        lead_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Validate foreign key relationships and lifecycle states."""
        # 1. Validate property
        prop = await self.property_repo.get_by_id(session, property_id)
        if prop is None:
            raise NotFoundError("Property not found.", code="PROPERTY_NOT_FOUND")
        if prop.is_archived:
            raise ValidationAppError("Cannot schedule site visits for an archived property.")
        if prop.status in {"SOLD", "RENTED", "ARCHIVED"}:
            raise ValidationAppError(
                f"Cannot schedule site visits for a property with status '{prop.status}'."
            )

        # 2. Validate client
        client = await self.client_repo.get_by_id(session, client_id)
        if client is None:
            raise NotFoundError("Client not found.", code="CLIENT_NOT_FOUND")
        if client.is_archived:
            raise ValidationAppError("Cannot schedule site visits for an archived client.")

        # 3. Validate lead if provided
        if lead_id is not None:
            lead = await self.lead_repo.get_by_id(session, lead_id)
            if lead is None:
                raise NotFoundError("Lead not found.", code="LEAD_NOT_FOUND")
            if lead.client_id != client_id:
                raise ValidationAppError(
                    "Lead does not belong to the specified client.",
                    code="VALIDATION_ERROR",
                )
            if lead.status in {"CONVERTED", "LOST"}:
                raise ValidationAppError(
                    f"Cannot schedule site visits for a {lead.status} lead.",
                    code="VALIDATION_ERROR",
                )

    async def request_visit(
        self,
        session: AsyncSession,
        data: SiteVisitPublicRequest,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> SiteVisit:
        """Customer-initiated site visit request.
        
        Always creates a visit in REQUESTED status. Never automatically confirms.
        """
        async with transaction(session):
            await self._validate_related_entities(
                session,
                client_id=data.client_id,
                property_id=data.property_id,
                lead_id=data.lead_id,
            )

            scheduled_at = normalize_datetime(data.scheduled_at)

            visit = SiteVisit(
                client_id=data.client_id,
                property_id=data.property_id,
                lead_id=data.lead_id,
                scheduled_at=scheduled_at,
                status="REQUESTED",
                notes=data.notes,
            )
            created = await self.site_visit_repo.create(session, visit)

            await self.audit_repo.record(
                session,
                action="SITE_VISIT_CREATED",
                entity_type="site_visit",
                entity_id=created.id,
                actor_id=actor_id,
                change_diff={
                    "status": "REQUESTED",
                    "client_id": str(data.client_id),
                    "property_id": str(data.property_id),
                    "scheduled_at": scheduled_at.isoformat(),
                    "source": "CUSTOMER_REQUEST",
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            # Reload with eager relationships
            return await self.site_visit_repo.get_by_id(session, created.id)  # type: ignore

    async def create_visit(
        self,
        session: AsyncSession,
        data: SiteVisitCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> SiteVisit:
        """Consultant-initiated site visit creation (REQUESTED or CONFIRMED)."""
        target_status = data.status or "REQUESTED"

        async with transaction(session):
            await self._validate_related_entities(
                session,
                client_id=data.client_id,
                property_id=data.property_id,
                lead_id=data.lead_id,
            )

            scheduled_at = normalize_datetime(data.scheduled_at)

            if target_status == "CONFIRMED":
                # Acquire advisory lock to serialize schedule conflict checks
                await session.execute(
                    text(f"SELECT pg_advisory_xact_lock({SITE_VISIT_ADVISORY_LOCK_ID})")
                )
                conflicts = await self.site_visit_repo.find_conflicts(
                    session,
                    scheduled_at=scheduled_at,
                    buffer_minutes=CONFLICT_BUFFER_MINUTES,
                )
                if conflicts:
                    raise ConflictError(
                        f"The requested site visit conflicts with an existing confirmed visit at {conflicts[0].scheduled_at.isoformat()}.",
                        code="RESOURCE_CONFLICT",
                    )

            visit = SiteVisit(
                client_id=data.client_id,
                property_id=data.property_id,
                lead_id=data.lead_id,
                scheduled_at=scheduled_at,
                status=target_status,
                notes=data.notes,
            )
            created = await self.site_visit_repo.create(session, visit)

            await self.audit_repo.record(
                session,
                action="SITE_VISIT_CREATED",
                entity_type="site_visit",
                entity_id=created.id,
                actor_id=actor_id,
                change_diff={
                    "status": target_status,
                    "client_id": str(data.client_id),
                    "property_id": str(data.property_id),
                    "scheduled_at": scheduled_at.isoformat(),
                    "source": "CONSULTANT_DIRECT",
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            if target_status == "CONFIRMED":
                await self.audit_repo.record(
                    session,
                    action="SITE_VISIT_CONFIRMED",
                    entity_type="site_visit",
                    entity_id=created.id,
                    actor_id=actor_id,
                    change_diff={"scheduled_at": scheduled_at.isoformat()},
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )

            return await self.site_visit_repo.get_by_id(session, created.id)  # type: ignore

    async def confirm_visit(
        self,
        session: AsyncSession,
        visit_id: uuid.UUID,
        data: Optional[SiteVisitConfirm] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> SiteVisit:
        """Confirm a site visit. Checks for conflicts under PostgreSQL advisory lock."""
        async with transaction(session):
            # 1. Acquire advisory lock to serialize schedule conflict checks
            await session.execute(
                text(f"SELECT pg_advisory_xact_lock({SITE_VISIT_ADVISORY_LOCK_ID})")
            )

            # 2. Row lock on the target visit
            visit = await self.site_visit_repo.get_by_id_for_update(session, visit_id)
            if visit is None:
                raise NotFoundError("Site visit not found.", code="SITE_VISIT_NOT_FOUND")

            # Determine scheduled timestamp
            new_scheduled_at = visit.scheduled_at
            if data and data.scheduled_at:
                new_scheduled_at = normalize_datetime(data.scheduled_at)

            # Idempotency: already confirmed with identical schedule
            if visit.status == "CONFIRMED" and visit.scheduled_at == new_scheduled_at:
                return visit

            # Validate transition
            if visit.status != "REQUESTED":
                raise ValidationAppError(
                    f"Cannot confirm a visit in '{visit.status}' status.",
                    code="INVALID_SITE_VISIT_TRANSITION",
                )

            # 3. Conflict check against other CONFIRMED visits
            conflicts = await self.site_visit_repo.find_conflicts(
                session,
                scheduled_at=new_scheduled_at,
                buffer_minutes=CONFLICT_BUFFER_MINUTES,
                exclude_id=visit.id,
            )
            if conflicts:
                raise ConflictError(
                    "The requested site visit conflicts with an existing confirmed visit.",
                    code="RESOURCE_CONFLICT",
                )

            old_scheduled = visit.scheduled_at
            visit.status = "CONFIRMED"
            visit.scheduled_at = new_scheduled_at
            if data and data.notes:
                visit.notes = f"{visit.notes}\n[Confirmed]: {data.notes}" if visit.notes else data.notes

            await session.flush()

            await self.audit_repo.record(
                session,
                action="SITE_VISIT_CONFIRMED",
                entity_type="site_visit",
                entity_id=visit.id,
                actor_id=actor_id,
                change_diff={
                    "status": "CONFIRMED",
                    "previous_status": "REQUESTED",
                    "scheduled_at": new_scheduled_at.isoformat(),
                    "previous_scheduled_at": old_scheduled.isoformat(),
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            return await self.site_visit_repo.get_by_id(session, visit.id)  # type: ignore

    async def complete_visit(
        self,
        session: AsyncSession,
        visit_id: uuid.UUID,
        data: Optional[SiteVisitComplete] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> SiteVisit:
        """Mark a confirmed visit as completed."""
        async with transaction(session):
            visit = await self.site_visit_repo.get_by_id_for_update(session, visit_id)
            if visit is None:
                raise NotFoundError("Site visit not found.", code="SITE_VISIT_NOT_FOUND")

            if visit.status == "COMPLETED":
                # Idempotent
                return visit

            if visit.status == "REQUESTED":
                raise ValidationAppError(
                    "A site visit must be CONFIRMED before it can be marked as COMPLETED.",
                    code="INVALID_SITE_VISIT_TRANSITION",
                )

            if visit.status != "CONFIRMED":
                raise ValidationAppError(
                    f"Cannot complete a site visit in '{visit.status}' status.",
                    code="INVALID_SITE_VISIT_TRANSITION",
                )

            visit.status = "COMPLETED"
            if data and data.feedback:
                visit.feedback = data.feedback
            if data and data.notes:
                visit.notes = f"{visit.notes}\n[Completed]: {data.notes}" if visit.notes else data.notes

            await session.flush()

            await self.audit_repo.record(
                session,
                action="SITE_VISIT_COMPLETED",
                entity_type="site_visit",
                entity_id=visit.id,
                actor_id=actor_id,
                change_diff={
                    "status": "COMPLETED",
                    "previous_status": "CONFIRMED",
                    "feedback": data.feedback if data else None,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            return await self.site_visit_repo.get_by_id(session, visit.id)  # type: ignore

    async def cancel_visit(
        self,
        session: AsyncSession,
        visit_id: uuid.UUID,
        data: SiteVisitCancel,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> SiteVisit:
        """Cancel a site visit with mandatory cancellation reason."""
        async with transaction(session):
            visit = await self.site_visit_repo.get_by_id_for_update(session, visit_id)
            if visit is None:
                raise NotFoundError("Site visit not found.", code="SITE_VISIT_NOT_FOUND")

            if visit.status == "CANCELLED":
                return visit

            if visit.status in {"COMPLETED", "RESCHEDULED"}:
                raise ValidationAppError(
                    f"Cannot cancel a site visit in '{visit.status}' status.",
                    code="INVALID_SITE_VISIT_TRANSITION",
                )

            old_status = visit.status
            visit.status = "CANCELLED"
            visit.cancellation_reason = data.cancellation_reason
            if data.notes:
                visit.notes = f"{visit.notes}\n[Cancelled]: {data.notes}" if visit.notes else data.notes

            await session.flush()

            await self.audit_repo.record(
                session,
                action="SITE_VISIT_CANCELLED",
                entity_type="site_visit",
                entity_id=visit.id,
                actor_id=actor_id,
                change_diff={
                    "status": "CANCELLED",
                    "previous_status": old_status,
                    "cancellation_reason": data.cancellation_reason,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            return await self.site_visit_repo.get_by_id(session, visit.id)  # type: ignore

    async def reschedule_visit(
        self,
        session: AsyncSession,
        visit_id: uuid.UUID,
        data: SiteVisitReschedule,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> SiteVisit:
        """Reschedule a site visit.
        
        Marks the existing visit as RESCHEDULED and creates a new linked SiteVisit record,
        preserving complete audit and scheduling history.
        """
        async with transaction(session):
            # 1. Acquire advisory lock for conflict checking
            await session.execute(
                text(f"SELECT pg_advisory_xact_lock({SITE_VISIT_ADVISORY_LOCK_ID})")
            )

            # 2. Lock existing visit
            original_visit = await self.site_visit_repo.get_by_id_for_update(session, visit_id)
            if original_visit is None:
                raise NotFoundError("Site visit not found.", code="SITE_VISIT_NOT_FOUND")

            if original_visit.status in {"COMPLETED", "CANCELLED", "RESCHEDULED"}:
                raise ValidationAppError(
                    f"Cannot reschedule a visit in '{original_visit.status}' status.",
                    code="INVALID_SITE_VISIT_TRANSITION",
                )

            new_scheduled_at = normalize_datetime(data.new_scheduled_at)

            # Check conflicts for the new time
            conflicts = await self.site_visit_repo.find_conflicts(
                session,
                scheduled_at=new_scheduled_at,
                buffer_minutes=CONFLICT_BUFFER_MINUTES,
                exclude_id=original_visit.id,
            )
            if conflicts:
                raise ConflictError(
                    "The requested site visit conflicts with an existing confirmed visit.",
                    code="RESOURCE_CONFLICT",
                )

            # 3. Mark original visit as RESCHEDULED
            old_status = original_visit.status
            original_visit.status = "RESCHEDULED"
            reschedule_note = f"[Rescheduled to {new_scheduled_at.isoformat()}]: Reason: {data.reason or 'Not specified'}"
            original_visit.notes = (
                f"{original_visit.notes}\n{reschedule_note}"
                if original_visit.notes
                else reschedule_note
            )

            # 4. Create new linked visit in CONFIRMED status
            new_visit = SiteVisit(
                client_id=original_visit.client_id,
                property_id=original_visit.property_id,
                lead_id=original_visit.lead_id,
                scheduled_at=new_scheduled_at,
                status="CONFIRMED",
                rescheduled_from_id=original_visit.id,
                notes=data.notes or f"Rescheduled from visit {original_visit.id}.",
            )
            created_new = await self.site_visit_repo.create(session, new_visit)

            # Record audit logs for both entities
            await self.audit_repo.record(
                session,
                action="SITE_VISIT_RESCHEDULED",
                entity_type="site_visit",
                entity_id=original_visit.id,
                actor_id=actor_id,
                change_diff={
                    "status": "RESCHEDULED",
                    "previous_status": old_status,
                    "new_visit_id": str(created_new.id),
                    "new_scheduled_at": new_scheduled_at.isoformat(),
                    "reason": data.reason,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            await self.audit_repo.record(
                session,
                action="SITE_VISIT_CREATED",
                entity_type="site_visit",
                entity_id=created_new.id,
                actor_id=actor_id,
                change_diff={
                    "status": "CONFIRMED",
                    "rescheduled_from_id": str(original_visit.id),
                    "scheduled_at": new_scheduled_at.isoformat(),
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            return await self.site_visit_repo.get_by_id(session, created_new.id)  # type: ignore

    async def update_visit(
        self,
        session: AsyncSession,
        visit_id: uuid.UUID,
        data: SiteVisitUpdate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> SiteVisit:
        """Update editable visit metadata."""
        async with transaction(session):
            visit = await self.site_visit_repo.get_by_id_for_update(session, visit_id)
            if visit is None:
                raise NotFoundError("Site visit not found.", code="SITE_VISIT_NOT_FOUND")

            diff = {}
            if data.scheduled_at is not None:
                if visit.status != "REQUESTED":
                    raise ValidationAppError(
                        "Cannot modify scheduled time directly for a visit that is already confirmed or closed. Use reschedule instead.",
                        code="INVALID_SITE_VISIT_TRANSITION",
                    )
                new_scheduled = normalize_datetime(data.scheduled_at)
                diff["scheduled_at"] = new_scheduled.isoformat()
                visit.scheduled_at = new_scheduled

            if data.notes is not None:
                diff["notes"] = data.notes
                visit.notes = data.notes

            if data.feedback is not None:
                diff["feedback"] = data.feedback
                visit.feedback = data.feedback

            await session.flush()

            if diff:
                await self.audit_repo.record(
                    session,
                    action="SITE_VISIT_UPDATED",
                    entity_type="site_visit",
                    entity_id=visit.id,
                    actor_id=actor_id,
                    change_diff=diff,
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )

            return await self.site_visit_repo.get_by_id(session, visit.id)  # type: ignore

    async def get_visit(
        self, session: AsyncSession, visit_id: uuid.UUID
    ) -> SiteVisit:
        """Retrieve site visit by ID or raise NotFoundError."""
        visit = await self.site_visit_repo.get_by_id(session, visit_id)
        if visit is None:
            raise NotFoundError("Site visit not found.", code="SITE_VISIT_NOT_FOUND")
        return visit

    async def list_visits(
        self,
        session: AsyncSession,
        filters: SiteVisitFilterParams,
    ) -> PaginatedResponse[SiteVisitPrivateResponse]:
        """List site visits with filters and pagination."""
        visits, total_count = await self.site_visit_repo.list_visits(session, filters)
        items = [SiteVisitPrivateResponse.model_validate(v) for v in visits]
        return PaginatedResponse[SiteVisitPrivateResponse](
            items=items,
            total=total_count,
            limit=filters.limit,
            offset=filters.offset,
        )
