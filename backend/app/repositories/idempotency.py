"""Idempotency repository layer.

Provides atomic persistence, lookup, and status tracking for client mutation idempotency keys.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.idempotency import IdempotencyRecord


class IdempotencyRepository:
    """Repository handling idempotency record persistence."""

    async def get_record(
        self,
        session: AsyncSession,
        key: str,
        user_id: Optional[uuid.UUID],
        endpoint: str,
    ) -> Optional[IdempotencyRecord]:
        """Fetch active idempotency record by key, user_id, and endpoint."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(IdempotencyRecord)
            .where(
                IdempotencyRecord.key == key,
                IdempotencyRecord.user_id == user_id,
                IdempotencyRecord.endpoint == endpoint,
                IdempotencyRecord.expires_at > now,
            )
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def reserve_key(
        self,
        session: AsyncSession,
        key: str,
        user_id: Optional[uuid.UUID],
        endpoint: str,
        request_hash: str,
        expires_at: datetime,
    ) -> IdempotencyRecord:
        """Reserve idempotency key in PROCESSING state under transaction."""
        record = IdempotencyRecord(
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            request_hash=request_hash,
            status="PROCESSING",
            expires_at=expires_at,
        )
        session.add(record)
        try:
            await session.commit()
            return record
        except IntegrityError as exc:
            # Concurrent identical request attempted reservation
            await session.rollback()
            raise ConflictError(
                "A concurrent request with this Idempotency-Key is currently being processed.",
                code="IDEMPOTENCY_CONFLICT",
            ) from exc

    async def complete_record(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
        status_code: int,
        response_body: str,
    ) -> None:
        """Update record to COMPLETED state with serialized response."""
        stmt = select(IdempotencyRecord).where(IdempotencyRecord.id == record_id)
        result = await session.execute(stmt)
        rec = result.scalars().first()
        if rec:
            rec.status = "COMPLETED"
            rec.status_code = status_code
            rec.response_body = response_body
            await session.commit()

    async def delete_or_fail_record(
        self,
        session: AsyncSession,
        record_id: uuid.UUID,
    ) -> None:
        """Remove or mark failed an in-flight reservation so subsequent retries are not blocked."""
        stmt = delete(IdempotencyRecord).where(IdempotencyRecord.id == record_id)
        await session.execute(stmt)
        await session.commit()
