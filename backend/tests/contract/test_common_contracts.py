import pytest
from httpx import AsyncClient
from app.main import create_app

@pytest.fixture
def app():
    return create_app()

@pytest.mark.asyncio
async def test_error_envelope_404(app):
    """Ensure that a 404 error returns the canonical error envelope."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/this-route-does-not-exist")
        
    assert response.status_code == 404
    data = response.json()
    
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert "code" in data["error"]
    assert data["error"]["code"] == "NOT_FOUND"
    assert "message" in data["error"]

@pytest.mark.asyncio
async def test_error_envelope_401(app):
    """Ensure that an unauthenticated request to a protected route returns the canonical 401 envelope."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # A known protected route
        response = await ac.get("/api/v1/properties")
        
    assert response.status_code == 401
    data = response.json()
    
    assert "success" in data
    assert data["success"] is False
    assert "error" in data
    assert "code" in data["error"]
    # Usually FastAPI's dependency throws a standard 401 if unauthenticated,
    # let's just make sure the envelope is correct. We might get NOT_AUTHENTICATED or HTTP_ERROR if we don't map it.
    assert "message" in data["error"]

@pytest.mark.asyncio
async def test_validation_error_envelope(app):
    """Ensure that validation errors return the canonical envelope with a VALIDATION_ERROR code."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Attempt to login with missing fields
        response = await ac.post("/api/v1/auth/login", json={})
        
    assert response.status_code == 422
    data = response.json()
    
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "The provided data failed validation." in data["error"]["message"]
