"""Unit tests for Phase 9 Tamil Nadu Property Intelligence and Verification Enhancements."""
from datetime import date
from decimal import Decimal
import uuid
import pytest

from app.domain.tamil_nadu.actions import (
    ConsultantActionItem,
    ConsultantActionType,
    generate_consultant_actions,
)
from app.domain.tamil_nadu.chronology import (
    ChronologyAnalysis,
    ChronologyStatus,
    DocumentRelationship,
    analyze_document_chronology,
)
from app.domain.tamil_nadu.measurements import (
    compare_property_extents,
    convert_to_sqft,
)
from app.domain.tamil_nadu.names import (
    compare_tamil_nadu_names,
    is_tamil_unicode,
    normalize_name_tokens,
)
from app.domain.tamil_nadu.planning import (
    JurisdictionConfidence,
    PlanningAuthority,
    PlanningDetermination,
    determine_planning_jurisdiction,
)
from app.domain.tamil_nadu.survey import (
    SurveyComparisonGrade,
    compare_survey_parcels,
    normalize_survey_identifier,
)
from app.models.document import Document
from app.models.property import Property
from app.schemas.verification import (
    CheckCategory,
    CheckResult,
    CheckStatus,
    DetailedEvidenceItem,
    EvidenceIntelligenceReport,
    EvidenceItem,
    EvidenceStatus,
    PlanningAuthorityType,
    ProcessingConfidence,
    PropertyVerificationInput,
    ReraApplicability,
    ReraApplicabilityReason,
    RiskLevel,
)
from app.services.tn_verification_engine import (
    DeterministicTNVerificationEngine,
    EngineEvaluationResult,
)
from app.services.verification_providers import (
    DefaultTamilNaduVerificationProvider,
)


# ============================================================================
# 1. PLANNING JURISDICTION TESTS
# ============================================================================

def test_planning_jurisdiction_cmda_chennai():
    """Verify Chennai district resolves to CMDA with HIGH confidence."""
    det = determine_planning_jurisdiction(district="Chennai", locality="Alwarpet")
    assert det.authority == PlanningAuthority.CMDA
    assert det.confidence == JurisdictionConfidence.HIGH
    assert det.basis == "district_statutory_jurisdiction"
    assert det.requires_consultant_confirmation is False


def test_planning_jurisdiction_cmda_cma_locality():
    """Verify CMA expanded locality resolves to CMDA."""
    det = determine_planning_jurisdiction(district="Unknown", locality="Anna Nagar")
    assert det.authority == PlanningAuthority.CMDA
    assert det.confidence == JurisdictionConfidence.MEDIUM
    assert det.basis == "cma_expanded_locality_configuration"


def test_planning_jurisdiction_dtcp_coimbatore():
    """Verify Coimbatore district resolves to DTCP."""
    det = determine_planning_jurisdiction(district="Coimbatore", locality="RS Puram")
    assert det.authority == PlanningAuthority.DTCP
    assert det.confidence == JurisdictionConfidence.HIGH
    assert det.basis == "state_planning_jurisdiction"


def test_planning_jurisdiction_dtcp_other_districts():
    """Verify Madurai, Trichy, Salem, Tirunelveli resolve to DTCP."""
    for dist in ["Madurai", "Salem", "Tiruchirappalli", "Tirunelveli"]:
        det = determine_planning_jurisdiction(district=dist, locality="Main Road")
        assert det.authority == PlanningAuthority.DTCP
        assert det.confidence == JurisdictionConfidence.HIGH


def test_planning_jurisdiction_unknown_district_fallback():
    """Verify empty or unrecognized district defaults to UNKNOWN with LOW confidence."""
    det = determine_planning_jurisdiction(district=None, locality=None)
    assert det.authority == PlanningAuthority.UNKNOWN
    assert det.confidence == JurisdictionConfidence.LOW
    assert det.requires_consultant_confirmation is True


# ============================================================================
# 2. MEASUREMENT CONVERSION & COMPARISON TESTS
# ============================================================================

def test_measurement_conversion_cents():
    """Verify 1 cent = 435.6 sq.ft with Decimal precision."""
    sqft, unit = convert_to_sqft(Decimal("1.0"), "cent")
    assert sqft == Decimal("435.6")
    assert unit == "cent"

    sqft, _ = convert_to_sqft(Decimal("5.5"), "cents")
    assert sqft == Decimal("2395.8")


def test_measurement_conversion_grounds():
    """Verify 1 ground = 2400 sq.ft."""
    sqft, unit = convert_to_sqft(Decimal("1.0"), "ground")
    assert sqft == Decimal("2400.0")
    assert unit == "ground"

    sqft, _ = convert_to_sqft(Decimal("2.5"), "grounds")
    assert sqft == Decimal("6000.0")


def test_measurement_conversion_acres():
    """Verify 1 acre = 43560 sq.ft."""
    sqft, unit = convert_to_sqft(Decimal("1.0"), "acre")
    assert sqft == Decimal("43560.0")
    assert unit == "acre"


def test_measurement_conversion_hectares():
    """Verify 1 hectare = 107639.1 sq.ft."""
    sqft, unit = convert_to_sqft(Decimal("1.0"), "hectare")
    assert sqft == Decimal("107639.1")
    assert unit == "hectare"


def test_measurement_conversion_unknown_unit():
    """Verify uninterpretable unit returns UNKNOWN_UNIT and None."""
    sqft, unit = convert_to_sqft(Decimal("100"), "marla")
    assert sqft is None
    assert unit == "UNKNOWN_UNIT"

    sqft, unit = convert_to_sqft(Decimal("50"), "bigha")
    assert sqft is None
    assert unit == "UNKNOWN_UNIT"

    sqft, unit = convert_to_sqft(Decimal("0.0"), "cent")
    assert sqft is None
    assert unit == "INVALID_EXTENT"


def test_compare_extents_precision():
    """Verify extent comparison with tolerances."""
    # Within 2% tolerance -> MATCH
    res, diff, msg = compare_property_extents(
        Decimal("2400"), "sq.ft", Decimal("1.0"), "ground"
    )
    assert res == "MATCH"
    assert diff == Decimal("0.0")

    # 5.51 cents vs 1 ground (2400 sq.ft) -> diff ~ 0.0065% -> MATCH
    res, diff, msg = compare_property_extents(
        Decimal("5.51"), "cent", Decimal("2400"), "sq.ft"
    )
    assert res == "MATCH"

    # 15% discrepancy -> SIGNIFICANT_MISMATCH
    res, diff, msg = compare_property_extents(
        Decimal("1000"), "sq.ft", Decimal("1200"), "sq.ft"
    )
    assert res == "SIGNIFICANT_MISMATCH"
    assert diff > Decimal("10.0")

    # Unknown unit handles gracefully
    res, diff, msg = compare_property_extents(
        Decimal("1000"), "unknown_unit", Decimal("1000"), "sq.ft"
    )
    assert res == "UNKNOWN"
    assert "Uninterpretable" in msg


# ============================================================================
# 3. OWNER NAME MATCHING TESTS (INCLUDING TAMIL UNICODE)
# ============================================================================

def test_name_matching_exact():
    """Verify exact name matching."""
    res, msg = compare_tamil_nadu_names("Ramanathan Sundaram", "Ramanathan Sundaram")
    assert res == "MATCH"
    assert "match" in msg.lower()


def test_name_matching_initials_permutation():
    """Verify initials vs expanded names and token permutation in Tamil Nadu."""
    res, msg = compare_tamil_nadu_names("S. Ramanathan", "Ramanathan S")
    assert res == "MATCH"
    assert "token order" in msg.lower() or "match" in msg.lower()

    res, msg = compare_tamil_nadu_names("Kuppusamy Vijay Anand", "Vijay Anand Kuppusamy")
    assert res == "MATCH"


def test_name_matching_tamil_unicode():
    """Verify native Tamil script support."""
    assert is_tamil_unicode("ராமசாமி") is True
    assert is_tamil_unicode("Ramasamy") is False

    res, msg = compare_tamil_nadu_names("ராமசாமி", "ராமசாமி")
    assert res == "MATCH"
    assert "exact" in msg.lower() or "match" in msg.lower()


def test_name_matching_mismatch():
    """Verify distinct names produce MISMATCH."""
    res, msg = compare_tamil_nadu_names("Ramanathan Sundaram", "Kaliappan Perumal")
    assert res == "MISMATCH"
    assert "mismatch" in msg.lower()


# ============================================================================
# 4. SURVEY NUMBER NORMALIZATION & SUBDIVISION TESTS
# ============================================================================

def test_survey_normalization_clean_and_messy():
    """Verify stripping prefixes and normalizing survey identifiers."""
    assert normalize_survey_identifier("S.F.No: 124 / 3A") == "124/3A"
    assert normalize_survey_identifier("R.S.No. 45 - 2") == "45-2"
    assert normalize_survey_identifier("T.S.No. 12/3B1") == "12/3B1"
    assert normalize_survey_identifier("Survey No. 99") == "99"
    assert normalize_survey_identifier(None) is None


def test_survey_subdivision_comparison():
    """Verify exact match, parent parcel, and distinct subdivision comparison."""
    # Exact match
    grade, msg = compare_survey_parcels("124/3A", "S.No. 124/3A")
    assert grade == SurveyComparisonGrade.MATCH

    # Parent parcel relationship (124/3 vs 124/3A)
    grade, msg = compare_survey_parcels("124/3", "124/3A")
    assert grade == SurveyComparisonGrade.PARENT_PARCEL
    assert "parent-to-subdivision" in msg

    # Subdivision mismatch (124/3A vs 124/3B)
    grade, msg = compare_survey_parcels("124/3A", "124/3B")
    assert grade == SurveyComparisonGrade.MISMATCH
    assert "subdivision mismatch" in msg

    # Disjoint survey numbers (124 vs 125)
    grade, msg = compare_survey_parcels("124", "125")
    assert grade == SurveyComparisonGrade.MISMATCH


# ============================================================================
# 5. DOCUMENT CHRONOLOGY GRAPH TESTS
# ============================================================================

def test_chronology_valid_chain():
    """Verify a clean document chain produces valid chronology without loops or future deeds."""
    doc_a_id = uuid.uuid4()
    doc_b_id = uuid.uuid4()
    doc_c_id = uuid.uuid4()

    analysis = analyze_document_chronology(
        current_doc_id=doc_c_id,
        current_doc_date=date(2022, 1, 15),
        parent_doc_id=doc_b_id,
        parent_doc_date=date(2010, 8, 20),
        additional_parents=[(doc_a_id, date(1995, 5, 12))],
    )
    assert analysis.status == ChronologyStatus.CHRONOLOGY_OK
    assert len(analysis.issues) == 0
    assert len(analysis.nodes) == 3
    assert len(analysis.edges) == 2


def test_chronology_circular_link_detection():
    """Verify circular parent self-reference is detected as review issue."""
    doc_a_id = uuid.uuid4()

    analysis = analyze_document_chronology(
        current_doc_id=doc_a_id,
        current_doc_date=date(2010, 1, 1),
        parent_doc_id=doc_a_id,
        parent_doc_date=date(2010, 1, 1),
    )
    assert analysis.status == ChronologyStatus.CHRONOLOGY_REVIEW
    assert any("Circular" in issue for issue in analysis.issues)


def test_chronology_future_parent_deed_detection():
    """Verify that a parent deed dated AFTER the child deed is flagged as anomaly."""
    doc_parent_id = uuid.uuid4()
    doc_child_id = uuid.uuid4()

    analysis = analyze_document_chronology(
        current_doc_id=doc_child_id,
        current_doc_date=date(2015, 1, 1),
        parent_doc_id=doc_parent_id,
        parent_doc_date=date(2024, 1, 1),
    )
    assert any("Future parent deed" in issue for issue in analysis.issues)


# ============================================================================
# 6. DOCUMENTARY COMPLETENESS SCORING TESTS (100-POINT MODEL)
# ============================================================================

def test_completeness_scoring_zero_when_no_docs():
    """Verify completeness score is low when minimal or no documents are present."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PROP-EMPTY-01",
        title="Empty Land",
        property_type="LAND",
        transaction_type="SALE",
        price=Decimal("1500000.00"),
        district="Chennai",
        city="Chennai",
        locality="Saidapet",
        pincode="600015",
        plot_area=Decimal("2400"),
        area_unit="sq.ft",
    )
    engine = DeterministicTNVerificationEngine()
    res = engine.evaluate(prop, [], PropertyVerificationInput())

    # With no documents, score must be low (< 35) and status NEEDS_REVIEW
    assert res.completeness_score < 35
    assert res.status == "NEEDS_REVIEW"


def test_completeness_scoring_dynamic_scaling_for_non_applicable():
    """Verify non-applicable categories (e.g., RERA for resale land) scale score dynamically."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PROP-LAND-RESALE",
        title="Agricultural Land Resale",
        property_type="AGRICULTURAL",
        transaction_type="SALE",
        price=Decimal("4500000.00"),
        district="Coimbatore",
        city="Coimbatore",
        locality="Sulur",
        pincode="641402",
        plot_area=Decimal("2.0"),
        area_unit="acre",
        owner_name="Kaliappan",
    )
    # Provided: Sale deed, Parent deed, Patta, EC
    doc_sale = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="SALE_DEED",
        original_filename="sale.pdf",
        storage_key="docs/sale.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="chk1",
        is_archived=False,
    )
    doc_patta = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="PATTA",
        original_filename="patta.pdf",
        storage_key="docs/patta.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="chk2",
        is_archived=False,
    )
    doc_ec = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="EC",
        original_filename="ec.pdf",
        storage_key="docs/ec.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="chk3",
        is_archived=False,
    )
    doc_parent = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="PARENT_DOCUMENT",
        original_filename="parent.pdf",
        storage_key="docs/parent.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="chk4",
        is_archived=False,
    )

    engine = DeterministicTNVerificationEngine()
    inp = PropertyVerificationInput(
        survey_number="45/2",
        owner_name="Kaliappan",
        extent=Decimal("2.0"),
        extent_unit="acre",
        ec_years=30,
        disclaimer_acknowledged=True,
    )
    res = engine.evaluate(prop, [doc_sale, doc_patta, doc_ec, doc_parent], inp)

    # RERA is non-applicable for resale agricultural land; score scales dynamically
    assert res.completeness_score >= 60
    assert res.rera_applicability == ReraApplicability.RERA_NOT_APPLICABLE


# ============================================================================
# 7. CONSULTANT ACTIONS GENERATION TESTS
# ============================================================================

def test_consultant_actions_priority_ordering():
    """Verify actions are generated with HIGH priority items first, followed by MEDIUM."""
    actions = generate_consultant_actions(
        risk_flags=["Circular parent deed reference detected", "Missing 30-year EC history"],
        missing_info=["Missing Patta document", "Missing Parent deed"],
        has_active_ec_charge=True,
        is_planning_missing=True,
        has_survey_mismatch=True,
    )
    assert len(actions) > 0
    # First action must be HIGH priority
    assert actions[0].priority == "HIGH"

    # Check priorities order is strictly non-increasing (HIGH before MEDIUM before LOW)
    priority_order = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
    }
    scores = [priority_order.get(a.priority, 0) for a in actions]
    assert scores == sorted(scores, reverse=True)


# ============================================================================
# 8. PROVIDER OFFLINE RESPONSE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_default_provider_offline_responses():
    """Verify DefaultTamilNaduVerificationProvider returns PROVIDER_NOT_CONFIGURED offline."""
    provider = DefaultTamilNaduVerificationProvider()

    patta_res = await provider.verify_patta("Coimbatore", "Coimbatore South", "Singanallur", "45/1")
    assert patta_res["status"] == "PROVIDER_NOT_CONFIGURED"
    assert "provider is not configured" in patta_res["message"].lower()

    ec_res = await provider.verify_ec("Saidapet", "45/1")
    assert ec_res["status"] == "PROVIDER_NOT_CONFIGURED"
    assert "provider is not configured" in ec_res["message"].lower()

    rera_res = await provider.verify_rera("TN/01/Building/0001/2020")
    assert rera_res["status"] == "PROVIDER_NOT_CONFIGURED"
    assert "provider is not configured" in rera_res["message"].lower()
