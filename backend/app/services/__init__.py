"""Business/service layer.

Services orchestrate one or more repositories inside a single transaction
and enforce business rules (state machines, RBAC checks, financial
calculations, etc.). Routers call services; services never talk HTTP.
"""
from app.services.auth import AuthService
from app.services.property import PropertyService
from app.services.client import ClientService
from app.services.lead import LeadService
from app.services.matching import DeterministicMatchingEngine
from app.services.requirement import PropertyRequirementService
from app.services.document import DocumentService

__all__ = [
    "AuthService",
    "PropertyService",
    "ClientService",
    "LeadService",
    "DeterministicMatchingEngine",
    "PropertyRequirementService",
    "DocumentService",
]
