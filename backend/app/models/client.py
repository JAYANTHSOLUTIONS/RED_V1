"""Client model.

Represents customer profiles with strictly guarded contact details, classification,
and relationships to leads, requirements, visits, documents, and deals.
"""
from datetime import datetime
import uuid
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    preferred_contact_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CALL"
    )
    postal_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    classification: Mapped[str] = mapped_column(
        String(30), nullable=False, default="BUYER"
    )
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
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
    requirements: Mapped[List["PropertyRequirement"]] = relationship(
        "PropertyRequirement", back_populates="client", cascade="all, delete-orphan"
    )
    leads: Mapped[List["Lead"]] = relationship(
        "Lead", back_populates="client"
    )
    site_visits: Mapped[List["SiteVisit"]] = relationship(
        "SiteVisit", back_populates="client"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="client"
    )
    deals: Mapped[List["Deal"]] = relationship(
        "Deal", back_populates="client"
    )
    follow_ups: Mapped[List["FollowUp"]] = relationship(
        "FollowUp", back_populates="client", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.full_name} phone={self.phone}>"
