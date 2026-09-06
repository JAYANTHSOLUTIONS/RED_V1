"""Property and PropertyImage models.

Encapsulates inventory data, listing state machine, visual media metadata,
location, and strictly isolated private owner/evaluation details.
"""
from datetime import datetime
from decimal import Decimal
import uuid
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    public_reference: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    property_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DRAFT", index=True
    )

    # Financials (strictly NUMERIC/Decimal)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    price_negotiable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    # Dimensions & Specifications
    built_up_area: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    plot_area: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    area_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sq.ft"
    )
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    facing: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    furnishing_state: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    parking_spaces: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    property_age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Location Information
    district: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    taluk: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    locality: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    pincode: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    longitude: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    google_maps_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    # Strictly Private / Consultant Only
    owner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    owner_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    owner_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    inventory_source: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    advertisement_authorized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_verified_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Archival / Soft Delete
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    images: Mapped[List["PropertyImage"]] = relationship(
        "PropertyImage", back_populates="property", cascade="all, delete-orphan"
    )
    leads: Mapped[List["Lead"]] = relationship(
        "Lead", back_populates="property"
    )
    site_visits: Mapped[List["SiteVisit"]] = relationship(
        "SiteVisit", back_populates="property"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="property"
    )
    deals: Mapped[List["Deal"]] = relationship(
        "Deal", back_populates="property"
    )
    verification_cases: Mapped[List["VerificationCase"]] = relationship(
        "VerificationCase", back_populates="property"
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_properties_price_non_negative"),
        CheckConstraint(
            "built_up_area IS NULL OR built_up_area >= 0",
            name="ck_properties_built_up_area_non_negative",
        ),
        CheckConstraint(
            "plot_area IS NULL OR plot_area >= 0",
            name="ck_properties_plot_area_non_negative",
        ),
        CheckConstraint(
            "bedrooms IS NULL OR bedrooms >= 0",
            name="ck_properties_bedrooms_non_negative",
        ),
        CheckConstraint(
            "bathrooms IS NULL OR bathrooms >= 0",
            name="ck_properties_bathrooms_non_negative",
        ),
        CheckConstraint(
            "parking_spaces IS NULL OR parking_spaces >= 0",
            name="ck_properties_parking_spaces_non_negative",
        ),
        CheckConstraint(
            "property_age IS NULL OR property_age >= 0",
            name="ck_properties_property_age_non_negative",
        ),
        Index("ix_properties_search_composite", "district", "city", "locality", "status"),
    )

    def __repr__(self) -> str:
        return f"<Property id={self.id} ref={self.public_reference} status={self.status}>"


class PropertyImage(Base):
    __tablename__ = "property_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    property: Mapped["Property"] = relationship("Property", back_populates="images")
    uploader: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        CheckConstraint("file_size > 0", name="ck_property_images_file_size_positive"),
    )

    def __repr__(self) -> str:
        return f"<PropertyImage id={self.id} property_id={self.property_id} primary={self.is_primary}>"
