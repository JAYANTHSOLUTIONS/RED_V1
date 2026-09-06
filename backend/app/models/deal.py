"""Deal and Fee models.

Tracks closed transactions and financial records. Enforces strict segregation
between official government charges (stamp duty, registration fees) and consultant
revenue (brokerage, consultancy service fees). All amounts are Decimal / NUMERIC.
"""
from datetime import date, datetime
from decimal import Decimal
import uuid
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    deal_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    agreed_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="INITIATED", index=True
    )
    execution_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(
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
    property: Mapped["Property"] = relationship("Property", back_populates="deals")
    client: Mapped["Client"] = relationship("Client", back_populates="deals")
    fees: Mapped[List["Fee"]] = relationship(
        "Fee", back_populates="deal", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("agreed_amount >= 0", name="ck_deals_agreed_amount_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<Deal id={self.id} property_id={self.property_id} amount={self.agreed_amount} status={self.status}>"


class Fee(Base):
    __tablename__ = "fees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deals.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    fee_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False
    )
    is_government_fee: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    payment_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    received_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
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
    deal: Mapped["Deal"] = relationship("Deal", back_populates="fees")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_fees_amount_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<Fee id={self.id} type={self.fee_type} amount={self.amount} gov={self.is_government_fee}>"
