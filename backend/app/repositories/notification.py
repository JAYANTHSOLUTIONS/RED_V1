"""Notification repository.

Handles database operations for notifications: creation, filtered queries,
recipient isolation (anti-IDOR), row-level locking for status updates,
and database-level unread count aggregation.
"""
from datetime import datetime
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.schemas.notification import NotificationFilterParams


class NotificationRepository:
    """Encapsulates all database operations on notifications."""

    async def create(
        self,
        session: AsyncSession,
        notification: Notification,
    ) -> Notification:
        """Persist a new notification entity."""
        session.add(notification)
        await session.flush()
        return notification

    async def get_by_id(
        self,
        session: AsyncSession,
        notification_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Notification]:
        """Fetch a notification by ID.
        
        If user_id is provided, strictly enforces user ownership to prevent IDOR.
        """
        stmt = select(Notification).where(Notification.id == notification_id)
        if user_id is not None:
            stmt = stmt.where(Notification.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self,
        session: AsyncSession,
        notification_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Notification]:
        """Fetch a notification by ID with PostgreSQL row-level lock (SELECT ... FOR UPDATE)."""
        stmt = (
            select(Notification)
            .where(Notification.id == notification_id)
            .with_for_update()
        )
        if user_id is not None:
            stmt = stmt.where(Notification.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_notifications(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        filters: NotificationFilterParams,
    ) -> Tuple[List[Notification], int]:
        """Retrieve paginated notifications for a specific user with filtering."""
        base_query = select(Notification).where(Notification.user_id == user_id)

        # Filters
        if filters.is_read is not None:
            base_query = base_query.where(Notification.is_read == filters.is_read)

        if filters.channel is not None:
            ch = filters.channel.strip().upper()
            if ch == "IN_APP" or ch == "DASHBOARD":
                base_query = base_query.where(Notification.channel.in_(["IN_APP", "DASHBOARD"]))
            else:
                base_query = base_query.where(Notification.channel == ch)

        if filters.notification_type is not None:
            base_query = base_query.where(
                Notification.notification_type == filters.notification_type.strip().upper()
            )

        if filters.entity_type is not None:
            base_query = base_query.where(
                Notification.entity_type == filters.entity_type.strip().upper()
            )

        if filters.created_from is not None:
            base_query = base_query.where(Notification.created_at >= filters.created_from)

        if filters.created_to is not None:
            base_query = base_query.where(Notification.created_at <= filters.created_to)

        # Total count query
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_res = await session.execute(count_stmt)
        total = count_res.scalar() or 0

        # Bounded pagination and deterministic descending order
        paginated_stmt = (
            base_query
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(filters.offset)
            .limit(filters.limit)
        )
        items_res = await session.execute(paginated_stmt)
        items = list(items_res.scalars().all())

        return items, total

    async def count_unread(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """Efficient SQL aggregate count of unread notifications for a user."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        res = await session.execute(stmt)
        return res.scalar() or 0

    async def mark_as_read(
        self,
        session: AsyncSession,
        notification: Notification,
    ) -> Notification:
        """Mark notification as read with server-side timestamp (idempotent)."""
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = func.now()
            session.add(notification)
            await session.flush()
            await session.refresh(notification)
        return notification

    async def mark_as_unread(
        self,
        session: AsyncSession,
        notification: Notification,
    ) -> Notification:
        """Mark notification as unread with read_at set to NULL (idempotent)."""
        if notification.is_read:
            notification.is_read = False
            notification.read_at = None
            session.add(notification)
            await session.flush()
            await session.refresh(notification)
        return notification
