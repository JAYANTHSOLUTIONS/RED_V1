"""Authentication and authorization service.

Orchestrates user verification, secure token issuance, opaque refresh token
rotation with row-level locking, token revocation, and immutable audit logging.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.db.session import transaction
from app.models.user import RefreshToken, User
from app.repositories.audit import AuditRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse, UserResponse

settings = get_settings()

_SYSTEM_AUDIT_ENTITY_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


class AuthService:
    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        refresh_token_repo: Optional[RefreshTokenRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
    ):
        self.user_repo = user_repo or UserRepository()
        self.refresh_token_repo = refresh_token_repo or RefreshTokenRepository()
        self.audit_repo = audit_repo or AuditRepository()

    async def login(
        self,
        session: AsyncSession,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Tuple[TokenResponse, User]:
        """Authenticate user and issue access and refresh tokens.
        
        Prevents user enumeration by using generic error messages and logging
        security audit events for both successful and failed attempts.
        """
        normalized_email = email.strip().lower()
        user = await self.user_repo.get_by_email(session, normalized_email)

        if user is None:
            await self.audit_repo.record(
                session,
                action="LOGIN_FAILURE",
                entity_type="USER",
                entity_id=_SYSTEM_AUDIT_ENTITY_ID,
                actor_id=None,
                change_diff={"reason": "User not found", "email": normalized_email},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            await session.commit()
            raise AuthenticationError("Invalid email or password.")

        if not verify_password(password, user.hashed_password):
            await self.audit_repo.record(
                session,
                action="LOGIN_FAILURE",
                entity_type="USER",
                entity_id=user.id,
                actor_id=user.id,
                change_diff={"reason": "Invalid credentials"},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            await session.commit()
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            await self.audit_repo.record(
                session,
                action="LOGIN_FAILURE",
                entity_type="USER",
                entity_id=user.id,
                actor_id=user.id,
                change_diff={"reason": "Inactive account"},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            await session.commit()
            raise AuthenticationError("Account is inactive or disabled.")

        # Generate tokens
        access_token = create_access_token(
            subject=str(user.id),
            extra_claims={"role": user.role, "email": user.email},
        )
        raw_refresh = generate_refresh_token()
        token_hash = hash_refresh_token(raw_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        async with transaction(session):
            new_token = RefreshToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=expires_at,
                revoked=False,
            )
            await self.refresh_token_repo.create(session, new_token)
            await self.audit_repo.record(
                session,
                action="LOGIN_SUCCESS",
                entity_type="USER",
                entity_id=user.id,
                actor_id=user.id,
                change_diff={"email": user.email, "role": user.role},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )
        return token_response, user

    async def refresh_tokens(
        self,
        session: AsyncSession,
        raw_refresh_token: str,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> TokenResponse:
        """Rotate refresh token and issue new access token.
        
        Uses row-level locking (SELECT FOR UPDATE) to prevent race conditions.
        Detects token reuse: if an already-revoked token is submitted, all active
        refresh tokens for that user are immediately revoked as a security precaution.
        """
        token_hash = hash_refresh_token(raw_refresh_token)

        token = await self.refresh_token_repo.get_by_hash_for_update(session, token_hash)
        if token is None:
            raise AuthenticationError("Invalid or expired refresh token.")

        if token.revoked:
            # Token reuse detected! Revoke all sessions for this user.
            await self.refresh_token_repo.revoke_all_for_user(session, token.user_id)
            await self.audit_repo.record(
                session,
                action="REFRESH_TOKEN_REUSE_DETECTED",
                entity_type="REFRESH_TOKEN",
                entity_id=token.id,
                actor_id=token.user_id,
                change_diff={"warning": "Token reuse attempt; all active sessions revoked"},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            await session.commit()
            raise AuthenticationError("Invalid or expired refresh token.")

        now = datetime.now(timezone.utc)
        if token.expires_at < now:
            await self.refresh_token_repo.revoke(session, token)
            await self.audit_repo.record(
                session,
                action="REFRESH_TOKEN_EXPIRED",
                entity_type="REFRESH_TOKEN",
                entity_id=token.id,
                actor_id=token.user_id,
                ip_address=ip_address,
                correlation_id=correlation_id,
            )
            await session.commit()
            raise AuthenticationError("Refresh token has expired.")

        user = await self.user_repo.get_by_id(session, token.user_id)
        if user is None or not user.is_active:
            await self.refresh_token_repo.revoke(session, token)
            await session.commit()
            raise AuthenticationError("User account is inactive or not found.")

        # Rotate: revoke old token and issue new pair inside transaction
        new_raw_refresh = generate_refresh_token()
        new_token_hash = hash_refresh_token(new_raw_refresh)
        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        async with transaction(session):
            await self.refresh_token_repo.revoke(session, token)
            new_token = RefreshToken(
                user_id=user.id,
                token_hash=new_token_hash,
                expires_at=new_expires_at,
                revoked=False,
            )
            await self.refresh_token_repo.create(session, new_token)

            new_access_token = create_access_token(
                subject=str(user.id),
                extra_claims={"role": user.role, "email": user.email},
            )

            await self.audit_repo.record(
                session,
                action="REFRESH_TOKEN_ROTATED",
                entity_type="REFRESH_TOKEN",
                entity_id=token.id,
                actor_id=user.id,
                change_diff={"new_token_id": str(new_token.id)},
                ip_address=ip_address,
                correlation_id=correlation_id,
            )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(
        self,
        session: AsyncSession,
        raw_refresh_token: str,
        current_user: Optional[User] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Revoke the provided refresh token and record audit log."""
        token_hash = hash_refresh_token(raw_refresh_token)

        async with transaction(session):
            token = await self.refresh_token_repo.get_by_hash_for_update(
                session, token_hash
            )
            if token and not token.revoked:
                await self.refresh_token_repo.revoke(session, token)
                actor_id = current_user.id if current_user else token.user_id
                await self.audit_repo.record(
                    session,
                    action="LOGOUT",
                    entity_type="REFRESH_TOKEN",
                    entity_id=token.id,
                    actor_id=actor_id,
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )
