"""Pydantic schemas for Property Requirements and Matching domain."""
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional
import uuid

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.client import ClientSummaryResponse

VALID_REQUIREMENT_TRANSACTION_TYPES = {"BUY", "SALE", "RENT", "LEASE"}


class PropertyRequirementBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    transaction_type: str = Field(..., max_length=20, description="Desired transaction: BUY, SALE, RENT, LEASE")
    property_types: Optional[str] = Field(None, max_length=255, description="Target property type(s), e.g. Apartment, Villa")
    target_locations: Optional[str] = Field(None, description="Preferred locations, localities, or districts")
    min_budget: Optional[Decimal] = Field(None, ge=0, description="Minimum acceptable price")
    max_budget: Optional[Decimal] = Field(None, ge=0, description="Maximum acceptable price")
    min_area: Optional[Decimal] = Field(None, ge=0, description="Minimum acceptable area")
    max_area: Optional[Decimal] = Field(None, ge=0, description="Maximum acceptable area")
    area_unit: str = Field("sq.ft", max_length=20, description="Area measurement unit (default sq.ft)")
    bedrooms: Optional[int] = Field(None, ge=0, description="Preferred bedroom count")
    bathrooms: Optional[int] = Field(None, ge=0, description="Preferred bathroom count")
    facing: Optional[str] = Field(None, max_length=50, description="Preferred facing orientation")
    furnishing_state: Optional[str] = Field(None, max_length=30, description="Furnishing requirement")
    notes: Optional[str] = Field(None, description="Internal consultant notes regarding requirement")

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in VALID_REQUIREMENT_TRANSACTION_TYPES:
            raise ValueError(
                f"Invalid transaction type '{v}'. Allowed: {', '.join(sorted(VALID_REQUIREMENT_TRANSACTION_TYPES))}"
            )
        return v_upper

    @model_validator(mode="after")
    def validate_bounds(self) -> "PropertyRequirementBase":
        if self.min_budget is not None and self.max_budget is not None:
            if self.min_budget > self.max_budget:
                raise ValueError("min_budget cannot be greater than max_budget.")
        if self.min_area is not None and self.max_area is not None:
            if self.min_area > self.max_area:
                raise ValueError("min_area cannot be greater than max_area.")
        return self


class PropertyRequirementCreate(PropertyRequirementBase):
    client_id: uuid.UUID = Field(..., description="ID of client seeking property")


class PropertyRequirementUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    transaction_type: Optional[str] = Field(None, max_length=20)
    property_types: Optional[str] = Field(None, max_length=255)
    target_locations: Optional[str] = None
    min_budget: Optional[Decimal] = Field(None, ge=0)
    max_budget: Optional[Decimal] = Field(None, ge=0)
    min_area: Optional[Decimal] = Field(None, ge=0)
    max_area: Optional[Decimal] = Field(None, ge=0)
    area_unit: Optional[str] = Field(None, max_length=20)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    facing: Optional[str] = Field(None, max_length=50)
    furnishing_state: Optional[str] = Field(None, max_length=30)
    notes: Optional[str] = None

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.strip().upper()
            if v_upper not in VALID_REQUIREMENT_TRANSACTION_TYPES:
                raise ValueError(
                    f"Invalid transaction type '{v}'. Allowed: {', '.join(sorted(VALID_REQUIREMENT_TRANSACTION_TYPES))}"
                )
            return v_upper
        return v

    @model_validator(mode="after")
    def validate_bounds(self) -> "PropertyRequirementUpdate":
        if self.min_budget is not None and self.max_budget is not None:
            if self.min_budget > self.max_budget:
                raise ValueError("min_budget cannot be greater than max_budget.")
        if self.min_area is not None and self.max_area is not None:
            if self.min_area > self.max_area:
                raise ValueError("min_area cannot be greater than max_area.")
        return self


class PropertyRequirementSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    transaction_type: str
    property_types: Optional[str] = None
    min_budget: Optional[Decimal] = None
    max_budget: Optional[Decimal] = None
    status: str
    created_at: datetime


class PropertyRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    transaction_type: str
    property_types: Optional[str] = None
    target_locations: Optional[str] = None
    min_budget: Optional[Decimal] = None
    max_budget: Optional[Decimal] = None
    min_area: Optional[Decimal] = None
    max_area: Optional[Decimal] = None
    area_unit: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    facing: Optional[str] = None
    furnishing_state: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    client: Optional[ClientSummaryResponse] = None


class RequirementFilterParams:
    def __init__(
        self,
        client_id: Optional[uuid.UUID] = Query(None, description="Filter by client ID"),
        transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
        property_type: Optional[str] = Query(None, description="Filter by property type substring"),
        status: Optional[str] = Query(None, description="Filter by status (ACTIVE, FULFILLED, CANCELLED, ARCHIVED)"),
        search: Optional[str] = Query(None, description="Search target locations or notes"),
        limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
        offset: int = Query(0, ge=0, description="Offset index"),
        sort_by: str = Query("created_at", description="Sort field: created_at, min_budget, max_budget"),
        sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    ):
        self.client_id = client_id
        self.transaction_type = transaction_type
        self.property_type = property_type
        self.status = status
        self.search = search
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.sort_order = sort_order


# ---------------------------------------------------------------------------
# Matching Result Schemas
# ---------------------------------------------------------------------------


class MatchingPropertySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_reference: str
    title: str
    property_type: str
    transaction_type: str
    price: Decimal
    price_negotiable: bool
    built_up_area: Optional[Decimal] = None
    plot_area: Optional[Decimal] = None
    area_unit: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    facing: Optional[str] = None
    furnishing_state: Optional[str] = None
    parking_spaces: Optional[int] = None
    district: str
    city: str
    locality: str
    status: str


class PropertyMatchItem(BaseModel):
    property: MatchingPropertySummary
    match_grade: str = Field(..., description="EXACT_MATCH or PARTIAL_MATCH")
    score: int = Field(..., ge=0, le=100, description="Matching percentage score (0-100)")
    matched_criteria: List[str] = Field(default_factory=list, description="List of criteria that satisfied the requirement")
    unmatched_criteria: List[str] = Field(default_factory=list, description="List of criteria that failed the requirement")


class RequirementMatchParams:
    def __init__(
        self,
        min_score: int = Query(50, ge=0, le=100, description="Minimum match score to include (0-100)"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        offset: int = Query(0, ge=0, description="Offset index"),
    ):
        self.min_score = min_score
        self.limit = limit
        self.offset = offset
