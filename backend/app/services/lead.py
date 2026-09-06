"""Lead Management service.

Enforces lead business rules, strict lifecycle state machine transitions with
PostgreSQL row-level locking, client/property relationship integrity, and audit logging.
"""
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.session import transaction
from app.models.lead import Lead
from app.repositories.audit import AuditRepository
from app.repositories.client import ClientRepository
from app.repositories.lead import LeadRepository
from app.repositories.property import PropertyRepository
from app.schemas.common import PaginatedResponse
from app.schemas.lead import (
    LeadCreate,
    LeadFilterParams,
    LeadResponse,
    LeadUpdate,
)

# Valid lifecycle state transitions
LEAD_VALID_TRANSITIONS = {
    "NEW": {"CONTACTED", "LOST"},
    "CONTACTED": {"INTERESTED", "LOST"},
    "INTERESTED": {"SITE_VISIT", "LOST"},
    "SITE_VISIT": {"NEGOTIATION", "LOST"},
    "NEGOTIATION": {"CONVERTED", "LOST"},
    "CONVERTED": set(),  # terminal
    "LOST": set(),       # terminal
}


class LeadService:
    def __init__(
        self,
        lead_repo: Optional[LeadRepository] = None,
        client_repo: Optional[ClientRepository] = None,
        property_repo: Optional[PropertyRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.lead_repo = lead_repo or LeadRepository()
        self.client_repo = client_repo or ClientRepository()
        self.property_repo = property_repo or PropertyRepository()
        self.audit_repo = audit_repo or AuditRepository()

    async def create_lead(
        self,
        session: AsyncSession,
        data: LeadCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        """Create a new lead in NEW status, validating client and property relationships."""
        async with transaction(session):
            # Validate client
            client = await self.client_repo.get_by_id(session, data.client_id)
            if client is None:
                raise NotFoundError("Client not found.")
            if client.is_archived:
                raise ValidationAppError("Cannot create a lead for an archived client.")

            # Validate property if provided
            if data.property_id is not None:
                prop = await self.property_repo.get_by_id(session, data.property_id)
                if prop is None:
                    raise NotFoundError("Property not found.")
                if prop.is_archived:
                    raise ValidationAppError("Cannot link an archived property to a lead.")

            lead = Lead(
                client_id=data.client_id,
                property_id=data.property_id,
                requirement_id=data.requirement_id,
                source=data.source,
                status="NEW",
                notes=data.notes,
            )
            await self.lead_repo.create(session, lead)

            await self.audit_repo.record(
                session,
                action="LEAD_CREATED",
                entity_type="LEAD",
                entity_id=lead.id,
                actor_id=actor_id,
                change_diff={
                    "client_id": str(lead.client_id),
                    "property_id": str(lead.property_id) if lead.property_id else None,
                    "source": lead.source,
                    "status": lead.status,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return await self.get_lead(session, lead.id)

    async def get_lead(
        self, session: AsyncSession, lead_id: uuid.UUID
    ) -> Lead:
        """Retrieve lead record or raise NotFoundError."""
        lead = await self.lead_repo.get_by_id(session, lead_id)
        if lead is None:
            raise NotFoundError("Lead not found.")
        return lead

    async def update_lead(
        self,
        session: AsyncSession,
        lead_id: uuid.UUID,
        data: LeadUpdate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        """Update non-lifecycle fields with row-level lock and audit log."""
        async with transaction(session):
            lead = await self.lead_repo.get_by_id_for_update(session, lead_id)
            if lead is None:
                raise NotFoundError("Lead not found.")

            update_dict = data.model_dump(exclude_unset=True)

            # Validate property if updating property_id
            if "property_id" in update_dict and update_dict["property_id"] is not None:
                prop = await self.property_repo.get_by_id(session, update_dict["property_id"])
                if prop is None:
                    raise NotFoundError("Property not found.")
                if prop.is_archived:
                    raise ValidationAppError("Cannot link an archived property to a lead.")

            if update_dict:
                await self.lead_repo.update(session, lead, update_dict)
                await self.audit_repo.record(
                    session,
                    action="LEAD_UPDATED",
                    entity_type="LEAD",
                    entity_id=lead.id,
                    actor_id=actor_id,
                    change_diff={k: str(v) for k, v in update_dict.items()},
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )

            await session.refresh(lead)

        return await self.get_lead(session, lead.id)

    async def list_leads(
        self,
        session: AsyncSession,
        filters: LeadFilterParams,
    ) -> PaginatedResponse[LeadResponse]:
        """List leads with filtering and database-level pagination."""
        leads, total = await self.lead_repo.list_leads(session, filters)
        items = [LeadResponse.model_validate(ld) for ld in leads]
        return PaginatedResponse[LeadResponse](
            items=items,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    # -----------------------------------------------------------------------
    # Lifecycle Transitions
    # -----------------------------------------------------------------------

    async def _transition_status(
        self,
        session: AsyncSession,
        lead_id: uuid.UUID,
        target_status: str,
        audit_action: str,
        actor_id: uuid.UUID,
        lost_reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        async with transaction(session):
            lead = await self.lead_repo.get_by_id_for_update(session, lead_id)
            if lead is None:
                raise NotFoundError("Lead not found.")

            if lead.status != target_status:
                # Terminal states guard
                if lead.status in ("CONVERTED", "LOST"):
                    raise ValidationAppError(
                        f"Cannot transition lead from terminal status '{lead.status}'."
                    )

                # Valid transitions check
                allowed = LEAD_VALID_TRANSITIONS.get(lead.status, set())
                if target_status not in allowed:
                    raise ValidationAppError(
                        f"Invalid status transition from '{lead.status}' to '{target_status}'."
                    )

                old_status = lead.status
                lead.status = target_status

                diff_data = {"old_status": old_status, "new_status": target_status}

                if target_status == "LOST":
                    if not lost_reason or not lost_reason.strip():
                        raise ValidationAppError(
                            "A non-empty lost_reason is required when marking a lead as lost."
                        )
                    lead.lost_reason = lost_reason.strip()
                    diff_data["lost_reason"] = lead.lost_reason

                await session.flush()

                await self.audit_repo.record(
                    session,
                    action=audit_action,
                    entity_type="LEAD",
                    entity_id=lead.id,
                    actor_id=actor_id,
                    change_diff=diff_data,
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )

                await session.refresh(lead)

        return await self.get_lead(session, lead_id)

    async def contact_lead(
        self,
        session: AsyncSession,
        lead_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        return await self._transition_status(
            session=session,
            lead_id=lead_id,
            target_status="CONTACTED",
            audit_action="LEAD_STATUS_CHANGED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def mark_interested(
        self,
        session: AsyncSession,
        lead_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        return await self._transition_status(
            session=session,
            lead_id=lead_id,
            target_status="INTERESTED",
            audit_action="LEAD_STATUS_CHANGED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def schedule_site_visit_stage(
        self,
        session: AsyncSession,
        lead_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        return await self._transition_status(
            session=session,
            lead_id=lead_id,
            target_status="SITE_VISIT",
            audit_action="LEAD_STATUS_CHANGED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def move_to_negotiation(
        self,
        session: AsyncSession,
        lead_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        return await self._transition_status(
            session=session,
            lead_id=lead_id,
            target_status="NEGOTIATION",
            audit_action="LEAD_STATUS_CHANGED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def convert_lead(
        self,
        session: AsyncSession,
        lead_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        return await self._transition_status(
            session=session,
            lead_id=lead_id,
            target_status="CONVERTED",
            audit_action="LEAD_CONVERTED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def mark_lost(
        self,
        session: AsyncSession,
        lead_id: uuid.UUID,
        lost_reason: str,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Lead:
        return await self._transition_status(
            session=session,
            lead_id=lead_id,
            target_status="LOST",
            audit_action="LEAD_MARKED_LOST",
            actor_id=actor_id,
            lost_reason=lost_reason,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
