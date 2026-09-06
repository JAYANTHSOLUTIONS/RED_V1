"""Authentication and Authorization API routes.

Exposes:
  - POST /api/v1/auth/login
  - POST /api/v1/auth/refresh
  - POST /api/v1/auth/logout
  - GET  /api/v1/auth/me
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_ip_address, get_request_id
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse, UserResponse
from app.schemas.common import SuccessEnvelope, success_envelope
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.post(
    "/login",
    response_model=SuccessEnvelope[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate consultant and issue tokens",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Authenticate user by email and password, issuing access and refresh tokens."""
    token_response, _ = await auth_service.login(
        session=db,
        email=payload.email,
        password=payload.password,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=token_response.model_dump(mode="json"),
        message="Login successful.",
    )


@router.post(
    "/refresh",
    response_model=SuccessEnvelope[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue new access token",
)
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Exchange an active refresh token for a newly rotated token pair."""
    token_response = await auth_service.refresh_tokens(
        session=db,
        raw_refresh_token=payload.refresh_token,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=token_response.model_dump(mode="json"),
        message="Tokens refreshed successfully.",
    )


@router.post(
    "/logout",
    response_model=SuccessEnvelope[None],
    status_code=status.HTTP_200_OK,
    summary="Revoke refresh token and terminate session",
)
async def logout(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke the given refresh token, invalidating the session."""
    await auth_service.logout(
        session=db,
        raw_refresh_token=payload.refresh_token,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=None,
        message="Logged out successfully.",
    )


@router.get(
    "/me",
    response_model=SuccessEnvelope[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
async def me(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the profile of the currently authenticated user."""
    return success_envelope(
        data=UserResponse.model_validate(current_user).model_dump(mode="json"),
        message="User profile retrieved successfully.",
    )
