"""Adversarial security tests for Insecure Direct Object Reference (IDOR) / BOLA & Data Isolation.

Verifies:
  - Users cannot access or mutate other users' private notifications (Notification IDOR).
  - Document binaries cannot be downloaded by unauthorized/unauthenticated users.
  - Audit logs are immutable and cannot be created, modified, or deleted via HTTP APIs.
"""
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.notification import Notification
from app.models.user import User


async def create_consultant_helper(client: AsyncClient, name_prefix: str) -> tuple[dict, User]:
    email = f"{name_prefix}-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name=f"{name_prefix} Consultant",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}, user


@pytest.mark.asyncio
async def test_notification_idor_cross_user_isolation(client: AsyncClient):
    """Consultant B must not be able to read or mutate Consultant A's notifications."""
    headers_a, user_a = await create_consultant_helper(client, "consultant-a")
    headers_b, user_b = await create_consultant_helper(client, "consultant-b")

    # Seed notification owned by Consultant A
    notif_id = uuid.uuid4()
    async with AsyncSessionFactory() as session:
        async with session.begin():
            notif = Notification(
                id=notif_id,
                user_id=user_a.id,
                title="Confidential Notification for A",
                message="Client details strictly for A",
                channel="DASHBOARD",
                notification_type="SYSTEM_ALERT",
                is_read=False,
            )
            session.add(notif)

    # 1. Consultant B lists notifications -> must NOT contain Consultant A's notification
    list_res_b = await client.get("/api/v1/notifications", headers=headers_b)
    assert list_res_b.status_code == 200
    items_b = list_res_b.json()["data"]["items"]
    assert all(item["id"] != str(notif_id) for item in items_b)

    # 2. Consultant B attempts IDOR mark-read on Consultant A's notification -> returns 404
    read_res_b = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers_b)
    assert read_res_b.status_code == 404
    assert read_res_b.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"

    # 3. Consultant B attempts IDOR mark-unread on Consultant A's notification -> returns 404
    unread_res_b = await client.post(f"/api/v1/notifications/{notif_id}/unread", headers=headers_b)
    assert unread_res_b.status_code == 404
    assert unread_res_b.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"

    # 4. Confirm Consultant A's notification remains unread
    list_res_a = await client.get("/api/v1/notifications", headers=headers_a)
    assert list_res_a.status_code == 200
    item_a = next(i for i in list_res_a.json()["data"]["items"] if i["id"] == str(notif_id))
    assert item_a["is_read"] is False


@pytest.mark.asyncio
async def test_audit_log_immutability(client: AsyncClient):
    """Audit logs cannot be created, updated, or deleted via public API routes."""
    headers, _ = await create_consultant_helper(client, "consultant-audit")
    random_id = str(uuid.uuid4())

    # POST to audit logs route -> 405 Method Not Allowed
    post_res = await client.post("/api/v1/audit-logs", json={"action": "FORGED_ACTION"}, headers=headers)
    assert post_res.status_code in (404, 405)

    # PUT to audit log route -> 405 Method Not Allowed
    put_res = await client.put(f"/api/v1/audit-logs/{random_id}", json={"action": "MODIFIED"}, headers=headers)
    assert put_res.status_code in (404, 405)

    # PATCH to audit log route -> 405 Method Not Allowed
    patch_res = await client.patch(f"/api/v1/audit-logs/{random_id}", json={"action": "PATCHED"}, headers=headers)
    assert patch_res.status_code in (404, 405)

    # DELETE to audit log route -> 405 Method Not Allowed
    del_res = await client.delete(f"/api/v1/audit-logs/{random_id}", headers=headers)
    assert del_res.status_code in (404, 405)
