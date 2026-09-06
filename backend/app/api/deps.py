"""Shared FastAPI dependencies used across API routers.

Provides database session injection, request correlation ID extraction,
JWT Bearer token verification, user resolution, and role-based access control (RBAC).
"""
from typing import AsyncIterator, Callable, Optional
import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

import jwt

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.db.session import get_db as _get_db
from app.models.user import User
from app.repositories.user import UserRepository

__all__ = [
    "get_db",
    "get_request_id",
    "get_ip_address",
    "get_current_user",
    "require_roles",
]

security_bearer = HTTPBearer(auto_error=False)
_user_repo = UserRepository()


async def get_db() -> AsyncIterator[AsyncSession]:
    """Re-exported so routers depend on `app.api.deps`, never `app.db` directly."""
    async for session in _get_db():
        yield session


def get_request_id(request: Request) -> str:
    """Return the current request's correlation ID (set by RequestIdMiddleware)."""
    return getattr(request.state, "request_id", "-")


def get_ip_address(request: Request) -> Optional[str]:
    """Extract client IP address from request headers or socket info."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Validate Bearer access token and return the active User entity."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Authentication credentials were not provided.")

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise AuthenticationError("Invalid or expired access token.")

    token_type = payload.get("type")
    if token_type != "access":
        raise AuthenticationError("Invalid token type.")

    subject = payload.get("sub")
    if not subject:
        raise AuthenticationError("Token subject is missing.")

    try:
        user_id = uuid.UUID(subject)
    except (ValueError, TypeError):
        raise AuthenticationError("Invalid user ID in token.")

    user = await _user_repo.get_by_id(session, user_id)
    if user is None:
        raise AuthenticationError("User not found.")

    if not user.is_active:
        raise AuthenticationError("Account is inactive or disabled.")

    return user


def require_roles(*roles: str) -> Callable:
    """Dependency factory enforcing Role-Based Access Control (RBAC)."""
    allowed_roles = {r.upper() for r in roles}

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.upper() not in allowed_roles:
            raise AuthorizationError("You do not have permission to perform this action.")
        return current_user

    return role_checker
