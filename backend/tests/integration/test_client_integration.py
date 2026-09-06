"""Integration tests for Client Management API endpoints."""
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.user import User


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-client-test-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Client Test Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_and_get_client(client: AsyncClient, auth_headers: dict):
    payload = {
        "full_name": "Arun Prakash",
        "phone": "+91 9840123456",
        "email": "arun.prakash@example.com",
        "preferred_contact_method": "CALL",
        "classification": "BUYER",
        "notes": "Looking for residential land",
    }
    create_res = await client.post("/api/v1/clients", json=payload, headers=auth_headers)
    assert create_res.status_code == 201
    body = create_res.json()
    assert body["success"] is True
    client_data = body["data"]
    client_id = client_data["id"]
    assert client_data["full_name"] == "Arun Prakash"
    assert client_data["phone"] == "+91 9840123456"
    assert client_data["classification"] == "BUYER"
    assert client_data["is_archived"] is False

    # Get client detail
    get_res = await client.get(f"/api/v1/clients/{client_id}", headers=auth_headers)
    assert get_res.status_code == 200
    get_body = get_res.json()
    assert get_body["data"]["id"] == client_id
    assert "leads" in get_body["data"]
    assert len(get_body["data"]["leads"]) == 0

    # Verify audit log
    async with AsyncSessionFactory() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(client_id),
                AuditLog.action == "CLIENT_CREATED",
            )
        )
        log = audit_res.scalar_one_or_none()
        assert log is not None
        assert log.entity_type == "CLIENT"


@pytest.mark.asyncio
async def test_duplicate_phone_clients_coexistence(client: AsyncClient, auth_headers: dict):
    """Section 7 requirement: Phone number is not a unique key; do not silently merge clients."""
    phone = "+91 9999900001"
    res1 = await client.post(
        "/api/v1/clients",
        json={"full_name": "Family Member A", "phone": phone},
        headers=auth_headers,
    )
    assert res1.status_code == 201

    res2 = await client.post(
        "/api/v1/clients",
        json={"full_name": "Family Member B", "phone": phone},
        headers=auth_headers,
    )
    assert res2.status_code == 201
    assert res1.json()["data"]["id"] != res2.json()["data"]["id"]


@pytest.mark.asyncio
async def test_update_client(client: AsyncClient, auth_headers: dict):
    create_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Original Name", "phone": "+91 9123456780"},
        headers=auth_headers,
    )
    client_id = create_res.json()["data"]["id"]

    update_res = await client.patch(
        f"/api/v1/clients/{client_id}",
        json={"full_name": "Updated Name", "notes": "Updated note"},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()["data"]
    assert updated_data["full_name"] == "Updated Name"
    assert updated_data["notes"] == "Updated note"

    # Verify audit log
    async with AsyncSessionFactory() as session:
        audit_res = await session.execute(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(client_id),
                AuditLog.action == "CLIENT_UPDATED",
            )
        )
        assert audit_res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_list_and_search_clients(client: AsyncClient, auth_headers: dict):
    suffix = uuid.uuid4().hex[:6]
    await client.post(
        "/api/v1/clients",
        json={
            "full_name": f"Searchable Client {suffix}",
            "phone": f"+91 888{suffix[:4]}",
            "email": f"search_{suffix}@example.com",
            "classification": "INVESTOR",
        },
        headers=auth_headers,
    )

    # Search by name
    list_res = await client.get(f"/api/v1/clients?search=Searchable Client {suffix}", headers=auth_headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]["items"]
    assert len(items) >= 1
    assert any(c["full_name"] == f"Searchable Client {suffix}" for c in items)

    # Filter by classification
    inv_res = await client.get("/api/v1/clients?classification=INVESTOR", headers=auth_headers)
    assert inv_res.status_code == 200
    assert all(c["classification"] == "INVESTOR" for c in inv_res.json()["data"]["items"])


@pytest.mark.asyncio
async def test_archive_client(client: AsyncClient, auth_headers: dict):
    create_res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Client To Archive", "phone": "+91 9777700002"},
        headers=auth_headers,
    )
    client_id = create_res.json()["data"]["id"]

    archive_res = await client.post(f"/api/v1/clients/{client_id}/archive", headers=auth_headers)
    assert archive_res.status_code == 200
    archived_data = archive_res.json()["data"]
    assert archived_data["is_archived"] is True
    assert archived_data["status"] == "ARCHIVED"

    # Idempotent archive
    archive_res_again = await client.post(f"/api/v1/clients/{client_id}/archive", headers=auth_headers)
    assert archive_res_again.status_code == 200
    assert archive_res_again.json()["data"]["is_archived"] is True

    # Default active list excludes archived
    active_list = await client.get("/api/v1/clients?is_archived=false", headers=auth_headers)
    assert not any(c["id"] == client_id for c in active_list.json()["data"]["items"])
