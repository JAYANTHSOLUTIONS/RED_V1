"""Verification service orchestrating Tamil Nadu Preliminary Property Verification.

Coordinates property retrieval, attached document inspection, deterministic rule
evaluation via DeterministicTNVerificationEngine, database persistence, and immutable
audit logging.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.session import transaction
from app.models.document import Document
from app.models.property import Property
from app.models.verification import VerificationCase, VerificationItem
from app.repositories.audit import AuditRepository
from app.repositories.verification import VerificationRepository
from app.schemas.common import PaginatedResponse
from app.schemas.verification import (
    CheckCategory,
    CheckExplanation,
    CheckResult,
    CheckStatus,
    ChronologyReport,
    ConsultantActionItemSchema,
    DetailedEvidenceItem,
    EvidenceIntelligenceReport,
    EvidenceItem,
    PlanningAuthorityType,
    PropertyVerificationInput,
    ReraApplicability,
    ReraApplicabilityReason,
    RiskLevel,
    TAMIL_NADU_VERIFICATION_DISCLAIMER,
    VerificationCaseResponse,
    VerificationCaseSummary,
    VerificationCaseUpdate,
    VerificationFilterParams,
    VerificationStatus,
    VerificationSummaryResponse,
)
from app.services.tn_verification_engine import (
    DeterministicTNVerificationEngine,
    EngineEvaluationResult,
)


class VerificationService:
    """Service encapsulating Tamil Nadu Preliminary Property Verification operations."""

    def __init__(
        self,
        repo: Optional[VerificationRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
        engine: Optional[DeterministicTNVerificationEngine] = None,
    ):
        self.repo = repo or VerificationRepository()
        self.audit_repo = audit_repo or AuditRepository()
        self.engine = engine or DeterministicTNVerificationEngine()

    @staticmethod
    def _pack_observations(eval_result: EngineEvaluationResult, consultant_notes: Optional[str] = None) -> str:
        """Serialize structured evaluation metadata into consultant observations field."""
        payload = {
            "engine_version": "TN-VERIFICATION-2.0",
            "risk_level": eval_result.risk_level.value,
            "completeness_score": eval_result.completeness_score,
            "planning_authority_type": eval_result.planning_authority_type.value,
            "rera_applicability": eval_result.rera_applicability.value,
            "rera_applicability_reason": eval_result.rera_applicability_reason.value if eval_result.rera_applicability_reason else None,
            "risk_flags": eval_result.risk_flags,
            "missing_information": eval_result.missing_information,
            "consultant_notes": consultant_notes or eval_result.observations,
            "chronology_report": eval_result.chronology.model_dump(mode="json") if getattr(eval_result, "chronology", None) else None,
            "actions": [a.model_dump(mode="json") for a in eval_result.actions],
            "explanations": [e.model_dump(mode="json") for e in eval_result.explanations],
            "evidence_report": eval_result.evidence_report.model_dump(mode="json") if eval_result.evidence_report else None,
            "summary": eval_result.summary.model_dump(mode="json") if eval_result.summary else None,
        }
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _unpack_observations(raw: Optional[str]) -> Dict[str, Any]:
        """Deserialize structured evaluation metadata with graceful raw-text fallback."""
        default_data = {
            "engine_version": "TN-VERIFICATION-2.0",
            "risk_level": RiskLevel.MEDIUM.value,
            "completeness_score": 0,
            "planning_authority_type": PlanningAuthorityType.UNKNOWN.value,
            "rera_applicability": ReraApplicability.RERA_UNKNOWN.value,
            "rera_applicability_reason": None,
            "risk_flags": [],
            "missing_information": [],
            "consultant_notes": raw or "",
            "chronology_report": None,
            "actions": [],
            "explanations": [],
            "evidence_report": None,
            "summary": None,
        }
        if not raw:
            return default_data
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return {
                    "engine_version": parsed.get("engine_version", "TN-VERIFICATION-2.0"),
                    "risk_level": parsed.get("risk_level", RiskLevel.MEDIUM.value),
                    "completeness_score": parsed.get("completeness_score", 0),
                    "planning_authority_type": parsed.get("planning_authority_type", PlanningAuthorityType.UNKNOWN.value),
                    "rera_applicability": parsed.get("rera_applicability", ReraApplicability.RERA_UNKNOWN.value),
                    "rera_applicability_reason": parsed.get("rera_applicability_reason"),
                    "risk_flags": parsed.get("risk_flags", []),
                    "missing_information": parsed.get("missing_information", []),
                    "consultant_notes": parsed.get("consultant_notes", raw),
                    "chronology_report": parsed.get("chronology_report"),
                    "actions": parsed.get("actions", []),
                    "explanations": parsed.get("explanations", []),
                    "evidence_report": parsed.get("evidence_report"),
                    "summary": parsed.get("summary"),
                }
        except Exception:
            pass
        return default_data

    @staticmethod
    def _determine_category(checklist_code: str) -> CheckCategory:
        """Map checklist code to standard Tamil Nadu check category."""
        code = checklist_code.upper()
        if "IDENTITY" in code or "SURVEY" in code or "EXTENT" in code or "OWNER" in code or "ADDRESS" in code:
            return CheckCategory.PROPERTY_IDENTITY
        if "PATTA" in code or "LAND_RECORD" in code:
            return CheckCategory.LAND_RECORDS
        if "EC" in code or "SRO" in code or "ENCUMBRANCE" in code:
            return CheckCategory.REGISTRATION_SRO
        if "PLANNING" in code or "LAYOUT" in code or "CMDA" in code or "DTCP" in code or "BUILDING" in code:
            return CheckCategory.PLANNING_APPROVAL
        if "RERA" in code:
            return CheckCategory.RERA
        if "TITLE" in code or "PARENT" in code or "SEQUENCE" in code or "CHAIN" in code:
            return CheckCategory.DOCUMENT_CHAIN
        if "TAX" in code or "MUNICIPAL" in code or "ASSESSMENT" in code:
            return CheckCategory.MUNICIPAL_TAX
        return CheckCategory.PROPERTY_IDENTITY

    def _format_case_response(self, case: VerificationCase) -> VerificationCaseResponse:
        """Format a database VerificationCase entity into standard API response schema."""
        meta = self._unpack_observations(case.consultant_observations)

        formatted_checks: List[CheckResult] = []
        for item in case.items:
            cat = self._determine_category(item.checklist_code)
            status_enum = CheckStatus.INFO
            try:
                status_enum = CheckStatus(item.status)
            except ValueError:
                status_enum = CheckStatus.REVIEW

            # Derive risk level from check status
            if status_enum == CheckStatus.FAIL:
                risk_lvl = RiskLevel.HIGH
            elif status_enum == CheckStatus.REVIEW:
                risk_lvl = RiskLevel.MEDIUM
            elif status_enum == CheckStatus.PASS:
                risk_lvl = RiskLevel.LOW
            else:
                risk_lvl = RiskLevel.INFO

            evidence_items: List[EvidenceItem] = []
            if item.document:
                evidence_items.append(
                    EvidenceItem(
                        document_id=item.document.id,
                        document_type=item.document.document_type,
                        original_filename=item.document.original_filename,
                    )
                )

            formatted_checks.append(
                CheckResult(
                    checklist_code=item.checklist_code,
                    item_name=item.item_name,
                    category=cat,
                    status=status_enum,
                    is_present=item.is_present,
                    risk_level=risk_lvl,
                    notes=item.notes,
                    evidence=evidence_items,
                )
            )

        # Reconstruct Phase 9 intelligence models
        chronology_obj = None
        if meta.get("chronology_report"):
            try:
                chronology_obj = ChronologyReport.model_validate(meta["chronology_report"])
            except Exception:
                pass

        actions_list = []
        for act in meta.get("actions", []):
            try:
                actions_list.append(ConsultantActionItemSchema.model_validate(act))
            except Exception:
                pass

        explanations_list = []
        for exp in meta.get("explanations", []):
            try:
                explanations_list.append(CheckExplanation.model_validate(exp))
            except Exception:
                pass

        evidence_rep = None
        if meta.get("evidence_report"):
            try:
                evidence_rep = EvidenceIntelligenceReport.model_validate(meta["evidence_report"])
            except Exception:
                pass

        summary_obj = None
        if meta.get("summary"):
            try:
                summary_obj = VerificationSummaryResponse.model_validate(meta["summary"])
            except Exception:
                pass

        rera_reason = None
        if meta.get("rera_applicability_reason"):
            try:
                rera_reason = ReraApplicabilityReason(meta["rera_applicability_reason"])
            except Exception:
                pass

        return VerificationCaseResponse(
            id=case.id,
            property_id=case.property_id,
            status=case.status,
            risk_level=meta["risk_level"],
            completeness_score=meta["completeness_score"],
            planning_authority_type=meta["planning_authority_type"],
            rera_applicability=meta["rera_applicability"],
            rera_applicability_reason=rera_reason,
            risk_flags=meta["risk_flags"],
            missing_information=meta["missing_information"],
            checks=formatted_checks,
            chronology=chronology_obj,
            actions=actions_list,
            explanations=explanations_list,
            evidence_report=evidence_rep,
            summary=summary_obj,
            consultant_observations=meta["consultant_notes"],
            missing_documents_notes=case.missing_documents_notes,
            disclaimer=TAMIL_NADU_VERIFICATION_DISCLAIMER,
            disclaimer_acknowledged=case.disclaimer_acknowledged,
            reviewed_by=case.reviewed_by,
            completed_at=case.completed_at,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    async def run_verification(
        self,
        session: AsyncSession,
        property_id: uuid.UUID,
        payload: Optional[PropertyVerificationInput] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> VerificationCaseResponse:
        """Run preliminary Tamil Nadu verification assessment on a property."""
        payload = payload or PropertyVerificationInput()

        async with transaction(session):
            # 1. Fetch target property with documents
            stmt = (
                select(Property)
                .where(Property.id == property_id)
                .options(
                    selectinload(Property.documents.and_(Document.is_archived.is_(False)))
                )
            )
            res = await session.execute(stmt)
            prop = res.scalar_one_or_none()

            if not prop or prop.is_archived:
                raise NotFoundError("Property not found or has been archived.")

            # Record audit log event: VERIFICATION_REQUESTED
            await self.audit_repo.record(
                session=session,
                action="VERIFICATION_REQUESTED",
                entity_type="PROPERTY",
                entity_id=prop.id,
                actor_id=actor_id,
                change_diff={"property_id": str(prop.id)},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

            # 2. Extract active documents
            active_documents = [d for d in prop.documents if not d.is_archived]

            # 3. Execute deterministic evaluation
            eval_result = self.engine.evaluate(prop, active_documents, payload)

            # 4. Pack observations
            packed_obs = self._pack_observations(eval_result, payload.consultant_notes)

            # 5. Create VerificationCase entity
            now_utc = datetime.now(timezone.utc)
            case = VerificationCase(
                property_id=prop.id,
                status=eval_result.status,
                consultant_observations=packed_obs,
                missing_documents_notes=eval_result.missing_docs_notes,
                disclaimer_acknowledged=payload.disclaimer_acknowledged,
                reviewed_by=actor_id,
                completed_at=now_utc if eval_result.status == "COMPLETED" else None,
            )

            # 6. Map checklist items
            for chk in eval_result.checks:
                doc_id = chk.evidence[0].document_id if chk.evidence else None
                item = VerificationItem(
                    checklist_code=chk.checklist_code,
                    item_name=chk.item_name,
                    is_present=chk.is_present,
                    status=chk.status.value,
                    notes=chk.notes,
                    document_id=doc_id,
                )
                case.items.append(item)

            # Update last_verified_date on Property
            prop.last_verified_date = now_utc

            # 7. Persist to DB
            case = await self.repo.create(session, case)
            await session.flush()

            # Record completion audit log event
            completion_action = (
                "VERIFICATION_COMPLETED"
                if eval_result.status == "COMPLETED"
                else "VERIFICATION_NEEDS_REVIEW"
            )
            await self.audit_repo.record(
                session=session,
                action=completion_action,
                entity_type="VERIFICATION_CASE",
                entity_id=case.id,
                actor_id=actor_id,
                change_diff={
                    "status": eval_result.status,
                    "risk_level": eval_result.risk_level.value,
                    "completeness": eval_result.completeness_score,
                    "risk_flags": eval_result.risk_flags,
                    "engine_version": "TN-VERIFICATION-2.0",
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            case_id = case.id

        # Reload with eager associations to return complete response
        loaded_case = await self.repo.get_by_id(session, case_id)
        if not loaded_case:
            raise NotFoundError("Verification case could not be reloaded.")

        return self._format_case_response(loaded_case)

    async def get_verification(
        self, session: AsyncSession, verification_id: uuid.UUID
    ) -> VerificationCaseResponse:
        """Fetch verification case details by case ID."""
        case = await self.repo.get_by_id(session, verification_id)
        if not case:
            raise NotFoundError("Verification case not found.")
        return self._format_case_response(case)

    async def get_latest_for_property(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> VerificationCaseResponse:
        """Fetch latest verification assessment for a given property."""
        case = await self.repo.get_latest_by_property_id(session, property_id)
        if not case:
            raise NotFoundError("No preliminary verification case found for this property.")
        return self._format_case_response(case)

    async def list_verifications(
        self, session: AsyncSession, filters: VerificationFilterParams
    ) -> PaginatedResponse[VerificationCaseSummary]:
        """List verification cases with pagination and optional filtering."""
        cases, total = await self.repo.list_cases(session, filters)

        summaries: List[VerificationCaseSummary] = []
        for c in cases:
            meta = self._unpack_observations(c.consultant_observations)
            summaries.append(
                VerificationCaseSummary(
                    id=c.id,
                    property_id=c.property_id,
                    status=c.status,
                    risk_level=meta.get("risk_level"),
                    completeness_score=meta.get("completeness_score"),
                    disclaimer_acknowledged=c.disclaimer_acknowledged,
                    reviewed_by=c.reviewed_by,
                    completed_at=c.completed_at,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                )
            )

        return PaginatedResponse(
            items=summaries,
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def update_verification(
        self,
        session: AsyncSession,
        verification_id: uuid.UUID,
        payload: VerificationCaseUpdate,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> VerificationCaseResponse:
        """Update consultant observations or review notes for an existing case."""
        async with transaction(session):
            case = await self.repo.get_by_id_for_update(session, verification_id)
            if not case:
                raise NotFoundError("Verification case not found.")

            meta = self._unpack_observations(case.consultant_observations)

            if payload.consultant_observations is not None:
                meta["consultant_notes"] = payload.consultant_observations
                case.consultant_observations = json.dumps(meta, ensure_ascii=False)

            if payload.missing_documents_notes is not None:
                case.missing_documents_notes = payload.missing_documents_notes

            if payload.disclaimer_acknowledged is not None:
                case.disclaimer_acknowledged = payload.disclaimer_acknowledged

            if payload.status is not None:
                case.status = payload.status.upper()
                if case.status == "COMPLETED" and not case.completed_at:
                    case.completed_at = datetime.now(timezone.utc)

            case.reviewed_by = actor_id

            await self.audit_repo.record(
                session=session,
                action="VERIFICATION_UPDATED",
                entity_type="VERIFICATION_CASE",
                entity_id=case.id,
                actor_id=actor_id,
                change_diff={
                    "status": case.status,
                    "disclaimer_acknowledged": case.disclaimer_acknowledged,
                },
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            case_id = case.id

        loaded_case = await self.repo.get_by_id(session, case_id)
        return self._format_case_response(loaded_case)

    async def get_verification_summary(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> VerificationSummaryResponse:
        """Fetch machine-readable summary metrics for a property's verification."""
        case = await self.repo.get_latest_by_property_id(session, property_id)
        if not case:
            raise NotFoundError("No preliminary verification case found for this property.")
        meta = self._unpack_observations(case.consultant_observations)
        if meta.get("summary"):
            try:
                return VerificationSummaryResponse.model_validate(meta["summary"])
            except Exception:
                pass
        return VerificationSummaryResponse(
            property_id=case.property_id,
            overall_risk=meta.get("risk_level", RiskLevel.MEDIUM.value),
            documentary_completeness_score=meta.get("completeness_score", 0),
            critical_issue_count=len(meta.get("risk_flags", [])),
            high_risk_issue_count=0,
            medium_risk_issue_count=0,
            low_risk_issue_count=0,
            missing_document_count=len(meta.get("missing_information", [])),
            review_required_count=len([item for item in case.items if item.status == "REVIEW"]),
            disclaimer=TAMIL_NADU_VERIFICATION_DISCLAIMER,
        )

    async def get_verification_evidence(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> EvidenceIntelligenceReport:
        """Fetch detailed documentary evidence intelligence for a property."""
        case = await self.repo.get_latest_by_property_id(session, property_id)
        if not case:
            raise NotFoundError("No preliminary verification case found for this property.")
        meta = self._unpack_observations(case.consultant_observations)
        if meta.get("evidence_report"):
            try:
                return EvidenceIntelligenceReport.model_validate(meta["evidence_report"])
            except Exception:
                pass
        return EvidenceIntelligenceReport(
            property_id=case.property_id,
            evidence_completeness=meta.get("completeness_score", 0),
            evidence_quality="MEDIUM",
            evidence_conflict_count=0,
            missing_critical_evidence=meta.get("missing_information", []),
            unresolved_review_items=[],
            chronology_integrity="CHRONOLOGY_INCOMPLETE",
            identity_consistency="INCOMPLETE",
            evidence_items=[],
            disclaimer=TAMIL_NADU_VERIFICATION_DISCLAIMER,
        )

    async def get_verification_actions(
        self, session: AsyncSession, property_id: uuid.UUID
    ) -> List[ConsultantActionItemSchema]:
        """Fetch prioritized consultant action items for a property's verification."""
        case = await self.repo.get_latest_by_property_id(session, property_id)
        if not case:
            raise NotFoundError("No preliminary verification case found for this property.")
        meta = self._unpack_observations(case.consultant_observations)
        actions_list = []
        for act in meta.get("actions", []):
            try:
                actions_list.append(ConsultantActionItemSchema.model_validate(act))
            except Exception:
                pass
        return actions_list
