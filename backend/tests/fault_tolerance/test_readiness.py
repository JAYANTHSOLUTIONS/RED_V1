"""Tests for liveness and readiness probe resilience and root endpoints."""
import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from app.api.deps import get_db


async def test_root_liveness_probe_returns_200(client: AsyncClient):
    """GET /health must return 200 alive without database dependency."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "alive"


async def test_root_readiness_probe_returns_200_when_healthy(client: AsyncClient):
    """GET /ready returns 200 when database connection is reachable."""
    response = await client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["database"] == "ok"


async def test_root_readiness_probe_returns_503_on_db_outage(app, client: AsyncClient):
    """GET /ready returns 503 without leaking credentials when database is down."""
    class DroppedDbSession:
        async def execute(self, *args, **kwargs):
            raise OperationalError("Connection refused by host", params=None, orig=Exception("refused"))

    async def override_failing_db():
        yield DroppedDbSession()

    app.dependency_overrides[get_db] = override_failing_db

    response = await client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
    # Never leak internal driver details or passwords
    assert "OperationalError" not in response.text
    assert "postgresql" not in response.text
    assert "refused by host" not in response.text

    app.dependency_overrides.clear()


async def test_root_readiness_probe_returns_503_on_db_timeout(app, client: AsyncClient):
    """GET /ready returns 503 when the database ping hangs beyond timeout."""
    class HangingDbSession:
        async def execute(self, *args, **kwargs):
            await asyncio.sleep(5.0)

    async def override_hanging_db():
        yield HangingDbSession()

    app.dependency_overrides[get_db] = override_hanging_db

    response = await client.get("/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"

    app.dependency_overrides.clear()


async def test_versioned_health_endpoints_remain_backward_compatible(client: AsyncClient):
    """GET /api/v1/health/live and GET /api/v1/health/ready remain active and functional."""
    live_resp = await client.get("/api/v1/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["data"]["status"] == "alive"

    ready_resp = await client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["data"]["database"] == "ok"
