"""Pydantic schemas for Client domain.

Strictly isolates client data, performs whitespace normalization,
validates contact methods and classifications, and provides safe response structures.
"""
from datetime import datetime
from typing import Any, List, Optional
import uuid

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


class ClientBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(..., min_length=1, max_length=255, description="Client full legal or display name")
    phone: str = Field(..., min_length=3, max_length=50, description="Primary contact phone number")
    email: Optional[str] = Field(None, max_length=255, pattern=EMAIL_REGEX, description="Client email address")
    preferred_contact_method: str = Field("CALL", max_length=20, description="Preferred contact method")
    postal_address: Optional[str] = Field(None, description="Physical postal address")
    classification: str = Field("BUYER", max_length=30, description="Client classification: BUYER, SELLER, TENANT, LANDLORD, INVESTOR")
    source: Optional[str] = Field(None, max_length=50, description="Origination source")
    notes: Optional[str] = Field(None, description="Internal consultant notes")

    @field_validator("full_name", "phone", mode="before")
    @classmethod
    def check_not_empty(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Field cannot be empty or whitespace-only.")
            return v_stripped
        return v

    @field_validator("preferred_contact_method")
    @classmethod
    def validate_contact_method(cls, v: str) -> str:
        allowed = {"CALL", "WHATSAPP", "EMAIL", "SMS"}
        v_upper = v.strip().upper()
        if v_upper not in allowed:
            raise ValueError(f"Invalid contact method '{v}'. Allowed: {', '.join(sorted(allowed))}")
        return v_upper

    @field_validator("classification")
    @classmethod
    def validate_classification(cls, v: str) -> str:
        allowed = {"BUYER", "SELLER", "TENANT", "LANDLORD", "INVESTOR"}
        v_upper = v.strip().upper()
        if v_upper not in allowed:
            raise ValueError(f"Invalid classification '{v}'. Allowed: {', '.join(sorted(allowed))}")
        return v_upper


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None, max_length=255, pattern=EMAIL_REGEX)
    preferred_contact_method: Optional[str] = Field(None, max_length=20)
    postal_address: Optional[str] = None
    classification: Optional[str] = Field(None, max_length=30)
    source: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=30)
    notes: Optional[str] = None

    @field_validator("full_name", "phone")
    @classmethod
    def check_not_empty_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Field cannot be empty or whitespace-only.")
            return v_stripped
        return v

    @field_validator("preferred_contact_method")
    @classmethod
    def validate_contact_method(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"CALL", "WHATSAPP", "EMAIL", "SMS"}
            v_upper = v.strip().upper()
            if v_upper not in allowed:
                raise ValueError(f"Invalid contact method '{v}'. Allowed: {', '.join(sorted(allowed))}")
            return v_upper
        return v

    @field_validator("classification")
    @classmethod
    def validate_classification(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"BUYER", "SELLER", "TENANT", "LANDLORD", "INVESTOR"}
            v_upper = v.strip().upper()
            if v_upper not in allowed:
                raise ValueError(f"Invalid classification '{v}'. Allowed: {', '.join(sorted(allowed))}")
            return v_upper
        return v


class ClientSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    email: Optional[str] = None
    classification: str
    status: str
    is_archived: bool


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    phone: str
    email: Optional[str] = None
    preferred_contact_method: str
    postal_address: Optional[str] = None
    classification: str
    source: Optional[str] = None
    status: str
    notes: Optional[str] = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ClientLeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: Optional[uuid.UUID] = None
    source: str
    status: str
    lost_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ClientWithLeadsResponse(ClientResponse):
    leads: List[ClientLeadSummary] = []


class ClientFilterParams:
    def __init__(
        self,
        search: Optional[str] = Query(None, description="Search across full_name, phone, or email"),
        phone: Optional[str] = Query(None, description="Exact or partial phone filter"),
        email: Optional[str] = Query(None, description="Exact or partial email filter"),
        classification: Optional[str] = Query(None, description="Filter by classification (BUYER, SELLER, etc.)"),
        status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE, etc.)"),
        is_archived: Optional[bool] = Query(False, description="Filter archived records (default False)"),
        limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
        offset: int = Query(0, ge=0, description="Offset index"),
        sort_by: str = Query("created_at", description="Sort field: created_at, full_name, phone"),
        sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    ):
        self.search = search
        self.phone = phone
        self.email = email
        self.classification = classification
        self.status = status
        self.is_archived = is_archived
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.sort_order = sort_order
