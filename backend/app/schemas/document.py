"""Pydantic schemas for Document Management and Secure Storage."""
from datetime import datetime
from typing import List, Optional
import uuid

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_DOCUMENT_TYPES = {
    # Property / Land Records
    "EC",
    "ENCUMBRANCE_CERTIFICATE",
    "PATTA",
    "CHITTA",
    "ADANGAL",
    "A_REGISTER",
    "TSLR",
    "FMB",
    "SURVEY_DOCUMENT",
    "SUBDIVISION_DOCUMENT",
    "PROPERTY_TAX_DOCUMENT",
    "PROPERTY_TAX_RECEIPT",
    "PROPERTY_TAX_ASSESSMENT",
    "ASSESSMENT_DOCUMENT",
    # Ownership / Deeds
    "SALE_DEED",
    "SALE_AGREEMENT",
    "AGREEMENT_OF_SALE",
    "PARENT_DOCUMENT",
    "LINK_DOCUMENT",
    "GIFT_DEED",
    "SETTLEMENT_DEED",
    "PARTITION_DEED",
    "RELEASE_DEED",
    "POWER_OF_ATTORNEY",
    "MORTGAGE_DEED",
    "LEASE_DEED",
    # Approvals / Planning / RERA
    "BUILDING_APPROVAL",
    "BUILDING_PERMISSION",
    "LAYOUT_APPROVAL",
    "PLANNING_PERMISSION",
    "CMDA_APPROVAL",
    "DTCP_APPROVAL",
    "LOCAL_BODY_APPROVAL",
    "RERA_DOCUMENT",
    "TNRERA_REGISTRATION",
    # Client / Identity Proofs
    "IDENTITY_PROOF",
    "AUTHORIZATION_LETTER",
    "OTHER",
}

VALID_DOCUMENT_STATUSES = {
    "UPLOADED",
    "UNDER_REVIEW",
    "PRELIMINARILY_CHECKED",
    "REQUIRES_ATTENTION",
    "ARCHIVED",
}


class TamilNaduMetadata(BaseModel):
    """Optional structured Tamil Nadu registration and municipal references."""
    model_config = ConfigDict(str_strip_whitespace=True)

    district: Optional[str] = Field(None, max_length=100)
    taluk: Optional[str] = Field(None, max_length=100)
    village: Optional[str] = Field(None, max_length=100)
    survey_number: Optional[str] = Field(None, max_length=100)
    subdivision_number: Optional[str] = Field(None, max_length=100)
    sro_name: Optional[str] = Field(None, max_length=100)
    document_number: Optional[str] = Field(None, max_length=50)
    document_year: Optional[int] = Field(None, ge=1800, le=2100)
    assessment_number: Optional[str] = Field(None, max_length=100)
    rera_reference: Optional[str] = Field(None, max_length=100)


class DocumentResponse(BaseModel):
    """Safe user-facing document metadata response.

    Excludes raw filesystem paths, storage provider credentials, and internal keys.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None
    document_type: str
    original_filename: str
    mime_type: str
    file_size: int
    checksum: str
    status: str
    notes: Optional[str] = None
    is_archived: bool
    archived_at: Optional[datetime] = None
    uploaded_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    """Schema for updating editable document metadata."""
    model_config = ConfigDict(str_strip_whitespace=True)

    document_type: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None

    @field_validator("document_type")
    @classmethod
    def validate_doc_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_upper = v.strip().upper()
            if v_upper not in VALID_DOCUMENT_TYPES:
                raise ValueError(
                    f"Invalid document_type '{v}'. Allowed types: {', '.join(sorted(VALID_DOCUMENT_TYPES))}"
                )
            return v_upper
        return v


class DocumentFilterParams:
    """Query parameter dependency for filtering and paginating documents."""
    def __init__(
        self,
        property_id: Optional[uuid.UUID] = Query(None, description="Filter by property ID"),
        client_id: Optional[uuid.UUID] = Query(None, description="Filter by client ID"),
        document_type: Optional[str] = Query(None, description="Filter by document type"),
        status: Optional[str] = Query(None, description="Filter by status (UPLOADED, UNDER_REVIEW, etc.)"),
        is_archived: Optional[bool] = Query(False, description="Filter by archival status"),
        search: Optional[str] = Query(None, description="Search filename or notes"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        offset: int = Query(0, ge=0, description="Offset index"),
        sort_by: str = Query("created_at", description="Sort field: created_at, file_size, document_type"),
        sort_order: str = Query("desc", description="Sort direction: asc or desc"),
    ):
        self.property_id = property_id
        self.client_id = client_id
        self.document_type = document_type
        self.status = status
        self.is_archived = is_archived
        self.search = search
        self.limit = limit
        self.offset = offset
        self.sort_by = sort_by
        self.sort_order = sort_order
