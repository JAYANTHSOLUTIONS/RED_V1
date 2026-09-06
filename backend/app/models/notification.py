"""Notification model.

Persistent alert and messaging journal for dashboard, email, and WhatsApp hooks.
Decoupled from actual delivery providers.
"""
from datetime import datetime
import uuid
from typing import Optional

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


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DASHBOARD"
    )
    notification_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, index=True
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="notifications"
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.notification_type} channel={self.channel} read={self.is_read}>"
