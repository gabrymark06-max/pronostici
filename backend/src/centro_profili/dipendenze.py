"""Chi sta chiamando, e i cookie.

I GETTONI VIAGGIANO IN COOKIE `httpOnly`, non in `localStorage`. Un gettone in
`localStorage` e' leggibile da qualunque JavaScript giri sulla pagina: basta una
dipendenza compromessa — non un attacco al nostro codice, una riga in un
pacchetto qualsiasi — e le sessioni di tutti se ne vanno. Un cookie `httpOnly`
il JavaScript non lo vede nemmeno.

Il prezzo di questa scelta e' il CSRF, che con `localStorage` non esisterebbe.
Si paga con `SameSite` sul cookie e con l'allowlist di CORS, e si paga volentieri:
il CSRF colpisce chi visita un sito malevolo mentre e' collegato qui, la lettura
del gettone colpisce tutti insieme e in silenzio.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from . import sicurezza
from .db import sessione
from .errori import ErroreApi
from .impostazioni import impostazioni
from .modelli import Utente

COOKIE_ACCESSO = "centro_accesso"
COOKIE_RINNOVO = "centro_rinnovo"

# IL PERCORSO DEL COOKIE DI RINNOVO.
#
# Un cookie che vale trenta giorni non deve essere spedito a ogni richiesta:
# meno viaggia, meno occasioni ci sono di intercettarlo. Ma stringerlo troppo
# lo rende inutile, e qui era stato stretto troppo.
#
# Era `/profili/rinnovo`, cioe' la rotta che lo consuma. Il browser mandava il
# cookie SOLO li', quindi `/profili/uscita` non lo vedeva mai: cancellava i
# cookie dal browser e lasciava la riga in `sessioni` viva per trenta giorni.
# «Esci» sembrava funzionare — sparisci dalla pagina — e non invalidava
# niente. Chi avesse copiato quel gettone sarebbe rimasto dentro.
#
# Trovato da `test_uscita_invalida_la_sessione`, che riesuma il cookie a mano
# dopo l'uscita e prova a rientrare. E' esattamente il difetto che una prova
# «esci e verifica che sparisca dalla pagina» non avrebbe mai visto.
#
# `/profili` e' il prefisso piu' stretto che copre le tre rotte che il gettone
# gli serve davvero — rinnovo, uscita, sessioni — e continua a tenerlo fuori
# da `/salute`, `/openapi.json` e dalla documentazione.
PERCORSO_RINNOVO = "/profili"


def _comuni() -> dict:
    imp = impostazioni()
    return {
        "httponly": True,
        "secure": imp.cookie_secure,
        "samesite": imp.cookie_samesite,
        "domain": imp.cookie_dominio,
    }


def posa_cookie(risposta: Response, accesso: str, rinnovo: str) -> None:
    imp = impostazioni()
    risposta.set_cookie(
        COOKIE_ACCESSO, accesso, max_age=imp.minuti_accesso * 60, path="/", **_comuni()
    )
    risposta.set_cookie(
        COOKIE_RINNOVO,
        rinnovo,
        max_age=imp.giorni_rinnovo * 86_400,
        path=PERCORSO_RINNOVO,
        **_comuni(),
    )


def togli_cookie(risposta: Response) -> None:
    """Gli stessi attributi con cui sono stati posati.

    Un `delete_cookie` con `path` o `domain` diversi da quelli d'origine NON
    cancella niente: il browser lo tratta come un altro cookie. E' il difetto
    per cui «esci» sembra funzionare finche' non si ricarica la pagina.
    """
    imp = impostazioni()
    for nome, percorso in ((COOKIE_ACCESSO, "/"), (COOKIE_RINNOVO, PERCORSO_RINNOVO)):
        risposta.delete_cookie(
            nome,
            path=percorso,
            domain=imp.cookie_dominio,
            secure=imp.cookie_secure,
            httponly=True,
            samesite=imp.cookie_samesite,
        )


async def utente_corrente(
    db: Annotated[AsyncSession, Depends(sessione)],
    centro_accesso: Annotated[str | None, Cookie()] = None,
) -> Utente:
    non_autenticato = ErroreApi(
        status.HTTP_401_UNAUTHORIZED,
        "non_autenticato",
        "Devi accedere per vedere questa pagina.",
    )
    if not centro_accesso:
        raise non_autenticato
    try:
        corpo = sicurezza.leggi(centro_accesso, "accesso")
    except sicurezza.GettoneNonValido as exc:
        raise non_autenticato from exc

    try:
        id_utente = uuid.UUID(corpo["sub"])
    except (KeyError, ValueError) as exc:
        raise non_autenticato from exc

    utente = await db.get(Utente, id_utente)
    if utente is None or not utente.attivo:
        # Il profilo e' stato chiuso mentre il gettone era ancora valido. Non e'
        # un caso raro: la finestra e' di quindici minuti.
        raise non_autenticato

    # LA GENERAZIONE. Un gettone coniato prima dell'ultimo cambio password (o
    # dell'ultimo «esci da tutti i dispositivi») non vale piu', anche se la
    # firma torna e la scadenza e' lontana. Vedi `modelli.Utente.generazione`.
    if corpo.get("gen") != utente.generazione:
        raise non_autenticato

    return utente


def impronta(richiesta: Request) -> str:
    """Come chiamare chi sta bussando, ai fini dei limiti.

    `X-Forwarded-For` va letto perche' dietro un proxy `client.host` e'
    l'indirizzo del proxy — cioe' lo stesso per tutti — e il limitatore
    chiuderebbe fuori il mondo intero al nono tentativo di chiunque. Si prende
    il PRIMO della lista, che e' il client, e si accetta che sia falsificabile:
    per un limitatore va bene, per un controllo d'accesso non basterebbe.
    """
    inoltrato = richiesta.headers.get("x-forwarded-for")
    if inoltrato:
        return inoltrato.split(",")[0].strip()
    return richiesta.client.host if richiesta.client else "ignoto"


def agente(richiesta: Request) -> str | None:
    ua = richiesta.headers.get("user-agent")
    return ua[:200] if ua else None
