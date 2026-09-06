"""Unit tests for Deterministic Tamil Nadu Preliminary Property Verification Engine."""
from datetime import date
from decimal import Decimal
import uuid
import pytest

from app.models.document import Document
from app.models.property import Property
from app.schemas.verification import (
    CheckStatus,
    PlanningAuthorityType,
    PropertyVerificationInput,
    ReraApplicability,
    RiskLevel,
    TAMIL_NADU_VERIFICATION_DISCLAIMER,
)
from app.services.tn_verification_engine import (
    DeterministicTNVerificationEngine,
)


@pytest.fixture
def engine():
    return DeterministicTNVerificationEngine()


def test_survey_number_normalization():
    """Verify Tamil Nadu survey number normalization strips prefixes and standardizes format."""
    assert DeterministicTNVerificationEngine.normalize_survey_number("S.No. 124 / 3 A") == "124/3A"
    assert DeterministicTNVerificationEngine.normalize_survey_number("S.F.No: 45 / 1") == "45/1"
    assert DeterministicTNVerificationEngine.normalize_survey_number("R.S.No. 88-2") == "88-2"
    assert DeterministicTNVerificationEngine.normalize_survey_number("T.S.No. 12/3A1") == "12/3A1"
    assert DeterministicTNVerificationEngine.normalize_survey_number("Survey No: 99") == "99"
    assert DeterministicTNVerificationEngine.normalize_survey_number("") is None
    assert DeterministicTNVerificationEngine.normalize_survey_number("  ") is None


def test_survey_number_subdivision_comparison():
    """Verify sub-division comparison: identical vs different sub-division vs parent parcel."""
    # 1. Exact match
    res, msg = DeterministicTNVerificationEngine.compare_survey_identifiers("124/3A", "S.No. 124/3A")
    assert res == "MATCH"

    # 2. Different sub-division in Tamil Nadu land records -> MISMATCH
    res, msg = DeterministicTNVerificationEngine.compare_survey_identifiers("124/3A", "124/3B")
    assert res == "MISMATCH"
    assert "subdivision mismatch" in msg

    # 3. Parent parcel vs subdivided parcel -> REVIEW
    res, msg = DeterministicTNVerificationEngine.compare_survey_identifiers("124/3", "124/3A")
    assert res == "REVIEW"
    assert "parent-to-subdivision" in msg

    # 4. Completely distinct base survey numbers -> MISMATCH
    res, msg = DeterministicTNVerificationEngine.compare_survey_identifiers("124", "125")
    assert res == "MISMATCH"


def test_extent_unit_conversions_and_comparison():
    """Verify Tamil Nadu extent unit conversions (sq.ft, cents, grounds, acres) and tolerances."""
    # 1 ground = 2400 sq.ft
    res, pct, msg = DeterministicTNVerificationEngine.compare_extents(
        Decimal("1.0"), "ground", Decimal("2400.0"), "sq.ft"
    )
    assert res == "MATCH"
    assert pct == Decimal("0.0")

    # 1 cent = 435.6 sq.ft -> 5.51 cents approx 2400.156 sq.ft
    res, pct, msg = DeterministicTNVerificationEngine.compare_extents(
        Decimal("5.51"), "cent", Decimal("2400.0"), "sq.ft"
    )
    assert res == "MATCH"
    assert pct < Decimal("2.0")

    # 10% tolerance boundary check
    res, pct, msg = DeterministicTNVerificationEngine.compare_extents(
        Decimal("2400"), "sq.ft", Decimal("2550"), "sq.ft"
    )
    assert res == "REVIEW"
    assert Decimal("2.0") < pct <= Decimal("10.0")

    # Significant mismatch > 10%
    res, pct, msg = DeterministicTNVerificationEngine.compare_extents(
        Decimal("2400"), "sq.ft", Decimal("3200"), "sq.ft"
    )
    assert res == "SIGNIFICANT_MISMATCH"
    assert pct > Decimal("10.0")


def test_owner_name_consistency_and_initials():
    """Verify owner name comparison recognizes initials, token order, and flags distinct initials."""
    # Exact match
    res, msg = DeterministicTNVerificationEngine.compare_owner_names("R. Kumar", "R. Kumar")
    assert res == "MATCH"

    # Spacing and punctuation variation
    res, msg = DeterministicTNVerificationEngine.compare_owner_names("R. Kumar", "R Kumar")
    assert res == "MATCH"

    # Token order variation (Tamil Nadu surname/given name order)
    res, msg = DeterministicTNVerificationEngine.compare_owner_names("Kumar R", "R. Kumar")
    assert res == "MATCH"

    # Distinct initial -> Legal entity MISMATCH
    res, msg = DeterministicTNVerificationEngine.compare_owner_names("R. Kumar", "S. Kumar")
    assert res == "MISMATCH"
    assert "Conflicting initial" in msg

    # Name expansion (full first name vs initial)
    res, msg = DeterministicTNVerificationEngine.compare_owner_names("Rajesh Kumar", "R. Kumar")
    assert res == "POSSIBLE_MATCH"


def test_planning_authority_determination():
    """Verify planning authority detection for CMDA vs DTCP based on Tamil Nadu jurisdictions."""
    # Chennai district -> CMDA
    assert DeterministicTNVerificationEngine.determine_planning_authority("Chennai", "Mylapore") == PlanningAuthorityType.CMDA

    # CMA expanded locality outside Chennai district
    assert DeterministicTNVerificationEngine.determine_planning_authority("Chengalpattu", "Tambaram") == PlanningAuthorityType.CMDA
    assert DeterministicTNVerificationEngine.determine_planning_authority("Tiruvallur", "Avadi") == PlanningAuthorityType.CMDA

    # Outside CMA -> DTCP
    assert DeterministicTNVerificationEngine.determine_planning_authority("Coimbatore", "RS Puram") == PlanningAuthorityType.DTCP
    assert DeterministicTNVerificationEngine.determine_planning_authority("Madurai", "KK Nagar") == PlanningAuthorityType.DTCP

    # Explicit override
    assert DeterministicTNVerificationEngine.determine_planning_authority("Chennai", "Egmore", "DTCP") == PlanningAuthorityType.DTCP


def test_tnrera_applicability_engine():
    """Verify RERA applicability logic: new promoter projects vs secondary market resales."""
    prop_resale = Property(
        id=uuid.uuid4(),
        public_reference="PR-2026-000001",
        title="15 Year Old Independent Resale House",
        property_type="INDEPENDENT_HOUSE",
        transaction_type="SALE",
        price=Decimal("8500000.00"),
        district="Chennai",
        city="Chennai",
        locality="Anna Nagar",
        pincode="600040",
        property_age=15,
    )
    assert DeterministicTNVerificationEngine.determine_rera_applicability(prop_resale) == ReraApplicability.RERA_NOT_APPLICABLE

    prop_promoter = Property(
        id=uuid.uuid4(),
        public_reference="PR-2026-000002",
        title="Premium Gated Community Layout by Prestige Promoters",
        property_type="PLOT",
        transaction_type="SALE",
        price=Decimal("4500000.00"),
        district="Chengalpattu",
        city="Chengalpattu",
        locality="Guduvanchery",
        pincode="603202",
        inventory_source="Builder Direct",
        property_age=0,
    )
    assert DeterministicTNVerificationEngine.determine_rera_applicability(prop_promoter) == ReraApplicability.RERA_APPLICABLE


def test_engine_evaluates_plot_with_full_evidence(engine):
    """Verify fully documented plot evaluates to COMPLETED status with high completeness score."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PR-2026-000010",
        title="CMDA Approved Plot in Tambaram",
        property_type="PLOT",
        transaction_type="SALE",
        price=Decimal("6000000.00"),
        plot_area=Decimal("2400.00"),
        area_unit="sq.ft",
        district="Chengalpattu",
        city="Tambaram",
        taluk="Tambaram",
        locality="Tambaram",
        pincode="600045",
        owner_name="R. Kumar",
    )

    doc_deed = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="SALE_DEED",
        original_filename="sale_deed_2020.pdf",
        storage_key="docs/deed.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="hash1",
        is_archived=False,
    )
    doc_ec = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="EC",
        original_filename="ec_30_years.pdf",
        storage_key="docs/ec.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="hash2",
        is_archived=False,
    )
    doc_patta = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="PATTA",
        original_filename="patta_copy.pdf",
        storage_key="docs/patta.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="hash3",
        is_archived=False,
    )
    doc_approval = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="LAYOUT_APPROVAL",
        original_filename="cmda_approval_letter.pdf",
        storage_key="docs/approval.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="hash4",
        is_archived=False,
    )
    doc_parent = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="PARENT_DOCUMENT",
        original_filename="parent_deed_1994.pdf",
        storage_key="docs/parent.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="hash5",
        is_archived=False,
    )

    docs = [doc_deed, doc_parent, doc_ec, doc_patta, doc_approval]
    inp = PropertyVerificationInput(
        survey_number="124/3A",
        subdivision_number="3A",
        patta_number="842",
        ec_start_date=date(1994, 1, 1),
        ec_end_date=date(2024, 1, 1),
        ec_has_encumbrance_entries=False,
        planning_approval_number="CMDA/L/042/2019",
        is_new_project_or_promoter_sale=False,
    )

    res = engine.evaluate(prop, docs, inp)
    assert res.status == "COMPLETED"
    assert res.risk_level == RiskLevel.LOW
    assert res.completeness_score >= 85
    assert res.planning_authority_type == PlanningAuthorityType.CMDA
    assert "NO_OBVIOUS_INCONSISTENCY" in res.risk_flags


def test_engine_flags_adverse_ec_entry_as_high_risk(engine):
    """Verify active registered charge/mortgage on EC immediately triggers HIGH risk."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PR-2026-000011",
        title="Independent Villa in Anna Nagar",
        property_type="INDEPENDENT_HOUSE",
        transaction_type="SALE",
        price=Decimal("25000000.00"),
        plot_area=Decimal("3000.00"),
        built_up_area=Decimal("2800.00"),
        area_unit="sq.ft",
        district="Chennai",
        city="Chennai",
        taluk="Aminjikarai",
        locality="Anna Nagar",
        pincode="600040",
        owner_name="S. Sundaram",
    )
    doc_ec = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="EC",
        original_filename="ec_with_charge.pdf",
        storage_key="docs/ec_charge.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="hash-charge",
        is_archived=False,
    )

    inp = PropertyVerificationInput(
        survey_number="88/1",
        ec_start_date=date(2000, 1, 1),
        ec_end_date=date(2024, 1, 1),
        ec_has_encumbrance_entries=True,  # Active mortgage observed
    )

    res = engine.evaluate(prop, [doc_ec], inp)
    assert res.risk_level == RiskLevel.HIGH
    assert "REGISTERED_ENTRY_REQUIRES_REVIEW" in res.risk_flags
    assert res.status == "NEEDS_REVIEW"


def test_engine_flags_chronological_date_anomaly(engine):
    """Verify impossible document sequence (parent deed date later than current deed date) is flagged."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PR-2026-000012",
        title="Apartment in Adyar",
        property_type="APARTMENT",
        transaction_type="SALE",
        price=Decimal("12000000.00"),
        built_up_area=Decimal("1450.00"),
        area_unit="sq.ft",
        district="Chennai",
        city="Chennai",
        taluk="Mylapore",
        locality="Adyar",
        pincode="600020",
        owner_name="M. Ramesh",
    )

    inp = PropertyVerificationInput(
        current_deed_date=date(2018, 5, 10),
        parent_document_date=date(2024, 1, 15),  # Anomaly: parent document dated AFTER current deed!
    )

    res = engine.evaluate(prop, [], inp)
    assert "DOCUMENT_SEQUENCE_REVIEW" in res.risk_flags
    seq_check = next(c for c in res.checks if c.checklist_code == "DOCUMENT_SEQUENCE_CHRONOLOGY")
    assert seq_check.status == CheckStatus.REVIEW
    assert seq_check.risk_level == RiskLevel.MEDIUM


def test_mandatory_disclaimer_constant():
    """Verify mandatory statutory disclaimer contains the required legal non-title-guarantee text."""
    assert "preliminary property verification assessment" in TAMIL_NADU_VERIFICATION_DISCLAIMER
    assert "does not constitute legal title verification" in TAMIL_NADU_VERIFICATION_DISCLAIMER
    assert "confirmation of document authenticity" in TAMIL_NADU_VERIFICATION_DISCLAIMER
    assert "free from encumbrances" in TAMIL_NADU_VERIFICATION_DISCLAIMER
