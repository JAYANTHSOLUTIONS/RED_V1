"""Document metadata model.

Sequestered private documents metadata (Sale Deeds, Encumbrance Certificates,
Patta/Chitta, Tax Receipts, Identity Proofs). Binary files reside exclusively in
private S3-compatible storage. Physical deletes are prohibited (soft-archive only).
"""
from datetime import datetime
import uuid
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
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


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    property_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(
        String(500), unique=True, nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UPLOADED", index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    client: Mapped[Optional["Client"]] = relationship(
        "Client", back_populates="documents"
    )
    property: Mapped[Optional["Property"]] = relationship(
        "Property", back_populates="documents"
    )
    uploader: Mapped[Optional["User"]] = relationship("User")
    verification_items: Mapped[List["VerificationItem"]] = relationship(
        "VerificationItem", back_populates="document"
    )

    __table_args__ = (
        CheckConstraint("file_size > 0", name="ck_documents_file_size_positive"),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} type={self.document_type} status={self.status}>"
