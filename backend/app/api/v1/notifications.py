"""Notification API endpoints.

Exposes consultant endpoints for listing notifications, fetching unread counts,
viewing single notifications, marking notifications read/unread,
and generating safe WhatsApp deep links for client communication.
"""
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_ip_address, get_request_id, require_roles
from app.models.user import User
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.schemas.notification import (
    NotificationFilterParams,
    NotificationResponse,
    UnreadCountResponse,
    WhatsAppLinkRequest,
    WhatsAppLinkResponse,
)
from app.services.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])
notification_service = NotificationService()


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[NotificationResponse]],
    status_code=status.HTTP_200_OK,
    summary="List notifications for the current consultant",
)
async def list_notifications(
    filters: NotificationFilterParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve paginated notifications with optional status, channel, and type filters."""
    paginated = await notification_service.list_notifications(
        session=db,
        user_id=current_user.id,
        filters=filters,
    )
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Notifications retrieved successfully.",
    )


@router.get(
    "/unread-count",
    response_model=SuccessEnvelope[UnreadCountResponse],
    status_code=status.HTTP_200_OK,
    summary="Get count of unread notifications",
)
async def get_unread_count(
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Efficient SQL aggregate count of unread notifications for the current consultant."""
    count = await notification_service.get_unread_count(
        session=db,
        user_id=current_user.id,
    )
    return success_envelope(
        data={"unread_count": count},
        message="Unread notification count retrieved successfully.",
    )


@router.get(
    "/{notification_id}",
    response_model=SuccessEnvelope[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific notification",
)
async def get_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch single notification details (enforces user isolation / anti-IDOR)."""
    notification = await notification_service.get_notification(
        session=db,
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return success_envelope(
        data=NotificationResponse.model_validate(notification).model_dump(mode="json"),
        message="Notification retrieved successfully.",
    )


@router.post(
    "/{notification_id}/read",
    response_model=SuccessEnvelope[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
)
async def mark_as_read(
    notification_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark notification as read with server timestamp (idempotent)."""
    notification = await notification_service.mark_as_read(
        session=db,
        notification_id=notification_id,
        user_id=current_user.id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=NotificationResponse.model_validate(notification).model_dump(mode="json"),
        message="Notification marked as read.",
    )


@router.post(
    "/{notification_id}/unread",
    response_model=SuccessEnvelope[NotificationResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark notification as unread",
)
async def mark_as_unread(
    notification_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark notification as unread (idempotent)."""
    notification = await notification_service.mark_as_unread(
        session=db,
        notification_id=notification_id,
        user_id=current_user.id,
        actor_id=current_user.id,
        ip_address=get_ip_address(request),
        correlation_id=get_request_id(request),
    )
    return success_envelope(
        data=NotificationResponse.model_validate(notification).model_dump(mode="json"),
        message="Notification marked as unread.",
    )


@router.post(
    "/whatsapp-link",
    response_model=SuccessEnvelope[WhatsAppLinkResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate safe WhatsApp deep link for client communication",
)
async def generate_whatsapp_link(
    payload: WhatsAppLinkRequest,
    current_user: User = Depends(require_roles("CONSULTANT")),
) -> dict:
    """Generate encoded https://wa.me deep link with validated phone number."""
    response = notification_service.generate_whatsapp_link(
        phone=payload.phone,
        message=payload.message,
    )
    return success_envelope(
        data=response.model_dump(mode="json"),
        message="WhatsApp deep link generated successfully.",
    )
