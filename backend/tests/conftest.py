"""Shared pytest fixtures.

Environment variables are set *before* any `app.*` module is imported,
because `Settings` requires `DATABASE_URL` and `JWT_SECRET_KEY` with no
default (fail-fast at boot). These are test-only values — never real
credentials.
"""
import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test_db"
)
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-not-for-production-use")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("DEBUG", "true")

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.rate_limiter import get_login_rate_limiter
from app.db.session import dispose_engine
from app.main import create_app


@pytest.fixture(autouse=True)
async def reset_rate_limiter():
    """Reset the in-memory login rate limiter between tests."""
    await get_login_rate_limiter().reset()
    yield
    await get_login_rate_limiter().reset()


@pytest.fixture(autouse=True)
async def reset_db_engine():
    """Ensure connections in the connection pool are disposed before the test event loop closes."""
    yield
    await dispose_engine()


@pytest.fixture()
def app():
    """A fresh FastAPI app per test, so dependency overrides and
    dynamically-added test routes never leak between tests."""
    return create_app()


@pytest.fixture()
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
