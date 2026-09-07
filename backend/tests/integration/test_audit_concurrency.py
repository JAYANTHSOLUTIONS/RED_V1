"""Concurrency tests for append-only AuditLog persistence."""
import asyncio
import uuid
import pytest
from sqlalchemy import func, select, text

from app.db.session import AsyncSessionFactory
from app.models.audit import AuditLog
from app.services.audit import AuditService


@pytest.fixture(autouse=True)
async def clean_audit_logs():
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM audit_logs"))
    yield
    async with AsyncSessionFactory() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM audit_logs"))


@pytest.mark.asyncio
async def test_concurrent_audit_logging():
    """Ensure concurrent audit events from multiple sessions are recorded without contention or loss."""
    service = AuditService()
    num_concurrent_events = 20

    async def _record_single_event(index: int):
        async with AsyncSessionFactory() as session:
            async with session.begin():
                await service.record_event(
                    session=session,
                    action="CONCURRENT_EVENT",
                    entity_type="SYSTEM",
                    entity_id=uuid.uuid4(),
                    change_diff={"index": index, "data": f"thread_payload_{index}"},
                    correlation_id=f"corr-conc-{index}",
                )

    tasks = [_record_single_event(i) for i in range(num_concurrent_events)]
    await asyncio.gather(*tasks)

    # Verify all entries are present in database
    async with AsyncSessionFactory() as session:
        count_res = await session.execute(
            select(func.count(AuditLog.id)).where(AuditLog.action == "CONCURRENT_EVENT")
        )
        total_recorded = count_res.scalar()
        assert total_recorded == num_concurrent_events
