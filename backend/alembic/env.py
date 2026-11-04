"""Alembic environment.

Two entry points:
- At app startup, app/db/migrate.py passes an open connection via `config.attributes`.
- From the CLI (`alembic upgrade head`, `alembic revision --autogenerate`), a connection
  is created from the app settings.
"""

import asyncio

from alembic import context
from sqlalchemy import Connection

from app.core.config import get_settings
from app.db.base import Base

# Import every feature's models so autogenerate sees all tables.
from app.tickets import models as _tickets_models  # noqa: F401
from app.users import models as _users_models  # noqa: F401

target_metadata = Base.metadata


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def _run_from_settings() -> None:
    from app.db.session import create_engine

    engine = create_engine(get_settings())
    async with engine.connect() as conn:
        await conn.run_sync(_run)
        await conn.commit()
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline (SQL script) mode is not supported; run against a database.")

connection = context.config.attributes.get("connection")
if connection is not None:
    _run(connection)
else:
    asyncio.run(_run_from_settings())
