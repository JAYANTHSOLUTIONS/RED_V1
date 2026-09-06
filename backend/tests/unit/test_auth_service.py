"""Unit tests for AuthService and auth schemas / utilities."""
import uuid
from datetime import datetime, timezone
import pytest

from app.core.exceptions import AuthorizationError
from app.core.security import (
    create_access_token,
    decode_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse, UserResponse


def test_jti_is_unique_per_access_token():
    """Verify each generated access token receives a unique jti UUID."""
    user_id = str(uuid.uuid4())
    token1 = create_access_token(subject=user_id)
    token2 = create_access_token(subject=user_id)

    payload1 = decode_token(token1)
    payload2 = decode_token(token2)

    assert payload1["jti"] != payload2["jti"]
    assert payload1["sub"] == user_id
    assert payload2["sub"] == user_id


def test_refresh_token_entropy_and_hashing():
    """Verify refresh token generation produces high entropy and SHA-256 digests."""
    tokens = {generate_refresh_token() for _ in range(50)}
    assert len(tokens) == 50
    for tok in tokens:
        assert len(tok) >= 43
        digest = hash_refresh_token(tok)
        assert len(digest) == 64
        # Hash is deterministic
        assert hash_refresh_token(tok) == digest


def test_argon2_password_hashing():
    """Verify password hashing with Argon2id and verification."""
    pw = "MyComplexPassword#2026"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword#2026", hashed) is False


def test_user_response_excludes_password_hash():
    """Verify UserResponse schema never includes sensitive password hashes."""
    user = User(
        id=uuid.uuid4(),
        email="consultant@example.com",
        hashed_password="$argon2id$v=19$m=65536,t=3,p=4$somehashvalue",
        full_name="Jane Doe",
        phone="+919876543210",
        role="CONSULTANT",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    user_resp = UserResponse.model_validate(user)
    dumped = user_resp.model_dump()

    assert "hashed_password" not in dumped
    assert dumped["email"] == "consultant@example.com"
    assert dumped["role"] == "CONSULTANT"
    assert dumped["is_active"] is True


def test_token_response_structure():
    """Verify TokenResponse schema output contract."""
    resp = TokenResponse(
        access_token="fake.access.token",
        refresh_token="fake_refresh_token",
        token_type="bearer",
        expires_in=1200,
    )
    data = resp.model_dump()
    assert data["access_token"] == "fake.access.token"
    assert data["refresh_token"] == "fake_refresh_token"
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 1200
    assert data["user"] is None


@pytest.mark.asyncio
async def test_require_roles_case_insensitivity():
    """Verify require_roles handles case-insensitivity correctly."""
    from app.api.deps import require_roles

    consultant_user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hash",
        full_name="Test User",
        role="consultant",
        is_active=True,
    )

    checker = require_roles("CONSULTANT")
    result = await checker(current_user=consultant_user)
    assert result.id == consultant_user.id

    admin_checker = require_roles("ADMIN")
    with pytest.raises(AuthorizationError):
        await admin_checker(current_user=consultant_user)
