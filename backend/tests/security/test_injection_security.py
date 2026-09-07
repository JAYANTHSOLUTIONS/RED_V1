"""Adversarial security tests for SQL Injection, XSS/HTML Handling, and Unicode/Tamil Preservation.

Verifies:
  - Search and filter queries with SQL injection payloads are strictly parameterized
    and safely executed as literal text by SQLAlchemy ORM.
  - Script tags and HTML payloads (<script>, <img>) are treated as passive text.
  - Tamil Unicode real-estate data (அண்ணா நகர், வில்லா) is preserved without loss or corruption.
  - CRLF injection attempts in email fields are rejected by input validation.
"""
from decimal import Decimal
import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.db.session import AsyncSessionFactory
from app.models.user import User


@pytest.fixture
async def consultant_headers(client: AsyncClient):
    email = f"injection-sec-{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPassword123!"

    async with AsyncSessionFactory() as session:
        async with session.begin():
            user = User(
                email=email,
                hashed_password=hash_password(password),
                full_name="Consultant Injection Sec",
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
@pytest.mark.parametrize(
    "sql_payload",
    [
        "' OR '1'='1",
        "'; DROP TABLE properties; --",
        "1' UNION SELECT null, null, null; --",
        "admin'--",
        "')) OR 1=1--",
    ],
)
async def test_sql_injection_in_search_queries_parameterized(
    client: AsyncClient, consultant_headers: dict, sql_payload: str
):
    """SQL injection payloads in search filters must be executed as parameterized literals without syntax error."""
    # 1. Test property search
    res = await client.get(f"/api/v1/properties?search={sql_payload}", headers=consultant_headers)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 2. Test client search
    res_client = await client.get(f"/api/v1/clients?search={sql_payload}", headers=consultant_headers)
    assert res_client.status_code == 200
    assert res_client.json()["success"] is True


@pytest.mark.asyncio
async def test_tamil_unicode_real_estate_preservation(client: AsyncClient, consultant_headers: dict):
    """Tamil language strings (Tamil Nadu real estate terms) must be preserved without corruption."""
    tamil_payload = {
        "title": "சென்னையில் ஆடம்பர வில்லா - 3 BHK",
        "property_type": "VILLA",
        "transaction_type": "SALE",
        "price": "17500000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "அண்ணா நகர்",
        "pincode": "600040",
        "taluk": "அம்பத்தூர்",
        "village": "அண்ணா நகர் மேற்கு",
        "address": "கதவு எண் 12, முதலாவது மெயின் ரோடு",
        "description": "அனைத்து வசதிகளுடன் கூடிய அழகிய தனி வீடு. பட்டா மற்றும் EC சரிபார்க்கப்பட்டது.",
    }

    res = await client.post("/api/v1/properties", json=tamil_payload, headers=consultant_headers)
    assert res.status_code == 201
    data = res.json()["data"]

    # Verify exact Unicode retention
    assert data["title"] == "சென்னையில் ஆடம்பர வில்லா - 3 BHK"
    assert data["taluk"] == "அம்பத்தூர்"
    assert data["locality"] == "அண்ணா நகர்"
    assert data["address"] == "கதவு எண் 12, முதலாவது மெயின் ரோடு"
    assert "பட்டா மற்றும் EC" in data["description"]

    # Verify search query with Tamil characters finds the property
    search_res = await client.get("/api/v1/properties?search=வில்லா", headers=consultant_headers)
    assert search_res.status_code == 200
    items = search_res.json()["data"]["items"]
    assert any(i["id"] == data["id"] for i in items)


@pytest.mark.asyncio
async def test_stored_xss_payload_stored_safely_as_text(client: AsyncClient, consultant_headers: dict):
    """Payloads containing HTML/script tags are stored strictly as text data."""
    xss_payload = {
        "title": "<script>alert('XSS')</script> Luxury Flat",
        "property_type": "APARTMENT",
        "transaction_type": "SALE",
        "price": "8500000.00",
        "district": "CHENNAI",
        "city": "Chennai",
        "locality": "Nungambakkam",
        "pincode": "600034",
        "taluk": "Egmore",
        "village": "Nungambakkam",
        "description": "<img src=x onerror=alert(document.cookie)> Great location",
    }

    res = await client.post("/api/v1/properties", json=xss_payload, headers=consultant_headers)
    assert res.status_code == 201
    data = res.json()["data"]

    assert "<script>alert('XSS')</script>" in data["title"]
    assert "<img src=x onerror=alert(document.cookie)>" in data["description"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "crlf_email",
    [
        "user@example.com\r\nBcc: attacker@example.com",
        "user@example.com%0d%0aBcc: attacker@example.com",
        "user\r\n@example.com",
    ],
)
async def test_crlf_email_injection_rejected(client: AsyncClient, crlf_email: str):
    """Attempting CRLF injection in email field during login must be rejected with 422."""
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": crlf_email, "password": "Password123!"},
    )
    assert res.status_code == 422
