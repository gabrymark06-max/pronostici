"""L'applicazione.

PERCHE' UN SERVIZIO SEPARATO E NON UNA PARTE DEL SITO. Il sito e' un export
statico: nessun runtime, nessuna chiave, e per questo non puo' rompersi sotto
carico ne' consumare quote. Quella decisione (brief 11.2) regge il prodotto e
non si tocca. I profili hanno bisogno di un server, quindi il server e' un'altra
cosa, con un altro indirizzo e un altro ciclo di vita: se questo servizio cade,
il sito continua a funzionare e a pubblicare pronostici — si perde solo la
possibilita' di accedere.

E' il motivo per cui vale la pena tenerli separati anche se costa un dominio in
piu': la parte che puo' rompersi non deve poter portare giu' quella che non
puo'.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import motore
from .errori import Errore, registra_gestori
from .impostazioni import impostazioni
from .rotte.profili import rotte as rotte_profili

logging.basicConfig(
    level=logging.INFO,
    format='{"quando":"%(asctime)s","livello":"%(levelname)s","dove":"%(name)s","cosa":"%(message)s"}',
)
log = logging.getLogger("centro.profili")


@asynccontextmanager
async def ciclo(_: FastAPI) -> AsyncIterator[None]:
    imp = impostazioni()
    log.info("avvio: ambiente=%s origini=%s", imp.ambiente, ",".join(imp.origini))
    # NIENTE `create_all` QUI. Lo schema lo fa Alembic, e basta: `create_all`
    # crea le tabelle mancanti ma non modifica quelle che ci sono, quindi il
    # giorno di una colonna nuova funziona in sviluppo (database vuoto) e
    # fallisce in produzione (tabella piena) — nel modo peggiore, cioe' senza
    # dire niente finche' qualcuno non usa quella colonna.
    yield
    await motore.dispose()


def crea() -> FastAPI:
    imp = impostazioni()
    app = FastAPI(
        title=imp.nome,
        version="1.0.0",
        summary="Profili del sito dei pronostici: registrazione, accesso, sessioni.",
        description=(
            "Ogni errore ha la stessa forma: "
            '`{"errore": {"codice": "...", "dettaglio": "..."}}`. '
            "`codice` è stabile e va usato dal codice, `dettaglio` è in italiano "
            "e si può mostrare così com'è.\n\n"
            "I gettoni viaggiano in cookie `httpOnly`, mai nel corpo: nessuna "
            "risposta di questa API contiene un gettone."
        ),
        lifespan=ciclo,
        # La documentazione interattiva resta accesa anche in produzione: e' un
        # servizio pubblico senza segreti nelle rotte, e un'API il cui contratto
        # si legge da fuori e' un'API che il frontend non deve indovinare.
        docs_url="/documentazione",
        redoc_url=None,
        openapi_url="/openapi.json",
        # Ogni rotta puo' fallire, e fallisce sempre con questa forma. Dirlo qui
        # una volta la mette nell'OpenAPI di tutte senza ripeterlo su ognuna.
        responses={
            400: {"model": Errore},
            401: {"model": Errore},
            403: {"model": Errore},
            409: {"model": Errore},
            422: {"model": Errore},
            429: {"model": Errore},
            500: {"model": Errore},
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=imp.origini,
        allow_credentials=True,
        # Solo quello che si usa davvero. `allow_methods=["*"]` non e' un buco
        # di sicurezza ma e' una dichiarazione falsa: dice che l'API accetta
        # verbi che non ha.
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        max_age=600,
    )

    registra_gestori(app)
    app.include_router(rotte_profili)

    @app.get("/salute", tags=["servizio"], summary="Il servizio è in piedi")
    async def salute() -> dict[str, str]:
        return {"stato": "va"}

    return app


app = crea()
