"""Failure and boundary mode tests for Phase 9 Tamil Nadu Verification Intelligence."""
from datetime import date
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.domain.tamil_nadu.chronology import (
    ChronologyStatus,
    analyze_document_chronology,
)
from app.domain.tamil_nadu.survey import (
    SurveyComparisonGrade,
    compare_survey_parcels,
)
from app.models.document import Document
from app.models.property import Property
from app.models.user import User
from app.schemas.verification import PropertyVerificationInput, RiskLevel
from app.services.tn_verification_engine import DeterministicTNVerificationEngine
from app.services.verification_providers import DefaultTamilNaduVerificationProvider


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    email = f"consultant-intel-fail-{uuid.uuid4().hex[:8]}@example.com"
    password = "FailConsultantPass123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Failure Tester Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_unverified_property():
    ref_code = f"VR-FAIL-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Unverified Test Land Parcel",
                property_type="LAND",
                transaction_type="SALE",
                price=Decimal("3500000.00"),
                plot_area=Decimal("2400.00"),
                area_unit="sq.ft",
                district="Madurai",
                city="Madurai",
                locality="KK Nagar",
                pincode="625020",
                status="PUBLISHED",
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id
    return prop_id


@pytest.fixture
async def sample_archived_property():
    ref_code = f"VR-ARC-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Archived Test Land Parcel",
                property_type="LAND",
                transaction_type="SALE",
                price=Decimal("2500000.00"),
                plot_area=Decimal("1200.00"),
                area_unit="sq.ft",
                district="Salem",
                city="Salem",
                locality="Fairlands",
                pincode="636016",
                status="ARCHIVED",
                is_archived=True,
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id
    return prop_id


# ============================================================================
# 1. 404 CHECKS ON NEW INTELLIGENCE ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_summary_on_unverified_property_404(
    client: AsyncClient, consultant_auth: dict, sample_unverified_property: uuid.UUID
):
    """Verify requesting summary for a property with no verification returns 404."""
    res = await client.get(
        f"/api/v1/properties/{sample_unverified_property}/verification/summary",
        headers=consultant_auth,
    )
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False
    assert "no preliminary verification case found" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_get_evidence_on_unverified_property_404(
    client: AsyncClient, consultant_auth: dict, sample_unverified_property: uuid.UUID
):
    """Verify requesting evidence report for a property with no verification returns 404."""
    res = await client.get(
        f"/api/v1/properties/{sample_unverified_property}/verification/evidence",
        headers=consultant_auth,
    )
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_get_actions_on_unverified_property_404(
    client: AsyncClient, consultant_auth: dict, sample_unverified_property: uuid.UUID
):
    """Verify requesting actions for a property with no verification returns 404."""
    res = await client.get(
        f"/api/v1/properties/{sample_unverified_property}/verification/actions",
        headers=consultant_auth,
    )
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False


@pytest.mark.asyncio
async def test_intelligence_endpoints_on_nonexistent_property_404(
    client: AsyncClient, consultant_auth: dict
):
    """Verify requesting intelligence endpoints on random non-existent UUID returns 404."""
    random_id = uuid.uuid4()

    res_sum = await client.get(
        f"/api/v1/properties/{random_id}/verification/summary",
        headers=consultant_auth,
    )
    assert res_sum.status_code == 404

    res_ev = await client.get(
        f"/api/v1/properties/{random_id}/verification/evidence",
        headers=consultant_auth,
    )
    assert res_ev.status_code == 404

    res_act = await client.get(
        f"/api/v1/properties/{random_id}/verification/actions",
        headers=consultant_auth,
    )
    assert res_act.status_code == 404


@pytest.mark.asyncio
async def test_run_verification_on_archived_property_404(
    client: AsyncClient, consultant_auth: dict, sample_archived_property: uuid.UUID
):
    """Verify executing verification on an archived property returns 404."""
    res = await client.post(
        f"/api/v1/properties/{sample_archived_property}/verification",
        json={"disclaimer_acknowledged": True},
        headers=consultant_auth,
    )
    assert res.status_code == 404
    body = res.json()
    assert body["success"] is False
    assert "archived" in body["error"]["message"].lower()


# ============================================================================
# 2. DOMAIN LOGIC HIGH RISK AND ANOMALY DETECTION
# ============================================================================

def test_circular_parent_deed_produces_review_status():
    """Verify self-referencing parent deed raises critical risk flag in engine evaluation."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PROP-CIRC-01",
        title="Circular Chain Property",
        property_type="PLOT",
        transaction_type="SALE",
        price=Decimal("1000000"),
        district="Chennai",
        city="Chennai",
        locality="Mylapore",
        pincode="600004",
        plot_area=Decimal("2400"),
        area_unit="sq.ft",
    )
def test_circular_parent_deed_produces_review_status():
    """Verify self-referencing parent deed raises review status in chronology analysis."""
    doc_id = uuid.uuid4()
    analysis = analyze_document_chronology(
        current_doc_id=doc_id,
        current_doc_date=date(2010, 1, 1),
        parent_doc_id=doc_id,
        parent_doc_date=date(2010, 1, 1),
    )
    assert analysis.status == ChronologyStatus.CHRONOLOGY_REVIEW
    assert any("circular" in issue.lower() for issue in analysis.issues)


def test_future_parent_deed_date_produces_risk_flag():
    """Verify parent deed date occurring AFTER current deed date produces anomaly flag."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PROP-FUTURE-01",
        title="Future Parent Chain Property",
        property_type="PLOT",
        transaction_type="SALE",
        price=Decimal("1000000"),
        district="Coimbatore",
        city="Coimbatore",
        locality="Ramanathapuram",
        pincode="641045",
        plot_area=Decimal("2400"),
        area_unit="sq.ft",
    )
    doc_parent = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="PARENT_DOCUMENT",
        original_filename="parent.pdf",
        storage_key="test/parent.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="p1",
        is_archived=False,
    )
    doc_current = Document(
        id=uuid.uuid4(),
        property_id=prop.id,
        document_type="SALE_DEED",
        original_filename="current.pdf",
        storage_key="test/current.pdf",
        mime_type="application/pdf",
        file_size=1024,
        checksum="c1",
        is_archived=False,
    )

    engine = DeterministicTNVerificationEngine()
    inp = PropertyVerificationInput(
        current_deed_date=date(2010, 1, 1),
        parent_document_date=date(2025, 1, 1),  # Parent deed executed in 2025, current in 2010!
        disclaimer_acknowledged=True,
    )
    res = engine.evaluate(prop, [doc_current, doc_parent], inp)

    # Must detect future parent anomaly
    assert any("future parent" in f.lower() for f in res.risk_flags) or any("future parent" in issue.lower() for issue in res.chronology.issues)


def test_survey_subdivision_mismatch_elevates_risk():
    """Verify distinct subdivision numbers in Tamil Nadu designate distinct parcels and result in MISMATCH."""
    grade, msg = compare_survey_parcels("45/3A", "45/3B")
    assert grade == SurveyComparisonGrade.MISMATCH
    assert "subdivision mismatch" in msg.lower()

    # Also test via DeterministicTNVerificationEngine delegation
    res, msg = DeterministicTNVerificationEngine.compare_survey_identifiers("45/3A", "45/3B")
    assert res == "MISMATCH"
    assert "subdivision mismatch" in msg.lower()


def test_unknown_measurement_unit_handles_gracefully():
    """Verify uninterpretable measurement unit does not cause crash or divide-by-zero."""
    prop = Property(
        id=uuid.uuid4(),
        public_reference="PROP-UNIT-01",
        title="Unknown Unit Property",
        property_type="LAND",
        transaction_type="SALE",
        price=Decimal("1000000"),
        district="Salem",
        city="Salem",
        locality="Fairlands",
        pincode="636016",
        plot_area=Decimal("50"),
        area_unit="bigha",  # Non-Tamil Nadu unit
    )
    engine = DeterministicTNVerificationEngine()
    inp = PropertyVerificationInput(
        extent=Decimal("50"),
        extent_unit="bigha",
        disclaimer_acknowledged=True,
    )
    # Must evaluate without crashing
    res = engine.evaluate(prop, [], inp)
    assert res is not None
    assert res.completeness_score < 30
