"""FollowUp model.

Task and reminder tracking system for maintaining operational momentum
across leads, clients, and active property evaluations.
"""
from datetime import datetime
import uuid
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="SCHEDULED", index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    client: Mapped[Optional["Client"]] = relationship(
        "Client", back_populates="follow_ups"
    )
    lead: Mapped[Optional["Lead"]] = relationship(
        "Lead", back_populates="follow_ups"
    )
    property: Mapped[Optional["Property"]] = relationship("Property")

    __table_args__ = (
        CheckConstraint(
            "client_id IS NOT NULL OR lead_id IS NOT NULL",
            name="ck_follow_ups_target_present",
        ),
    )

    def __repr__(self) -> str:
        return f"<FollowUp id={self.id} action={self.action_type} scheduled_at={self.scheduled_at} status={self.status}>"
