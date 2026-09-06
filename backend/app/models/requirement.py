"""PropertyRequirement model.

Encapsulates customer search criteria and budget boundaries used for
rule-based algorithmic matching.
"""
from datetime import datetime
from decimal import Decimal
import uuid
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PropertyRequirement(Base):
    __tablename__ = "property_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    property_types: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    target_locations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Budget Bounds (strictly NUMERIC/Decimal)
    min_budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    max_budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )

    # Area Bounds
    min_area: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    max_area: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    area_unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sq.ft"
    )

    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    facing: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    furnishing_state: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE"
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
    client: Mapped["Client"] = relationship("Client", back_populates="requirements")
    leads: Mapped[List["Lead"]] = relationship(
        "Lead", back_populates="requirement"
    )

    __table_args__ = (
        CheckConstraint(
            "min_budget IS NULL OR min_budget >= 0",
            name="ck_property_requirements_min_budget_positive",
        ),
        CheckConstraint(
            "max_budget IS NULL OR max_budget >= 0",
            name="ck_property_requirements_max_budget_positive",
        ),
        CheckConstraint(
            "min_budget IS NULL OR max_budget IS NULL OR max_budget >= min_budget",
            name="ck_property_requirements_budget_bounds",
        ),
        CheckConstraint(
            "min_area IS NULL OR min_area >= 0",
            name="ck_property_requirements_min_area_positive",
        ),
        CheckConstraint(
            "max_area IS NULL OR max_area >= 0",
            name="ck_property_requirements_max_area_positive",
        ),
        CheckConstraint(
            "min_area IS NULL OR max_area IS NULL OR max_area >= min_area",
            name="ck_property_requirements_area_bounds",
        ),
    )

    def __repr__(self) -> str:
        return f"<PropertyRequirement id={self.id} client_id={self.client_id} status={self.status}>"
