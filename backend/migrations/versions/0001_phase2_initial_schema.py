"""Initial Phase 2 schema migration.

Revision ID: 0001_phase2_initial_schema
Revises: None
Create Date: 2026-09-05 13:05:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_phase2_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Concurrency-safe property reference sequence
    op.execute(sa.schema.CreateSequence(sa.Sequence("property_ref_seq", start=1, increment=1)))

    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="CONSULTANT"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_refresh_tokens_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"])
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=True)

    # 3. properties
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("public_reference", sa.String(32), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("property_type", sa.String(50), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("price_negotiable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("built_up_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("plot_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("area_unit", sa.String(20), nullable=False, server_default="sq.ft"),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("total_floors", sa.Integer(), nullable=True),
        sa.Column("facing", sa.String(20), nullable=True),
        sa.Column("furnishing_state", sa.String(30), nullable=True),
        sa.Column("parking_spaces", sa.Integer(), nullable=True),
        sa.Column("property_age", sa.Integer(), nullable=True),
        sa.Column("district", sa.String(100), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("taluk", sa.String(100), nullable=True),
        sa.Column("locality", sa.String(150), nullable=False),
        sa.Column("pincode", sa.String(20), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("google_maps_url", sa.String(500), nullable=True),
        sa.Column("owner_name", sa.String(255), nullable=True),
        sa.Column("owner_phone", sa.String(50), nullable=True),
        sa.Column("owner_email", sa.String(255), nullable=True),
        sa.Column("inventory_source", sa.String(100), nullable=True),
        sa.Column("advertisement_authorized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("last_verified_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_properties")),
        sa.UniqueConstraint("public_reference", name=op.f("uq_properties_public_reference")),
        sa.CheckConstraint("price >= 0", name=op.f("ck_properties_ck_properties_price_non_negative")),
        sa.CheckConstraint("built_up_area IS NULL OR built_up_area >= 0", name=op.f("ck_properties_ck_properties_built_up_area_non_negative")),
        sa.CheckConstraint("plot_area IS NULL OR plot_area >= 0", name=op.f("ck_properties_ck_properties_plot_area_non_negative")),
        sa.CheckConstraint("bedrooms IS NULL OR bedrooms >= 0", name=op.f("ck_properties_ck_properties_bedrooms_non_negative")),
        sa.CheckConstraint("bathrooms IS NULL OR bathrooms >= 0", name=op.f("ck_properties_ck_properties_bathrooms_non_negative")),
        sa.CheckConstraint("parking_spaces IS NULL OR parking_spaces >= 0", name=op.f("ck_properties_ck_properties_parking_spaces_non_negative")),
        sa.CheckConstraint("property_age IS NULL OR property_age >= 0", name=op.f("ck_properties_ck_properties_property_age_non_negative")),
    )
    op.create_index(op.f("ix_properties_public_reference"), "properties", ["public_reference"], unique=True)
    op.create_index(op.f("ix_properties_property_type"), "properties", ["property_type"])
    op.create_index(op.f("ix_properties_transaction_type"), "properties", ["transaction_type"])
    op.create_index(op.f("ix_properties_status"), "properties", ["status"])
    op.create_index(op.f("ix_properties_locality"), "properties", ["locality"])
    op.create_index(op.f("ix_properties_is_archived"), "properties", ["is_archived"])
    op.create_index(op.f("ix_properties_created_at"), "properties", ["created_at"])
    op.create_index("ix_properties_search_composite", "properties", ["district", "city", "locality", "status"])

    # 4. property_images
    op.create_table(
        "property_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name=op.f("fk_property_images_property_id_properties"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name=op.f("fk_property_images_uploaded_by_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_property_images")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_property_images_storage_key")),
        sa.CheckConstraint("file_size > 0", name=op.f("ck_property_images_ck_property_images_file_size_positive")),
    )
    op.create_index(op.f("ix_property_images_property_id"), "property_images", ["property_id"])

    # 5. clients
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("preferred_contact_method", sa.String(20), nullable=False, server_default="CALL"),
        sa.Column("postal_address", sa.Text(), nullable=True),
        sa.Column("classification", sa.String(30), nullable=False, server_default="BUYER"),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
    )
    op.create_index(op.f("ix_clients_phone"), "clients", ["phone"])
    op.create_index(op.f("ix_clients_email"), "clients", ["email"])
    op.create_index(op.f("ix_clients_is_archived"), "clients", ["is_archived"])

    # 6. property_requirements
    op.create_table(
        "property_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("property_types", sa.String(255), nullable=True),
        sa.Column("target_locations", sa.Text(), nullable=True),
        sa.Column("min_budget", sa.Numeric(14, 2), nullable=True),
        sa.Column("max_budget", sa.Numeric(14, 2), nullable=True),
        sa.Column("min_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_area", sa.Numeric(12, 2), nullable=True),
        sa.Column("area_unit", sa.String(20), nullable=False, server_default="sq.ft"),
        sa.Column("bedrooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("facing", sa.String(50), nullable=True),
        sa.Column("furnishing_state", sa.String(30), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_property_requirements_client_id_clients"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_property_requirements")),
        sa.CheckConstraint("min_budget IS NULL OR min_budget >= 0", name=op.f("ck_property_requirements_ck_property_requirements_min_budget_positive")),
        sa.CheckConstraint("max_budget IS NULL OR max_budget >= 0", name=op.f("ck_property_requirements_ck_property_requirements_max_budget_positive")),
        sa.CheckConstraint("min_budget IS NULL OR max_budget IS NULL OR max_budget >= min_budget", name=op.f("ck_property_requirements_ck_property_requirements_budget_bounds")),
        sa.CheckConstraint("min_area IS NULL OR min_area >= 0", name=op.f("ck_property_requirements_ck_property_requirements_min_area_positive")),
        sa.CheckConstraint("max_area IS NULL OR max_area >= 0", name=op.f("ck_property_requirements_ck_property_requirements_max_area_positive")),
        sa.CheckConstraint("min_area IS NULL OR max_area IS NULL OR max_area >= min_area", name=op.f("ck_property_requirements_ck_property_requirements_area_bounds")),
    )
    op.create_index(op.f("ix_property_requirements_client_id"), "property_requirements", ["client_id"])

    # 7. leads
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="NEW"),
        sa.Column("lost_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_leads_client_id_clients"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name=op.f("fk_leads_property_id_properties"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requirement_id"], ["property_requirements.id"], name=op.f("fk_leads_requirement_id_property_requirements"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leads")),
    )
    op.create_index(op.f("ix_leads_client_id"), "leads", ["client_id"])
    op.create_index(op.f("ix_leads_property_id"), "leads", ["property_id"])
    op.create_index(op.f("ix_leads_requirement_id"), "leads", ["requirement_id"])
    op.create_index(op.f("ix_leads_status"), "leads", ["status"])

    # 8. enquiries
    op.create_table(
        "enquiries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_ref", sa.String(32), nullable=True),
        sa.Column("visitor_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="WEBSITE"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], name=op.f("fk_enquiries_lead_id_leads"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name=op.f("fk_enquiries_property_id_properties"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enquiries")),
    )
    op.create_index(op.f("ix_enquiries_lead_id"), "enquiries", ["lead_id"])

    # 9. site_visits
    op.create_table(
        "site_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="REQUESTED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("rescheduled_from_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_site_visits_client_id_clients"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name=op.f("fk_site_visits_property_id_properties"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], name=op.f("fk_site_visits_lead_id_leads"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rescheduled_from_id"], ["site_visits.id"], name=op.f("fk_site_visits_rescheduled_from_id_site_visits"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_site_visits")),
    )
    op.create_index(op.f("ix_site_visits_client_id"), "site_visits", ["client_id"])
    op.create_index(op.f("ix_site_visits_property_id"), "site_visits", ["property_id"])
    op.create_index(op.f("ix_site_visits_lead_id"), "site_visits", ["lead_id"])
    op.create_index(op.f("ix_site_visits_scheduled_at"), "site_visits", ["scheduled_at"])
    op.create_index(op.f("ix_site_visits_status"), "site_visits", ["status"])
    op.create_index("ix_site_visits_property_schedule", "site_visits", ["property_id", "scheduled_at"])

    # 10. follow_ups
    op.create_table(
        "follow_ups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="SCHEDULED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_follow_ups_client_id_clients"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], name=op.f("fk_follow_ups_lead_id_leads"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name=op.f("fk_follow_ups_property_id_properties"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_follow_ups")),
        sa.CheckConstraint("client_id IS NOT NULL OR lead_id IS NOT NULL", name=op.f("ck_follow_ups_ck_follow_ups_target_present")),
    )
    op.create_index(op.f("ix_follow_ups_client_id"), "follow_ups", ["client_id"])
    op.create_index(op.f("ix_follow_ups_lead_id"), "follow_ups", ["lead_id"])
    op.create_index(op.f("ix_follow_ups_scheduled_at"), "follow_ups", ["scheduled_at"])
    op.create_index(op.f("ix_follow_ups_status"), "follow_ups", ["status"])

    # 11. documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="UPLOADED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_documents_client_id_clients"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name=op.f("fk_documents_property_id_properties"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name=op.f("fk_documents_uploaded_by_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_documents")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_documents_storage_key")),
        sa.CheckConstraint("file_size > 0", name=op.f("ck_documents_ck_documents_file_size_positive")),
    )
    op.create_index(op.f("ix_documents_client_id"), "documents", ["client_id"])
    op.create_index(op.f("ix_documents_property_id"), "documents", ["property_id"])
    op.create_index(op.f("ix_documents_document_type"), "documents", ["document_type"])
    op.create_index(op.f("ix_documents_checksum"), "documents", ["checksum"])
    op.create_index(op.f("ix_documents_status"), "documents", ["status"])
    op.create_index(op.f("ix_documents_is_archived"), "documents", ["is_archived"])

    # 12. verification_cases
    op.create_table(
        "verification_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="INCOMPLETE"),
        sa.Column("consultant_observations", sa.Text(), nullable=True),
        sa.Column("missing_documents_notes", sa.Text(), nullable=True),
        sa.Column("disclaimer_acknowledged", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name=op.f("fk_verification_cases_property_id_properties"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], name=op.f("fk_verification_cases_reviewed_by_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_cases")),
    )
    op.create_index(op.f("ix_verification_cases_property_id"), "verification_cases", ["property_id"])
    op.create_index(op.f("ix_verification_cases_status"), "verification_cases", ["status"])

    # 13. verification_items
    op.create_table(
        "verification_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("checklist_code", sa.String(50), nullable=False),
        sa.Column("item_name", sa.String(255), nullable=False),
        sa.Column("is_present", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["case_id"], ["verification_cases.id"], name=op.f("fk_verification_items_case_id_verification_cases"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name=op.f("fk_verification_items_document_id_documents"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verification_items")),
    )
    op.create_index(op.f("ix_verification_items_case_id"), "verification_items", ["case_id"])
    op.create_index(op.f("ix_verification_items_document_id"), "verification_items", ["document_id"])

    # 14. deals
    op.create_table(
        "deals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deal_type", sa.String(20), nullable=False),
        sa.Column("agreed_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="INITIATED"),
        sa.Column("execution_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], name=op.f("fk_deals_property_id_properties"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], name=op.f("fk_deals_client_id_clients"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deals")),
        sa.CheckConstraint("agreed_amount >= 0", name=op.f("ck_deals_ck_deals_agreed_amount_non_negative")),
    )
    op.create_index(op.f("ix_deals_property_id"), "deals", ["property_id"])
    op.create_index(op.f("ix_deals_client_id"), "deals", ["client_id"])
    op.create_index(op.f("ix_deals_status"), "deals", ["status"])

    # 15. fees
    op.create_table(
        "fees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fee_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("is_government_fee", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payment_status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], name=op.f("fk_fees_deal_id_deals"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fees")),
        sa.CheckConstraint("amount >= 0", name=op.f("ck_fees_ck_fees_amount_non_negative")),
    )
    op.create_index(op.f("ix_fees_deal_id"), "fees", ["deal_id"])

    # 16. notifications
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False, server_default="DASHBOARD"),
        sa.Column("notification_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_notifications_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"])
    op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"])

    # 17. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("change_diff", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], name=op.f("fk_audit_logs_actor_id_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(op.f("ix_audit_logs_actor_id"), "audit_logs", ["actor_id"])
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index(op.f("ix_audit_logs_entity_type"), "audit_logs", ["entity_type"])
    op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"])
    op.create_index(op.f("ix_audit_logs_correlation_id"), "audit_logs", ["correlation_id"])
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"])

    # 18. system_settings
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name=op.f("fk_system_settings_updated_by_users"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_system_settings")),
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("system_settings")
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("fees")
    op.drop_table("deals")
    op.drop_table("verification_items")
    op.drop_table("verification_cases")
    op.drop_table("documents")
    op.drop_table("follow_ups")
    op.drop_table("site_visits")
    op.drop_table("enquiries")
    op.drop_table("leads")
    op.drop_table("property_requirements")
    op.drop_table("clients")
    op.drop_table("property_images")
    op.drop_table("properties")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    # Drop sequence
    op.execute(sa.schema.DropSequence(sa.Sequence("property_ref_seq")))
