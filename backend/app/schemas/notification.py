"""Notification schemas and enums.

Defines payloads for in-app alert persistence, delivery results across channels,
filtering parameters, unread counts, and safe WhatsApp deep-link generation.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NotificationChannel(str, Enum):
    IN_APP = "IN_APP"
    DASHBOARD = "DASHBOARD"  # Supported alias for IN_APP
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class NotificationType(str, Enum):
    FOLLOW_UP_DUE = "FOLLOW_UP_DUE"
    FOLLOW_UP_COMPLETED = "FOLLOW_UP_COMPLETED"
    FOLLOW_UP_MISSED = "FOLLOW_UP_MISSED"
    SITE_VISIT_REQUESTED = "SITE_VISIT_REQUESTED"
    SITE_VISIT_CONFIRMED = "SITE_VISIT_CONFIRMED"
    SITE_VISIT_RESCHEDULED = "SITE_VISIT_RESCHEDULED"
    SITE_VISIT_CANCELLED = "SITE_VISIT_CANCELLED"
    DOCUMENT_REQUIRED = "DOCUMENT_REQUIRED"
    VERIFICATION_REVIEW_REQUIRED = "VERIFICATION_REVIEW_REQUIRED"
    LEAD_STATUS_CHANGED = "LEAD_STATUS_CHANGED"
    GENERAL = "GENERAL"


class DeliveryStatus(str, Enum):
    DELIVERED = "DELIVERED"
    SENT = "SENT"
    FAILED = "FAILED"
    PENDING = "PENDING"
    READY = "READY"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class NotificationCreateInternal(BaseModel):
    """Internal creation payload used by domain services."""
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification body")
    channel: str = Field(default="IN_APP", description="Target notification channel")
    notification_type: str = Field(..., description="Operational notification type")
    entity_type: Optional[str] = Field(None, max_length=50, description="Associated entity type (e.g. FOLLOW_UP)")
    entity_id: Optional[uuid.UUID] = Field(None, description="Associated entity primary key")

    @field_validator("channel")
    @classmethod
    def normalize_channel(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper == "DASHBOARD":
            return "IN_APP"
        valid = {c.value for c in NotificationChannel}
        if v_upper not in valid and v_upper != "DASHBOARD":
            raise ValueError(f"Invalid channel '{v}'. Allowed: {', '.join(sorted(valid))}")
        return v_upper

    @field_validator("notification_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v_upper = v.strip().upper()
        valid = {t.value for t in NotificationType}
        if v_upper not in valid:
            raise ValueError(f"Invalid notification type '{v}'. Allowed: {', '.join(sorted(valid))}")
        return v_upper


class NotificationResponse(BaseModel):
    """Public serialized view of a notification record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    message: str
    channel: str
    notification_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[uuid.UUID] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationFilterParams(BaseModel):
    """Query filtering parameters for listing notifications."""
    is_read: Optional[bool] = Field(None, description="Filter by read status")
    channel: Optional[str] = Field(None, description="Filter by channel")
    notification_type: Optional[str] = Field(None, description="Filter by notification type")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    created_from: Optional[datetime] = Field(None, description="Filter created on or after")
    created_to: Optional[datetime] = Field(None, description="Filter created on or before")
    limit: int = Field(20, ge=1, le=100, description="Number of records to return (1-100)")
    offset: int = Field(0, ge=0, description="Pagination offset")


class UnreadCountResponse(BaseModel):
    """Aggregated unread count response."""
    unread_count: int = Field(..., ge=0, description="Total number of unread notifications")


class WhatsAppLinkRequest(BaseModel):
    """Payload to generate a consultant-triggered WhatsApp deep link."""
    model_config = ConfigDict(str_strip_whitespace=True)

    phone: str = Field(..., min_length=7, max_length=50, description="Client or lead phone number")
    message: str = Field(..., min_length=1, max_length=1000, description="Operational message to pre-fill")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = "".join(c for c in v if c.isdigit() or c == "+")
        digits_only = "".join(c for c in v if c.isdigit())
        if len(digits_only) < 7 or len(digits_only) > 15:
            raise ValueError("Phone number must contain between 7 and 15 digits.")
        return cleaned


class WhatsAppLinkResponse(BaseModel):
    """Result of WhatsApp deep-link generation."""
    deep_link: str = Field(..., description="Encoded https://wa.me link")
    sanitized_phone: str = Field(..., description="Sanitized digits used for link")
    message: str = Field(..., description="Message text")


class DeliveryResult(BaseModel):
    """Delivery result returned by channel providers."""
    success: bool
    status: DeliveryStatus
    channel: str
    message: Optional[str] = None
    deep_link: Optional[str] = None
    notification_id: Optional[uuid.UUID] = None
