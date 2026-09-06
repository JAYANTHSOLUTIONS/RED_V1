"""Tests for the security primitives prepared for the future Auth phase.

Nothing here exercises an actual login/refresh flow — that is out of
scope until the Auth module is implemented.
"""
import jwt
import pytest

from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_and_verify_roundtrip():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed) is True


def test_password_verify_rejects_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("a-completely-different-password", hashed) is False


def test_password_hash_uses_argon2id():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed.startswith("$argon2id$")


def test_access_token_roundtrip():
    token = create_access_token(subject="00000000-0000-0000-0000-000000000000")
    payload = decode_token(token)

    assert payload["sub"] == "00000000-0000-0000-0000-000000000000"
    assert payload["type"] == "access"


def test_access_token_rejects_tampering():
    token = create_access_token(subject="00000000-0000-0000-0000-000000000000")
    header, payload, signature = token.split(".")
    tampered_sig = ("X" if signature[0] != "X" else "Y") + signature[1:]
    tampered = f"{header}.{payload}.{tampered_sig}"

    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered)


def test_access_token_carries_extra_claims():
    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000000",
        extra_claims={"role": "owner"},
    )
    payload = decode_token(token)
    assert payload["role"] == "owner"
    assert "jti" in payload


def test_refresh_token_generation_and_hashing():
    from app.core.security import generate_refresh_token, hash_refresh_token

    raw_token_1 = generate_refresh_token()
    raw_token_2 = generate_refresh_token()

    assert raw_token_1 != raw_token_2
    assert len(raw_token_1) >= 40

    hash_1 = hash_refresh_token(raw_token_1)
    hash_2 = hash_refresh_token(raw_token_2)

    assert len(hash_1) == 64  # SHA-256 hex digest
    assert hash_1 != hash_2
    # Deterministic hashing
    assert hash_refresh_token(raw_token_1) == hash_1
