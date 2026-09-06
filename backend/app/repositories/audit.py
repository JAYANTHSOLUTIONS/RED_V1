"""Audit repository for recording immutable business and security event logs."""
import json
from typing import Any, Dict, Optional, Union
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    async def record(
        self,
        session: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        change_diff: Optional[Union[str, Dict[str, Any]]] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditLog:
        diff_str: Optional[str] = None
        if change_diff is not None:
            if isinstance(change_diff, dict):
                diff_str = json.dumps(change_diff)
            else:
                diff_str = str(change_diff)

        audit_log = AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            change_diff=diff_str,
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
        session.add(audit_log)
        await session.flush()
        return audit_log
