"""PropertyRequirement and Property Matching service.

Enforces requirement lifecycle, client relationship validation, deterministic candidate matching,
and audit logging.
"""
from typing import List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.session import transaction
from app.models.requirement import PropertyRequirement
from app.repositories.audit import AuditRepository
from app.repositories.client import ClientRepository
from app.repositories.requirement import PropertyRequirementRepository
from app.schemas.common import PaginatedResponse
from app.schemas.requirement import (
    MatchingPropertySummary,
    PropertyMatchItem,
    PropertyRequirementCreate,
    PropertyRequirementResponse,
    PropertyRequirementUpdate,
    RequirementFilterParams,
    RequirementMatchParams,
)
from app.services.matching import DeterministicMatchingEngine


class PropertyRequirementService:
    def __init__(
        self,
        req_repo: Optional[PropertyRequirementRepository] = None,
        client_repo: Optional[ClientRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
        matching_engine: Optional[DeterministicMatchingEngine] = None,
    ):
        self.req_repo = req_repo or PropertyRequirementRepository()
        self.client_repo = client_repo or ClientRepository()
        self.audit_repo = audit_repo or AuditRepository()
        self.matching_engine = matching_engine or DeterministicMatchingEngine()

    async def create_requirement(
        self,
        session: AsyncSession,
        data: PropertyRequirementCreate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PropertyRequirement:
        """Create a new requirement in ACTIVE status after verifying client eligibility."""
        async with transaction(session):
            client = await self.client_repo.get_by_id(session, data.client_id)
            if client is None:
                raise NotFoundError("Client not found.")
            if client.is_archived:
                raise ValidationAppError("Cannot create a property requirement for an archived client.")

            req_data = data.model_dump()
            requirement = PropertyRequirement(
                status="ACTIVE",
                **req_data,
            )
            await self.req_repo.create(session, requirement)

            await self.audit_repo.record(
                session,
                action="PROPERTY_REQUIREMENT_CREATED",
                entity_type="PROPERTY_REQUIREMENT",
                entity_id=requirement.id,
                actor_id=actor_id,
                change_diff={
                    "client_id": str(requirement.client_id),
                    "transaction_type": requirement.transaction_type,
                    "property_types": requirement.property_types,
                    "min_budget": str(requirement.min_budget) if requirement.min_budget is not None else None,
                    "max_budget": str(requirement.max_budget) if requirement.max_budget is not None else None,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return await self.get_requirement(session, requirement.id)

    async def get_requirement(
        self, session: AsyncSession, req_id: uuid.UUID
    ) -> PropertyRequirement:
        """Retrieve requirement or raise NotFoundError."""
        req = await self.req_repo.get_by_id(session, req_id)
        if req is None:
            raise NotFoundError("Property requirement not found.")
        return req

    async def update_requirement(
        self,
        session: AsyncSession,
        req_id: uuid.UUID,
        data: PropertyRequirementUpdate,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PropertyRequirement:
        """Update requirement fields while enforcing terminal status immutability."""
        async with transaction(session):
            req = await self.req_repo.get_by_id_for_update(session, req_id)
            if req is None:
                raise NotFoundError("Property requirement not found.")

            if req.status in ("ARCHIVED", "FULFILLED", "CANCELLED"):
                raise ValidationAppError(
                    f"Cannot modify requirement in terminal status '{req.status}'."
                )

            update_dict = data.model_dump(exclude_unset=True)
            if update_dict:
                # Cross-validate merged budget bounds
                new_min_budget = update_dict.get("min_budget", req.min_budget)
                new_max_budget = update_dict.get("max_budget", req.max_budget)
                if new_min_budget is not None and new_max_budget is not None:
                    if new_min_budget > new_max_budget:
                        raise ValidationAppError("min_budget cannot be greater than max_budget.")

                # Cross-validate merged area bounds
                new_min_area = update_dict.get("min_area", req.min_area)
                new_max_area = update_dict.get("max_area", req.max_area)
                if new_min_area is not None and new_max_area is not None:
                    if new_min_area > new_max_area:
                        raise ValidationAppError("min_area cannot be greater than max_area.")

                await self.req_repo.update(session, req, update_dict)
                await self.audit_repo.record(
                    session,
                    action="PROPERTY_REQUIREMENT_UPDATED",
                    entity_type="PROPERTY_REQUIREMENT",
                    entity_id=req.id,
                    actor_id=actor_id,
                    change_diff={k: str(v) for k, v in update_dict.items()},
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )

        return await self.get_requirement(session, req_id)

    async def list_requirements(
        self,
        session: AsyncSession,
        filters: RequirementFilterParams,
    ) -> PaginatedResponse[PropertyRequirementResponse]:
        """List requirements with filtering and database-level pagination."""
        reqs, total = await self.req_repo.list_requirements(session, filters)
        items = [PropertyRequirementResponse.model_validate(r) for r in reqs]
        return PaginatedResponse[PropertyRequirementResponse](
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
        req_id: uuid.UUID,
        target_status: str,
        audit_action: str,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PropertyRequirement:
        async with transaction(session):
            req = await self.req_repo.get_by_id_for_update(session, req_id)
            if req is None:
                raise NotFoundError("Property requirement not found.")

            if req.status == target_status:
                raise ValidationAppError(
                    f"Property requirement is already in status '{target_status}'."
                )

            if req.status == "ARCHIVED":
                raise ValidationAppError(
                    "Cannot transition requirement from terminal status 'ARCHIVED'."
                )

            if req.status in ("FULFILLED", "CANCELLED") and target_status != "ARCHIVED":
                raise ValidationAppError(
                    f"Cannot transition requirement from terminal status '{req.status}' to '{target_status}'."
                )

            old_status = req.status
            req.status = target_status
            await session.flush()

            await self.audit_repo.record(
                session,
                action=audit_action,
                entity_type="PROPERTY_REQUIREMENT",
                entity_id=req.id,
                actor_id=actor_id,
                change_diff={"old_status": old_status, "new_status": target_status},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return await self.get_requirement(session, req_id)

    async def fulfill_requirement(
        self,
        session: AsyncSession,
        req_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PropertyRequirement:
        return await self._transition_status(
            session=session,
            req_id=req_id,
            target_status="FULFILLED",
            audit_action="PROPERTY_REQUIREMENT_FULFILLED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def cancel_requirement(
        self,
        session: AsyncSession,
        req_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PropertyRequirement:
        return await self._transition_status(
            session=session,
            req_id=req_id,
            target_status="CANCELLED",
            audit_action="PROPERTY_REQUIREMENT_CANCELLED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def archive_requirement(
        self,
        session: AsyncSession,
        req_id: uuid.UUID,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PropertyRequirement:
        return await self._transition_status(
            session=session,
            req_id=req_id,
            target_status="ARCHIVED",
            audit_action="PROPERTY_REQUIREMENT_ARCHIVED",
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    # -----------------------------------------------------------------------
    # Property Matching
    # -----------------------------------------------------------------------

    async def find_matches(
        self,
        session: AsyncSession,
        req_id: uuid.UUID,
        params: RequirementMatchParams,
        actor_id: uuid.UUID,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> PaginatedResponse[PropertyMatchItem]:
        """Find and rank candidate properties matching the requirement with explainability."""
        req = await self.get_requirement(session, req_id)
        if req.status == "ARCHIVED":
            raise ValidationAppError("Cannot find matches for an archived property requirement.")

        # Query only eligible published properties matching the transaction type
        candidates = await self.req_repo.get_candidate_properties(
            session, req.transaction_type
        )

        match_results: List[PropertyMatchItem] = []
        for prop in candidates:
            evaluation = self.matching_engine.evaluate(req, prop)
            if evaluation.is_match and evaluation.score >= params.min_score:
                match_results.append(
                    PropertyMatchItem(
                        property=MatchingPropertySummary.model_validate(prop),
                        match_grade=evaluation.match_grade,
                        score=evaluation.score,
                        matched_criteria=evaluation.matched_criteria,
                        unmatched_criteria=evaluation.unmatched_criteria,
                    )
                )

        # Sort primarily by score desc, then by property price asc
        match_results.sort(key=lambda m: (-m.score, m.property.price))

        total_matches = len(match_results)
        page_items = match_results[params.offset : params.offset + params.limit]

        # Audit match search
        async with transaction(session):
            await self.audit_repo.record(
                session,
                action="PROPERTY_MATCHES_REQUESTED",
                entity_type="PROPERTY_REQUIREMENT",
                entity_id=req.id,
                actor_id=actor_id,
                change_diff={
                    "total_candidates": len(candidates),
                    "matches_found": total_matches,
                    "min_score": params.min_score,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return PaginatedResponse[PropertyMatchItem](
            items=page_items,
            total=total_matches,
            limit=params.limit,
            offset=params.offset,
        )
