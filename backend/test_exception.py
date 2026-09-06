import asyncio
import os
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/test_db')
os.environ.setdefault('JWT_SECRET_KEY', 'test-only-secret-key-not-for-production-use')
os.environ.setdefault('CORS_ALLOWED_ORIGINS', 'http://localhost:3000')
os.environ.setdefault('APP_ENV', 'local')
os.environ.setdefault('DEBUG', 'true')

from app.main import create_app
from httpx import ASGITransport, AsyncClient
from fastapi import APIRouter

async def test():
    app_obj = create_app()
    
    # Unwrap the ServerErrorMiddleware to get the FastAPI app
    if hasattr(app_obj, 'app'):
        app = app_obj.app
    else:
        app = app_obj
    
    # Add fault route
    router = APIRouter()
    @router.get('/boom/unexpected')
    async def boom_unexpected():
        raise RuntimeError('unexpected failure near /etc/passwd, secret=abc123')
    
    app.include_router(router, prefix='/_fault_test')
    
    transport = ASGITransport(app=app_obj, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get('/_fault_test/boom/unexpected')
        print(f'Status: {response.status_code}')
        try:
            json_body = response.json()
            print(f'Body JSON: {json_body}')
        except Exception as e:
            print(f'JSON parse error - response text (first 300 chars):')
            print(response.text[:300])
        print(f'Has secret in response: {"secret" in response.text}')

asyncio.run(test())
