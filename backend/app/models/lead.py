"""Lead and Enquiry models.

Tracks customer inquiry funnel from public submission or direct capture
through to qualification, site visits, negotiation, and conversion.
"""
from datetime import datetime
import uuid
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    requirement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("property_requirements.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="NEW", index=True
    )
    lost_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    client: Mapped["Client"] = relationship("Client", back_populates="leads")
    property: Mapped[Optional["Property"]] = relationship(
        "Property", back_populates="leads"
    )
    requirement: Mapped[Optional["PropertyRequirement"]] = relationship(
        "PropertyRequirement", back_populates="leads"
    )
    enquiries: Mapped[List["Enquiry"]] = relationship(
        "Enquiry", back_populates="lead"
    )
    site_visits: Mapped[List["SiteVisit"]] = relationship(
        "SiteVisit", back_populates="lead"
    )
    follow_ups: Mapped[List["FollowUp"]] = relationship(
        "FollowUp", back_populates="lead", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} client_id={self.client_id} status={self.status}>"


class Enquiry(Base):
    __tablename__ = "enquiries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
    )
    property_ref: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    visitor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="WEBSITE"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    lead: Mapped[Optional["Lead"]] = relationship("Lead", back_populates="enquiries")
    property: Mapped[Optional["Property"]] = relationship("Property")

    def __repr__(self) -> str:
        return f"<Enquiry id={self.id} visitor={self.visitor_name} phone={self.phone}>"
