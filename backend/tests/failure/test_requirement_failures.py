"""Failure and boundary tests for Property Requirement Management and Matching."""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-fail-req-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Req Failures Consultant",
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


@pytest.fixture
async def active_client(client: AsyncClient, auth_headers: dict):
    res = await client.post(
        "/api/v1/clients",
        json={
            "full_name": "Active Client For Failures",
            "phone": f"+91 91{uuid.uuid4().int % 100000000:08d}",
            "classification": "BUYER",
        },
        headers=auth_headers,
    )
    return res.json()["data"]


@pytest.mark.asyncio
async def test_nonexistent_requirement_404(client: AsyncClient, auth_headers: dict):
    random_id = uuid.uuid4()

    res_get = await client.get(f"/api/v1/property-requirements/{random_id}", headers=auth_headers)
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "NOT_FOUND"

    res_patch = await client.patch(
        f"/api/v1/property-requirements/{random_id}",
        json={"notes": "Update non-existent"},
        headers=auth_headers,
    )
    assert res_patch.status_code == 404
    assert res_patch.json()["error"]["code"] == "NOT_FOUND"

    res_fulfill = await client.post(
        f"/api/v1/property-requirements/{random_id}/fulfill", headers=auth_headers
    )
    assert res_fulfill.status_code == 404
    assert res_fulfill.json()["error"]["code"] == "NOT_FOUND"

    res_cancel = await client.post(
        f"/api/v1/property-requirements/{random_id}/cancel", headers=auth_headers
    )
    assert res_cancel.status_code == 404
    assert res_cancel.json()["error"]["code"] == "NOT_FOUND"

    res_archive = await client.post(
        f"/api/v1/property-requirements/{random_id}/archive", headers=auth_headers
    )
    assert res_archive.status_code == 404
    assert res_archive.json()["error"]["code"] == "NOT_FOUND"

    res_matches = await client.get(
        f"/api/v1/property-requirements/{random_id}/matches", headers=auth_headers
    )
    assert res_matches.status_code == 404
    assert res_matches.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_requirement_for_nonexistent_client_404(
    client: AsyncClient, auth_headers: dict
):
    random_client_id = uuid.uuid4()
    res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": str(random_client_id),
            "transaction_type": "BUY",
            "property_types": "Apartment",
        },
        headers=auth_headers,
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_create_requirement_for_archived_client_422(
    client: AsyncClient, auth_headers: dict, active_client: dict
):
    client_id = active_client["id"]
    # Archive client
    arch_res = await client.post(f"/api/v1/clients/{client_id}/archive", headers=auth_headers)
    assert arch_res.status_code == 200

    # Attempt to create requirement for archived client
    res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": client_id,
            "transaction_type": "BUY",
            "property_types": "Apartment",
        },
        headers=auth_headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "archived client" in res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_cannot_update_archived_requirement_422(
    client: AsyncClient, auth_headers: dict, active_client: dict
):
    # Create requirement
    create_res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": active_client["id"],
            "transaction_type": "BUY",
            "property_types": "Apartment",
        },
        headers=auth_headers,
    )
    req_id = create_res.json()["data"]["id"]

    # Archive requirement
    await client.post(f"/api/v1/property-requirements/{req_id}/archive", headers=auth_headers)

    # Attempt update
    patch_res = await client.patch(
        f"/api/v1/property-requirements/{req_id}",
        json={"notes": "Should not be updated"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 422
    assert patch_res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "terminal status" in patch_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_cannot_transition_from_terminal_status_422(
    client: AsyncClient, auth_headers: dict, active_client: dict
):
    # Create requirement
    create_res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": active_client["id"],
            "transaction_type": "BUY",
            "property_types": "Apartment",
        },
        headers=auth_headers,
    )
    req_id = create_res.json()["data"]["id"]

    # Fulfill
    await client.post(f"/api/v1/property-requirements/{req_id}/fulfill", headers=auth_headers)

    # Fulfill again -> 422
    res_repeat = await client.post(
        f"/api/v1/property-requirements/{req_id}/fulfill", headers=auth_headers
    )
    assert res_repeat.status_code == 422
    assert res_repeat.json()["error"]["code"] == "VALIDATION_ERROR"

    # Cancel after fulfill -> 422
    res_cancel = await client.post(
        f"/api/v1/property-requirements/{req_id}/cancel", headers=auth_headers
    )
    assert res_cancel.status_code == 422
    assert res_cancel.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_cannot_match_archived_requirement_422(
    client: AsyncClient, auth_headers: dict, active_client: dict
):
    create_res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": active_client["id"],
            "transaction_type": "BUY",
            "property_types": "Apartment",
        },
        headers=auth_headers,
    )
    req_id = create_res.json()["data"]["id"]

    # Archive
    await client.post(f"/api/v1/property-requirements/{req_id}/archive", headers=auth_headers)

    # Attempt matching
    match_res = await client.get(
        f"/api/v1/property-requirements/{req_id}/matches", headers=auth_headers
    )
    assert match_res.status_code == 422
    assert match_res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "archived" in match_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_cross_field_bounds_validation_on_update(
    client: AsyncClient, auth_headers: dict, active_client: dict
):
    create_res = await client.post(
        "/api/v1/property-requirements",
        json={
            "client_id": active_client["id"],
            "transaction_type": "BUY",
            "property_types": "Apartment",
            "min_budget": 5000000,
            "max_budget": 7000000,
            "min_area": 1000,
            "max_area": 1500,
        },
        headers=auth_headers,
    )
    req_id = create_res.json()["data"]["id"]

    # Try updating min_budget higher than existing max_budget (7000000)
    patch_budget = await client.patch(
        f"/api/v1/property-requirements/{req_id}",
        json={"min_budget": 8000000},
        headers=auth_headers,
    )
    assert patch_budget.status_code == 422
    assert patch_budget.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "min_budget cannot be greater than max_budget" in patch_budget.json()["error"]["message"]

    # Try updating max_area lower than existing min_area (1000)
    patch_area = await client.patch(
        f"/api/v1/property-requirements/{req_id}",
        json={"max_area": 800},
        headers=auth_headers,
    )
    assert patch_area.status_code == 422
    assert patch_area.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "min_area cannot be greater than max_area" in patch_area.json()["error"]["message"]
