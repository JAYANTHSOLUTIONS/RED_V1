"""Security and failure tests for Authentication and Authorization.

Covers:
  - User enumeration resistance (generic error responses)
  - Invalid password attempts & audit logging
  - Inactive user rejection
  - Missing, invalid, expired, and tampered JWT access tokens
  - Opaque refresh token reuse detection & defensive user-wide session revocation
  - Expired and nonexistent refresh token rejection
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
import jwt
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, hash_refresh_token
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.user import RefreshToken, User

settings = get_settings()


@pytest.fixture
async def sample_user():
    """Create a standard active consultant user."""
    unique_id = uuid.uuid4().hex[:8]
    email = f"user-{unique_id}@example.com"
    password = "CorrectPassword123!"
    hashed_pw = hash_password(password)

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hashed_pw,
                full_name="Standard User",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)
            await session.flush()
            user_id = user.id

    return {"id": user_id, "email": email, "password": password}


@pytest.fixture
async def inactive_user():
    """Create a disabled consultant user."""
    unique_id = uuid.uuid4().hex[:8]
    email = f"inactive-{unique_id}@example.com"
    password = "CorrectPassword123!"
    hashed_pw = hash_password(password)

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hashed_pw,
                full_name="Inactive User",
                role="CONSULTANT",
                is_active=False,
            )
            session.add(user)
            await session.flush()
            user_id = user.id

    return {"id": user_id, "email": email, "password": password}


@pytest.mark.asyncio
async def test_login_unknown_email_prevents_enumeration(client: AsyncClient):
    """Unknown email returns 401 with generic error message and logs security event."""
    fake_email = f"nonexistent-{uuid.uuid4().hex[:8]}@example.com"
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": fake_email,
            "password": "AnyPassword123!",
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Invalid email or password."

    # Verify audit log was committed despite failure
    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "LOGIN_FAILURE",
                AuditLog.change_diff.contains(fake_email),
            )
        )
        assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_login_wrong_password_returns_generic_message(
    client: AsyncClient, sample_user: dict
):
    """Wrong password returns identical 401 error message as unknown user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": sample_user["email"],
            "password": "WrongPassword999!",
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Invalid email or password."

    # Verify audit log was recorded with user ID
    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "LOGIN_FAILURE",
                AuditLog.actor_id == sample_user["id"],
            )
        )
        assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(client: AsyncClient, inactive_user: dict):
    """Inactive user cannot log in."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": inactive_user["email"],
            "password": inactive_user["password"],
        },
    )

    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert "inactive or disabled" in body["error"]["message"].lower()


@pytest.mark.asyncio
async def test_me_rejects_missing_or_malformed_auth(client: AsyncClient):
    """GET /me requires Bearer token."""
    # 1. Missing header
    res1 = await client.get("/api/v1/auth/me")
    assert res1.status_code == 401

    # 2. Not Bearer scheme
    res2 = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"}
    )
    assert res2.status_code == 401

    # 3. Malformed token string
    res3 = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt"}
    )
    assert res3.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_expired_access_token(client: AsyncClient, sample_user: dict):
    """Expired access token cannot access /me."""
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(sample_user["id"]),
        "type": "access",
        "role": "CONSULTANT",
        "jti": str(uuid.uuid4()),
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(
        expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_me_rejects_tampered_signature(client: AsyncClient, sample_user: dict):
    """Token signed with wrong key is rejected."""
    wrong_key_token = jwt.encode(
        {
            "sub": str(sample_user["id"]),
            "type": "access",
            "role": "CONSULTANT",
            "jti": str(uuid.uuid4()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
        },
        "attacker-secret-key-different-from-server",
        algorithm="HS256",
    )

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {wrong_key_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_reuse_triggers_blanket_revocation(
    client: AsyncClient, sample_user: dict
):
    """Attacker attempting to use an already-revoked refresh token causes all user tokens to be revoked."""
    # 1. First login (creates session 1)
    res1 = await client.post(
        "/api/v1/auth/login",
        json={"email": sample_user["email"], "password": sample_user["password"]},
    )
    token1 = res1.json()["data"]["refresh_token"]

    # 2. Second login (creates session 2)
    res2 = await client.post(
        "/api/v1/auth/login",
        json={"email": sample_user["email"], "password": sample_user["password"]},
    )
    token2 = res2.json()["data"]["refresh_token"]
    hash2 = hash_refresh_token(token2)

    # 3. Legitimate rotation of session 1
    rotate_res = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token1}
    )
    assert rotate_res.status_code == 200

    # 4. Attacker attempts to reuse token 1 (which was revoked during rotation)
    reuse_res = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token1}
    )
    assert reuse_res.status_code == 401

    # 5. Verify security defense: session 2 (token2) was also revoked because reuse was detected!
    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash2)
        )
        token2_record = res.scalar_one_or_none()
        assert token2_record is not None
        assert token2_record.revoked is True

        # Audit log for reuse detection exists
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "REFRESH_TOKEN_REUSE_DETECTED",
                AuditLog.actor_id == sample_user["id"],
            )
        )
        assert audit_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_refresh_expired_token(client: AsyncClient, sample_user: dict):
    """Expired refresh token is rejected and revoked in DB."""
    past_date = datetime.now(timezone.utc) - timedelta(days=1)
    token_str = "expired-test-refresh-token-" + uuid.uuid4().hex
    token_hash = hash_refresh_token(token_str)

    async with AsyncSessionFactory() as session:
        async with session.begin():
            rf = RefreshToken(
                user_id=sample_user["id"],
                token_hash=token_hash,
                expires_at=past_date,
                revoked=False,
            )
            session.add(rf)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_str},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["error"]["message"].lower()

    # Verify it is marked revoked in DB
    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        rf_rec = res.scalar_one_or_none()
        assert rf_rec is not None
        assert rf_rec.revoked is True


@pytest.mark.asyncio
async def test_refresh_nonexistent_token(client: AsyncClient):
    """Attempting to refresh with an unknown token returns 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "definitely-not-a-real-refresh-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_refresh_with_inactive_user(client: AsyncClient, inactive_user: dict):
    """Refreshing a token for a disabled/inactive user is rejected and revokes the token."""
    now = datetime.now(timezone.utc)
    token_str = "inactive-user-refresh-token-" + uuid.uuid4().hex
    token_hash = hash_refresh_token(token_str)

    async with AsyncSessionFactory() as session:
        async with session.begin():
            rf = RefreshToken(
                user_id=inactive_user["id"],
                token_hash=token_hash,
                expires_at=now + timedelta(days=7),
                revoked=False,
            )
            session.add(rf)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_str},
    )
    assert response.status_code == 401
    assert "inactive" in response.json()["error"]["message"].lower()

    # Verify token revoked
    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        rf_rec = res.scalar_one_or_none()
        assert rf_rec is not None
        assert rf_rec.revoked is True
