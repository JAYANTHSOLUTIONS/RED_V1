"""Property Management Pydantic schemas.

Separates public client representations from internal/private consultant models
so that sensitive owner information, private addresses, and internal notes are
never serialized to public consumers.
"""
from datetime import datetime
from decimal import Decimal
from typing import Generic, List, Optional, TypeVar
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")

VALID_TRANSACTION_TYPES = {"SALE", "RENT", "LEASE"}


# ---------------------------------------------------------------------------
# Image Schemas
# ---------------------------------------------------------------------------

class PropertyImageCreate(BaseModel):
    storage_key: str = Field(..., max_length=500, description="S3 storage key or URL identifier")
    original_filename: str = Field(..., max_length=255, description="Original filename of the upload")
    mime_type: str = Field(..., max_length=100, description="MIME content type")
    file_size: int = Field(..., gt=0, description="Size of file in bytes")
    checksum: Optional[str] = Field(None, max_length=64, description="SHA-256 hash")
    display_order: int = Field(0, ge=0, description="Sort order in image gallery")
    is_primary: bool = Field(False, description="Primary thumbnail indicator")


class PropertyImageUpdate(BaseModel):
    display_order: Optional[int] = Field(None, ge=0)
    is_primary: Optional[bool] = None


class PublicPropertyImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    storage_key: str
    original_filename: str
    mime_type: str
    file_size: int
    display_order: int
    is_primary: bool


class PrivatePropertyImageResponse(PublicPropertyImageResponse):
    property_id: uuid.UUID
    checksum: Optional[str] = None
    is_archived: bool
    uploaded_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Property Mutation Schemas (Private Consultant Only)
# ---------------------------------------------------------------------------

class PropertyCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, description="Listing title")
    description: Optional[str] = None
    property_type: str = Field(..., min_length=2, max_length=50, description="e.g. Apartment, Villa, Plot")
    transaction_type: str = Field(..., min_length=2, max_length=20, description="SALE, RENT, or LEASE")
    price: Decimal = Field(..., ge=0, description="Listing price (non-negative)")
    price_negotiable: bool = Field(False, description="Negotiability indicator")

    # Dimensions & Specifications
    built_up_area: Optional[Decimal] = Field(None, ge=0)
    plot_area: Optional[Decimal] = Field(None, ge=0)
    area_unit: str = Field("sq.ft", max_length=20)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[int] = Field(None, ge=0)
    total_floors: Optional[int] = Field(None, ge=0)
    facing: Optional[str] = Field(None, max_length=20)
    furnishing_state: Optional[str] = Field(None, max_length=30)
    parking_spaces: Optional[int] = Field(None, ge=0)
    property_age: Optional[int] = Field(None, ge=0)

    # Location Information
    district: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    taluk: Optional[str] = Field(None, max_length=100)
    locality: str = Field(..., min_length=2, max_length=150)
    pincode: str = Field(..., min_length=3, max_length=20)
    address: Optional[str] = None
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    google_maps_url: Optional[str] = Field(None, max_length=500)

    # Private / Owner Information
    owner_name: Optional[str] = Field(None, max_length=255)
    owner_phone: Optional[str] = Field(None, max_length=50)
    owner_email: Optional[str] = Field(None, max_length=255)
    inventory_source: Optional[str] = Field(None, max_length=100)
    advertisement_authorized: bool = Field(False)
    internal_notes: Optional[str] = None

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in VALID_TRANSACTION_TYPES:
            raise ValueError(f"Invalid transaction type '{v}'. Allowed: {sorted(VALID_TRANSACTION_TYPES)}")
        return norm


class PropertyUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    property_type: Optional[str] = Field(None, min_length=2, max_length=50)
    transaction_type: Optional[str] = Field(None, min_length=2, max_length=20)
    price: Optional[Decimal] = Field(None, ge=0)
    price_negotiable: Optional[bool] = None

    built_up_area: Optional[Decimal] = Field(None, ge=0)
    plot_area: Optional[Decimal] = Field(None, ge=0)
    area_unit: Optional[str] = Field(None, max_length=20)
    bedrooms: Optional[int] = Field(None, ge=0)
    bathrooms: Optional[int] = Field(None, ge=0)
    floor: Optional[int] = Field(None, ge=0)
    total_floors: Optional[int] = Field(None, ge=0)
    facing: Optional[str] = Field(None, max_length=20)
    furnishing_state: Optional[str] = Field(None, max_length=30)
    parking_spaces: Optional[int] = Field(None, ge=0)
    property_age: Optional[int] = Field(None, ge=0)

    district: Optional[str] = Field(None, min_length=2, max_length=100)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    taluk: Optional[str] = Field(None, max_length=100)
    locality: Optional[str] = Field(None, min_length=2, max_length=150)
    pincode: Optional[str] = Field(None, min_length=3, max_length=20)
    address: Optional[str] = None
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    google_maps_url: Optional[str] = Field(None, max_length=500)

    owner_name: Optional[str] = Field(None, max_length=255)
    owner_phone: Optional[str] = Field(None, max_length=50)
    owner_email: Optional[str] = Field(None, max_length=255)
    inventory_source: Optional[str] = Field(None, max_length=100)
    advertisement_authorized: Optional[bool] = None
    internal_notes: Optional[str] = None

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        norm = v.strip().upper()
        if norm not in VALID_TRANSACTION_TYPES:
            raise ValueError(f"Invalid transaction type '{v}'. Allowed: {sorted(VALID_TRANSACTION_TYPES)}")
        return norm


# ---------------------------------------------------------------------------
# Property Representation Schemas
# ---------------------------------------------------------------------------

class PublicPropertyResponse(BaseModel):
    """Safe public representation — zero owner information, zero internal notes."""
    model_config = ConfigDict(from_attributes=True)

    public_reference: str
    title: str
    description: Optional[str] = None
    property_type: str
    transaction_type: str
    status: str
    price: Decimal
    price_negotiable: bool

    built_up_area: Optional[Decimal] = None
    plot_area: Optional[Decimal] = None
    area_unit: str = "sq.ft"
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    facing: Optional[str] = None
    furnishing_state: Optional[str] = None
    parking_spaces: Optional[int] = None
    property_age: Optional[int] = None

    district: str
    city: str
    taluk: Optional[str] = None
    locality: str
    pincode: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    google_maps_url: Optional[str] = None

    images: List[PublicPropertyImageResponse] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("area_unit", mode="before")
    @classmethod
    def default_area_unit(cls, v: Optional[str]) -> str:
        return v or "sq.ft"


class PrivatePropertyResponse(BaseModel):
    """Full private representation for authenticated consultant workspace."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    public_reference: str
    title: str
    description: Optional[str] = None
    property_type: str
    transaction_type: str
    status: str
    price: Decimal
    price_negotiable: bool

    built_up_area: Optional[Decimal] = None
    plot_area: Optional[Decimal] = None
    area_unit: str = "sq.ft"
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    facing: Optional[str] = None
    furnishing_state: Optional[str] = None
    parking_spaces: Optional[int] = None
    property_age: Optional[int] = None

    district: str
    city: str
    taluk: Optional[str] = None
    locality: str
    pincode: str
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    google_maps_url: Optional[str] = None

    # Sensitive owner and operational attributes
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[str] = None
    inventory_source: Optional[str] = None
    advertisement_authorized: bool
    internal_notes: Optional[str] = None
    last_verified_date: Optional[datetime] = None

    is_archived: bool
    archived_at: Optional[datetime] = None

    images: List[PrivatePropertyImageResponse] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("area_unit", mode="before")
    @classmethod
    def default_area_unit(cls, v: Optional[str]) -> str:
        return v or "sq.ft"


# ---------------------------------------------------------------------------
# Filter and Pagination Schemas
# ---------------------------------------------------------------------------

class PropertyFilterParams(BaseModel):
    property_type: Optional[str] = None
    transaction_type: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    locality: Optional[str] = None
    min_price: Optional[Decimal] = Field(None, ge=0)
    max_price: Optional[Decimal] = Field(None, ge=0)
    min_area: Optional[Decimal] = Field(None, ge=0)
    max_area: Optional[Decimal] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0)
    search: Optional[str] = Field(None, max_length=100)

    # Private-only filters
    status: Optional[str] = None
    is_archived: Optional[bool] = None

    # Pagination & Sorting
    sort_by: str = Field("created_at", pattern="^(created_at|price|built_up_area|title)$")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int
