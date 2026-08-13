"""Alembic, con la URL presa dalle impostazioni e non dall'ini.

`run_migrations_online` gira in modo ASINCRONO perche' il motore
dell'applicazione e' asyncpg: usarne uno sincrono qui vorrebbe dire una seconda
stringa di connessione con un altro driver, cioe' due posti dove sbagliarla.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from centro_profili.impostazioni import impostazioni
from centro_profili.modelli import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def migra(connessione) -> None:
    context.configure(
        connection=connessione,
        target_metadata=target_metadata,
        # Senza questo Alembic non vede i cambi di tipo di una colonna, e una
        # migrazione generata sembra vuota quando invece manca un pezzo.
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def offline() -> None:
    context.configure(
        url=impostazioni().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def _online() -> None:
    motore = create_async_engine(impostazioni().database_url, pool_pre_ping=True)
    async with motore.connect() as connessione:
        await connessione.run_sync(migra)
    await motore.dispose()


def online() -> None:
    asyncio.run(_online())


if context.is_offline_mode():
    offline()
else:
    online()
