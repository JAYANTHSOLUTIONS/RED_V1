"""Audit repository for recording and querying immutable business and security event logs."""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sanitizer import sanitize_audit_diff
from app.models.audit import AuditLog
from app.schemas.audit import AuditFilterParams


class AuditRepository:
    """Encapsulates all database operations for immutable audit logs.
    
    Adheres strictly to an append-only architecture: provides write and query
    methods with zero update or deletion capabilities.
    """

    async def record(
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
        """Persist an immutable audit record with automatic secret and PII sanitization."""
        sanitized_diff = sanitize_audit_diff(change_diff)

        audit_log = AuditLog(
            actor_id=actor_id,
            action=action.strip(),
            entity_type=entity_type.strip().upper(),
            entity_id=entity_id,
            change_diff=sanitized_diff,
            ip_address=ip_address.strip() if ip_address else None,
            correlation_id=correlation_id.strip() if correlation_id else None,
        )
        session.add(audit_log)
        await session.flush()
        return audit_log

    async def get_by_id(
        self,
        session: AsyncSession,
        log_id: uuid.UUID,
    ) -> Optional[AuditLog]:
        """Retrieve a single audit log entry by primary key."""
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_audit_logs(
        self,
        session: AsyncSession,
        filters: Optional[AuditFilterParams] = None,
    ) -> Tuple[List[AuditLog], int]:
        """Query audit records with filtering, total count aggregation, and bounded pagination."""
        if filters is None:
            filters = AuditFilterParams()
        base_query = select(AuditLog)

        if filters.actor_id is not None:
            base_query = base_query.where(AuditLog.actor_id == filters.actor_id)

        if filters.action is not None:
            base_query = base_query.where(AuditLog.action == filters.action.strip())

        if filters.entity_type is not None:
            base_query = base_query.where(AuditLog.entity_type == filters.entity_type.strip().upper())

        if filters.entity_id is not None:
            base_query = base_query.where(AuditLog.entity_id == filters.entity_id)

        if filters.correlation_id is not None:
            base_query = base_query.where(AuditLog.correlation_id == filters.correlation_id.strip())

        if filters.from_date is not None:
            base_query = base_query.where(AuditLog.created_at >= filters.from_date)

        if filters.to_date is not None:
            base_query = base_query.where(AuditLog.created_at <= filters.to_date)

        # Count total matching rows
        count_stmt = select(func.count()).select_from(base_query.subquery())
        count_res = await session.execute(count_stmt)
        total = count_res.scalar() or 0

        # Bounded pagination with deterministic newest-first ordering
        paginated_stmt = (
            base_query
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(filters.offset)
            .limit(filters.limit)
        )
        items_res = await session.execute(paginated_stmt)
        items = list(items_res.scalars().all())

        return items, total
