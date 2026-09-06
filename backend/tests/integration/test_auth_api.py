"""Integration tests for Authentication API endpoints.

Tests:
  - POST /api/v1/auth/login
  - GET  /api/v1/auth/me
  - POST /api/v1/auth/refresh
  - POST /api/v1/auth/logout
  - Role-Based Access Control (RBAC) via require_roles
"""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password, hash_refresh_token
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.user import RefreshToken, User


@pytest.fixture
async def consultant_user():
    """Create a persistent test consultant user in the test database."""
    unique_id = uuid.uuid4().hex[:8]
    email = f"consultant-{unique_id}@example.com"
    password = "SuperSecretPassword123!"
    hashed_pw = hash_password(password)

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hashed_pw,
                full_name="Principal Consultant",
                phone="+919876543210",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            user_id = user.id

    return {
        "id": user_id,
        "email": email,
        "password": password,
        "full_name": "Principal Consultant",
        "role": "CONSULTANT",
    }


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, consultant_user: dict):
    """Verify login issues valid tokens, records audit log, and stores refresh token hash."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": consultant_user["email"],
            "password": consultant_user["password"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1200
    assert data["user"]["email"] == consultant_user["email"]
    assert data["user"]["role"] == "CONSULTANT"
    assert "hashed_password" not in data["user"]

    # Verify refresh token in database
    token_hash = hash_refresh_token(data["refresh_token"])
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalar_one_or_none()
        assert stored_token is not None
        assert stored_token.user_id == consultant_user["id"]
        assert stored_token.revoked is False

        # Verify audit log
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "LOGIN_SUCCESS",
                AuditLog.actor_id == consultant_user["id"],
            )
        )
        audit_log = audit_res.scalar_one_or_none()
        assert audit_log is not None
        assert audit_log.entity_type == "USER"
        assert audit_log.entity_id == consultant_user["id"]


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, consultant_user: dict):
    """Verify GET /api/v1/auth/me returns current user profile using valid Bearer token."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": consultant_user["email"],
            "password": consultant_user["password"],
        },
    )
    access_token = login_res.json()["data"]["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["id"] == str(consultant_user["id"])
    assert data["email"] == consultant_user["email"]
    assert data["role"] == "CONSULTANT"
    assert data["is_active"] is True
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient, consultant_user: dict):
    """Verify refresh endpoint rotates tokens, revokes the previous token, and keeps session alive."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": consultant_user["email"],
            "password": consultant_user["password"],
        },
    )
    first_refresh = login_res.json()["data"]["refresh_token"]
    first_hash = hash_refresh_token(first_refresh)

    # Rotate tokens
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert refresh_res.status_code == 200
    refresh_body = refresh_res.json()
    assert refresh_body["success"] is True
    second_refresh = refresh_body["data"]["refresh_token"]
    second_access = refresh_body["data"]["access_token"]

    assert second_refresh != first_refresh

    # Verify first token is marked revoked in DB
    async with AsyncSessionFactory() as session:
        res1 = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == first_hash)
        )
        old_token = res1.scalar_one_or_none()
        assert old_token is not None
        assert old_token.revoked is True
        assert old_token.revoked_at is not None

        # Verify new token is active in DB
        second_hash = hash_refresh_token(second_refresh)
        res2 = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == second_hash)
        )
        new_token = res2.scalar_one_or_none()
        assert new_token is not None
        assert new_token.revoked is False

        # Verify audit log recorded
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "REFRESH_TOKEN_ROTATED",
                AuditLog.actor_id == consultant_user["id"],
            )
        )
        assert audit_res.scalar_one_or_none() is not None

    # Verify new access token functions properly for /me
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {second_access}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"]["email"] == consultant_user["email"]


@pytest.mark.asyncio
async def test_logout_revokes_token(client: AsyncClient, consultant_user: dict):
    """Verify logout revokes the refresh token and prevents future refresh."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": consultant_user["email"],
            "password": consultant_user["password"],
        },
    )
    refresh_token = login_res.json()["data"]["refresh_token"]
    token_hash = hash_refresh_token(refresh_token)

    logout_res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["success"] is True

    # Check token in DB is revoked
    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token = res.scalar_one_or_none()
        assert token is not None
        assert token.revoked is True

        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "LOGOUT",
                AuditLog.actor_id == consultant_user["id"],
            )
        )
        assert audit_res.scalar_one_or_none() is not None

    # Subsequent refresh must fail with 401
    retry_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert retry_res.status_code == 401
    assert retry_res.json()["success"] is False


@pytest.mark.asyncio
async def test_rbac_dependency(app, client: AsyncClient, consultant_user: dict):
    """Verify require_roles dependency grants access to allowed roles and forbids others."""
    from fastapi import Depends
    from app.api.deps import require_roles
    from app.schemas.common import success_envelope

    @app.get("/test-consultant-only")
    async def consultant_route(_=Depends(require_roles("CONSULTANT"))):
        return success_envelope(data={"access": "granted"})

    @app.get("/test-admin-only")
    async def admin_route(_=Depends(require_roles("ADMIN"))):
        return success_envelope(data={"access": "granted"})

    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": consultant_user["email"],
            "password": consultant_user["password"],
        },
    )
    access_token = login_res.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Allowed role: CONSULTANT accessing consultant_route -> 200
    res_ok = await client.get("/test-consultant-only", headers=headers)
    assert res_ok.status_code == 200
    assert res_ok.json()["data"]["access"] == "granted"

    # 2. Forbidden role: CONSULTANT accessing admin_route -> 403
    res_forbidden = await client.get("/test-admin-only", headers=headers)
    assert res_forbidden.status_code == 403
    assert res_forbidden.json()["success"] is False
    assert res_forbidden.json()["error"]["code"] == "FORBIDDEN"
