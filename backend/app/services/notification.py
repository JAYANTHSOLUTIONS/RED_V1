"""Notification domain service.

Coordinates in-app notification persistence, read/unread state machine transitions,
anti-IDOR recipient ownership checks, channel dispatch via providers,
SQL aggregate unread counts, and audit logging.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.db.session import transaction
from app.models.notification import Notification
from app.repositories.audit import AuditRepository
from app.repositories.notification import NotificationRepository
from app.repositories.user import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.notification import (
    DeliveryResult,
    DeliveryStatus,
    NotificationCreateInternal,
    NotificationFilterParams,
    NotificationResponse,
    WhatsAppLinkResponse,
)
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.whatsapp import sanitize_phone_for_whatsapp
import urllib.parse

logger = logging.getLogger("red.services.notification")


class NotificationService:
    """Business service governing notifications."""

    def __init__(
        self,
        notification_repo: Optional[NotificationRepository] = None,
        user_repo: Optional[UserRepository] = None,
        audit_repo: Optional[AuditRepository] = None,
        dispatcher: Optional[NotificationDispatcher] = None,
    ):
        self.notification_repo = notification_repo or NotificationRepository()
        self.user_repo = user_repo or UserRepository()
        self.audit_repo = audit_repo or AuditRepository()
        self.dispatcher = dispatcher or NotificationDispatcher(
            in_app_channel=None  # will use default InAppNotificationChannel
        )

    async def create_notification(
        self,
        session: AsyncSession,
        data: NotificationCreateInternal,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Notification:
        """Create and persist an in-app notification, recording an audit event."""
        # 1. Validate user existence if user_id is provided
        if data.user_id is not None:
            user = await self.user_repo.get_by_id(session, data.user_id)
            if user is None:
                raise NotFoundError("Recipient user not found.", code="USER_NOT_FOUND")

        # 2. Normalize channel (DASHBOARD alias maps to IN_APP)
        channel = data.channel.upper()
        if channel == "DASHBOARD":
            channel = "IN_APP"

        # 3. Instantiate model
        notification = Notification(
            user_id=data.user_id,
            title=data.title,
            message=data.message,
            channel=channel,
            notification_type=data.notification_type,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
            is_read=False,
        )

        created = await self.notification_repo.create(session, notification)

        # 4. Record audit event
        await self.audit_repo.record(
            session=session,
            action="NOTIFICATION_CREATED",
            entity_type="NOTIFICATION",
            entity_id=created.id,
            actor_id=actor_id or data.user_id,
            change_diff={
                "title": created.title,
                "channel": created.channel,
                "notification_type": created.notification_type,
                "user_id": str(created.user_id) if created.user_id else None,
                "entity_type": created.entity_type,
                "entity_id": str(created.entity_id) if created.entity_id else None,
            },
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

        return created

    async def list_notifications(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
        filters: NotificationFilterParams,
    ) -> PaginatedResponse[NotificationResponse]:
        """List notifications belonging strictly to the specified user."""
        items, total = await self.notification_repo.list_notifications(
            session=session,
            user_id=user_id,
            filters=filters,
        )
        return PaginatedResponse(
            items=[NotificationResponse.model_validate(item) for item in items],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get_notification(
        self,
        session: AsyncSession,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification:
        """Fetch a notification strictly belonging to the given user (anti-IDOR)."""
        notification = await self.notification_repo.get_by_id(
            session=session,
            notification_id=notification_id,
            user_id=user_id,
        )
        if notification is None:
            raise NotFoundError("Notification not found.", code="NOTIFICATION_NOT_FOUND")
        return notification

    async def mark_as_read(
        self,
        session: AsyncSession,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Notification:
        """Mark a notification as read under row-level lock (idempotent)."""
        async with transaction(session):
            notification = await self.notification_repo.get_by_id_for_update(
                session=session,
                notification_id=notification_id,
                user_id=user_id,
            )
            if notification is None:
                raise NotFoundError("Notification not found.", code="NOTIFICATION_NOT_FOUND")

            if not notification.is_read:
                updated = await self.notification_repo.mark_as_read(session, notification)
                await self.audit_repo.record(
                    session=session,
                    action="NOTIFICATION_READ",
                    entity_type="NOTIFICATION",
                    entity_id=updated.id,
                    actor_id=actor_id or user_id,
                    change_diff={"is_read": True, "read_at": str(updated.read_at)},
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )
                return updated

            return notification

    async def mark_as_unread(
        self,
        session: AsyncSession,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Notification:
        """Mark a notification as unread under row-level lock (idempotent)."""
        async with transaction(session):
            notification = await self.notification_repo.get_by_id_for_update(
                session=session,
                notification_id=notification_id,
                user_id=user_id,
            )
            if notification is None:
                raise NotFoundError("Notification not found.", code="NOTIFICATION_NOT_FOUND")

            if notification.is_read:
                updated = await self.notification_repo.mark_as_unread(session, notification)
                await self.audit_repo.record(
                    session=session,
                    action="NOTIFICATION_UNREAD",
                    entity_type="NOTIFICATION",
                    entity_id=updated.id,
                    actor_id=actor_id or user_id,
                    change_diff={"is_read": False, "read_at": None},
                    ip_address=ip_address,
                    correlation_id=correlation_id,
                )
                return updated

            return notification

    async def get_unread_count(
        self,
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> int:
        """Return the count of unread notifications for a user."""
        return await self.notification_repo.count_unread(session, user_id)

    def generate_whatsapp_link(
        self,
        phone: str,
        message: str,
    ) -> WhatsAppLinkResponse:
        """Generate a safe, URL-encoded WhatsApp deep link."""
        digits = sanitize_phone_for_whatsapp(phone)
        if len(digits) < 7 or len(digits) > 15:
            raise ValidationAppError("Phone number must contain between 7 and 15 digits.")

        encoded_msg = urllib.parse.quote(message.strip())
        deep_link = f"https://wa.me/{digits}?text={encoded_msg}"

        return WhatsAppLinkResponse(
            deep_link=deep_link,
            sanitized_phone=digits,
            message=message.strip(),
        )

    async def dispatch_external(
        self,
        channel: str,
        recipient: str,
        title: str,
        message: str,
        notification_type: str,
        user_id: Optional[uuid.UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DeliveryResult:
        """Dispatch a notification externally (Email / WhatsApp) via registered providers."""
        result = await self.dispatcher.dispatch(
            channel_name=channel,
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )
        return result

    # --- Domain Event Helper Methods ---

    async def create_follow_up_due_notification(
        self,
        session: AsyncSession,
        follow_up_id: uuid.UUID,
        action_type: str,
        user_id: uuid.UUID,
        scheduled_at_str: str,
        target_name: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Notification:
        """Generate a FOLLOW_UP_DUE operational notification for the consultant."""
        target_info = f" with {target_name}" if target_name else ""
        title = f"Follow-up Due: {action_type}"
        message = (
            f"Scheduled follow-up task ({action_type}){target_info} is due at {scheduled_at_str}."
        )
        data = NotificationCreateInternal(
            user_id=user_id,
            title=title,
            message=message,
            channel="IN_APP",
            notification_type="FOLLOW_UP_DUE",
            entity_type="FOLLOW_UP",
            entity_id=follow_up_id,
        )
        return await self.create_notification(
            session=session,
            data=data,
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def create_site_visit_notification(
        self,
        session: AsyncSession,
        site_visit_id: uuid.UUID,
        event_type: str,
        user_id: uuid.UUID,
        scheduled_at_str: str,
        property_title: Optional[str] = None,
        actor_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Notification:
        """Generate a site visit notification (REQUESTED, CONFIRMED, RESCHEDULED, CANCELLED)."""
        prop_str = f" for '{property_title}'" if property_title else ""
        title = f"Site Visit {event_type.title()}"
        message = f"Site visit{prop_str} scheduled for {scheduled_at_str} has been {event_type.lower()}."

        data = NotificationCreateInternal(
            user_id=user_id,
            title=title,
            message=message,
            channel="IN_APP",
            notification_type=f"SITE_VISIT_{event_type.upper()}",
            entity_type="SITE_VISIT",
            entity_id=site_visit_id,
        )
        return await self.create_notification(
            session=session,
            data=data,
            actor_id=actor_id,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
