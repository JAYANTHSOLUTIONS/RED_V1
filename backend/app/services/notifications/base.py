"""Base notification channel interface.

Defines the abstract protocol implemented by all notification delivery providers.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import uuid

from app.schemas.notification import DeliveryResult


class BaseNotificationChannel(ABC):
    """Abstract interface for notification delivery channels."""

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """The identifier of the channel (e.g. 'IN_APP', 'EMAIL', 'WHATSAPP')."""
        pass

    @abstractmethod
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
        """Deliver the notification or generate the communication artifact."""
        pass
