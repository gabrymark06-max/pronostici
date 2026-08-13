"""Le prove girano su SQLite in memoria, non su Postgres.

Il rischio di questa scelta e' noto e limitato: SQLite non ha il tipo UUID
nativo, quindi il modello lo dichiara con `postgresql.UUID` e qui si sostituisce
con una variante generica. Tutto il resto — vincoli di unicita', cascata sulla
chiave esterna, transazioni — si comporta allo stesso modo, ed e' quello che le
prove verificano.

Cio' che SQLite NON verifica e' la migrazione Alembic, che e' scritta per
Postgres. Quella si prova facendola girare davvero contro un Postgres, ed e'
scritto nel README come si fa.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest.fixture(scope="session", autouse=True)
def ambiente(tmp_path_factory):
    import os

    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("CHIAVE_JWT", "chiave-di-prova-lunga-abbastanza-per-passare")
    os.environ.setdefault("AMBIENTE", "sviluppo")


@pytest_asyncio.fixture
async def app_e_db(ambiente):
    from sqlalchemy import types
    from sqlalchemy.dialects.postgresql import UUID as PgUUID

    # SQLite non conosce UUID: lo si rende come stringa. Serve solo alle prove.
    @staticmethod
    def _adatta(dialect):
        return types.CHAR(36)

    PgUUID.load_dialect_impl = lambda self, dialect: dialect.type_descriptor(types.CHAR(36))  # type: ignore[assignment]

    from centro_conti import db as modulo_db
    from centro_conti.modelli import Base

    motore = create_async_engine("sqlite+aiosqlite:///:memory:")
    fabbrica = async_sessionmaker(motore, expire_on_commit=False)
    async with motore.begin() as c:
        await c.run_sync(Base.metadata.create_all)

    modulo_db.Sessione = fabbrica  # type: ignore[assignment]

    from centro_conti.main import crea
    from centro_conti.rotte.conti import svuota_limiti

    # I limitatori vivono nel modulo e sopravvivono all'app: senza questo, i
    # tentativi falliti di una prova chiuderebbero fuori quella dopo.
    svuota_limiti()

    app = crea()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://prova"
    ) as cliente:
        yield cliente, fabbrica
    await motore.dispose()


@pytest_asyncio.fixture
async def cliente(app_e_db):
    return app_e_db[0]
