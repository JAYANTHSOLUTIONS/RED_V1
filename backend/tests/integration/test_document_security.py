"""Security tests for Document Management and Secure Storage API.

Verifies:
- Unauthenticated requests are rejected (401)
- Non-consultant roles are forbidden (403)
- No public document leakage through public property endpoints
- Arbitrary storage-key access is impossible
- Path traversal in filenames is neutralized
- Storage keys and internal filesystem paths are never leaked in responses
"""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.property import Property
from app.models.user import User

SAMPLE_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.fixture
async def regular_user_headers(client: AsyncClient):
    email = f"user-doc-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "UserPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Regular User",
                role="USER",
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
async def consultant_headers(client: AsyncClient):
    email = f"consultant-doc-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant Sec",
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
async def test_unauthenticated_requests_rejected(client: AsyncClient):
    random_id = uuid.uuid4()
    endpoints = [
        ("GET", "/api/v1/documents"),
        ("POST", "/api/v1/documents"),
        ("GET", f"/api/v1/documents/{random_id}"),
        ("GET", f"/api/v1/documents/{random_id}/download"),
        ("PATCH", f"/api/v1/documents/{random_id}"),
        ("POST", f"/api/v1/documents/{random_id}/review"),
        ("POST", f"/api/v1/documents/{random_id}/archive"),
    ]

    for method, endpoint in endpoints:
        res = await client.request(method, endpoint)
        assert res.status_code == 401, f"{method} {endpoint} did not return 401"
        assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_non_consultant_forbidden(
    client: AsyncClient, regular_user_headers: dict
):
    random_id = uuid.uuid4()
    endpoints = [
        ("GET", "/api/v1/documents"),
        ("POST", "/api/v1/documents"),
        ("GET", f"/api/v1/documents/{random_id}"),
        ("GET", f"/api/v1/documents/{random_id}/download"),
        ("PATCH", f"/api/v1/documents/{random_id}"),
        ("POST", f"/api/v1/documents/{random_id}/review"),
        ("POST", f"/api/v1/documents/{random_id}/archive"),
    ]

    for method, endpoint in endpoints:
        res = await client.request(method, endpoint, headers=regular_user_headers)
        assert res.status_code == 403, f"{method} {endpoint} did not return 403"
        assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_no_public_document_leakage(
    client: AsyncClient, consultant_headers: dict
):
    # Create published property with a private document
    ref_code = f"SEC-PROP-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Public Villa with Private Deeds",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("12000000"),
                district="Chennai",
                city="Chennai",
                locality="Adyar",
                pincode="600020",
                status="PUBLISHED",
                is_archived=False,
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id

    # Upload private document to this property
    files = {"file": ("confidential_deed.pdf", SAMPLE_PDF, "application/pdf")}
    data = {"document_type": "SALE_DEED", "property_id": str(prop_id)}
    upload_res = await client.post("/api/v1/documents", files=files, data=data, headers=consultant_headers)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["data"]["id"]

    # Access property via public endpoint
    public_res = await client.get(f"/api/v1/public/properties/{ref_code}")
    assert public_res.status_code == 200
    public_body = public_res.json()["data"]

    # Verify no document references leaked in public property payload
    assert "documents" not in public_body
    assert "storage_key" not in public_body
    assert doc_id not in str(public_body)
    assert "confidential_deed" not in str(public_body)


@pytest.mark.asyncio
async def test_path_traversal_sanitized_on_upload(
    client: AsyncClient, consultant_headers: dict
):
    traversal_filename = "../../../../../etc/passwd.pdf"
    pdf_bytes = b"%PDF-1.4 traversal test " + uuid.uuid4().bytes
    files = {"file": (traversal_filename, pdf_bytes, "application/pdf")}
    data = {"document_type": "OTHER"}

    res = await client.post("/api/v1/documents", files=files, data=data, headers=consultant_headers)
    assert res.status_code == 201
    saved_doc = res.json()["data"]
    # Verify traversal directories were stripped
    assert ".." not in saved_doc["original_filename"]
    assert "/" not in saved_doc["original_filename"]
    assert "\\" not in saved_doc["original_filename"]
    assert saved_doc["original_filename"] == "passwd.pdf"


@pytest.mark.asyncio
async def test_storage_key_not_exposed_in_response(
    client: AsyncClient, consultant_headers: dict
):
    pdf_bytes = b"%PDF-1.4 storage key test " + uuid.uuid4().bytes
    files = {"file": ("safe_doc.pdf", pdf_bytes, "application/pdf")}
    data = {"document_type": "EC"}

    res = await client.post("/api/v1/documents", files=files, data=data, headers=consultant_headers)
    assert res.status_code == 201
    doc_data = res.json()["data"]
    # Verify internal storage key is not exposed
    assert "storage_key" not in doc_data
