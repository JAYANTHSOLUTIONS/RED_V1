"""Pydantic schemas for Lead domain.

Enforces lead validation, non-lifecycle field isolation for updates,
structured lost reasons, and safe summaries.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
import uuid

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.client import ClientSummaryResponse


class PropertySummaryInLead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_reference: str
    title: str
    property_type: str
    transaction_type: str
    price: Decimal
    city: str
    locality: str
    status: str


class LeadSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    property_id: Optional[uuid.UUID] = None
    source: str
    status: str
    lost_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: uuid.UUID = Field(..., description="ID of associated client")
    property_id: Optional[uuid.UUID] = Field(None, description="Optional ID of associated property")
    requirement_id: Optional[uuid.UUID] = Field(None, description="Optional ID of associated requirement")
    source: str = Field(..., min_length=1, max_length=50, description="Lead origination source (e.g. WEBSITE, DIRECT_CALL, WHATSAPP, REFERRAL, WALK_IN)")
    notes: Optional[str] = Field(None, description="Initial internal notes")

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Lead source cannot be empty or whitespace-only.")
        return v_stripped


class LeadUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    property_id: Optional[uuid.UUID] = Field(None, description="Updated associated property")
    requirement_id: Optional[uuid.UUID] = Field(None, description="Updated associated requirement")
    source: Optional[str] = Field(None, min_length=1, max_length=50, description="Updated source")
    notes: Optional[str] = Field(None, description="Updated notes")

    @field_validator("source")
    @classmethod
    def validate_source_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Lead source cannot be empty or whitespace-only.")
            return v_stripped
        return v


class LeadLostPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    lost_reason: str = Field(..., min_length=1, max_length=1000, description="Mandatory reason explaining why the lead was lost")

    @field_validator("lost_reason")
    @classmethod
    def validate_lost_reason(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Lost reason cannot be empty or whitespace-only.")
        return v_stripped


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    property_id: Optional[uuid.UUID] = None
    requirement_id: Optional[uuid.UUID] = None
    source: str
    status: str
    lost_reason: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    client: Optional[ClientSummaryResponse] = None
    property: Optional[PropertySummaryInLead] = None


class LeadFilterParams:
    def __init__(
        self,
        status: Optional[str] = Query(None, description="Filter by status (NEW, CONTACTED, etc.)"),
        client_id: Optional[uuid.UUID] = Query(None, description="Filter by client ID"),
        property_id: Optional[uuid.UUID] = Query(None, description="Filter by property ID"),
        source: Optional[str] = Query(None, description="Filter by source"),
        search: Optional[str] = Query(None, description="Search across notes and lost reason"),
        limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
        offset: int = Query(0, ge=0, description="Offset index"),
        sort_by: str = Query("created_at", description="Sort field: created_at, status"),
        sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    ):
        self.status = status
        self.client_id = client_id
        self.property_id = property_id
        self.source = source
        self.search = search
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.sort_order = sort_order
