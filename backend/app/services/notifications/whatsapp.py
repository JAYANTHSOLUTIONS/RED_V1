"""WhatsApp deep-link notification channel provider.

Generates safe, encoded WhatsApp deep links for consultant-triggered communication.
Strictly avoids automated bots, unofficial APIs, and web scraping.
"""
from typing import Any, Dict, Optional
import urllib.parse
import uuid

from app.schemas.notification import DeliveryResult, DeliveryStatus
from app.services.notifications.base import BaseNotificationChannel


def sanitize_phone_for_whatsapp(phone: str) -> str:
    """Extract numeric digits and ensure valid Indian/international country prefix."""
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        # Standard 10-digit Indian mobile number: prefix with 91
        digits = f"91{digits}"
    return digits


class WhatsAppDeepLinkChannel(BaseNotificationChannel):
    """Channel provider for generating safe WhatsApp deep links."""

    @property
    def channel_name(self) -> str:
        return "WHATSAPP"

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
        """Format a safe WhatsApp deep link for the consultant."""
        if not recipient:
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                channel="WHATSAPP",
                message="Recipient phone number is required.",
            )

        sanitized = sanitize_phone_for_whatsapp(recipient)
        if len(sanitized) < 7 or len(sanitized) > 15:
            return DeliveryResult(
                success=False,
                status=DeliveryStatus.FAILED,
                channel="WHATSAPP",
                message="Invalid phone number format for WhatsApp link.",
            )

        # Build message payload incorporating title if provided and not already in message
        full_message = message.strip()
        if title and title.strip() not in full_message:
            full_message = f"*{title.strip()}*\n{full_message}"

        encoded_text = urllib.parse.quote(full_message)
        deep_link = f"https://wa.me/{sanitized}?text={encoded_text}"

        return DeliveryResult(
            success=True,
            status=DeliveryStatus.READY,
            channel="WHATSAPP",
            deep_link=deep_link,
            message="WhatsApp deep link generated successfully.",
        )
