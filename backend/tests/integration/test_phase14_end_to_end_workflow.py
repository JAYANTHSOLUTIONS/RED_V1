"""Phase 14 Integration Scenarios 10, 15, 21, 22, 23: Complete Consultant Workflow & Lifecycle.

Tests the full cross-module consultant journey:
1. Complete End-to-End Workflow:
   Login -> Create Property -> Publish Property -> Create Client -> Create Lead ->
   Create Requirement -> Match Requirement -> Upload Document -> Create Verification ->
   Review Verification -> Request Site Visit -> Confirm Site Visit -> Complete Site Visit ->
   Create Follow-Up -> Complete Follow-Up -> Trigger/Fetch Notification -> Mark Read ->
   Audit Trail Chain Verification.
2. Property Full Lifecycle State Machine (DRAFT -> PUBLISHED -> PAUSED -> PUBLISHED -> SOLD -> ARCHIVED).
3. Cross-Module Timezone & Timestamp Consistency (Asia/Kolkata UTC+05:30).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import io
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.property import Property
from app.models.site_visit import SiteVisit
from app.models.user import User
from app.services.notification import NotificationService


@pytest.fixture
async def consultant_auth(client: AsyncClient):
    """Create and authenticate a dedicated consultant user."""
    email = f"consultant-e2e-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="E2E Workflow Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    user_id = login_res.json()["data"]["user"]["id"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": uuid.UUID(user_id),
    }


@pytest.mark.asyncio
async def test_complete_consultant_workflow_and_audit_trail(
    client: AsyncClient, consultant_auth: dict
):
    """Scenario 10 & 23: Comprehensive 18-step end-to-end consultant workflow and complete audit verification."""
    headers = consultant_auth["headers"]
    user_id = consultant_auth["user_id"]

    # 1. CREATE PROPERTY
    prop_res = await client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "title": "E2E Grand Villa in Sholinganallur OMR",
            "description": "Premium 4BHK individual villa with private terrace",
            "property_type": "RESIDENTIAL_VILLA",
            "transaction_type": "SALE",
            "price": 22000000.00,
            "built_up_area": 2800.00,
            "plot_area": 2400.00,
            "area_unit": "sq.ft",
            "bedrooms": 4,
            "bathrooms": 4,
            "district": "Chennai",
            "city": "Chennai",
            "locality": "Sholinganallur",
            "pincode": "600119",
            "owner_name": "R. Ramanathan",
            "owner_phone": "+91 98401 22334",
        },
    )
    assert prop_res.status_code == 201, prop_res.text
    prop_data = prop_res.json()["data"]
    prop_id = prop_data["id"]
    assert prop_data["status"] == "DRAFT"

    # 2. PUBLISH PROPERTY
    pub_res = await client.post(f"/api/v1/properties/{prop_id}/publish", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["data"]["status"] == "PUBLISHED"

    # 3. CREATE CLIENT
    client_res = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "full_name": "Dr. Annamalai Chidambaram",
            "phone": "+91 97890 55667",
            "email": "dr.annamalai@example.com",
            "classification": "BUYER",
            "notes": "Looking for luxury villa in OMR/ECR IT corridor",
        },
    )
    assert client_res.status_code == 201, client_res.text
    client_id = client_res.json()["data"]["id"]

    # 4. CREATE LEAD
    lead_res = await client.post(
        "/api/v1/leads",
        headers=headers,
        json={
            "client_id": client_id,
            "property_id": prop_id,
            "source": "DIRECT_CALL",
            "notes": "Client called inquiring about published Sholinganallur villa",
        },
    )
    assert lead_res.status_code == 201, lead_res.text
    lead_id = lead_res.json()["data"]["id"]

    # 5. CREATE REQUIREMENT
    req_res = await client.post(
        "/api/v1/property-requirements",
        headers=headers,
        json={
            "client_id": client_id,
            "transaction_type": "BUY",
            "property_types": "RESIDENTIAL_VILLA",
            "min_budget": 18000000.00,
            "max_budget": 25000000.00,
            "min_area": 2500.00,
            "max_area": 3500.00,
            "target_locations": "Sholinganallur",
            "bedrooms": 4,
        },
    )
    assert req_res.status_code == 201, req_res.text
    req_id = req_res.json()["data"]["id"]

    # 6. MATCH REQUIREMENT TO PROPERTY
    match_res = await client.get(
        f"/api/v1/property-requirements/{req_id}/matches",
        headers=headers,
    )
    assert match_res.status_code == 200
    matched_items = match_res.json()["data"]["items"]
    matched_refs = [m["property"]["public_reference"] for m in matched_items]
    assert prop_data["public_reference"] in matched_refs, "Published villa must match client requirements"

    # 7. UPLOAD LEGAL DOCUMENT
    pdf_content = b"%PDF-1.4 Phase 14 E2E Legal Document Patta Passbook content..."
    doc_res = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("patta_chitta_e2e.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={
            "document_type": "PATTA",
            "property_id": prop_id,
            "client_id": client_id,
        },
    )
    assert doc_res.status_code == 201, doc_res.text
    doc_id = doc_res.json()["data"]["id"]

    # 8. CREATE PRELIMINARY VERIFICATION CASE
    verif_res = await client.post(
        f"/api/v1/properties/{prop_id}/verification",
        headers=headers,
        json={
            "survey_number": "142/2B",
            "subdivision_number": "2B",
            "patta_number": "6789",
            "ec_start_date": "1994-01-01",
            "ec_end_date": "2024-01-01",
            "ec_has_encumbrance_entries": False,
            "planning_approval_number": "CMDA/P/089/2021",
            "is_new_project_or_promoter_sale": False,
            "consultant_notes": "All original deeds physically inspected.",
            "disclaimer_acknowledged": True,
        },
    )
    assert verif_res.status_code == 201, verif_res.text
    verif_id = verif_res.json()["data"]["id"]

    # 9. CONSULTANT REVIEWS VERIFICATION
    verif_update = await client.patch(
        f"/api/v1/verifications/{verif_id}",
        headers=headers,
        json={
            "consultant_observations": "Patta verified against revenue portal. Survey boundaries clear.",
            "status": "COMPLETED",
        },
    )
    assert verif_update.status_code == 200

    # 10. REQUEST SITE VISIT
    visit_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    visit_res = await client.post(
        "/api/v1/site-visits/request",
        headers=headers,
        json={
            "property_id": prop_id,
            "client_id": client_id,
            "lead_id": lead_id,
            "scheduled_at": visit_time,
            "notes": "Client requested evening visit between 4 PM and 5 PM",
        },
    )
    assert visit_res.status_code == 201, visit_res.text
    visit_id = visit_res.json()["data"]["id"]

    # 11. CONFIRM SITE VISIT
    confirm_res = await client.post(
        f"/api/v1/site-visits/{visit_id}/confirm",
        headers=headers,
        json={"notes": "Visit confirmed with property security"},
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["data"]["status"] == "CONFIRMED"

    # 12. COMPLETE SITE VISIT
    complete_res = await client.post(
        f"/api/v1/site-visits/{visit_id}/complete",
        headers=headers,
        json={"feedback": "Client loved the property layout and garden area"},
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["data"]["status"] == "COMPLETED"

    # 13. CREATE FOLLOW-UP
    follow_up_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    follow_res = await client.post(
        "/api/v1/follow-ups",
        headers=headers,
        json={
            "client_id": client_id,
            "lead_id": lead_id,
            "property_id": prop_id,
            "action_type": "CALL",
            "scheduled_at": follow_up_time,
            "notes": "Follow up on pricing negotiation and bank loan approval",
        },
    )
    assert follow_res.status_code == 201, follow_res.text
    follow_up_id = follow_res.json()["data"]["id"]

    # 14. COMPLETE FOLLOW-UP
    complete_follow = await client.post(
        f"/api/v1/follow-ups/{follow_up_id}/complete",
        headers=headers,
        json={"completion_notes": "Client agreed to price; token advance discussion scheduled"},
    )
    assert complete_follow.status_code == 200
    assert complete_follow.json()["data"]["status"] == "COMPLETED"

    # 15. CREATE DIRECT NOTIFICATION FOR CONSULTANT
    notif_service = NotificationService()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            notif = await notif_service.create_follow_up_due_notification(
                session=session,
                follow_up_id=uuid.UUID(follow_up_id),
                action_type="CALL",
                user_id=user_id,
                scheduled_at_str="2026-09-08 14:00 IST",
                target_name="Dr. Annamalai Chidambaram",
            )
            notif_id = str(notif.id)

    # 16. READ NOTIFICATION
    read_res = await client.post(
        f"/api/v1/notifications/{notif_id}/read",
        headers=headers,
    )
    assert read_res.status_code == 200
    assert read_res.json()["data"]["is_read"] is True

    # 17. VERIFY AUDIT TRAIL CHAIN
    audit_res = await client.get("/api/v1/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    audit_items = audit_res.json()["data"]["items"]

    actions_recorded = [a["action"] for a in audit_items]

    # Verify key lifecycle actions are present in the audit log
    expected_actions = [
        "PROPERTY_CREATED",
        "PROPERTY_PUBLISHED",
        "CLIENT_CREATED",
        "LEAD_CREATED",
        "DOCUMENT_UPLOADED",
        "SITE_VISIT_CREATED",
        "SITE_VISIT_CONFIRMED",
        "SITE_VISIT_COMPLETED",
        "FOLLOW_UP_CREATED",
        "FOLLOW_UP_COMPLETED",
        "NOTIFICATION_READ",
    ]
    for exp_action in expected_actions:
        assert exp_action in actions_recorded, f"Audit action {exp_action} missing from audit trail"

    # Verify no sensitive auth tokens or password hashes in change_diff across any audit entry
    for entry in audit_items:
        diff_str = str(entry.get("change_diff") or {})
        assert "password" not in diff_str.lower()
        assert "access_token" not in diff_str.lower()
        assert "refresh_token" not in diff_str.lower()
        assert "secret_key" not in diff_str.lower()


@pytest.mark.asyncio
async def test_property_full_lifecycle_state_machine_and_inactivation(
    client: AsyncClient, consultant_auth: dict
):
    """Scenario 15 & 21: Tests DRAFT -> PUBLISHED -> PAUSED -> PUBLISHED -> SOLD -> ARCHIVED and blocks invalid downstream actions."""
    headers = consultant_auth["headers"]

    # 1. Create Property in DRAFT
    create_res = await client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "title": "Lifecycle Test Flat in Tambaram Sanatorium",
            "property_type": "APARTMENT",
            "transaction_type": "SALE",
            "price": 4800000.00,
            "district": "Chengalpattu",
            "city": "Tambaram",
            "locality": "Tambaram Sanatorium",
            "pincode": "600047",
        },
    )
    assert create_res.status_code == 201
    prop_id = create_res.json()["data"]["id"]
    assert create_res.json()["data"]["status"] == "DRAFT"

    # 2. Publish: DRAFT -> PUBLISHED
    pub_res = await client.post(f"/api/v1/properties/{prop_id}/publish", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["data"]["status"] == "PUBLISHED"

    # 3. Pause: PUBLISHED -> PAUSED
    pause_res = await client.post(f"/api/v1/properties/{prop_id}/pause", headers=headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["status"] == "PAUSED"

    # 4. Resume: PAUSED -> PUBLISHED
    resume_res = await client.post(f"/api/v1/properties/{prop_id}/publish", headers=headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["data"]["status"] == "PUBLISHED"

    # 5. Mark Sold: PUBLISHED -> SOLD
    sold_res = await client.post(f"/api/v1/properties/{prop_id}/mark-sold", headers=headers)
    assert sold_res.status_code == 200
    assert sold_res.json()["data"]["status"] == "SOLD"

    # 6. Cannot Pause an already SOLD property
    pause_again = await client.post(f"/api/v1/properties/{prop_id}/pause", headers=headers)
    assert pause_again.status_code in (400, 422)

    # 7. Archive: SOLD -> ARCHIVED
    archive_res = await client.post(f"/api/v1/properties/{prop_id}/archive", headers=headers)
    assert archive_res.status_code == 200
    assert archive_res.json()["data"]["status"] == "ARCHIVED"
    assert archive_res.json()["data"]["is_archived"] is True

    # 8. Cannot Publish an ARCHIVED property (terminal state)
    pub_archived = await client.post(f"/api/v1/properties/{prop_id}/publish", headers=headers)
    assert pub_archived.status_code in (400, 422)

    # 9. Cannot update an ARCHIVED property
    patch_archived = await client.patch(
        f"/api/v1/properties/{prop_id}",
        headers=headers,
        json={"title": "Updated Archived Title"},
    )
    assert patch_archived.status_code in (400, 422)


@pytest.mark.asyncio
async def test_cross_module_timezone_and_timestamp_consistency(
    client: AsyncClient, consultant_auth: dict
):
    """Scenario 22: Timezone integration ensuring Asia/Kolkata (UTC+05:30) strings serialize correctly to UTC."""
    headers = consultant_auth["headers"]

    # 1. Create a published property and active client
    prop_res = await client.post(
        "/api/v1/properties",
        headers=headers,
        json={
            "title": "Timezone Test Independent House in Medavakkam",
            "property_type": "INDEPENDENT_HOUSE",
            "transaction_type": "SALE",
            "price": 8500000.00,
            "district": "Chennai",
            "city": "Chennai",
            "locality": "Medavakkam",
            "pincode": "600100",
        },
    )
    prop_id = prop_res.json()["data"]["id"]
    await client.post(f"/api/v1/properties/{prop_id}/publish", headers=headers)

    client_res = await client.post(
        "/api/v1/clients",
        headers=headers,
        json={
            "full_name": "Suresh Krishnan",
            "phone": "+91 94444 11223",
            "classification": "BUYER",
        },
    )
    client_id = client_res.json()["data"]["id"]

    # 2. Schedule a Site Visit using explicit Asia/Kolkata offset (+05:30)
    # E.g., 2026-10-15 15:30:00 IST -> 2026-10-15 10:00:00 UTC
    ist_input = "2026-10-15T15:30:00+05:30"
    visit_res = await client.post(
        "/api/v1/site-visits/request",
        headers=headers,
        json={
            "property_id": prop_id,
            "client_id": client_id,
            "scheduled_at": ist_input,
            "notes": "Visiting at 3:30 PM IST",
        },
    )
    assert visit_res.status_code == 201
    visit_data = visit_res.json()["data"]
    visit_id = visit_data["id"]

    # Verify API returned ISO 8601 serialized datetime
    resp_scheduled = visit_data["scheduled_at"]
    assert resp_scheduled is not None
    dt_parsed = datetime.fromisoformat(resp_scheduled)
    assert dt_parsed.tzinfo is not None, "Response datetime must be timezone-aware"

    # 3. Direct DB check: verify stored timestamp matches exact UTC value
    async with AsyncSessionFactory() as session:
        db_visit = (
            await session.execute(select(SiteVisit).where(SiteVisit.id == uuid.UUID(visit_id)))
        ).scalar_one()

        # 15:30 IST is 10:00 UTC
        utc_dt = db_visit.scheduled_at.astimezone(timezone.utc)
        assert utc_dt.hour == 10
        assert utc_dt.minute == 0
        assert utc_dt.day == 15
        assert utc_dt.month == 10
        assert utc_dt.year == 2026
