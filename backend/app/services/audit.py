"""Audit domain service.

Coordinates audit event recording, filtered listing, detail queries,
and response envelope transformations.
"""
from typing import Any, Dict, List, Optional, Union
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.audit import AuditLog
from app.repositories.audit import AuditRepository
from app.schemas.audit import AuditFilterParams, AuditLogResponse
from app.schemas.common import PaginatedResponse


class AuditService:
    """Business service governing immutable audit records."""

    def __init__(self, audit_repo: Optional[AuditRepository] = None):
        self.audit_repo = audit_repo or AuditRepository()

    async def record_event(
        self,
        session: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        change_diff: Optional[Union[str, Dict[str, Any], List[Any]]] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditLog:
        """Record an immutable audit entry."""
        return await self.audit_repo.record(
            session=session,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            change_diff=change_diff,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    async def list_audit_logs(
        self,
        session: AsyncSession,
        filters: Optional[AuditFilterParams] = None,
    ) -> PaginatedResponse[AuditLogResponse]:
        """Fetch a paginated, filtered list of audit log entries."""
        if filters is None:
            filters = AuditFilterParams()
        items, total = await self.audit_repo.list_audit_logs(session, filters)
        return PaginatedResponse[AuditLogResponse](
            items=[AuditLogResponse.model_validate(item) for item in items],
            total=total,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def get_audit_log(
        self,
        session: AsyncSession,
        log_id: uuid.UUID,
    ) -> AuditLogResponse:
        """Fetch single audit log entry by ID or raise NotFoundError."""
        log_entry = await self.audit_repo.get_by_id(session, log_id)
        if log_entry is None:
            raise NotFoundError("Audit log not found.", code="AUDIT_LOG_NOT_FOUND")
        return AuditLogResponse.model_validate(log_entry)
