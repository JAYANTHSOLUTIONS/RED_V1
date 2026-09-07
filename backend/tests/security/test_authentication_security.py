"""Adversarial security tests for Authentication & JWT handling.

Verifies:
  - Missing, malformed, and tampered JWTs are rejected (401).
  - Algorithm confusion attacks (alg: none, mismatched algorithm) are rejected (401).
  - Expired access tokens are rejected (401).
  - Token type confusion (refresh token in Bearer header) is rejected (401).
  - Inactive / disabled users cannot authenticate or refresh tokens (401).
  - Refresh token reuse revokes all user sessions.
  - Login endpoints resist user enumeration by returning identical 401 envelopes.
"""
from datetime import datetime, timedelta, timezone
import uuid
import jwt
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def sample_user():
    email = f"auth-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Auth Security User",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    return {"email": email, "password": password, "id": user.id}


@pytest.fixture
async def inactive_user():
    email = f"inactive-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Inactive User",
                role="CONSULTANT",
                is_active=False,
            )
            session.add(user)

    return {"email": email, "password": password, "id": user.id}


@pytest.mark.asyncio
async def test_missing_auth_header_rejected(client: AsyncClient):
    """Calling protected endpoint without Authorization header must return 401."""
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_malformed_token_rejected(client: AsyncClient):
    """Calling protected endpoint with malformed JWT must return 401."""
    headers = {"Authorization": "Bearer not-a-valid-jwt-token"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_tampered_token_signature_rejected(client: AsyncClient, sample_user):
    """Altering token payload/signature must trigger signature mismatch and return 401."""
    token = create_access_token(str(sample_user["id"]))
    # Corrupt the signature part
    tampered = token[:-5] + "XXXXX"
    headers = {"Authorization": f"Bearer {tampered}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_algorithm_confusion_alg_none(client: AsyncClient, sample_user):
    """Token forged with alg='none' must be rejected (401)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sample_user["id"]),
        "iat": now.timestamp(),
        "exp": (now + timedelta(minutes=20)).timestamp(),
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    # Forge token without signature using alg=none
    forged_token = jwt.encode(payload, key="", algorithm="none")
    headers = {"Authorization": f"Bearer {forged_token}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_algorithm_confusion_mismatched_alg(client: AsyncClient, sample_user):
    """Token signed with an algorithm different from JWT_ALGORITHM (e.g. HS384) must be rejected."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sample_user["id"]),
        "iat": now.timestamp(),
        "exp": (now + timedelta(minutes=20)).timestamp(),
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    # Encode with HS384 instead of HS256
    mismatched_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS384")
    headers = {"Authorization": f"Bearer {mismatched_token}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_expired_access_token_rejected(client: AsyncClient, sample_user):
    """Expired access token must be rejected (401)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sample_user["id"]),
        "iat": (now - timedelta(hours=2)).timestamp(),
        "exp": (now - timedelta(hours=1)).timestamp(),
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {expired_token}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_token_type_confusion_rejected(client: AsyncClient, sample_user):
    """A JWT with type='refresh' used in Bearer header must be rejected."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sample_user["id"]),
        "iat": now.timestamp(),
        "exp": (now + timedelta(days=14)).timestamp(),
        "jti": uuid.uuid4().hex,
        "type": "refresh",  # Not "access"
    }
    refresh_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {refresh_jwt}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_token_missing_subject_rejected(client: AsyncClient):
    """Token missing 'sub' claim must be rejected."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "iat": now.timestamp(),
        "exp": (now + timedelta(minutes=20)).timestamp(),
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_token_invalid_uuid_subject_rejected(client: AsyncClient):
    """Token with non-UUID 'sub' claim must be rejected."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "admin-super-user-not-a-uuid",
        "iat": now.timestamp(),
        "exp": (now + timedelta(minutes=20)).timestamp(),
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_inactive_user_token_rejected(client: AsyncClient, inactive_user):
    """A valid token for a deactivated user must be rejected immediately (401)."""
    token = create_access_token(str(inactive_user["id"]))
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(client: AsyncClient, inactive_user):
    """An inactive user attempting to login must be rejected with 401."""
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": inactive_user["email"], "password": inactive_user["password"]},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_user_enumeration_resistance(client: AsyncClient, sample_user):
    """Login failures for non-existent user vs wrong password must return identical error responses."""
    # 1. Non-existent email
    res_nonexistent = await client.post(
        "/api/v1/auth/login",
        json={"email": f"nosuchuser-{uuid.uuid4().hex[:8]}@example.com", "password": "WrongPassword!"},
    )
    # 2. Existing email with wrong password
    res_wrong_pw = await client.post(
        "/api/v1/auth/login",
        json={"email": sample_user["email"], "password": "DefinitelyWrongPassword123!"},
    )

    assert res_nonexistent.status_code == 401
    assert res_wrong_pw.status_code == 401
    assert res_nonexistent.json() == res_wrong_pw.json()
    assert res_nonexistent.json()["error"]["message"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_refresh_token_reuse_detection(client: AsyncClient, sample_user):
    """Reusing an already rotated refresh token must trigger reuse detection and revoke sessions."""
    # 1. Login to get initial tokens
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": sample_user["email"], "password": sample_user["password"]},
    )
    assert login_res.status_code == 200
    token_1 = login_res.json()["data"]["refresh_token"]

    # 2. Rotate token 1 -> receive token 2
    refresh_res_1 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_1},
    )
    assert refresh_res_1.status_code == 200
    token_2 = refresh_res_1.json()["data"]["refresh_token"]
    assert token_2 != token_1

    # 3. Adversary attempts to re-use token 1 (replay attack)
    replay_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_1},
    )
    assert replay_res.status_code == 401

    # 4. As a result of reuse detection, even token 2 should now be revoked
    refresh_res_2 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": token_2},
    )
    assert refresh_res_2.status_code == 401
