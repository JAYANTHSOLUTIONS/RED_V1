"""Tests for database failure modes and session resilience."""
from unittest.mock import patch, MagicMock
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError, TimeoutError
from sqlalchemy import text

from app.api.deps import get_db
from app.core.exceptions import ServiceUnavailableError
from app.db.session import transaction, AsyncSessionFactory, get_db as real_get_db


async def test_database_connection_failure_maps_to_503(client: AsyncClient):
    """When database connection cannot be acquired, get_db translates it to 503 Service Unavailable."""
    with patch("app.db.session.AsyncSessionFactory") as mock_factory:
        mock_factory.side_effect = OperationalError("connection refused", params=None, orig=Exception("Connection refused"))
        
        response = await client.get("/api/v1/properties")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "connection refused" not in response.text
        assert "postgresql" not in response.text


async def test_database_pool_timeout_maps_to_503(client: AsyncClient):
    """When database pool is exhausted and times out, get_db translates it to 503 Service Unavailable."""
    with patch("app.db.session.AsyncSessionFactory") as mock_factory:
        mock_factory.side_effect = TimeoutError("QueuePool limit of size 20 overflow 10 reached, connection timed out")

        response = await client.get("/api/v1/properties")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "QueuePool" not in response.text


async def test_transaction_context_manager_catches_operational_error():
    """Verify transaction() translates OperationalError during commit into ServiceUnavailableError."""
    class MockFailingSession:
        async def commit(self):
            raise OperationalError("db dropped", params=None, orig=Exception("connection reset"))

        async def rollback(self):
            pass

    with pytest.raises(ServiceUnavailableError) as exc_info:
        async with transaction(MockFailingSession()):
            pass

    assert exc_info.value.code == "SERVICE_UNAVAILABLE"
    assert exc_info.value.status_code == 503


async def test_transaction_context_manager_rolls_back_on_error():
    """Verify transaction() executes rollback when an error occurs inside block."""
    rolled_back = False

    class MockSessionWithRollback:
        async def commit(self):
            pass

        async def rollback(self):
            nonlocal rolled_back
            rolled_back = True

    with pytest.raises(ValueError, match="simulated failure"):
        async with transaction(MockSessionWithRollback()):
            raise ValueError("simulated failure")

    assert rolled_back is True


async def test_database_healthy_query():
    """Verify database is reachable via AsyncSessionFactory and executes simple query."""
    async with AsyncSessionFactory() as session:
        result = await session.execute(text("SELECT 1 AS alive"))
        row = result.scalar()
        assert row == 1
