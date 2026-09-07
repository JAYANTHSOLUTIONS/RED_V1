"""Operational health probes.

- `GET /health/live`  — process heartbeat only; no dependencies checked.
  Returns 200 whenever the ASGI server is running.
- `GET /health/ready` — verifies the infrastructure required to safely
  accept traffic. Currently checks database connectivity only; future
  phases can register additional checks (e.g. object storage) in
  `READINESS_CHECKS` without touching the endpoint itself.

Neither endpoint exposes connection strings, credentials, or other
infrastructure details — only a per-dependency "ok" / "unavailable" status.
"""
import asyncio
from typing import Awaitable, Callable

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.logging import get_logger
from app.schemas.common import error_envelope, success_envelope

logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])

ReadinessCheck = Callable[[AsyncSession], Awaitable[None]]


async def check_database(db: AsyncSession) -> None:
    await asyncio.wait_for(db.execute(text("SELECT 1")), timeout=2.0)


# Registry of readiness checks. Later phases (e.g. the Documents module
# adding object-storage connectivity) append here.
READINESS_CHECKS: dict[str, ReadinessCheck] = {
    "database": check_database,
}


@router.get("/live")
async def liveness() -> dict:
    return success_envelope(data={"status": "alive"}, message="Service is running.")


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    results: dict[str, str] = {}
    all_ok = True

    for name, check in READINESS_CHECKS.items():
        try:
            await check(db)
            results[name] = "ok"
        except Exception:
            logger.exception("Readiness check failed: %s", name)
            results[name] = "unavailable"
            all_ok = False

    if all_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=success_envelope(data=results, message="Service is ready."),
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_envelope(
            "SERVICE_UNAVAILABLE", "One or more dependencies are unavailable."
        ),
    )
