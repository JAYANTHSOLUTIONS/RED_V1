"""Tests for Phase 17 Production Configuration Hardening.

Validates fail-fast secret verification, debug rejection, wildcard CORS rejection,
storage and SMTP validations in production mode.
"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_weak_jwt_secret():
    """Production mode must reject known insecure default secret keys."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            JWT_SECRET_KEY="test-only-secret-key-not-for-production-use",
            DEBUG=False,
        )
    errors = str(exc_info.value)
    assert "known default/insecure secret" in errors


def test_production_rejects_short_jwt_secret():
    """Production mode must reject JWT secrets shorter than 32 characters."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            JWT_SECRET_KEY="short-secret-key-12345",
            DEBUG=False,
        )
    errors = str(exc_info.value)
    assert "at least 32 characters long" in errors


def test_production_rejects_debug_mode():
    """Production mode must strictly reject DEBUG=True."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            JWT_SECRET_KEY="a-very-strong-and-sufficiently-long-production-secret-key-32chars!",
            DEBUG=True,
        )
    errors = str(exc_info.value)
    assert "DEBUG mode must be False in production" in errors


def test_production_rejects_cors_wildcard():
    """Production mode must reject wildcard '*' in CORS_ALLOWED_ORIGINS."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            JWT_SECRET_KEY="a-very-strong-and-sufficiently-long-production-secret-key-32chars!",
            DEBUG=False,
            CORS_ALLOWED_ORIGINS="*",
        )
    errors = str(exc_info.value)
    assert "must not contain wildcard '*'" in errors


def test_production_rejects_s3_missing_credentials():
    """Production mode must reject S3 storage backend if credentials/bucket are missing."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            JWT_SECRET_KEY="a-very-strong-and-sufficiently-long-production-secret-key-32chars!",
            DEBUG=False,
            STORAGE_BACKEND="s3",
            STORAGE_BUCKET="",
        )
    errors = str(exc_info.value)
    assert "S3 storage backend requires STORAGE_BUCKET" in errors


def test_production_rejects_invalid_smtp_config():
    """Production mode must reject invalid SMTP port or from address."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
            JWT_SECRET_KEY="a-very-strong-and-sufficiently-long-production-secret-key-32chars!",
            DEBUG=False,
            SMTP_HOST="smtp.mailgun.org",
            SMTP_PORT=999999,  # invalid port
        )
    errors = str(exc_info.value)
    assert "Invalid SMTP_PORT" in errors


def test_production_accepts_valid_configuration():
    """Production mode accepts valid strong secret, specific CORS, and non-debug settings."""
    settings = Settings(
        APP_ENV="production",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/prod_db",
        JWT_SECRET_KEY="a-very-strong-and-sufficiently-long-production-secret-key-32chars!",
        DEBUG=False,
        CORS_ALLOWED_ORIGINS="https://red.jayanthsolutions.com,https://admin.jayanthsolutions.com",
    )
    assert settings.is_production is True
    assert len(settings.CORS_ALLOWED_ORIGINS) == 2
    assert "https://red.jayanthsolutions.com" in settings.CORS_ALLOWED_ORIGINS


def test_non_production_allows_test_credentials():
    """Local and test environments should allow test credentials without failing."""
    settings = Settings(
        APP_ENV="local",
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test_db",
        JWT_SECRET_KEY="test-only-secret-key-not-for-production-use",
        DEBUG=True,
        CORS_ALLOWED_ORIGINS="*",
    )
    assert settings.is_production is False
    assert settings.DEBUG is True
