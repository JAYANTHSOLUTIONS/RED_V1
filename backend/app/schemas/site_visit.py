"""Pydantic schemas for Site Visit Coordination domain.

Provides strict request validation, public vs. private data isolation,
lifecycle transitions, and response envelopes for Tamil Nadu site visits.
"""
from datetime import datetime
from typing import Any, List, Optional
import uuid

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PaginatedResponse

TAMIL_NADU_PRELIMINARY_DISCLAIMER = (
    "This is a preliminary property verification assessment based on the information "
    "and documentary evidence available to RED_V1. It does not constitute legal title "
    "verification, certification of ownership, confirmation of document authenticity, "
    "or a guarantee that the property is free from encumbrances, disputes, planning "
    "violations, or other legal issues. Independent verification by the appropriate "
    "authorities and qualified legal professionals may be required."
)

VALID_STATUSES = {
    "REQUESTED",
    "CONFIRMED",
    "COMPLETED",
    "CANCELLED",
    "RESCHEDULED",
}


class ClientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    classification: Optional[str] = None


class PropertySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    public_reference: str
    property_type: str
    city: str
    locality: Optional[str] = None
    district: Optional[str] = None


class LeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str


# --- Request Schemas ---

class SiteVisitPublicRequest(BaseModel):
    """Customer-initiated visit request. Status is always REQUESTED."""
    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: uuid.UUID = Field(..., description="ID of the requesting client")
    property_id: uuid.UUID = Field(..., description="Target property ID")
    lead_id: Optional[uuid.UUID] = Field(None, description="Optional associated lead ID")
    scheduled_at: datetime = Field(..., description="Proposed visit timestamp (IST/timezone-aware)")
    notes: Optional[str] = Field(None, max_length=1000, description="Customer request notes or preferred timing details")


class SiteVisitCreate(BaseModel):
    """Consultant-initiated site visit creation."""
    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: uuid.UUID = Field(..., description="ID of the client")
    property_id: uuid.UUID = Field(..., description="Target property ID")
    lead_id: Optional[uuid.UUID] = Field(None, description="Optional associated lead ID")
    scheduled_at: datetime = Field(..., description="Proposed visit timestamp (IST/timezone-aware)")
    status: Optional[str] = Field("REQUESTED", description="Initial status (REQUESTED or CONFIRMED)")
    notes: Optional[str] = Field(None, max_length=2000, description="Internal consultant or operational notes")

    @field_validator("status")
    @classmethod
    def validate_initial_status(cls, v: Optional[str]) -> str:
        if v is None:
            return "REQUESTED"
        v_upper = v.strip().upper()
        if v_upper not in {"REQUESTED", "CONFIRMED"}:
            raise ValueError("Initial status on creation must be 'REQUESTED' or 'CONFIRMED'.")
        return v_upper


class SiteVisitUpdate(BaseModel):
    """Consultant update for editable metadata."""
    model_config = ConfigDict(str_strip_whitespace=True)

    scheduled_at: Optional[datetime] = Field(None, description="Updated schedule (if visit is still REQUESTED)")
    notes: Optional[str] = Field(None, max_length=2000, description="Consultant operational notes")
    feedback: Optional[str] = Field(None, max_length=2000, description="Site visit feedback/observations")


class SiteVisitConfirm(BaseModel):
    """Consultant confirmation payload."""
    model_config = ConfigDict(str_strip_whitespace=True)

    scheduled_at: Optional[datetime] = Field(None, description="Confirmed schedule (if modifying the requested time)")
    notes: Optional[str] = Field(None, max_length=2000, description="Optional notes upon confirmation")


class SiteVisitComplete(BaseModel):
    """Consultant completion payload."""
    model_config = ConfigDict(str_strip_whitespace=True)

    feedback: Optional[str] = Field(None, max_length=2000, description="Visit outcome, buyer reaction, or consultant feedback")
    notes: Optional[str] = Field(None, max_length=2000, description="Additional consultant notes")


class SiteVisitCancel(BaseModel):
    """Cancellation payload with mandatory reason."""
    model_config = ConfigDict(str_strip_whitespace=True)

    cancellation_reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory reason for cancellation")
    notes: Optional[str] = Field(None, max_length=2000, description="Optional cancellation notes")


class SiteVisitReschedule(BaseModel):
    """Reschedule payload creating a new linked visit record."""
    model_config = ConfigDict(str_strip_whitespace=True)

    new_scheduled_at: datetime = Field(..., description="New proposed/confirmed visit timestamp")
    reason: Optional[str] = Field(None, max_length=1000, description="Reason for rescheduling")
    notes: Optional[str] = Field(None, max_length=2000, description="Consultant notes for the rescheduled visit")


# --- Response Schemas ---

class SiteVisitPublicResponse(BaseModel):
    """Public customer-safe view of a site visit without consultant notes or client PII."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    scheduled_at: datetime
    status: str
    created_at: datetime
    disclaimer: str = TAMIL_NADU_PRELIMINARY_DISCLAIMER


class SiteVisitPrivateResponse(BaseModel):
    """Full consultant view of a site visit."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    property_id: uuid.UUID
    lead_id: Optional[uuid.UUID] = None
    scheduled_at: datetime
    status: str
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    rescheduled_from_id: Optional[uuid.UUID] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    client: Optional[ClientSummary] = None
    property: Optional[PropertySummary] = None
    lead: Optional[LeadSummary] = None
    disclaimer: str = TAMIL_NADU_PRELIMINARY_DISCLAIMER


# --- Query/Filter Parameters ---

class SiteVisitFilterParams:
    """Dependency query parameters for listing site visits."""

    def __init__(
        self,
        status: Optional[str] = Query(None, description="Filter by status (REQUESTED, CONFIRMED, COMPLETED, CANCELLED, RESCHEDULED)"),
        property_id: Optional[uuid.UUID] = Query(None, description="Filter by property ID"),
        client_id: Optional[uuid.UUID] = Query(None, description="Filter by client ID"),
        lead_id: Optional[uuid.UUID] = Query(None, description="Filter by lead ID"),
        date_from: Optional[datetime] = Query(None, description="Filter visits on or after this timestamp"),
        date_to: Optional[datetime] = Query(None, description="Filter visits on or before this timestamp"),
        upcoming_only: bool = Query(False, description="Filter only upcoming visits from now"),
        limit: int = Query(20, ge=1, le=100, description="Page limit (default: 20, max: 100)"),
        offset: int = Query(0, ge=0, description="Page offset (default: 0)"),
    ):
        self.status = status.upper().strip() if status else None
        self.property_id = property_id
        self.client_id = client_id
        self.lead_id = lead_id
        self.date_from = date_from
        self.date_to = date_to
        self.upcoming_only = upcoming_only
        self.limit = limit
        self.offset = offset
