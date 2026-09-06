"""Notification dispatcher.

Routes notification dispatch requests to the registered channel provider.
"""
from typing import Any, Dict, Optional
import uuid

from app.schemas.notification import DeliveryResult, DeliveryStatus
from app.services.notifications.base import BaseNotificationChannel
from app.services.notifications.email import EmailNotificationChannel
from app.services.notifications.in_app import InAppNotificationChannel
from app.services.notifications.whatsapp import WhatsAppDeepLinkChannel


class NotificationDispatcher:
    """Dispatches notifications to the corresponding channel provider."""

    def __init__(
        self,
        in_app_channel: Optional[BaseNotificationChannel] = None,
        email_channel: Optional[BaseNotificationChannel] = None,
        whatsapp_channel: Optional[BaseNotificationChannel] = None,
    ):
        self._channels: Dict[str, BaseNotificationChannel] = {}

        # Register default or provided channels
        in_app = in_app_channel or InAppNotificationChannel()
        email = email_channel or EmailNotificationChannel()
        whatsapp = whatsapp_channel or WhatsAppDeepLinkChannel()

        self.register_channel(in_app)
        self.register_channel(email)
        self.register_channel(whatsapp)
        # Support DASHBOARD alias for IN_APP
        self._channels["DASHBOARD"] = in_app

    def register_channel(self, channel: BaseNotificationChannel) -> None:
        """Register a channel provider instance."""
        self._channels[channel.channel_name.upper()] = channel

    def get_channel(self, channel_name: str) -> Optional[BaseNotificationChannel]:
        """Look up registered channel provider by name."""
        return self._channels.get(channel_name.upper())

    async def dispatch(
        self,
        channel_name: str,
        recipient: str,
        title: str,
        message: str,
        notification_type: str,
        user_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DeliveryResult:
        """Dispatch notification to specified channel."""
        ch_upper = channel_name.strip().upper()
        provider = self.get_channel(ch_upper)

        if provider is None:
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                channel=ch_upper,
                message=f"Notification channel '{channel_name}' is not supported or configured.",
            )

        return await provider.send(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )
