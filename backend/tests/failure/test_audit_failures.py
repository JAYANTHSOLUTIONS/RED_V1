"""Failure and validation error tests for Audit endpoints."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


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
    email = f"consultant-fail-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Failure Consultant",
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
async def test_audit_log_not_found(client: AsyncClient, consultant_user: dict):
    """Ensure non-existent audit log ID returns 404."""
    auth_headers = consultant_user["headers"]
    random_id = uuid.uuid4()
    res = await client.get(f"/api/v1/audit-logs/{random_id}", headers=auth_headers)
    assert res.status_code == 404
    assert "not found" in res.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_invalid_uuid_format(client: AsyncClient, consultant_user: dict):
    """Ensure malformed UUID string in path returns 422."""
    auth_headers = consultant_user["headers"]
    res = await client.get("/api/v1/audit-logs/not-a-valid-uuid", headers=auth_headers)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_invalid_pagination_bounds(client: AsyncClient, consultant_user: dict):
    """Ensure limit and offset bounds are validated strictly."""
    auth_headers = consultant_user["headers"]

    # limit > 100
    res_high = await client.get("/api/v1/audit-logs?limit=101", headers=auth_headers)
    assert res_high.status_code == 422

    # limit < 1
    res_low = await client.get("/api/v1/audit-logs?limit=0", headers=auth_headers)
    assert res_low.status_code == 422

    # negative offset
    res_neg = await client.get("/api/v1/audit-logs?offset=-1", headers=auth_headers)
    assert res_neg.status_code == 422


@pytest.mark.asyncio
async def test_invalid_date_filter_format(client: AsyncClient, consultant_user: dict):
    """Ensure invalid timestamp string returns 422."""
    auth_headers = consultant_user["headers"]
    res = await client.get("/api/v1/audit-logs?from_date=not-a-date", headers=auth_headers)
    assert res.status_code == 422
