"""Integration tests for Phase 9 Tamil Nadu Verification Intelligence Endpoints."""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.document import Document
from app.models.property import Property
from app.models.user import User


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    """Create and authenticate a consultant user."""
    email = f"consultant-intel-{uuid.uuid4().hex[:8]}@example.com"
    password = "IntelConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Intelligence Consultant",
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
async def client_auth(client: AsyncClient):
    """Create and authenticate a regular client user (non-consultant)."""
    email = f"client-intel-{uuid.uuid4().hex[:8]}@example.com"
    password = "ClientPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Regular Client",
                role="CLIENT",
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
async def sample_verified_property():
    """Create a sample residential property with attached documents."""
    ref_code = f"VR-INTEL-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Premium CMDA Residential Plot in Tambaram",
                property_type="PLOT",
                transaction_type="SALE",
                price=Decimal("4500000.00"),
                plot_area=Decimal("2400.00"),
                area_unit="sq.ft",
                district="Chengalpattu",
                city="Tambaram",
                locality="Tambaram West",
                pincode="600045",
                owner_name="R. Kumar",
                status="PUBLISHED",
            )
            session.add(prop)
            await session.flush()

            doc_deed = Document(
                property_id=prop.id,
                document_type="SALE_DEED",
                storage_key=f"intel/deed-{uuid.uuid4().hex}.pdf",
                original_filename="registered_sale_deed.pdf",
                mime_type="application/pdf",
                file_size=2048,
                checksum=f"chk-{uuid.uuid4().hex}",
                status="UPLOADED",
            )
            doc_ec = Document(
                property_id=prop.id,
                document_type="EC",
                storage_key=f"intel/ec-{uuid.uuid4().hex}.pdf",
                original_filename="encumbrance_certificate_30yr.pdf",
                mime_type="application/pdf",
                file_size=4096,
                checksum=f"chk-{uuid.uuid4().hex}",
                status="UPLOADED",
            )
            doc_patta = Document(
                property_id=prop.id,
                document_type="PATTA",
                storage_key=f"intel/patta-{uuid.uuid4().hex}.pdf",
                original_filename="patta_chitta.pdf",
                mime_type="application/pdf",
                file_size=1024,
                checksum=f"chk-{uuid.uuid4().hex}",
                status="UPLOADED",
            )
            session.add_all([doc_deed, doc_ec, doc_patta])
            await session.flush()
            prop_id = prop.id

    return prop_id


# ============================================================================
# 1. TEST POST EXECUTION WITH PHASE 9 INTELLIGENCE
# ============================================================================

@pytest.mark.asyncio
async def test_post_verification_returns_phase_9_intelligence(
    client: AsyncClient, consultant_auth: dict, sample_verified_property: uuid.UUID
):
    """Verify executing preliminary property verification returns all Phase 9 intelligence structures."""
    payload = {
        "survey_number": "124/3A",
        "subdivision_number": "3A",
        "patta_number": "412",
        "ec_start_date": "1994-01-01",
        "ec_end_date": "2024-01-01",
        "ec_has_encumbrance_entries": False,
        "planning_approval_number": "CMDA/P/045/2019",
        "is_new_project_or_promoter_sale": False,
        "consultant_notes": "Phase 9 Intelligence Evaluation",
        "disclaimer_acknowledged": True,
    }

    res = await client.post(
        f"/api/v1/properties/{sample_verified_property}/verification",
        json=payload,
        headers=consultant_auth,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    data = body["data"]

    # Verify Phase 9 intelligence models
    assert "chronology" in data and data["chronology"] is not None
    assert "nodes" in data["chronology"]
    assert "issues" in data["chronology"]
    assert "status" in data["chronology"]

    assert "actions" in data and isinstance(data["actions"], list)
    assert len(data["actions"]) > 0
    assert "action_type" in data["actions"][0]
    assert "priority" in data["actions"][0]
    assert "description" in data["actions"][0]

    assert "explanations" in data and isinstance(data["explanations"], list)
    assert len(data["explanations"]) > 0
    assert "checklist_code" in data["explanations"][0]
    assert "result" in data["explanations"][0]
    assert "explanation" in data["explanations"][0]
    assert "recommended_action" in data["explanations"][0]

    assert "evidence_report" in data and data["evidence_report"] is not None
    assert "evidence_items" in data["evidence_report"]
    assert len(data["evidence_report"]["evidence_items"]) >= 3

    assert "summary" in data and data["summary"] is not None
    assert data["summary"]["documentary_completeness_score"] > 0
    assert "preliminary property verification assessment" in data["disclaimer"].lower()


# ============================================================================
# 2. TEST GET /summary ENDPOINT
# ============================================================================

@pytest.mark.asyncio
async def test_get_verification_summary_endpoint(
    client: AsyncClient, consultant_auth: dict, sample_verified_property: uuid.UUID
):
    """Verify machine-readable summary metrics endpoint."""
    # Ensure verification has run
    await client.post(
        f"/api/v1/properties/{sample_verified_property}/verification",
        json={"survey_number": "124/3A", "disclaimer_acknowledged": True},
        headers=consultant_auth,
    )

    res = await client.get(
        f"/api/v1/properties/{sample_verified_property}/verification/summary",
        headers=consultant_auth,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]

    assert data["property_id"] == str(sample_verified_property)
    assert "overall_risk" in data
    assert "documentary_completeness_score" in data
    assert "critical_issue_count" in data
    assert "missing_document_count" in data
    assert "review_required_count" in data
    assert "preliminary" in data["disclaimer"].lower()


# ============================================================================
# 3. TEST GET /evidence ENDPOINT
# ============================================================================

@pytest.mark.asyncio
async def test_get_verification_evidence_endpoint(
    client: AsyncClient, consultant_auth: dict, sample_verified_property: uuid.UUID
):
    """Verify detailed documentary evidence intelligence endpoint."""
    # Ensure verification has run
    await client.post(
        f"/api/v1/properties/{sample_verified_property}/verification",
        json={"survey_number": "124/3A", "disclaimer_acknowledged": True},
        headers=consultant_auth,
    )

    res = await client.get(
        f"/api/v1/properties/{sample_verified_property}/verification/evidence",
        headers=consultant_auth,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]

    assert data["property_id"] == str(sample_verified_property)
    assert "evidence_completeness" in data
    assert "evidence_quality" in data
    assert "chronology_integrity" in data
    assert "evidence_items" in data
    assert len(data["evidence_items"]) >= 3
    for item in data["evidence_items"]:
        assert "evidence_type" in item
        assert "status" in item
        assert "confidence" in item


# ============================================================================
# 4. TEST GET /actions ENDPOINT
# ============================================================================

@pytest.mark.asyncio
async def test_get_verification_actions_endpoint(
    client: AsyncClient, consultant_auth: dict, sample_verified_property: uuid.UUID
):
    """Verify prioritized consultant actions endpoint."""
    # Ensure verification has run
    await client.post(
        f"/api/v1/properties/{sample_verified_property}/verification",
        json={"survey_number": "124/3A", "disclaimer_acknowledged": True},
        headers=consultant_auth,
    )

    res = await client.get(
        f"/api/v1/properties/{sample_verified_property}/verification/actions",
        headers=consultant_auth,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    actions = body["data"]

    assert isinstance(actions, list)
    assert len(actions) > 0
    for action in actions:
        assert "action_type" in action
        assert "priority" in action
        assert action["priority"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert "description" in action


# ============================================================================
# 5. TEST RBAC AUTHORIZATION ON INTELLIGENCE ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_rbac_non_consultant_forbidden_on_intelligence(
    client: AsyncClient, client_auth: dict, sample_verified_property: uuid.UUID
):
    """Verify that clients or non-consultant roles receive 403 Forbidden."""
    # 1. Summary
    res = await client.get(
        f"/api/v1/properties/{sample_verified_property}/verification/summary",
        headers=client_auth,
    )
    assert res.status_code == 403

    # 2. Evidence
    res = await client.get(
        f"/api/v1/properties/{sample_verified_property}/verification/evidence",
        headers=client_auth,
    )
    assert res.status_code == 403

    # 3. Actions
    res = await client.get(
        f"/api/v1/properties/{sample_verified_property}/verification/actions",
        headers=client_auth,
    )
    assert res.status_code == 403


# ============================================================================
# 6. TEST AUDIT LOG CAPTURES ENGINE VERSION "TN-VERIFICATION-2.0"
# ============================================================================

@pytest.mark.asyncio
async def test_audit_log_captures_engine_version(
    client: AsyncClient, consultant_auth: dict, sample_verified_property: uuid.UUID
):
    """Verify completion audit log records engine_version = 'TN-VERIFICATION-2.0'."""
    post_res = await client.post(
        f"/api/v1/properties/{sample_verified_property}/verification",
        json={"survey_number": "124/3A", "disclaimer_acknowledged": True},
        headers=consultant_auth,
    )
    assert post_res.status_code == 201
    case_id = uuid.UUID(post_res.json()["data"]["id"])

    async with AsyncSessionFactory() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == case_id,
                AuditLog.action.in_(["VERIFICATION_COMPLETED", "VERIFICATION_NEEDS_REVIEW"]),
            )
        )
        logs = audit_res.scalars().all()
        assert len(logs) >= 1
        completion_log = logs[-1]
        assert completion_log.change_diff is not None
        import json
        diff_dict = json.loads(completion_log.change_diff) if isinstance(completion_log.change_diff, str) else completion_log.change_diff
        assert diff_dict.get("engine_version") == "TN-VERIFICATION-2.0"
