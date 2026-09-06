"""Preliminary Document Review models.

Foundation for preliminary document check workflows and checklist items.
Explicitly non-legal title clearance, adhering strictly to compliance guardrails.
"""
from datetime import datetime
import uuid
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VerificationCase(Base):
    __tablename__ = "verification_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="INCOMPLETE", index=True
    )
    consultant_observations: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    missing_documents_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    disclaimer_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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
    property: Mapped["Property"] = relationship(
        "Property", back_populates="verification_cases"
    )
    reviewer: Mapped[Optional["User"]] = relationship("User")
    items: Mapped[List["VerificationItem"]] = relationship(
        "VerificationItem", back_populates="case", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<VerificationCase id={self.id} property_id={self.property_id} status={self.status}>"


class VerificationItem(Base):
    __tablename__ = "verification_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("verification_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    checklist_code: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_present: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )
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
    case: Mapped["VerificationCase"] = relationship(
        "VerificationCase", back_populates="items"
    )
    document: Mapped[Optional["Document"]] = relationship(
        "Document", back_populates="verification_items"
    )

    def __repr__(self) -> str:
        return f"<VerificationItem id={self.id} code={self.checklist_code} status={self.status}>"
