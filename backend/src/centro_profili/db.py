"""Il motore e la sessione, asincroni.

`pool_pre_ping` non e' un dettaglio di prestazioni: gli hosting gestiti chiudono
le connessioni inattive senza avvisare, e senza questo la prima richiesta dopo
una pausa muore con «connection was closed in the middle of operation». Costa
un giro a vuoto per connessione ripresa, e vale.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .impostazioni import impostazioni

_imp = impostazioni()

motore = create_async_engine(
    _imp.database_url,
    pool_pre_ping=True,
    # In sviluppo le query si vedono; in produzione no, perche' finirebbero
    # nei log insieme ai valori dei parametri.
    echo=_imp.ambiente == "sviluppo",
)

Sessione = async_sessionmaker(motore, expire_on_commit=False, class_=AsyncSession)


async def sessione() -> AsyncIterator[AsyncSession]:
    """La dipendenza delle rotte. Un commit per richiesta, e rollback se salta.

    Il commit sta QUI e non nelle rotte apposta: una rotta che scrive due cose
    e ne conferma una sola lascia il database a meta', e cercare i `commit`
    sparsi per capire dove finisce una transazione e' il modo piu' facile di
    scrivere quel difetto senza accorgersene.
    """
    async with Sessione() as s:
        try:
            yield s
            await s.commit()
        except Exception:
            await s.rollback()
            raise
