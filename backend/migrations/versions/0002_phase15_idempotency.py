"""Phase 15 Idempotency Records table migration.

Revision ID: 0002_phase15_idempotency
Revises: 0001_phase2_initial_schema
Create Date: 2026-09-07 13:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_phase15_idempotency"
down_revision: Union[str, None] = "0001_phase2_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PROCESSING"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_idempotency_records")),
        sa.UniqueConstraint("key", "user_id", "endpoint", name="uq_idempotency_key_user_endpoint"),
    )
    op.create_index(op.f("ix_idempotency_records_key"), "idempotency_records", ["key"], unique=False)
    op.create_index(op.f("ix_idempotency_records_user_id"), "idempotency_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_idempotency_records_endpoint"), "idempotency_records", ["endpoint"], unique=False)
    op.create_index(op.f("ix_idempotency_records_expires_at"), "idempotency_records", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_idempotency_records_expires_at"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_endpoint"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_user_id"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_key"), table_name="idempotency_records")
    op.drop_table("idempotency_records")
