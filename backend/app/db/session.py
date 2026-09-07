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

from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.exceptions import DatabaseError, ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
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

    Any operational database failure or pool timeout is rolled back and re-raised as
    `ServiceUnavailableError` (HTTP 503). Other SQLAlchemy errors become `DatabaseError` (HTTP 500).
    """
    try:
        async with AsyncSessionFactory() as session:
            try:
                yield session
            except (OperationalError, TimeoutError):
                await session.rollback()
                logger.exception("Database connection/pool failure during request")
                raise ServiceUnavailableError(
                    "Database service is temporarily unavailable. Please try again shortly."
                ) from None
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Unhandled database error during request")
                raise DatabaseError() from None
            except Exception:
                await session.rollback()
                raise
    except (OperationalError, TimeoutError):
        logger.exception("Failed to acquire database connection from pool")
        raise ServiceUnavailableError(
            "Database service is temporarily unavailable. Please try again shortly."
        ) from None


@asynccontextmanager
async def transaction(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    """Wrap multiple repository calls in a single atomic transaction."""
    try:
        yield session
        await session.commit()
    except (OperationalError, TimeoutError):
        await session.rollback()
        logger.exception("Transaction rolled back due to database connection/pool failure")
        raise ServiceUnavailableError(
            "Database service is temporarily unavailable. Please try again shortly."
        ) from None
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
