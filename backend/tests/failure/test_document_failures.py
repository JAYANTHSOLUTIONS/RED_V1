"""Failure and boundary tests for Document Management and Secure Storage."""
from decimal import Decimal
from unittest.mock import patch
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.client import Client
from app.models.property import Property
from app.models.user import User
from app.storage import get_storage_backend

SAMPLE_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


@pytest.fixture
async def auth_headers(client: AsyncClient):
    email = f"consultant-doc-fail-{uuid.uuid4().hex[:8]}@example.com"
    password = "ConsultantPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Doc Failure Consultant",
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
async def archived_property():
    ref_code = f"ARCH-PROP-{uuid.uuid4().hex[:8].upper()}"
    async with AsyncSessionFactory() as session:
        async with session.begin():
            prop = Property(
                public_reference=ref_code,
                title="Archived Villa",
                property_type="RESIDENTIAL_VILLA",
                transaction_type="SALE",
                price=Decimal("5000000"),
                district="Chennai",
                city="Chennai",
                locality="Anna Nagar",
                pincode="600040",
                status="ARCHIVED",
                is_archived=True,
            )
            session.add(prop)
            await session.flush()
            prop_id = prop.id
    return prop_id


@pytest.fixture
async def archived_client(client: AsyncClient, auth_headers: dict):
    res = await client.post(
        "/api/v1/clients",
        json={"full_name": "Archived Client", "phone": f"+91 97{uuid.uuid4().int % 100000000:08d}"},
        headers=auth_headers,
    )
    client_id = res.json()["data"]["id"]
    await client.post(f"/api/v1/clients/{client_id}/archive", headers=auth_headers)
    return client_id


@pytest.mark.asyncio
async def test_nonexistent_document_404(client: AsyncClient, auth_headers: dict):
    random_id = uuid.uuid4()

    res_get = await client.get(f"/api/v1/documents/{random_id}", headers=auth_headers)
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "NOT_FOUND"

    res_dl = await client.get(f"/api/v1/documents/{random_id}/download", headers=auth_headers)
    assert res_dl.status_code == 404
    assert res_dl.json()["error"]["code"] == "NOT_FOUND"

    res_patch = await client.patch(
        f"/api/v1/documents/{random_id}", json={"notes": "test"}, headers=auth_headers
    )
    assert res_patch.status_code == 404
    assert res_patch.json()["error"]["code"] == "NOT_FOUND"

    res_rev = await client.post(f"/api/v1/documents/{random_id}/review", headers=auth_headers)
    assert res_rev.status_code == 404
    assert res_rev.json()["error"]["code"] == "NOT_FOUND"

    res_arch = await client.post(f"/api/v1/documents/{random_id}/archive", headers=auth_headers)
    assert res_arch.status_code == 404
    assert res_arch.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_upload_nonexistent_associations_404(client: AsyncClient, auth_headers: dict):
    random_id = uuid.uuid4()
    files = {"file": ("test.pdf", SAMPLE_PDF, "application/pdf")}

    # Non-existent property
    res_prop = await client.post(
        "/api/v1/documents",
        files=files,
        data={"document_type": "EC", "property_id": str(random_id)},
        headers=auth_headers,
    )
    assert res_prop.status_code == 404
    assert res_prop.json()["error"]["code"] == "NOT_FOUND"

    # Non-existent client
    files2 = {"file": ("test.pdf", SAMPLE_PDF, "application/pdf")}
    res_cli = await client.post(
        "/api/v1/documents",
        files=files2,
        data={"document_type": "IDENTITY_PROOF", "client_id": str(random_id)},
        headers=auth_headers,
    )
    assert res_cli.status_code == 404
    assert res_cli.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_upload_to_archived_entities_422(
    client: AsyncClient, auth_headers: dict, archived_property: uuid.UUID, archived_client: str
):
    files1 = {"file": ("test.pdf", SAMPLE_PDF, "application/pdf")}
    res_prop = await client.post(
        "/api/v1/documents",
        files=files1,
        data={"document_type": "EC", "property_id": str(archived_property)},
        headers=auth_headers,
    )
    assert res_prop.status_code == 422
    assert res_prop.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "archived property" in res_prop.json()["error"]["message"].lower()

    files2 = {"file": ("test.pdf", SAMPLE_PDF, "application/pdf")}
    res_cli = await client.post(
        "/api/v1/documents",
        files=files2,
        data={"document_type": "IDENTITY_PROOF", "client_id": archived_client},
        headers=auth_headers,
    )
    assert res_cli.status_code == 422
    assert res_cli.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "archived client" in res_cli.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_upload_empty_or_corrupt_file_422(client: AsyncClient, auth_headers: dict):
    # Zero-byte file
    files_empty = {"file": ("empty.pdf", b"", "application/pdf")}
    res_empty = await client.post(
        "/api/v1/documents",
        files=files_empty,
        data={"document_type": "EC"},
        headers=auth_headers,
    )
    assert res_empty.status_code == 422
    assert "empty" in res_empty.json()["error"]["message"].lower()

    # Forged file (extension .pdf, but content is text)
    files_forged = {"file": ("fake.pdf", b"Random non-pdf string data", "application/pdf")}
    res_forged = await client.post(
        "/api/v1/documents",
        files=files_forged,
        data={"document_type": "EC"},
        headers=auth_headers,
    )
    assert res_forged.status_code == 422
    assert "does not match expected format" in res_forged.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_cannot_modify_archived_document_422(client: AsyncClient, auth_headers: dict):
    files = {"file": ("deed.pdf", SAMPLE_PDF, "application/pdf")}
    upload_res = await client.post(
        "/api/v1/documents", files=files, data={"document_type": "SALE_DEED"}, headers=auth_headers
    )
    doc_id = upload_res.json()["data"]["id"]

    # Archive
    await client.post(f"/api/v1/documents/{doc_id}/archive", headers=auth_headers)

    # Attempt PATCH
    patch_res = await client.patch(
        f"/api/v1/documents/{doc_id}",
        json={"notes": "Should fail on archived doc"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 422
    assert patch_res.json()["error"]["code"] == "VALIDATION_ERROR"

    # Attempt review transition
    review_res = await client.post(f"/api/v1/documents/{doc_id}/review", headers=auth_headers)
    assert review_res.status_code == 422
    assert review_res.json()["error"]["code"] == "VALIDATION_ERROR"

    # Attempt archiving again
    arch_again = await client.post(f"/api/v1/documents/{doc_id}/archive", headers=auth_headers)
    assert arch_again.status_code == 422
    assert arch_again.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_compensation_cleanup_on_database_failure(auth_headers: dict):
    """Simulate DB failure after file has been written to storage, verify file was deleted."""
    from app.services.document import DocumentService
    from app.repositories.document import DocumentRepository

    from app.core.exceptions import DatabaseError

    service = DocumentService()
    pdf_bytes = b"%PDF-1.4 compensation test " + uuid.uuid4().bytes

    deleted_keys = []
    original_delete = service.storage.delete

    async def tracking_delete(key: str) -> bool:
        deleted_keys.append(key)
        return await original_delete(key)

    # Patch create on doc_repo to simulate database failure
    with patch.object(service.storage, "delete", side_effect=tracking_delete):
        with patch.object(DocumentRepository, "create", side_effect=OperationalError("Simulated DB failure", None, None)):
            async with AsyncSessionFactory() as session:
                with pytest.raises(DatabaseError):
                    await service.upload_document(
                        session=session,
                        file_bytes=pdf_bytes,
                        original_filename="comp_test.pdf",
                        document_type="SALE_DEED",
                    )

    # Verify compensation delete was called and file does not exist
    assert len(deleted_keys) == 1
    assert await service.storage.exists(deleted_keys[0]) is False
