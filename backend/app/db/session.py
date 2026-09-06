"""Async SQLAlchemy engine and session lifecycle management.

Provides:
  - a single shared async engine/sessionmaker for the process
  - `get_db`, a FastAPI dependency yielding one session per request,
    rolled back automatically on error
  - `transaction`, an explicit atomic-block helper for the multi-record
    writes later modules require (e.g. Deal + Commission + Audit Log)

Routers and services never touch the engine or session factory directly —
only through `get_db` / `transaction`.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.exceptions import DatabaseError
from app.core.logging import get_logger

logger = get_logger(__name__)

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one session per request.

    Any SQLAlchemy error is rolled back and re-raised as a sanitized
    `DatabaseError` so it can be safely serialized to the client by the
    centralized exception handler.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            logger.exception("Unhandled database error during request")
            raise DatabaseError() from None
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Wrap multiple repository calls in a single atomic transaction.

    Usage (Phase 2+, e.g. in a service):

        async with transaction(db) as tx_db:
            deal = await deal_repo.create(tx_db, ...)
            await commission_repo.create(tx_db, deal_id=deal.id, ...)
            await audit_repo.record(tx_db, "DEAL_CLOSED", ...)
        # commits here on success; rolls back automatically on any error,
        # leaving no partial writes.
    """
    try:
        yield session
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Transaction rolled back due to a database error")
        raise DatabaseError() from None
    except Exception:
        await session.rollback()
        raise


async def dispose_engine() -> None:
    """Dispose of the engine's connection pool on application shutdown."""
    await engine.dispose()
