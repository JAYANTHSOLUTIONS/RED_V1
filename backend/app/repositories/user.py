"""User repository for database access."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    async def get_by_id(self, session: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        return await session.get(User, user_id)

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        result = await session.execute(
            select(User).where(User.email == email.strip().lower())
        )
        return result.scalar_one_or_none()

    async def create(self, session: AsyncSession, user: User) -> User:
        session.add(user)
        await session.flush()
        return user
