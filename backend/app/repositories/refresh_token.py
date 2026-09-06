"""Refresh token repository for database access."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import RefreshToken


class RefreshTokenRepository:
    async def create(self, session: AsyncSession, token: RefreshToken) -> RefreshToken:
        session.add(token)
        await session.flush()
        return token

    async def get_by_hash_for_update(
        self, session: AsyncSession, token_hash: str
    ) -> Optional[RefreshToken]:
        """Fetch token with row-level lock (SELECT FOR UPDATE) to prevent race conditions during rotation."""
        result = await session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_hash(
        self, session: AsyncSession, token_hash: str
    ) -> Optional[RefreshToken]:
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, session: AsyncSession, token: RefreshToken) -> None:
        token.revoked = True
        token.revoked_at = datetime.now(timezone.utc)
        await session.flush()

    async def revoke_all_for_user(self, session: AsyncSession, user_id: uuid.UUID) -> None:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        await session.flush()
