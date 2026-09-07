"""Idempotency service and helper utilities.

Provides transparent Idempotency-Key support for mutation requests:
- Detects duplicated client submissions after network drops.
- Returns identical cached response when same key + same payload is provided.
- Rejects with 409 Conflict when key is reused with a differing payload.
- Rejects with 409 Conflict when an in-flight duplicate request is detected.
- Cleans up reservations on transaction abort so retries can succeed.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Dict, Optional, Tuple
import uuid

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.repositories.idempotency import IdempotencyRepository


def compute_request_hash(payload: Any) -> str:
    """Compute deterministic SHA-256 hash of a request payload."""
    if payload is None:
        raw = b""
    elif isinstance(payload, bytes):
        raw = payload
    elif isinstance(payload, str):
        raw = payload.encode("utf-8")
    elif isinstance(payload, (dict, list)):
        raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    else:
        raw = str(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class IdempotencyService:
    """Service handling lifecycle of mutation idempotency keys."""

    def __init__(self, repo: Optional[IdempotencyRepository] = None):
        self.repo = repo or IdempotencyRepository()

    async def check_or_reserve(
        self,
        session: AsyncSession,
        key: str,
        user_id: Optional[uuid.UUID],
        endpoint: str,
        payload: Any,
    ) -> Tuple[Optional[JSONResponse], Optional[uuid.UUID]]:
        """Check if request was already processed or reserve key.

        Returns:
            (cached_response, None) if completed previously.
            (None, record_id) if newly reserved for execution.
        Raises:
            ConflictError if key is currently PROCESSING or payload differs.
        """
        req_hash = compute_request_hash(payload)
        existing = await self.repo.get_record(session, key=key, user_id=user_id, endpoint=endpoint)

        if existing:
            if existing.status == "COMPLETED":
                if existing.request_hash != req_hash:
                    raise ConflictError(
                        "Idempotency key was previously used with a different request payload.",
                        code="IDEMPOTENCY_PAYLOAD_MISMATCH",
                    )
                # Replay cached response with Idempotent-Replay header
                body = json.loads(existing.response_body) if existing.response_body else {}
                response = JSONResponse(
                    content=body,
                    status_code=existing.status_code or 200,
                    headers={"Idempotent-Replay": "true"},
                )
                return response, None
            elif existing.status == "PROCESSING":
                raise ConflictError(
                    "A request with this Idempotency-Key is currently in progress.",
                    code="IDEMPOTENCY_IN_PROGRESS",
                )

        # Reserve new record
        settings = get_settings()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.IDEMPOTENCY_EXPIRE_HOURS)
        record = await self.repo.reserve_key(
            session=session,
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            request_hash=req_hash,
            expires_at=expires_at,
        )
        return None, record.id

    async def finalize(
        self,
        session: AsyncSession,
        record_id: Optional[uuid.UUID],
        status_code: int,
        response_body: Any,
    ) -> None:
        """Mark reservation as COMPLETED and cache serialized response payload."""
        if record_id is None:
            return
        serialized = json.dumps(response_body, default=str)
        await self.repo.complete_record(
            session=session,
            record_id=record_id,
            status_code=status_code,
            response_body=serialized,
        )

    async def abort(
        self,
        session: AsyncSession,
        record_id: Optional[uuid.UUID],
    ) -> None:
        """Cancel or remove an in-flight reservation on execution failure."""
        if record_id is None:
            return
        await self.repo.delete_or_fail_record(session, record_id)
