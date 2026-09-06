"""Security primitives for the future authentication module.

This phase provides only the low-level, stateless primitives:
  - Argon2id password hashing/verification (RFC 9106)
  - JWT access-token creation/decoding

No routes, dependencies, or login/refresh flows are wired up yet — the
Auth phase will build session management, refresh-token rotation, and
revocation on top of these primitives, per the master specification.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

# argon2-cffi's defaults already follow current OWASP/RFC 9106 guidance;
# overridden here only if the client's infra requires different tuning.
_password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash.

    Returns False on mismatch rather than raising, so callers can use a
    simple boolean check.
    """
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(subject: str, extra_claims: Optional[dict[str, Any]] = None) -> str:
    """Create a short-lived JWT access token for `subject` (a user UUID)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT, raising jwt.PyJWTError on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def generate_refresh_token() -> str:
    """Generate a cryptographically secure 256-bit opaque refresh token."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(raw_token: str) -> str:
    """Compute the SHA-256 hash of a raw refresh token for safe storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
