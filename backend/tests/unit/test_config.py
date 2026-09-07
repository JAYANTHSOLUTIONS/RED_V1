"""Configuration validation tests.

These instantiate `Settings` directly (bypassing the process-wide
`get_settings()` cache) so each test controls its own environment.
"""
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)

    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.APP_ENV == "local"


def test_settings_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_requires_jwt_secret_key(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_rejects_unknown_app_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("APP_ENV", "production-typo")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_cors_origins_parsed_from_comma_separated_string(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://a.com, https://b.com")

    settings = Settings(_env_file=None)

    assert settings.CORS_ALLOWED_ORIGINS == ["https://a.com", "https://b.com"]


def test_cors_origins_default_to_empty_not_wildcard(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.CORS_ALLOWED_ORIGINS == []
    assert "*" not in settings.CORS_ALLOWED_ORIGINS


def test_is_production_property(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 32)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")

    settings = Settings(_env_file=None)

    assert settings.is_production is True
