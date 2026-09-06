"""Integration tests for Follow-up Management API and persistence."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.follow_up import FollowUp
from app.models.user import User


@pytest.fixture(autouse=True)
async def clean_follow_ups():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM follow_ups"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM follow_ups"))


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-fu-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="FollowUp Consultant",
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
async def sample_client(auth_headers: dict, client: AsyncClient):
    payload = {
        "full_name": "FollowUp Target Client",
        "phone": f"+91 96{uuid.uuid4().int % 100000000:08d}",
        "email": f"fu-client-{uuid.uuid4().hex[:6]}@example.com",
        "classification": "BUYER",
    }
    res = await client.post("/api/v1/clients", json=payload, headers=auth_headers)
    assert res.status_code == 201
    return res.json()["data"]


@pytest.fixture
async def sample_property(auth_headers: dict, client: AsyncClient):
    payload = {
        "title": "FollowUp Residential Land",
        "property_type": "Residential Plot",
        "transaction_type": "SALE",
        "price": "3000000.00",
        "plot_area": "1200.00",
        "district": "Kanchipuram",
        "city": "Kanchipuram",
        "locality": "Walajabad",
        "pincode": "631605",
    }
    res = await client.post("/api/v1/properties", json=payload, headers=auth_headers)
    assert res.status_code == 201
    return res.json()["data"]


@pytest.fixture
async def sample_lead(auth_headers: dict, client: AsyncClient, sample_client: dict, sample_property: dict):
    payload = {
        "client_id": sample_client["id"],
        "property_id": sample_property["id"],
        "source": "DIRECT_CALL",
        "notes": "Interested in Walajabad plot",
    }
    res = await client.post("/api/v1/leads", json=payload, headers=auth_headers)
    assert res.status_code == 201
    return res.json()["data"]


@pytest.mark.asyncio
async def test_full_follow_up_lifecycle_complete(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
    sample_property: dict,
):
    """Test full cycle: Create -> Get -> Update -> Complete -> Audit logs verified."""
    scheduled_time = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)

    # 1. Create Follow-up
    create_payload = {
        "client_id": sample_client["id"],
        "property_id": sample_property["id"],
        "action_type": "CALL",
        "scheduled_at": scheduled_time.isoformat(),
        "notes": "Call buyer to check availability for Walajabad plot visit",
    }
    res = await client.post("/api/v1/follow-ups", json=create_payload, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["status"] == "SCHEDULED"
    assert data["action_type"] == "CALL"
    assert data["client"]["id"] == sample_client["id"]
    assert data["property"]["id"] == sample_property["id"]
    assert "disclaimer" in data
    fu_id = data["id"]

    # 2. Get Follow-up
    res_get = await client.get(f"/api/v1/follow-ups/{fu_id}", headers=auth_headers)
    assert res_get.status_code == 200
    assert res_get.json()["data"]["id"] == fu_id

    # 3. Update Follow-up
    update_payload = {
        "action_type": "ARRANGE_VISIT",
        "notes": "Updated: Arrange physical inspection for Saturday morning",
    }
    res_upd = await client.patch(f"/api/v1/follow-ups/{fu_id}", json=update_payload, headers=auth_headers)
    assert res_upd.status_code == 200
    assert res_upd.json()["data"]["action_type"] == "ARRANGE_VISIT"
    assert "Arrange physical inspection" in res_upd.json()["data"]["notes"]

    # 4. Complete Follow-up
    complete_payload = {
        "completion_notes": "Buyer agreed for Saturday 10 AM. Site visit requested.",
    }
    res_comp = await client.post(
        f"/api/v1/follow-ups/{fu_id}/complete",
        json=complete_payload,
        headers=auth_headers,
    )
    assert res_comp.status_code == 200
    comp_data = res_comp.json()["data"]
    assert comp_data["status"] == "COMPLETED"
    assert comp_data["completion_notes"] == "Buyer agreed for Saturday 10 AM. Site visit requested."
    assert comp_data["completed_at"] is not None

    # 5. Verify Idempotency of complete
    res_comp_idempotent = await client.post(
        f"/api/v1/follow-ups/{fu_id}/complete",
        json=complete_payload,
        headers=auth_headers,
    )
    assert res_comp_idempotent.status_code == 200
    assert res_comp_idempotent.json()["data"]["status"] == "COMPLETED"

    # 6. Verify Audit Logs
    async with AsyncSessionFactory() as session:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_id == uuid.UUID(fu_id))
            .order_by(AuditLog.created_at.asc())
        )
        result = await session.execute(stmt)
        logs = list(result.scalars().all())
        actions = [log.action for log in logs]
        assert "FOLLOW_UP_CREATED" in actions
        assert "FOLLOW_UP_UPDATED" in actions
        assert "FOLLOW_UP_COMPLETED" in actions


@pytest.mark.asyncio
async def test_lead_target_and_miss_lifecycle(
    client: AsyncClient,
    auth_headers: dict,
    sample_lead: dict,
    sample_property: dict,
):
    """Test follow-up targeting a Lead and transitioning to MISSED."""
    scheduled_time = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)

    # 1. Create Follow-up targeting Lead
    create_payload = {
        "lead_id": sample_lead["id"],
        "property_id": sample_property["id"],
        "action_type": "SEND_DOCS",
        "scheduled_at": scheduled_time.isoformat(),
        "notes": "Send parent deed copy and Patta extract",
    }
    res = await client.post("/api/v1/follow-ups", json=create_payload, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["lead"]["id"] == sample_lead["id"]
    assert data["client_id"] == sample_lead["client_id"]  # Auto-associated
    fu_id = data["id"]

    # 2. Mark as Missed
    miss_payload = {
        "notes": "Client was unreachable after 3 attempts. Reschedule required.",
    }
    res_miss = await client.post(
        f"/api/v1/follow-ups/{fu_id}/miss",
        json=miss_payload,
        headers=auth_headers,
    )
    assert res_miss.status_code == 200
    miss_data = res_miss.json()["data"]
    assert miss_data["status"] == "MISSED"
    assert "Client was unreachable" in miss_data["notes"]

    # 3. Idempotent miss
    res_miss_idemp = await client.post(
        f"/api/v1/follow-ups/{fu_id}/miss",
        json=miss_payload,
        headers=auth_headers,
    )
    assert res_miss_idemp.status_code == 200
    assert res_miss_idemp.json()["data"]["status"] == "MISSED"


@pytest.mark.asyncio
async def test_list_follow_ups_with_filtering_and_pagination(
    client: AsyncClient,
    auth_headers: dict,
    sample_client: dict,
    sample_property: dict,
):
    """Test listing follow-ups with status and action_type filters."""
    base_time = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)

    # Create 3 follow-ups with different action types
    actions = ["CALL", "SEND_DOCS", "OWNER_FOLLOW_UP"]
    for i, action in enumerate(actions):
        payload = {
            "client_id": sample_client["id"],
            "property_id": sample_property["id"],
            "action_type": action,
            "scheduled_at": (base_time + timedelta(hours=i * 2)).isoformat(),
            "notes": f"Task {i}",
        }
        res = await client.post("/api/v1/follow-ups", json=payload, headers=auth_headers)
        assert res.status_code == 201

    # List all
    res_all = await client.get("/api/v1/follow-ups", headers=auth_headers)
    assert res_all.status_code == 200
    data_all = res_all.json()["data"]
    assert data_all["total"] == 3
    assert len(data_all["items"]) == 3

    # Filter by action_type CALL
    res_call = await client.get("/api/v1/follow-ups?action_type=CALL", headers=auth_headers)
    assert res_call.status_code == 200
    data_call = res_call.json()["data"]
    assert data_call["total"] == 1
    assert data_call["items"][0]["action_type"] == "CALL"

    # Filter by client_id
    res_cli = await client.get(f"/api/v1/follow-ups?client_id={sample_client['id']}", headers=auth_headers)
    assert res_cli.status_code == 200
    assert res_cli.json()["data"]["total"] == 3
