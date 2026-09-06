"""Data-access layer.

Repositories wrap SQLAlchemy queries for a single model/aggregate and are
the only layer allowed to touch the ORM session directly. They contain no
HTTP concerns and no business rules.
"""
from app.repositories.user import UserRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.audit import AuditRepository
from app.repositories.property import PropertyRepository
from app.repositories.client import ClientRepository
from app.repositories.lead import LeadRepository
from app.repositories.requirement import PropertyRequirementRepository
from app.repositories.document import DocumentRepository

__all__ = [
    "UserRepository",
    "RefreshTokenRepository",
    "AuditRepository",
    "PropertyRepository",
    "ClientRepository",
    "LeadRepository",
    "PropertyRequirementRepository",
    "DocumentRepository",
]
