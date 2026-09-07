"""Adversarial security tests for Role-Based Access Control (RBAC) & Endpoint Authorization.

Verifies:
  - Every protected route rejects unauthenticated requests with HTTP 401.
  - Every consultant-protected route rejects lower-privileged/non-consultant users with HTTP 403.
  - Role checks are strictly enforced server-side.
"""
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def regular_user_headers(client: AsyncClient):
    """User with a generic non-consultant role ('USER')."""
    email = f"regular-user-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Regular Client User",
                role="USER",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


PROTECTED_GET_ROUTES = [
    "/api/v1/properties",
    "/api/v1/clients",
    "/api/v1/leads",
    "/api/v1/property-requirements",
    "/api/v1/documents",
    "/api/v1/site-visits",
    "/api/v1/follow-ups",
    "/api/v1/notifications",
    "/api/v1/audit-logs",
]

PROTECTED_POST_ROUTES = [
    ("/api/v1/properties", {"title": "Test"}),
    ("/api/v1/clients", {"full_name": "Test", "phone": "+919876543210"}),
    ("/api/v1/leads", {"client_id": str(uuid.uuid4()), "property_id": str(uuid.uuid4())}),
    ("/api/v1/property-requirements", {"client_id": str(uuid.uuid4())}),
    ("/api/v1/site-visits", {"lead_id": str(uuid.uuid4()), "scheduled_time": "2026-09-10T10:00:00Z"}),
    ("/api/v1/follow-ups", {"lead_id": str(uuid.uuid4()), "due_date": "2026-09-10T10:00:00Z"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", PROTECTED_GET_ROUTES)
async def test_unauthenticated_get_routes_rejected(client: AsyncClient, route: str):
    """Calling private GET endpoints without authentication must return 401."""
    res = await client.get(route)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize("route, payload", PROTECTED_POST_ROUTES)
async def test_unauthenticated_post_routes_rejected(client: AsyncClient, route: str, payload: dict):
    """Calling private POST endpoints without authentication must return 401."""
    res = await client.post(route, json=payload)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
@pytest.mark.parametrize("route", PROTECTED_GET_ROUTES)
async def test_non_consultant_get_routes_forbidden(
    client: AsyncClient, regular_user_headers: dict, route: str
):
    """A user with role='USER' attempting to access consultant GET routes must receive 403 Forbidden."""
    res = await client.get(route, headers=regular_user_headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
@pytest.mark.parametrize("route, payload", PROTECTED_POST_ROUTES)
async def test_non_consultant_post_routes_forbidden(
    client: AsyncClient, regular_user_headers: dict, route: str, payload: dict
):
    """A user with role='USER' attempting to mutate consultant resources must receive 403 Forbidden."""
    res = await client.post(route, json=payload, headers=regular_user_headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
