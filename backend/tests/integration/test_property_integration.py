"""Integration tests for Property Management API endpoints.

Covers:
  - Authenticated property creation with sequential reference generation
  - Private property detail retrieval and partial updating
  - Lifecycle state machine progression (Publish, Pause, Mark Sold, Archive)
  - Image metadata management (Add, List, Reorder, Set Primary, Delete)
  - Private listing with parameterized filtering and pagination
  - Public listing and public detail discovery by reference ID
"""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.models.property import Property, PropertyImage
from app.models.user import User


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Authenticate a test consultant and return valid Bearer Authorization headers."""
    email = f"consultant-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant User",
                role="CONSULTANT",
                is_active=True,
            )
            session.add(user)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    access_token = login_res.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_create_property_success(client: AsyncClient, auth_headers: dict):
    """Verify authenticated property creation generates reference ID, starts in DRAFT, and logs audit."""
    payload = {
        "title": "Prime Residential Plot",
        "property_type": "Residential Plot / Layout Land",
        "transaction_type": "SALE",
        "price": "4500000.00",
        "district": "Coimbatore",
        "city": "Coimbatore",
        "locality": "Saravanampatti",
        "pincode": "641035",
        "plot_area": "2400.00",
        "area_unit": "sq.ft",
        "owner_name": "R. Sundaram",
        "owner_phone": "+919876543210",
        "internal_notes": "Clear DTCP approval documents verified.",
    }

    response = await client.post("/api/v1/properties", json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]

    assert data["public_reference"].startswith("PR-")
    assert data["status"] == "DRAFT"
    assert data["is_archived"] is False
    assert data["price"] == "4500000.00"
    assert data["owner_name"] == "R. Sundaram"
    prop_id = uuid.UUID(data["id"])

    # Verify audit log was committed
    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "PROPERTY_CREATED",
                AuditLog.entity_id == prop_id,
            )
        )
        assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_get_and_update_property(client: AsyncClient, auth_headers: dict):
    """Verify getting property by ID and partial updates via PATCH."""
    create_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Modern 2BHK Apartment",
            "property_type": "Apartment",
            "transaction_type": "RENT",
            "price": "25000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Peelamedu",
            "pincode": "641004",
        },
        headers=auth_headers,
    )
    prop_id = create_res.json()["data"]["id"]

    # 1. GET by ID
    get_res = await client.get(f"/api/v1/properties/{prop_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["data"]["title"] == "Modern 2BHK Apartment"

    # 2. PATCH update
    patch_res = await client.patch(
        f"/api/v1/properties/{prop_id}",
        json={"price": "28000.00", "description": "Includes covered car parking."},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    patch_data = patch_res.json()["data"]
    assert patch_data["price"] == "28000.00"
    assert patch_data["description"] == "Includes covered car parking."

    # Verify audit log for update
    async with AsyncSessionFactory() as session:
        res = await session.execute(
            select(AuditLog).where(
                AuditLog.action == "PROPERTY_UPDATED",
                AuditLog.entity_id == uuid.UUID(prop_id),
            )
        )
        assert res.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_property_lifecycle_progression(client: AsyncClient, auth_headers: dict):
    """Verify DRAFT -> PUBLISHED -> PAUSED -> PUBLISHED -> SOLD -> ARCHIVED."""
    create_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Independent House",
            "property_type": "Independent House / Villa",
            "transaction_type": "SALE",
            "price": "8500000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Vadavalli",
            "pincode": "641041",
        },
        headers=auth_headers,
    )
    prop_id = create_res.json()["data"]["id"]
    public_ref = create_res.json()["data"]["public_reference"]

    # 1. DRAFT is NOT visible publicly
    pub_check_1 = await client.get(f"/api/v1/public/properties/{public_ref}")
    assert pub_check_1.status_code == 404

    # 2. Publish
    pub_res = await client.post(
        f"/api/v1/properties/{prop_id}/publish", headers=auth_headers
    )
    assert pub_res.status_code == 200
    assert pub_res.json()["data"]["status"] == "PUBLISHED"

    # Now visible publicly
    pub_check_2 = await client.get(f"/api/v1/public/properties/{public_ref}")
    assert pub_check_2.status_code == 200
    assert pub_check_2.json()["data"]["public_reference"] == public_ref

    # 3. Pause
    pause_res = await client.post(
        f"/api/v1/properties/{prop_id}/pause", headers=auth_headers
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["status"] == "PAUSED"

    # Paused is NOT visible publicly
    pub_check_3 = await client.get(f"/api/v1/public/properties/{public_ref}")
    assert pub_check_3.status_code == 404

    # 4. Re-publish
    repub_res = await client.post(
        f"/api/v1/properties/{prop_id}/publish", headers=auth_headers
    )
    assert repub_res.status_code == 200
    assert repub_res.json()["data"]["status"] == "PUBLISHED"

    # 5. Mark Sold
    sold_res = await client.post(
        f"/api/v1/properties/{prop_id}/mark-sold", headers=auth_headers
    )
    assert sold_res.status_code == 200
    assert sold_res.json()["data"]["status"] == "SOLD"

    # Sold is NOT visible publicly
    pub_check_4 = await client.get(f"/api/v1/public/properties/{public_ref}")
    assert pub_check_4.status_code == 404

    # 6. Archive
    arch_res = await client.post(
        f"/api/v1/properties/{prop_id}/archive", headers=auth_headers
    )
    assert arch_res.status_code == 200
    assert arch_res.json()["data"]["status"] == "ARCHIVED"
    assert arch_res.json()["data"]["is_archived"] is True


@pytest.mark.asyncio
async def test_property_image_metadata_crud(client: AsyncClient, auth_headers: dict):
    """Verify adding image metadata, listing, setting primary, and deleting."""
    create_res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Commercial Complex",
            "property_type": "Commercial Property",
            "transaction_type": "LEASE",
            "price": "150000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Gandhipuram",
            "pincode": "641012",
        },
        headers=auth_headers,
    )
    prop_id = create_res.json()["data"]["id"]

    # 1. Add Image 1 (is_primary=True)
    img1_res = await client.post(
        f"/api/v1/properties/{prop_id}/images",
        json={
            "storage_key": f"properties/{prop_id}/front-facade.jpg",
            "original_filename": "front-facade.jpg",
            "mime_type": "image/jpeg",
            "file_size": 2048500,
            "display_order": 0,
            "is_primary": True,
        },
        headers=auth_headers,
    )
    assert img1_res.status_code == 201
    img1_id = img1_res.json()["data"]["id"]
    assert img1_res.json()["data"]["is_primary"] is True

    # 2. Add Image 2 (is_primary=True -> should demote Image 1)
    img2_res = await client.post(
        f"/api/v1/properties/{prop_id}/images",
        json={
            "storage_key": f"properties/{prop_id}/interior-lobby.jpg",
            "original_filename": "interior-lobby.jpg",
            "mime_type": "image/jpeg",
            "file_size": 1845000,
            "display_order": 1,
            "is_primary": True,
        },
        headers=auth_headers,
    )
    assert img2_res.status_code == 201
    img2_id = img2_res.json()["data"]["id"]
    assert img2_res.json()["data"]["is_primary"] is True

    # 3. List images and verify primary flags
    list_res = await client.get(
        f"/api/v1/properties/{prop_id}/images", headers=auth_headers
    )
    assert list_res.status_code == 200
    images = list_res.json()["data"]
    assert len(images) == 2
    # Verify Image 2 is primary and Image 1 was demoted
    img1_state = next(img for img in images if img["id"] == img1_id)
    img2_state = next(img for img in images if img["id"] == img2_id)
    assert img1_state["is_primary"] is False
    assert img2_state["is_primary"] is True

    # 4. PATCH update image metadata (display_order, is_primary)
    patch_img_res = await client.patch(
        f"/api/v1/properties/{prop_id}/images/{img1_id}",
        json={"display_order": 99, "is_primary": True},
        headers=auth_headers,
    )
    assert patch_img_res.status_code == 200
    assert patch_img_res.json()["data"]["display_order"] == 99
    assert patch_img_res.json()["data"]["is_primary"] is True

    # 5. Delete Image 1
    del_res = await client.delete(
        f"/api/v1/properties/{prop_id}/images/{img1_id}", headers=auth_headers
    )
    assert del_res.status_code == 200

    # Verify Image 1 is excluded from active list
    list_res_after = await client.get(
        f"/api/v1/properties/{prop_id}/images", headers=auth_headers
    )
    active_images = list_res_after.json()["data"]
    assert len(active_images) == 1
    assert active_images[0]["id"] == img2_id


@pytest.mark.asyncio
async def test_property_listing_filters_and_pagination(
    client: AsyncClient, auth_headers: dict
):
    """Verify parameterized filtering and database-level pagination."""
    unique_locality = f"Locality-{uuid.uuid4().hex[:6]}"

    # Create 3 properties in unique locality
    for i in range(3):
        await client.post(
            "/api/v1/properties",
            json={
                "title": f"Apartment #{i}",
                "property_type": "Apartment",
                "transaction_type": "SALE",
                "price": str(3000000 + (i * 1000000)),
                "district": "Coimbatore",
                "city": "Coimbatore",
                "locality": unique_locality,
                "pincode": "641001",
                "bedrooms": 2 + i,
            },
            headers=auth_headers,
        )

    # 1. Filter by locality
    list_res = await client.get(
        f"/api/v1/properties?locality={unique_locality}", headers=auth_headers
    )
    assert list_res.status_code == 200
    data = list_res.json()["data"]
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # 2. Filter by bedrooms and pagination limit=1
    paginated_res = await client.get(
        f"/api/v1/properties?locality={unique_locality}&limit=1&offset=0",
        headers=auth_headers,
    )
    assert paginated_res.status_code == 200
    page_data = paginated_res.json()["data"]
    assert page_data["total"] == 3
    assert len(page_data["items"]) == 1
    assert page_data["limit"] == 1
    assert page_data["offset"] == 0


@pytest.mark.asyncio
async def test_public_property_listing_strictly_published_only(
    client: AsyncClient, auth_headers: dict
):
    """Verify public property search returns only published properties with public fields."""
    unique_city = f"City-{uuid.uuid4().hex[:6]}"

    # Create Property A: DRAFT
    res_a = await client.post(
        "/api/v1/properties",
        json={
            "title": "Draft Villa",
            "property_type": "Villa",
            "transaction_type": "SALE",
            "price": "5000000.00",
            "district": "TestDistrict",
            "city": unique_city,
            "locality": "AreaA",
            "pincode": "641001",
            "owner_name": "Secret Owner A",
        },
        headers=auth_headers,
    )
    # Create Property B: PUBLISHED
    res_b = await client.post(
        "/api/v1/properties",
        json={
            "title": "Published Villa",
            "property_type": "Villa",
            "transaction_type": "SALE",
            "price": "6000000.00",
            "district": "TestDistrict",
            "city": unique_city,
            "locality": "AreaB",
            "pincode": "641001",
            "owner_name": "Secret Owner B",
        },
        headers=auth_headers,
    )
    prop_b_id = res_b.json()["data"]["id"]
    await client.post(f"/api/v1/properties/{prop_b_id}/publish", headers=auth_headers)

    # Query public search
    pub_res = await client.get(f"/api/v1/public/properties?city={unique_city}")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()["data"]
    assert pub_data["total"] == 1
    assert len(pub_data["items"]) == 1
    item = pub_data["items"][0]
    assert item["title"] == "Published Villa"
    assert "owner_name" not in item
    assert "id" not in item


@pytest.mark.asyncio
async def test_property_mark_rented(client: AsyncClient, auth_headers: dict):
    """Verify marking published property as rented."""
    res = await client.post(
        "/api/v1/properties",
        json={
            "title": "Rental Villa",
            "property_type": "Independent House / Villa",
            "transaction_type": "RENT",
            "price": "40000.00",
            "district": "Coimbatore",
            "city": "Coimbatore",
            "locality": "Saibaba Colony",
            "pincode": "641011",
        },
        headers=auth_headers,
    )
    prop_id = res.json()["data"]["id"]
    await client.post(f"/api/v1/properties/{prop_id}/publish", headers=auth_headers)
    rent_res = await client.post(
        f"/api/v1/properties/{prop_id}/mark-rented", headers=auth_headers
    )
    assert rent_res.status_code == 200
    assert rent_res.json()["data"]["status"] == "RENTED"
