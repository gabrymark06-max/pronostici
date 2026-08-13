"""UNA SOLA FORMA D'ERRORE, su tutta l'API.

Ogni errore che esce da qui ha esattamente questa forma:

    {"errore": {"codice": "credenziali_non_valide",
                "dettaglio": "Email o password non corretti."}}

`codice` e' per le macchine e non cambia mai: il frontend ci accende sopra un
messaggio, e se un giorno riscriviamo il testo italiano non si rompe niente.
`dettaglio` e' per le persone, e' in italiano, e si puo' mostrare cosi' com'e'.

PERCHE' ANCHE GLI ERRORI DI VALIDAZIONE. FastAPI ne ha uno suo,
`{"detail": [{"loc": ..., "msg": ...}]}`, ed e' una seconda forma che il
frontend dovrebbe imparare a parte. Qui viene tradotto nella stessa busta: chi
chiama impara UN formato.

NIENTE FUGHE DI NOTIZIE. Un'eccezione non prevista diventa `errore_interno` con
un testo fisso. Il traceback finisce nei log, non nella risposta: dire a chi
sta provando le password quale riga di quale file e' esplosa e' un regalo.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

log = logging.getLogger("centro.profili")


class CorpoErrore(BaseModel):
    codice: str
    dettaglio: str


class Errore(BaseModel):
    """Il `response_model` di ogni risposta non riuscita."""

    errore: CorpoErrore


class ErroreApi(Exception):
    """L'unica eccezione che le rotte sollevano di proposito."""

    def __init__(
        self,
        stato: int,
        codice: str,
        dettaglio: str,
        intestazioni: dict[str, str] | None = None,
    ) -> None:
        super().__init__(dettaglio)
        self.stato = stato
        self.codice = codice
        self.dettaglio = dettaglio
        self.intestazioni = intestazioni or {}


def _busta(
    stato: int,
    codice: str,
    dettaglio: str,
    intestazioni: dict[str, str] | None = None,
):
    return JSONResponse(
        status_code=stato,
        content={"errore": {"codice": codice, "dettaglio": dettaglio}},
        headers=intestazioni,
    )


def registra_gestori(app: FastAPI) -> None:
    @app.exception_handler(ErroreApi)
    async def _api(_: Request, exc: ErroreApi):
        return _busta(exc.stato, exc.codice, exc.dettaglio, exc.intestazioni)

    @app.exception_handler(RequestValidationError)
    async def _validazione(_: Request, exc: RequestValidationError):
        # Il primo campo che non va, detto in italiano. L'elenco completo resta
        # in `campi` per chi vuole evidenziare piu' di un riquadro.
        campi: list[dict[str, Any]] = [
            {
                "campo": ".".join(str(p) for p in e["loc"] if p != "body"),
                "problema": e["msg"],
            }
            for e in exc.errors()
        ]
        primo = campi[0]["campo"] if campi else "il modulo"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "errore": {
                    "codice": "dati_non_validi",
                    "dettaglio": f"Controlla il campo «{primo}».",
                    "campi": campi,
                }
            },
        )

    @app.exception_handler(Exception)
    async def _imprevisto(richiesta: Request, exc: Exception):
        log.exception(
            "errore non gestito",
            extra={"percorso": richiesta.url.path, "metodo": richiesta.method},
        )
        return _busta(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "errore_interno",
            "Qualcosa si e' rotto da parte nostra. Riprova fra poco.",
        )
