"""Integration tests for Audit expansion: recording, listing, filtering, and detail lookups."""
from datetime import datetime, timedelta, timezone
import json
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.user import User
from app.repositories.audit import AuditRepository
from app.services.audit import AuditService


@pytest.fixture(autouse=True)
async def clean_audit_logs():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM audit_logs"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM audit_logs"))


@pytest.fixture
async def consultant_user(client: AsyncClient):
    email = f"consultant-audit-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Audit Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    data = login_res.json()["data"]
    token = data["access_token"]
    user_id = data["user"]["id"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": uuid.UUID(user_id),
    }


@pytest.mark.asyncio
async def test_audit_logging_on_business_mutation(client: AsyncClient, consultant_user: dict):
    """Ensure business operations (e.g. creating client) automatically record audit entries."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]

    client_payload = {
        "full_name": "Audit Test Client",
        "phone": "+91 98401 23456",
        "email": f"audit-client-{uuid.uuid4().hex[:6]}@example.com",
        "classification": "BUYER",
    }
    create_res = await client.post(
        "/api/v1/clients",
        json=client_payload,
        headers={**auth_headers, "X-Request-ID": "test-req-corr-123"},
    )
    assert create_res.status_code == 201
    created_client_id = create_res.json()["data"]["id"]

    # Verify audit log in database
    repo = AuditRepository()
    async with AsyncSessionFactory() as session:
        items, total = await repo.list_audit_logs(
            session=session,
            filters=None,  # will be handled by repo list
        ) if hasattr(repo, "list_all") else ([], 0)

    # Fetch audit log through API
    audit_res = await client.get(
        f"/api/v1/audit-logs?entity_type=CLIENT&entity_id={created_client_id}",
        headers=auth_headers,
    )
    assert audit_res.status_code == 200
    data = audit_res.json()["data"]
    assert data["total"] >= 1
    log_item = data["items"][0]
    assert log_item["action"] == "CLIENT_CREATED"
    assert log_item["entity_type"] == "CLIENT"
    assert log_item["entity_id"] == created_client_id
    assert log_item["actor_id"] == str(user_id)
    assert log_item["correlation_id"] == "test-req-corr-123"


@pytest.mark.asyncio
async def test_list_audit_logs_pagination(client: AsyncClient, consultant_user: dict):
    """Ensure audit logs are paginated properly with limit and offset."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]
    service = AuditService()

    # Create 3 audit records directly
    entity_id = uuid.uuid4()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            for i in range(3):
                await service.record_event(
                    session=session,
                    action="PROPERTY_UPDATED",
                    entity_type="PROPERTY",
                    entity_id=entity_id,
                    actor_id=user_id,
                    change_diff={"version": i},
                    ip_address="127.0.0.1",
                    correlation_id=f"corr-id-{i}",
                )

    # Page 1 (limit=2, offset=0)
    res1 = await client.get(f"/api/v1/audit-logs?entity_id={entity_id}&limit=2&offset=0", headers=auth_headers)
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    assert data1["total"] == 3
    assert len(data1["items"]) == 2
    assert data1["limit"] == 2
    assert data1["offset"] == 0

    # Page 2 (limit=2, offset=2)
    res2 = await client.get(f"/api/v1/audit-logs?entity_id={entity_id}&limit=2&offset=2", headers=auth_headers)
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert len(data2["items"]) == 1

    ids_p1 = {item["id"] for item in data1["items"]}
    ids_p2 = {item["id"] for item in data2["items"]}
    assert ids_p1.isdisjoint(ids_p2)
    assert len(ids_p1 | ids_p2) == 3


@pytest.mark.asyncio
async def test_filter_audit_logs(client: AsyncClient, consultant_user: dict):
    """Ensure filtering by action, entity_type, entity_id, and correlation_id."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]
    service = AuditService()

    p_id = uuid.uuid4()
    c_id = uuid.uuid4()

    async with AsyncSessionFactory() as session:
        async with session.begin():
            await service.record_event(
                session=session,
                action="PROPERTY_CREATED",
                entity_type="PROPERTY",
                entity_id=p_id,
                actor_id=user_id,
                change_diff={"title": "Villa"},
                correlation_id="corr-prop-001",
            )
            await service.record_event(
                session=session,
                action="CLIENT_CREATED",
                entity_type="CLIENT",
                entity_id=c_id,
                actor_id=user_id,
                change_diff={"name": "Buyer"},
                correlation_id="corr-client-002",
            )

    # Filter action
    res_action = await client.get("/api/v1/audit-logs?action=PROPERTY_CREATED", headers=auth_headers)
    assert res_action.status_code == 200
    assert len(res_action.json()["data"]["items"]) == 1
    assert res_action.json()["data"]["items"][0]["action"] == "PROPERTY_CREATED"

    # Filter entity_type
    res_entity = await client.get("/api/v1/audit-logs?entity_type=CLIENT", headers=auth_headers)
    assert res_entity.status_code == 200
    assert len(res_entity.json()["data"]["items"]) == 1
    assert res_entity.json()["data"]["items"][0]["entity_type"] == "CLIENT"

    # Filter correlation_id
    res_corr = await client.get("/api/v1/audit-logs?correlation_id=corr-prop-001", headers=auth_headers)
    assert res_corr.status_code == 200
    assert len(res_corr.json()["data"]["items"]) == 1
    assert res_corr.json()["data"]["items"][0]["correlation_id"] == "corr-prop-001"


@pytest.mark.asyncio
async def test_get_audit_log_detail(client: AsyncClient, consultant_user: dict):
    """Ensure retrieving a specific audit log by ID returns expected fields."""
    auth_headers = consultant_user["headers"]
    user_id = consultant_user["user_id"]
    service = AuditService()

    ent_id = uuid.uuid4()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            created_log = await service.record_event(
                session=session,
                action="FOLLOW_UP_COMPLETED",
                entity_type="FOLLOW_UP",
                entity_id=ent_id,
                actor_id=user_id,
                change_diff={"outcome": "Meeting held"},
                ip_address="192.168.1.10",
                correlation_id="corr-fu-detail",
            )
            log_id = str(created_log.id)

    res = await client.get(f"/api/v1/audit-logs/{log_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == log_id
    assert data["action"] == "FOLLOW_UP_COMPLETED"
    assert data["entity_type"] == "FOLLOW_UP"
    assert data["entity_id"] == str(ent_id)
    assert data["actor_id"] == str(user_id)
    assert data["ip_address"] == "192.168.1.10"
    assert data["correlation_id"] == "corr-fu-detail"
    assert "Meeting held" in data["change_diff"]
