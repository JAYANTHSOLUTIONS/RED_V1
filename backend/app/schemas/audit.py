"""Audit schemas, filter parameters, and action catalog."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AuditAction(str, Enum):
    # Authentication & Security
    AUTH_LOGIN_SUCCESS = "LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE = "LOGIN_FAILURE"
    AUTH_REFRESH_TOKEN_ROTATED = "REFRESH_TOKEN_ROTATED"
    AUTH_REFRESH_TOKEN_REUSE_DETECTED = "REFRESH_TOKEN_REUSE_DETECTED"
    AUTH_REFRESH_TOKEN_EXPIRED = "REFRESH_TOKEN_EXPIRED"
    AUTH_LOGOUT = "LOGOUT"
    SECURITY_FORBIDDEN_ACCESS = "SECURITY_FORBIDDEN_ACCESS"
    SECURITY_UNAUTHORIZED_ACCESS = "SECURITY_UNAUTHORIZED_ACCESS"

    # Properties
    PROPERTY_CREATED = "PROPERTY_CREATED"
    PROPERTY_UPDATED = "PROPERTY_UPDATED"
    PROPERTY_PUBLISHED = "PROPERTY_PUBLISHED"
    PROPERTY_PAUSED = "PROPERTY_PAUSED"
    PROPERTY_ARCHIVED = "PROPERTY_ARCHIVED"
    PROPERTY_STATUS_CHANGED = "PROPERTY_STATUS_CHANGED"

    # Clients & Leads
    CLIENT_CREATED = "CLIENT_CREATED"
    CLIENT_UPDATED = "CLIENT_UPDATED"
    CLIENT_ARCHIVED = "CLIENT_ARCHIVED"
    LEAD_CREATED = "LEAD_CREATED"
    LEAD_UPDATED = "LEAD_UPDATED"
    LEAD_STATUS_CHANGED = "LEAD_STATUS_CHANGED"
    LEAD_ARCHIVED = "LEAD_ARCHIVED"

    # Requirements
    REQUIREMENT_CREATED = "REQUIREMENT_CREATED"
    REQUIREMENT_UPDATED = "REQUIREMENT_UPDATED"
    REQUIREMENT_MATCHED = "REQUIREMENT_MATCHED"

    # Documents
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_UPDATED = "DOCUMENT_UPDATED"
    DOCUMENT_ARCHIVED = "DOCUMENT_ARCHIVED"
    DOCUMENT_STATUS_CHANGED = "DOCUMENT_STATUS_CHANGED"
    DOCUMENT_ACCESSED = "DOCUMENT_ACCESSED"

    # Verification
    VERIFICATION_REQUESTED = "VERIFICATION_REQUESTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    VERIFICATION_NEEDS_REVIEW = "VERIFICATION_NEEDS_REVIEW"
    VERIFICATION_REVIEWED = "VERIFICATION_REVIEWED"

    # Site Visits
    SITE_VISIT_CREATED = "SITE_VISIT_CREATED"
    SITE_VISIT_CONFIRMED = "SITE_VISIT_CONFIRMED"
    SITE_VISIT_COMPLETED = "SITE_VISIT_COMPLETED"
    SITE_VISIT_CANCELLED = "SITE_VISIT_CANCELLED"
    SITE_VISIT_RESCHEDULED = "SITE_VISIT_RESCHEDULED"
    SITE_VISIT_UPDATED = "SITE_VISIT_UPDATED"

    # Follow-ups
    FOLLOW_UP_CREATED = "FOLLOW_UP_CREATED"
    FOLLOW_UP_UPDATED = "FOLLOW_UP_UPDATED"
    FOLLOW_UP_COMPLETED = "FOLLOW_UP_COMPLETED"
    FOLLOW_UP_MISSED = "FOLLOW_UP_MISSED"

    # Notifications
    NOTIFICATION_CREATED = "NOTIFICATION_CREATED"
    NOTIFICATION_READ = "NOTIFICATION_READ"
    NOTIFICATION_UNREAD = "NOTIFICATION_UNREAD"


class AuditLogResponse(BaseModel):
    """Public serialized view of an immutable audit record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    change_diff: Optional[str] = None
    ip_address: Optional[str] = None
    correlation_id: Optional[str] = None
    created_at: datetime


class AuditFilterParams(BaseModel):
    """Query parameters for filtering and paginating audit logs."""
    actor_id: Optional[uuid.UUID] = Field(None, description="Filter by actor user ID")
    action: Optional[str] = Field(None, description="Filter by action name")
    entity_type: Optional[str] = Field(None, description="Filter by target entity type")
    entity_id: Optional[uuid.UUID] = Field(None, description="Filter by target entity UUID")
    correlation_id: Optional[str] = Field(None, description="Filter by request correlation ID")
    from_date: Optional[datetime] = Field(None, description="Filter records created on or after timestamp")
    to_date: Optional[datetime] = Field(None, description="Filter records created on or before timestamp")
    limit: int = Field(50, ge=1, le=100, description="Page size (1-100, default 50)")
    offset: int = Field(0, ge=0, description="Offset for pagination")
