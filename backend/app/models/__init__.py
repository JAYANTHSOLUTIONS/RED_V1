"""SQLAlchemy model registry.

Registers all domain models onto `Base.metadata` for Alembic migrations,
runtime query construction, and cross-model relationships.
"""
from app.models.audit import AuditLog
from app.models.client import Client
from app.models.deal import Deal, Fee
from app.models.document import Document
from app.models.follow_up import FollowUp
from app.models.lead import Enquiry, Lead
from app.models.notification import Notification
from app.models.property import Property, PropertyImage
from app.models.requirement import PropertyRequirement
from app.models.setting import SystemSetting
from app.models.site_visit import SiteVisit
from app.models.user import RefreshToken, User
from app.models.verification import VerificationCase, VerificationItem

__all__ = [
    "AuditLog",
    "Client",
    "Deal",
    "Document",
    "Enquiry",
    "Fee",
    "FollowUp",
    "Lead",
    "Notification",
    "Property",
    "PropertyImage",
    "PropertyRequirement",
    "RefreshToken",
    "SystemSetting",
    "SiteVisit",
    "User",
    "VerificationCase",
    "VerificationItem",
]
