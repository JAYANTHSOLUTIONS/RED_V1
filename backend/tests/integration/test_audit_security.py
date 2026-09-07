"""Security tests for Audit system: RBAC, immutable append-only enforcement, and secret protection."""
import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.sanitizer import REDACTED_MARKER
from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User
from app.services.audit import AuditService


@pytest.fixture(autouse=True)
async def clean_audit_logs():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM audit_logs"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM audit_logs"))


@pytest.fixture
async def consultant_user(client: AsyncClient):
    email = f"consultant-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Security Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    data = login_res.json()["data"]
    return {
        "headers": {"Authorization": f"Bearer {data['access_token']}"},
        "user_id": uuid.UUID(data["user"]["id"]),
    }


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected(client: AsyncClient):
    """Ensure audit endpoints reject requests without valid Bearer token."""
    fake_id = uuid.uuid4()
    assert (await client.get("/api/v1/audit-logs")).status_code == 401
    assert (await client.get(f"/api/v1/audit-logs/{fake_id}")).status_code == 401


@pytest.mark.asyncio
async def test_audit_mutation_endpoints_prohibited(client: AsyncClient, consultant_user: dict):
    """Ensure audit logs are strictly append-only: mutation endpoints return 405 Method Not Allowed."""
    auth_headers = consultant_user["headers"]
    fake_id = uuid.uuid4()

    # POST to collection
    res_post = await client.post("/api/v1/audit-logs", json={"action": "TEST"}, headers=auth_headers)
    assert res_post.status_code == 405

    # PUT on item
    res_put = await client.put(f"/api/v1/audit-logs/{fake_id}", json={"action": "TEST"}, headers=auth_headers)
    assert res_put.status_code == 405

    # PATCH on item
    res_patch = await client.patch(f"/api/v1/audit-logs/{fake_id}", json={"action": "TEST"}, headers=auth_headers)
    assert res_patch.status_code == 405

    # DELETE on item
    res_del = await client.delete(f"/api/v1/audit-logs/{fake_id}", headers=auth_headers)
    assert res_del.status_code == 405


@pytest.mark.asyncio
async def test_secret_sanitization_in_persisted_audit_records(client: AsyncClient, consultant_user: dict):
    """Ensure that sensitive credentials passed in change diffs are scrubbed before persistence and API response."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]
    service = AuditService()

    raw_diff = {
        "user_email": "user@example.com",
        "password": "PlaintextPasswordThatMustNeverPersist",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.dummytoken",
        "storage_secret_key": "raw_secret_key_123",
        "notes": "Legitimate consultant note",
    }

    entity_id = uuid.uuid4()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            created = await service.record_event(
                session=session,
                action="USER_CREDENTIALS_UPDATED",
                entity_type="USER",
                entity_id=entity_id,
                actor_id=user_id,
                change_diff=raw_diff,
            )
            log_id = str(created.id)

    res = await client.get(f"/api/v1/audit-logs/{log_id}", headers=auth_headers)
    assert res.status_code == 200
    diff_str = res.json()["data"]["change_diff"]

    # Verify secrets are NOT in the returned diff
    assert "PlaintextPasswordThatMustNeverPersist" not in diff_str
    assert "raw_secret_key_123" not in diff_str
    assert "eyJ" not in diff_str

    # Verify [REDACTED] was used
    parsed = json.loads(diff_str)
    assert parsed["password"] == REDACTED_MARKER
    assert parsed["access_token"] == REDACTED_MARKER
    assert parsed["storage_secret_key"] == REDACTED_MARKER
    assert parsed["notes"] == "Legitimate consultant note"
