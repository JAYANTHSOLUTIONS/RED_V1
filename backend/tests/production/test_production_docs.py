"""Tests for OpenAPI docs exposure controls in production.

Verifies that /docs, /redoc, and /openapi.json are disabled in production by default,
and can be selectively enabled via OPENAPI_DOCS_ENABLED.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import create_app


@pytest.mark.asyncio
async def test_docs_disabled_in_production(monkeypatch):
    """By default in production, /docs, /redoc, and /openapi.json must return 404."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "super-secure-production-jwt-secret-key-that-is-at-least-32-chars-long!",
    )
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.delenv("OPENAPI_DOCS_ENABLED", raising=False)
    get_settings.cache_clear()

    prod_app = create_app()
    transport = ASGITransport(app=prod_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_docs = await client.get("/docs")
        assert r_docs.status_code == 404

        r_redoc = await client.get("/redoc")
        assert r_redoc.status_code == 404

        r_openapi = await client.get("/openapi.json")
        assert r_openapi.status_code == 404

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_docs_enabled_in_production_when_explicitly_configured(monkeypatch):
    """If OPENAPI_DOCS_ENABLED=True, docs should be accessible even in production."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "super-secure-production-jwt-secret-key-that-is-at-least-32-chars-long!",
    )
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("OPENAPI_DOCS_ENABLED", "true")
    get_settings.cache_clear()

    prod_app = create_app()
    transport = ASGITransport(app=prod_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_docs = await client.get("/docs")
        assert r_docs.status_code == 200

        r_openapi = await client.get("/openapi.json")
        assert r_openapi.status_code == 200

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_docs_enabled_by_default_in_non_production(monkeypatch):
    """In development/local mode, docs should be enabled by default."""
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.delenv("OPENAPI_DOCS_ENABLED", raising=False)
    get_settings.cache_clear()

    local_app = create_app()
    transport = ASGITransport(app=local_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r_docs = await client.get("/docs")
        assert r_docs.status_code == 200

        r_openapi = await client.get("/openapi.json")
        assert r_openapi.status_code == 200

    get_settings.cache_clear()
