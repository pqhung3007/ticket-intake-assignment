"""Run Alembic migrations at startup.

Several replicas (or a restart racing a new deploy) may boot at once, so the upgrade runs
inside one transaction holding a Postgres advisory lock: the first instance migrates,
the others wait and then find nothing to do.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
MIGRATION_LOCK_ID = 7_431_001  # arbitrary, app-wide


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return cfg


def _upgrade(connection: Connection) -> None:
    cfg = alembic_config()
    cfg.attributes["connection"] = connection
    command.upgrade(cfg, "head")


async def run_migrations(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        # Transaction-scoped lock: released automatically on commit/rollback, even on crash.
        await conn.execute(text("select pg_advisory_xact_lock(:id)"), {"id": MIGRATION_LOCK_ID})
        await conn.run_sync(_upgrade)
        await conn.commit()
    logger.info("migrations up to date")
