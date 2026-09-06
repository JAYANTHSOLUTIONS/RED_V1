"""Aggregates all /api/v1 routers.

Business routers (properties, leads, documents, site-visits, deals, ...)
are included here as each module is implemented in later phases. Nothing
else in the app needs to change as the API surface grows.
"""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    clients,
    documents,
    follow_ups,
    health,
    leads,
    notifications,
    properties,
    public_properties,
    requirements,
    site_visits,
    verification,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(properties.router)
api_router.include_router(public_properties.router)
api_router.include_router(clients.router)
api_router.include_router(leads.router)
api_router.include_router(requirements.router)
api_router.include_router(documents.router)
api_router.include_router(verification.router)
api_router.include_router(site_visits.router)
api_router.include_router(follow_ups.router)
api_router.include_router(notifications.router)

