"""SiteVisit model.

Tracks property visits with explicit consultant confirmation flow, rescheduling history,
and concurrency conflict guards to prevent overlapping bookings.
"""
from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SiteVisit(Base):
    __tablename__ = "site_visits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="REQUESTED", index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    rescheduled_from_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("site_visits.id", ondelete="SET NULL"),
        nullable=True,
    )
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    client: Mapped["Client"] = relationship("Client", back_populates="site_visits")
    property: Mapped["Property"] = relationship("Property", back_populates="site_visits")
    lead: Mapped[Optional["Lead"]] = relationship("Lead", back_populates="site_visits")
    rescheduled_from: Mapped[Optional["SiteVisit"]] = relationship(
        "SiteVisit", remote_side=[id]
    )

    __table_args__ = (
        Index("ix_site_visits_property_schedule", "property_id", "scheduled_at"),
    )

    def __repr__(self) -> str:
        return f"<SiteVisit id={self.id} property_id={self.property_id} scheduled_at={self.scheduled_at} status={self.status}>"
