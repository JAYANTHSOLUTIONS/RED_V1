"""Pydantic schemas for Follow-up Management domain.

Enforces action categories, target constraints (Client OR Lead),
lifecycle status transitions, and response serialization.
"""
from datetime import datetime
from typing import Any, List, Optional
import uuid

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import PaginatedResponse

TAMIL_NADU_PRELIMINARY_DISCLAIMER = (
    "This is a preliminary property verification assessment based on the information "
    "and documentary evidence available to RED_V1. It does not constitute legal title "
    "verification, certification of ownership, confirmation of document authenticity, "
    "or a guarantee that the property is free from encumbrances, disputes, planning "
    "violations, or other legal issues. Independent verification by the appropriate "
    "authorities and qualified legal professionals may be required."
)

VALID_ACTION_TYPES = {
    "CALL",
    "SEND_DOCS",
    "ARRANGE_VISIT",
    "OWNER_FOLLOW_UP",
    "MISSING_PAPERWORK",
}

VALID_STATUSES = {
    "SCHEDULED",
    "COMPLETED",
    "MISSED",
}


# --- Relation Summaries ---

class ClientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    classification: Optional[str] = None


class LeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    source: Optional[str] = None


class PropertySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    public_reference: str
    property_type: str
    city: str
    locality: Optional[str] = None
    district: Optional[str] = None


# --- Mutation Schemas ---

class FollowUpCreate(BaseModel):
    """Consultant follow-up task creation schema."""
    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: Optional[uuid.UUID] = Field(None, description="Target Client ID")
    lead_id: Optional[uuid.UUID] = Field(None, description="Target Lead ID")
    property_id: Optional[uuid.UUID] = Field(None, description="Optional associated Property ID")
    action_type: str = Field(..., description="Action: CALL, SEND_DOCS, ARRANGE_VISIT, OWNER_FOLLOW_UP, MISSING_PAPERWORK")
    scheduled_at: datetime = Field(..., description="Planned execution timestamp (IST/timezone-aware)")
    notes: Optional[str] = Field(None, max_length=2000, description="Task details / consultant instructions")

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in VALID_ACTION_TYPES:
            raise ValueError(
                f"Invalid action_type '{v}'. Allowed types: {', '.join(sorted(VALID_ACTION_TYPES))}"
            )
        return v_upper

    @model_validator(mode="after")
    def check_target_present(self) -> "FollowUpCreate":
        if self.client_id is None and self.lead_id is None:
            raise ValueError("Follow-up requires at least one target: client_id or lead_id must be provided.")
        return self


class FollowUpUpdate(BaseModel):
    """Consultant follow-up task partial update schema (metadata only)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    action_type: Optional[str] = Field(None, description="Updated action type")
    scheduled_at: Optional[datetime] = Field(None, description="Rescheduled execution timestamp")
    notes: Optional[str] = Field(None, max_length=2000, description="Updated notes")
    property_id: Optional[uuid.UUID] = Field(None, description="Updated property association")

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_upper = v.strip().upper()
        if v_upper not in VALID_ACTION_TYPES:
            raise ValueError(
                f"Invalid action_type '{v}'. Allowed types: {', '.join(sorted(VALID_ACTION_TYPES))}"
            )
        return v_upper


class FollowUpComplete(BaseModel):
    """Completion payload with optional outcome notes."""
    model_config = ConfigDict(str_strip_whitespace=True)

    completion_notes: Optional[str] = Field(None, max_length=2000, description="Outcome of the follow-up task")


class FollowUpMiss(BaseModel):
    """Missed task payload with optional reason."""
    model_config = ConfigDict(str_strip_whitespace=True)

    notes: Optional[str] = Field(None, max_length=2000, description="Reason follow-up was missed or next steps")


# --- Response Schemas ---

class FollowUpResponse(BaseModel):
    """Detailed response model for FollowUp entities."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: Optional[uuid.UUID] = None
    lead_id: Optional[uuid.UUID] = None
    property_id: Optional[uuid.UUID] = None
    scheduled_at: datetime
    action_type: str
    status: str
    notes: Optional[str] = None
    completion_notes: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    client: Optional[ClientSummary] = None
    lead: Optional[LeadSummary] = None
    property: Optional[PropertySummary] = None
    disclaimer: str = TAMIL_NADU_PRELIMINARY_DISCLAIMER


# --- Filter Parameters ---

class FollowUpFilterParams:
    """Dependency query parameters for listing follow-up tasks."""

    def __init__(
        self,
        status: Optional[str] = Query(None, description="Filter by status (SCHEDULED, COMPLETED, MISSED)"),
        action_type: Optional[str] = Query(None, description="Filter by action type"),
        client_id: Optional[uuid.UUID] = Query(None, description="Filter by target Client ID"),
        lead_id: Optional[uuid.UUID] = Query(None, description="Filter by target Lead ID"),
        property_id: Optional[uuid.UUID] = Query(None, description="Filter by related Property ID"),
        scheduled_from: Optional[datetime] = Query(None, description="Filter tasks on or after this timestamp"),
        scheduled_to: Optional[datetime] = Query(None, description="Filter tasks on or before this timestamp"),
        limit: int = Query(20, ge=1, le=100, description="Page limit (default: 20, max: 100)"),
        offset: int = Query(0, ge=0, description="Page offset (default: 0)"),
    ):
        self.status = status.upper().strip() if status else None
        self.action_type = action_type.upper().strip() if action_type else None
        self.client_id = client_id
        self.lead_id = lead_id
        self.property_id = property_id
        self.scheduled_from = scheduled_from
        self.scheduled_to = scheduled_to
        self.limit = limit
        self.offset = offset
