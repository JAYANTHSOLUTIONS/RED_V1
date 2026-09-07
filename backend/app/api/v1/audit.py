"""Private Audit Log API endpoints.

Exposes read-only, authenticated consultant endpoints for reviewing immutable
audit records. Strictly prohibits modification and deletion.
"""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models.user import User
from app.schemas.audit import AuditFilterParams, AuditLogResponse
from app.schemas.common import PaginatedResponse, SuccessEnvelope, success_envelope
from app.services.audit import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])
audit_service = AuditService()


@router.get(
    "",
    response_model=SuccessEnvelope[PaginatedResponse[AuditLogResponse]],
    status_code=status.HTTP_200_OK,
    summary="List audit logs with filtering and pagination",
)
async def list_audit_logs(
    filters: AuditFilterParams = Depends(),
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retrieve paginated audit logs for consultant review and troubleshooting."""
    paginated = await audit_service.list_audit_logs(session=db, filters=filters)
    return success_envelope(
        data=paginated.model_dump(mode="json"),
        message="Audit logs retrieved successfully.",
    )


@router.get(
    "/{log_id}",
    response_model=SuccessEnvelope[AuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific audit log",
)
async def get_audit_log(
    log_id: uuid.UUID,
    current_user: User = Depends(require_roles("CONSULTANT")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Fetch details of a single immutable audit log record."""
    entry = await audit_service.get_audit_log(session=db, log_id=log_id)
    return success_envelope(
        data=entry.model_dump(mode="json"),
        message="Audit log retrieved successfully.",
    )
