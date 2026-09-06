"""Alembic migration automated upgrade/downgrade test.

Verifies programmatically that migrations upgrade from empty database to head,
downgrade to base, and re-upgrade without error.
"""
from alembic import command
from alembic.config import Config
from app.core.config import get_settings


def test_alembic_upgrade_downgrade_cycle():
    """Verify full migration upgrade -> downgrade -> upgrade cycle."""
    settings = get_settings()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

    from app.db.session import engine

    # Dispose pool before dropping tables to prevent active connections holding old schema state
    engine.sync_engine.dispose()

    # 1. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # 2. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # 3. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # 4. Final upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Dispose pool after recreation so subsequent tests acquire fresh connections with new OIDs
    engine.sync_engine.dispose()
