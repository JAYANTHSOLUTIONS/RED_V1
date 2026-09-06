"""Integration tests for /api/v1/health/*.

Readiness tests fake the database session via FastAPI dependency
overrides rather than requiring a real PostgreSQL instance, so this suite
stays fast and deterministic in CI without a live database.
"""
from app.api.deps import get_db


async def test_liveness_returns_success_envelope(client):
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "alive"
    assert "message" in body


async def test_readiness_returns_200_when_database_reachable(app, client):
    class FakeSession:
        async def execute(self, *_args, **_kwargs):
            return None

    async def override_get_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_get_db

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["database"] == "ok"

    app.dependency_overrides.clear()


async def test_readiness_returns_503_when_database_unreachable(app, client):
    class FailingSession:
        async def execute(self, *_args, **_kwargs):
            raise ConnectionError("database unavailable")

    async def override_get_db():
        yield FailingSession()

    app.dependency_overrides[get_db] = override_get_db

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    # Never leak the underlying driver/connection error.
    assert "ConnectionError" not in response.text
    assert "database unavailable" not in response.text

    app.dependency_overrides.clear()


async def test_readiness_never_exposes_database_url(app, client):
    class FakeSession:
        async def execute(self, *_args, **_kwargs):
            return None

    async def override_get_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_get_db

    response = await client.get("/api/v1/health/ready")

    assert "postgresql" not in response.text
    assert "@localhost" not in response.text

    app.dependency_overrides.clear()
