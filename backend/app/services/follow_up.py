"""Follow-up Service.

Implements business logic for follow-up task management, target validation,
lifecycle state machine, PostgreSQL concurrency safety, and audit logging.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import uuid

try:
    from zoneinfo import ZoneInfo
    KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotFoundError,
    ValidationAppError,
)
from app.db.session import transaction
from app.models.follow_up import FollowUp
from app.repositories.audit import AuditRepository
from app.repositories.client import ClientRepository
from app.repositories.follow_up import FollowUpRepository
from app.repositories.lead import LeadRepository
from app.repositories.property import PropertyRepository
from app.schemas.common import PaginatedResponse
from app.schemas.follow_up import (
    FollowUpComplete,
    FollowUpCreate,
    FollowUpFilterParams,
    FollowUpMiss,
    FollowUpResponse,
    FollowUpUpdate,
)

VALID_TRANSITIONS = {
    "SCHEDULED": {"COMPLETED", "MISSED"},
    "COMPLETED": set(),
    "MISSED": set(),
}


def normalize_datetime(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware and normalized to UTC for database storage.
    
    If a naive datetime is provided, it is assumed to be Indian Standard Time (Asia/Kolkata).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KOLKATA_TZ)
    return dt.astimezone(timezone.utc)


class FollowUpService:
    def __init__(
        self,
        follow_up_repo: Optional[FollowUpRepository] = None,
        property_repo: Optional[PropertyRepository] = None,
        client_repo: Optional[ClientRepository] = None,
        lead_repo: Optional[LeadRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.follow_up_repo = follow_up_repo or FollowUpRepository()
        self.property_repo = property_repo or PropertyRepository()
        self.client_repo = client_repo or ClientRepository()
        self.lead_repo = lead_repo or LeadRepository()
        self.audit_repo = audit_repo or AuditRepository()

    async def _validate_relations(
        self,
        session: AsyncSession,
        client_id: Optional[uuid.UUID] = None,
        lead_id: Optional[uuid.UUID] = None,
        property_id: Optional[uuid.UUID] = None,
    ) -> Tuple[Optional[uuid.UUID], Optional[uuid.UUID]]:
        """Validate target (Client / Lead) and Property relationships.
        
        Returns validated (client_id, lead_id). If only lead_id is provided,
        client_id is automatically associated from the lead.
        """
        if client_id is None and lead_id is None:
            raise ValidationAppError(
                "A follow-up must target a client or a lead.",
                code="INVALID_FOLLOW_UP_TARGET",
            )

        resolved_client_id = client_id
        resolved_lead_id = lead_id

        # 1. Validate Client if present
        if client_id is not None:
            client = await self.client_repo.get_by_id(session, client_id)
            if client is None:
                raise NotFoundError("Client not found.", code="CLIENT_NOT_FOUND")
            if client.is_archived:
                raise ValidationAppError("Cannot create follow-up for an archived client.")

        # 2. Validate Lead if present
        if lead_id is not None:
            lead = await self.lead_repo.get_by_id(session, lead_id)
            if lead is None:
                raise NotFoundError("Lead not found.", code="LEAD_NOT_FOUND")
            if lead.status == "LOST":
                raise ValidationAppError("Cannot create follow-up for a lost lead.")

            if client_id is not None and lead.client_id != client_id:
                raise ValidationAppError(
                    "Lead does not belong to the specified client.",
                    code="VALIDATION_ERROR",
                )
            if resolved_client_id is None:
                resolved_client_id = lead.client_id

        # 3. Validate Property if present
        if property_id is not None:
            prop = await self.property_repo.get_by_id(session, property_id)
            if prop is None:
                raise NotFoundError("Property not found.", code="PROPERTY_NOT_FOUND")
            if prop.is_archived:
                raise ValidationAppError("Cannot associate an archived property with a follow-up.")

        return resolved_client_id, resolved_lead_id

    async def create_follow_up(
        self,
        session: AsyncSession,
        data: FollowUpCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> FollowUp:
        """Create a new follow-up task in SCHEDULED status."""
        async with transaction(session):
            client_id, lead_id = await self._validate_relations(
                session,
                client_id=data.client_id,
                lead_id=data.lead_id,
                property_id=data.property_id,
            )

            scheduled_at = normalize_datetime(data.scheduled_at)

            follow_up = FollowUp(
                client_id=client_id,
                lead_id=lead_id,
                property_id=data.property_id,
                scheduled_at=scheduled_at,
                action_type=data.action_type,
                status="SCHEDULED",
                notes=data.notes,
            )
            created = await self.follow_up_repo.create(session, follow_up)

            await self.audit_repo.record(
                session,
                action="FOLLOW_UP_CREATED",
                entity_type="follow_up",
                entity_id=created.id,
                actor_id=actor_id,
                change_diff={
                    "status": "SCHEDULED",
                    "action_type": data.action_type,
                    "client_id": str(client_id) if client_id else None,
                    "lead_id": str(lead_id) if lead_id else None,
                    "property_id": str(data.property_id) if data.property_id else None,
                    "scheduled_at": scheduled_at.isoformat(),
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            return await self.follow_up_repo.get_by_id(session, created.id)  # type: ignore

    async def get_follow_up(
        self, session: AsyncSession, follow_up_id: uuid.UUID
    ) -> FollowUp:
        """Retrieve a follow-up by ID or raise NotFoundError."""
        follow_up = await self.follow_up_repo.get_by_id(session, follow_up_id)
        if follow_up is None:
            raise NotFoundError("Follow-up not found.", code="FOLLOW_UP_NOT_FOUND")
        return follow_up

    async def list_follow_ups(
        self,
        session: AsyncSession,
        filters: FollowUpFilterParams,
    ) -> PaginatedResponse[FollowUpResponse]:
        """List follow-ups with filters and pagination."""
        follow_ups, total_count = await self.follow_up_repo.list_follow_ups(session, filters)
        items = [FollowUpResponse.model_validate(f) for f in follow_ups]
        return PaginatedResponse[FollowUpResponse](
            items=items,
            total=total_count,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update_follow_up(
        self,
        session: AsyncSession,
        follow_up_id: uuid.UUID,
        data: FollowUpUpdate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> FollowUp:
        """Update editable follow-up metadata."""
        async with transaction(session):
            follow_up = await self.follow_up_repo.get_by_id_for_update(session, follow_up_id)
            if follow_up is None:
                raise NotFoundError("Follow-up not found.", code="FOLLOW_UP_NOT_FOUND")

            if follow_up.status in {"COMPLETED", "MISSED"}:
                raise ValidationAppError(
                    f"Cannot update a follow-up in '{follow_up.status}' status.",
                    code="INVALID_FOLLOW_UP_STATE",
                )

            diff = {}
            if data.action_type is not None:
                diff["action_type"] = data.action_type
                follow_up.action_type = data.action_type

            if data.scheduled_at is not None:
                new_scheduled = normalize_datetime(data.scheduled_at)
                diff["scheduled_at"] = new_scheduled.isoformat()
                follow_up.scheduled_at = new_scheduled

            if data.notes is not None:
                diff["notes"] = data.notes
                follow_up.notes = data.notes

            if data.property_id is not None:
                prop = await self.property_repo.get_by_id(session, data.property_id)
                if prop is None:
                    raise NotFoundError("Property not found.", code="PROPERTY_NOT_FOUND")
                if prop.is_archived:
                    raise ValidationAppError("Cannot associate an archived property with a follow-up.")
                diff["property_id"] = str(data.property_id)
                follow_up.property_id = data.property_id

            await session.flush()

            if diff:
                await self.audit_repo.record(
                    session,
                    action="FOLLOW_UP_UPDATED",
                    entity_type="follow_up",
                    entity_id=follow_up.id,
                    actor_id=actor_id,
                    change_diff=diff,
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )

            return await self.follow_up_repo.get_by_id(session, follow_up.id)  # type: ignore

    async def complete_follow_up(
        self,
        session: AsyncSession,
        follow_up_id: uuid.UUID,
        data: Optional[FollowUpComplete] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> FollowUp:
        """Mark a follow-up task as COMPLETED with server-side completion timestamp."""
        async with transaction(session):
            follow_up = await self.follow_up_repo.get_by_id_for_update(session, follow_up_id)
            if follow_up is None:
                raise NotFoundError("Follow-up not found.", code="FOLLOW_UP_NOT_FOUND")

            # Idempotency
            if follow_up.status == "COMPLETED":
                return follow_up

            if follow_up.status != "SCHEDULED":
                raise ValidationAppError(
                    f"Cannot complete a follow-up in '{follow_up.status}' status.",
                    code="INVALID_FOLLOW_UP_STATE",
                )

            follow_up.status = "COMPLETED"
            follow_up.completed_at = datetime.now(timezone.utc)
            if data and data.completion_notes:
                follow_up.completion_notes = data.completion_notes

            await session.flush()

            await self.audit_repo.record(
                session,
                action="FOLLOW_UP_COMPLETED",
                entity_type="follow_up",
                entity_id=follow_up.id,
                actor_id=actor_id,
                change_diff={
                    "status": "COMPLETED",
                    "previous_status": "SCHEDULED",
                    "completed_at": follow_up.completed_at.isoformat(),
                    "completion_notes": data.completion_notes if data else None,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            return await self.follow_up_repo.get_by_id(session, follow_up.id)  # type: ignore

    async def mark_missed_follow_up(
        self,
        session: AsyncSession,
        follow_up_id: uuid.UUID,
        data: Optional[FollowUpMiss] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> FollowUp:
        """Mark a follow-up task as MISSED."""
        async with transaction(session):
            follow_up = await self.follow_up_repo.get_by_id_for_update(session, follow_up_id)
            if follow_up is None:
                raise NotFoundError("Follow-up not found.", code="FOLLOW_UP_NOT_FOUND")

            # Idempotency
            if follow_up.status == "MISSED":
                return follow_up

            if follow_up.status != "SCHEDULED":
                raise ValidationAppError(
                    f"Cannot mark a follow-up in '{follow_up.status}' status as missed.",
                    code="INVALID_FOLLOW_UP_STATE",
                )

            follow_up.status = "MISSED"
            if data and data.notes:
                follow_up.notes = f"{follow_up.notes}\n[Missed]: {data.notes}" if follow_up.notes else data.notes

            await session.flush()

            await self.audit_repo.record(
                session,
                action="FOLLOW_UP_MISSED",
                entity_type="follow_up",
                entity_id=follow_up.id,
                actor_id=actor_id,
                change_diff={
                    "status": "MISSED",
                    "previous_status": "SCHEDULED",
                    "notes": data.notes if data else None,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            return await self.follow_up_repo.get_by_id(session, follow_up.id)  # type: ignore
