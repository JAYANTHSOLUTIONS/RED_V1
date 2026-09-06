"""Pydantic schemas for Tamil Nadu Preliminary Property Verification.

Adheres strictly to the compliance requirement that preliminary property verification
is NOT legal title certification. Encapsulates explainable check findings, deterministic
risk flags, and evidence trace references.
"""
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

TAMIL_NADU_VERIFICATION_DISCLAIMER = (
    "This is a preliminary property verification assessment based on the information and "
    "documentary evidence available to RED_V1. It does not constitute legal title verification, "
    "certification of ownership, confirmation of document authenticity, or a guarantee that "
    "the property is free from encumbrances, disputes, planning violations, or other legal issues. "
    "Independent verification by the appropriate authorities and qualified legal professionals "
    "may be required."
)


class VerificationStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    INFO = "INFO"


class CheckStatus(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INFO = "INFO"


class CheckCategory(str, Enum):
    PROPERTY_IDENTITY = "PROPERTY_IDENTITY"
    LAND_RECORDS = "LAND_RECORDS"
    REGISTRATION_SRO = "REGISTRATION_SRO"
    PLANNING_APPROVAL = "PLANNING_APPROVAL"
    RERA = "RERA"
    DOCUMENT_CHAIN = "DOCUMENT_CHAIN"
    MUNICIPAL_TAX = "MUNICIPAL_TAX"


class PlanningAuthorityType(str, Enum):
    CMDA = "CMDA"
    DTCP = "DTCP"
    LOCAL_PLANNING_AUTHORITY = "LOCAL_PLANNING_AUTHORITY"
    LOCAL_BODY = "LOCAL_BODY"
    UNKNOWN = "UNKNOWN"


class ReraApplicability(str, Enum):
    RERA_APPLICABLE = "RERA_APPLICABLE"
    RERA_NOT_APPLICABLE = "RERA_NOT_APPLICABLE"
    RERA_UNKNOWN = "RERA_UNKNOWN"


class EvidenceItem(BaseModel):
    """Secure document reference tracing a verification finding to uploaded evidence."""
    model_config = ConfigDict(str_strip_whitespace=True)

    document_id: Optional[uuid.UUID] = None
    document_type: str
    original_filename: Optional[str] = None


class CheckResult(BaseModel):
    """Granular, explainable result of an individual verification rule."""
    model_config = ConfigDict(str_strip_whitespace=True)

    checklist_code: str
    item_name: str
    category: CheckCategory
    status: CheckStatus
    is_present: bool
    risk_level: RiskLevel
    notes: Optional[str] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)


class PropertyVerificationInput(BaseModel):
    """Optional consultant-supplied parameters or overrides for Tamil Nadu verification."""
    model_config = ConfigDict(str_strip_whitespace=True)

    survey_number: Optional[str] = Field(None, max_length=100)
    subdivision_number: Optional[str] = Field(None, max_length=100)
    patta_number: Optional[str] = Field(None, max_length=100)
    plot_number: Optional[str] = Field(None, max_length=100)
    door_number: Optional[str] = Field(None, max_length=100)
    flat_number: Optional[str] = Field(None, max_length=100)
    block: Optional[str] = Field(None, max_length=100)
    taluk: Optional[str] = Field(None, max_length=100)
    village: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    sro_name: Optional[str] = Field(None, max_length=100)

    # EC Details
    ec_start_date: Optional[date] = None
    ec_end_date: Optional[date] = None
    ec_has_encumbrance_entries: Optional[bool] = None
    ec_notes: Optional[str] = None

    # Planning Authority
    planning_authority: Optional[str] = None  # CMDA, DTCP, etc.
    planning_approval_number: Optional[str] = Field(None, max_length=100)
    layout_approval_number: Optional[str] = Field(None, max_length=100)

    # TNRERA
    rera_registration_number: Optional[str] = Field(None, max_length=100)
    rera_project_name: Optional[str] = Field(None, max_length=200)
    rera_promoter_name: Optional[str] = Field(None, max_length=200)
    is_new_project_or_promoter_sale: Optional[bool] = None

    # Title & Chain Dates
    parent_document_date: Optional[date] = None
    current_deed_date: Optional[date] = None

    # Municipal Tax
    property_tax_assessment_number: Optional[str] = Field(None, max_length=100)
    property_tax_paid_period: Optional[str] = Field(None, max_length=100)

    consultant_notes: Optional[str] = None
    disclaimer_acknowledged: bool = True


class EvidenceStatus(str, Enum):
    NOT_PROVIDED = "NOT_PROVIDED"
    PROVIDED = "PROVIDED"
    PARSED = "PARSED"
    CONSISTENT = "CONSISTENT"
    INCONSISTENT = "INCONSISTENT"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ProcessingConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOT_ASSESSED = "NOT_ASSESSED"


class ReraApplicabilityReason(str, Enum):
    PROMOTER_PROJECT = "PROMOTER_PROJECT"
    NEW_APARTMENT_DEVELOPMENT = "NEW_APARTMENT_DEVELOPMENT"
    MARKETED_LAYOUT = "MARKETED_LAYOUT"
    DEVELOPER_INVENTORY = "DEVELOPER_INVENTORY"
    SECONDARY_RESALE = "SECONDARY_RESALE"
    AGRICULTURAL_PROPERTY = "AGRICULTURAL_PROPERTY"
    STANDALONE_OLD_PROPERTY = "STANDALONE_OLD_PROPERTY"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class DetailedEvidenceItem(BaseModel):
    """Granular evidence status representation."""
    model_config = ConfigDict(str_strip_whitespace=True)

    evidence_type: str
    status: EvidenceStatus
    source_document_id: Optional[uuid.UUID] = None
    confidence: ProcessingConfidence = ProcessingConfidence.NOT_ASSESSED
    notes: Optional[str] = None


class CheckExplanation(BaseModel):
    """Structured, plain-language explanation of a verification check."""
    model_config = ConfigDict(str_strip_whitespace=True)

    checklist_code: str
    result: str
    explanation: str
    risk: RiskLevel
    recommended_action: str


class ConsultantActionItemSchema(BaseModel):
    """Recommended next-step action for consultant."""
    model_config = ConfigDict(str_strip_whitespace=True)

    action_type: str
    priority: str
    target_document_type: Optional[str] = None
    description: str


class ChronologyGraphNode(BaseModel):
    """Node in the title chain graph."""
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str
    type: str
    date: Optional[str] = None


class ChronologyReport(BaseModel):
    """Document chronology graph report."""
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str
    nodes: List[ChronologyGraphNode] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)


class VerificationSummaryResponse(BaseModel):
    """Concise machine-readable verification summary."""
    model_config = ConfigDict(from_attributes=True)

    property_id: uuid.UUID
    overall_risk: str
    documentary_completeness_score: int
    critical_issue_count: int
    high_risk_issue_count: int
    medium_risk_issue_count: int
    low_risk_issue_count: int
    missing_document_count: int
    review_required_count: int
    disclaimer: str = TAMIL_NADU_VERIFICATION_DISCLAIMER


class EvidenceIntelligenceReport(BaseModel):
    """Comprehensive evidence intelligence layer output."""
    model_config = ConfigDict(from_attributes=True)

    property_id: uuid.UUID
    evidence_completeness: int
    evidence_quality: str
    evidence_conflict_count: int
    missing_critical_evidence: List[str] = Field(default_factory=list)
    unresolved_review_items: List[str] = Field(default_factory=list)
    chronology_integrity: str
    identity_consistency: str
    evidence_items: List[DetailedEvidenceItem] = Field(default_factory=list)
    disclaimer: str = TAMIL_NADU_VERIFICATION_DISCLAIMER


class VerificationCaseResponse(BaseModel):
    """Comprehensive explainable verification assessment."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    status: str
    risk_level: str
    completeness_score: int
    completeness_notes: str = (
        "Completeness measures documentary evidence availability, NOT legal title certainty."
    )
    planning_authority_type: str
    rera_applicability: str
    rera_applicability_reason: Optional[str] = None
    risk_flags: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    checks: List[CheckResult] = Field(default_factory=list)
    explanations: List[CheckExplanation] = Field(default_factory=list)
    actions: List[ConsultantActionItemSchema] = Field(default_factory=list)
    chronology: Optional[ChronologyReport] = None
    evidence_report: Optional[EvidenceIntelligenceReport] = None
    summary: Optional[VerificationSummaryResponse] = None
    consultant_observations: Optional[str] = None
    missing_documents_notes: Optional[str] = None
    disclaimer: str = TAMIL_NADU_VERIFICATION_DISCLAIMER
    disclaimer_acknowledged: bool
    engine_version: str = "TN-VERIFICATION-2.0"
    reviewed_by: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class VerificationCaseSummary(BaseModel):
    """Compact summary of a verification case for listing collections."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    status: str
    risk_level: Optional[str] = None
    completeness_score: Optional[int] = None
    disclaimer_acknowledged: bool
    reviewed_by: Optional[uuid.UUID] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class VerificationCaseUpdate(BaseModel):
    """Consultant update for observations, missing documents, or disclaimer acknowledgement."""
    model_config = ConfigDict(str_strip_whitespace=True)

    consultant_observations: Optional[str] = None
    missing_documents_notes: Optional[str] = None
    disclaimer_acknowledged: Optional[bool] = None
    status: Optional[str] = None


class VerificationFilterParams:
    """Query parameters for filtering verification records."""
    def __init__(
        self,
        property_id: Optional[uuid.UUID] = Query(None, description="Filter by property ID"),
        status: Optional[str] = Query(None, description="Filter by verification status"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        offset: int = Query(0, ge=0, description="Pagination offset"),
    ):
        self.property_id = property_id
        self.status = status
        self.limit = limit
        self.offset = offset
