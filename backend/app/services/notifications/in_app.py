"""In-App notification channel provider.

Persists notification alerts directly to the database for dashboard display.
"""
from typing import Any, Dict, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.notification import NotificationRepository
from app.schemas.notification import DeliveryResult, DeliveryStatus
from app.services.notifications.base import BaseNotificationChannel


class InAppNotificationChannel(BaseNotificationChannel):
    """Channel provider for in-app / dashboard notifications."""

    @property
    def channel_name(self) -> str:
        return "IN_APP"

    def __init__(self, repo: Optional[NotificationRepository] = None):
        self.repo = repo or NotificationRepository()

    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        notification_type: str,
        user_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DeliveryResult:
        """Store notification in database if active session is passed in metadata."""
        session: Optional[AsyncSession] = None
        if metadata:
            session = metadata.get("session")

        if session is not None:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                channel="IN_APP",
                notification_type=notification_type,
                entity_type=entity_type,
                entity_id=entity_id,
                is_read=False,
            )
            created = await self.repo.create(session, notification)
            return DeliveryResult(
                success=True,
                status=DeliveryStatus.DELIVERED,
                channel="IN_APP",
                notification_id=created.id,
                message="In-app notification persisted successfully.",
            )

        return DeliveryResult(
            success=True,
            status=DeliveryStatus.READY,
            channel="IN_APP",
            message="In-app notification ready for persistence.",
        )
