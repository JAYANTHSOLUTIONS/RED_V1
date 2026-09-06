"""Schema integrity and metadata introspection tests.

Validates table registrations, foreign key delete rules (RESTRICT for business history,
CASCADE for tightly owned children), check constraints, and index definitions
against the Master Backend Specification.
"""
import pytest
from app.db.base import Base
import app.models  # ensure all models are loaded


def test_all_expected_tables_registered():
    """Verify all 18 core domain tables are registered in Base.metadata."""
    expected_tables = {
        "users",
        "refresh_tokens",
        "properties",
        "property_images",
        "clients",
        "property_requirements",
        "leads",
        "enquiries",
        "site_visits",
        "follow_ups",
        "documents",
        "verification_cases",
        "verification_items",
        "deals",
        "fees",
        "notifications",
        "audit_logs",
        "system_settings",
    }
    actual_tables = set(Base.metadata.tables.keys())
    missing = expected_tables - actual_tables
    assert not missing, f"Missing tables in Base.metadata: {missing}"


def test_foreign_key_delete_behaviors_protect_history():
    """Verify delete rules intentionally protect historical records and cascade children."""
    tables = Base.metadata.tables

    # Deals must NOT be cascade-deleted; RESTRICT protects business transaction history
    deal_fks = {fk.column.table.name: fk.ondelete for fk in tables["deals"].foreign_keys}
    assert deal_fks["properties"] == "RESTRICT"
    assert deal_fks["clients"] == "RESTRICT"

    # Fees must NOT be accidentally deleted; RESTRICT protects revenue records
    fee_fks = {fk.column.table.name: fk.ondelete for fk in tables["fees"].foreign_keys}
    assert fee_fks["deals"] == "RESTRICT"

    # Leads must NOT cascade delete clients
    lead_fks = {fk.column.table.name: fk.ondelete for fk in tables["leads"].foreign_keys}
    assert lead_fks["clients"] == "RESTRICT"

    # Site visits protect property and client history
    visit_fks = {fk.column.table.name: fk.ondelete for fk in tables["site_visits"].foreign_keys}
    assert visit_fks["properties"] == "RESTRICT"
    assert visit_fks["clients"] == "RESTRICT"

    # Verification cases protect property auditability
    verif_fks = {fk.column.table.name: fk.ondelete for fk in tables["verification_cases"].foreign_keys}
    assert verif_fks["properties"] == "RESTRICT"

    # Children that SHOULD cascade:
    img_fks = {fk.column.table.name: fk.ondelete for fk in tables["property_images"].foreign_keys}
    assert img_fks["properties"] == "CASCADE"

    req_fks = {fk.column.table.name: fk.ondelete for fk in tables["property_requirements"].foreign_keys}
    assert req_fks["clients"] == "CASCADE"

    item_fks = {fk.column.table.name: fk.ondelete for fk in tables["verification_items"].foreign_keys}
    assert item_fks["verification_cases"] == "CASCADE"


def test_check_constraints_defined():
    """Verify database-level check constraints are configured for financial and business sanity."""
    tables = Base.metadata.tables

    # Properties
    prop_cks = [ck.name for ck in tables["properties"].constraints if hasattr(ck, "sqltext")]
    assert any("price_non_negative" in (c or "") for c in prop_cks)

    # Deals
    deal_cks = [ck.name for ck in tables["deals"].constraints if hasattr(ck, "sqltext")]
    assert any("agreed_amount_non_negative" in (c or "") for c in deal_cks)

    # Fees
    fee_cks = [ck.name for ck in tables["fees"].constraints if hasattr(ck, "sqltext")]
    assert any("amount_non_negative" in (c or "") for c in fee_cks)

    # Property Images
    img_cks = [ck.name for ck in tables["property_images"].constraints if hasattr(ck, "sqltext")]
    assert any("file_size_positive" in (c or "") for c in img_cks)

    # Documents
    doc_cks = [ck.name for ck in tables["documents"].constraints if hasattr(ck, "sqltext")]
    assert any("file_size_positive" in (c or "") for c in doc_cks)

    # Follow-ups
    fu_cks = [ck.name for ck in tables["follow_ups"].constraints if hasattr(ck, "sqltext")]
    assert any("target_present" in (c or "") for c in fu_cks)


def test_critical_indexes_configured():
    """Verify indexes on high-frequency search and filter columns."""
    tables = Base.metadata.tables

    # Properties
    prop_indexes = {ix.name for ix in tables["properties"].indexes}
    assert "ix_properties_public_reference" in prop_indexes
    assert "ix_properties_status" in prop_indexes
    assert "ix_properties_property_type" in prop_indexes

    # Clients
    client_indexes = {ix.name for ix in tables["clients"].indexes}
    assert "ix_clients_phone" in client_indexes

    # Leads
    lead_indexes = {ix.name for ix in tables["leads"].indexes}
    assert "ix_leads_status" in lead_indexes

    # Site visits
    visit_indexes = {ix.name for ix in tables["site_visits"].indexes}
    assert "ix_site_visits_scheduled_at" in visit_indexes
