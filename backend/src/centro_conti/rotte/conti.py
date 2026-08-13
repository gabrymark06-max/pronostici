"""Le rotte dei conti.

    POST /conti/registrazione   crea il conto e ti fa entrare
    POST /conti/accesso         entra
    POST /conti/rinnovo         rinnova i gettoni (rotazione)
    POST /conti/uscita          esce da questo browser
    POST /conti/uscita-ovunque  chiude tutte le sessioni
    GET  /conti/io              chi sono
    GET  /conti/sessioni        dove sono collegato
    POST /conti/password        cambia password
    POST /conti/chiusura        chiude il conto e cancella tutto

TRE DECISIONI CHE VALGONO PIU' DEL CODICE.

1. L'ERRORE D'ACCESSO E' SEMPRE LO STESSO. «Email o password non corretti»,
   che l'email esista o no. Distinguere sarebbe piu' gentile e regalerebbe a
   chiunque la lista dei clienti: si prova un elenco di indirizzi e si tiene
   quello che risponde «password sbagliata». Per la stessa ragione, quando
   l'email non esiste si verifica lo stesso una password finta — il tempo di
   risposta non deve dire niente.

2. LA REGISTRAZIONE NON DICE SE L'EMAIL E' GIA' PRESA. Direbbe la stessa cosa
   dal lato opposto. Risponde come se fosse andata bene e, quando la casella
   esiste gia', il posto dove va detto e' un messaggio a quella casella — cosa
   che si potra' fare quando ci sara' un servizio di posta. Finche' non c'e',
   il conto non viene creato e chi ha davvero sbagliato se ne accorge provando
   ad accedere. E' l'unico punto in cui questa API e' meno chiara di quanto
   vorrebbe, ed e' un debito scritto, non nascosto.

3. IL GETTONE DI RINNOVO RUOTA A OGNI USO. Usato una volta, la sua riga in
   `sessioni` sparisce e ne nasce un'altra. Se un gettone rubato viene usato
   dopo che il proprietario ha gia' rinnovato, non trova piu' la riga e non
   entra; se lo usa per primo, il proprietario viene buttato fuori al giro
   dopo e se ne accorge. In entrambi i casi qualcuno se ne accorge, che e' il
   massimo ottenibile senza un secondo fattore.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import sicurezza
from ..db import sessione
from ..dipendenze import (
    agente,
    impronta,
    posa_cookie,
    togli_cookie,
    utente_corrente,
)
from ..errori import ErroreApi
from ..impostazioni import impostazioni
from ..limiti import Limitatore
from ..modelli import Sessione as SessioneDb
from ..modelli import Utente
from ..schemi import (
    AccessoIn,
    CambioPasswordIn,
    ChiusuraContoIn,
    Fatto,
    RegistrazioneIn,
    SessioneOut,
    UtenteOut,
)

log = logging.getLogger("centro.conti")
rotte = APIRouter(prefix="/conti", tags=["conti"])

_imp = impostazioni()
# I limitatori sono di MODULO, non dell'applicazione, ed e' voluto: devono
# sopravvivere a un `crea()` — altrimenti basterebbe far ricostruire l'app per
# azzerare i tentativi. Il prezzo e' che sopravvivono anche fra una prova e
# l'altra, e per questo `svuota_limiti()` esiste ed e' chiamata dalle prove.
_limite_accesso = Limitatore(_imp.tentativi_accesso, _imp.finestra_limite_s)
_limite_registrazione = Limitatore(_imp.tentativi_registrazione, _imp.finestra_limite_s)


def svuota_limiti() -> None:
    """Solo per le prove. In esercizio non la chiama nessuno."""
    _limite_accesso._storia.clear()
    _limite_registrazione._storia.clear()


def _con_fuso(quando: datetime) -> datetime:
    """Un istante letto dal database, sempre consapevole del fuso.

    Le colonne sono `DateTime(timezone=True)` e Postgres restituisce istanti
    con il fuso. Non tutti i driver lo fanno — SQLite, che usiamo nelle prove,
    li restituisce nudi — e confrontare un istante nudo con `datetime.now(UTC)`
    solleva `TypeError` a meta' del rinnovo, cioe' sulla rotta che ogni pagina
    chiama al caricamento.

    Non e' un aggiustamento per le prove: e' che un confronto fra istanti non
    deve dipendere da quale driver c'e' sotto. Un istante nudo, in questo
    servizio, e' UTC per costruzione — li' lo abbiamo scritto noi.
    """
    return quando if quando.tzinfo is not None else quando.replace(tzinfo=UTC)


def _troppi(secondi: int) -> ErroreApi:
    return ErroreApi(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "troppi_tentativi",
        f"Troppi tentativi. Riprova fra {max(1, secondi // 60)} minuti.",
        {"Retry-After": str(secondi)},
    )


async def _apri_sessione(
    db: AsyncSession, utente: Utente, risposta: Response, ua: str | None
) -> None:
    """Conia la coppia di gettoni, registra la sessione, posa i cookie."""
    jti = uuid.uuid4()
    gen = utente.generazione
    accesso, _ = sicurezza.conia(utente.id, "accesso", gen)
    rinnovo, scade = sicurezza.conia(utente.id, "rinnovo", gen, jti=jti)
    db.add(SessioneDb(id=jti, utente_id=utente.id, scade=scade, agente=ua))
    posa_cookie(risposta, accesso, rinnovo)


# ------------------------------------------------------------------ #
# Registrazione                                                      #
# ------------------------------------------------------------------ #


@rotte.post(
    "/registrazione",
    response_model=UtenteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Crea un conto e apre subito la sessione",
)
async def registrazione(
    dati: RegistrazioneIn,
    richiesta: Request,
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
) -> Utente:
    chiave = impronta(richiesta)
    passa, attesa = _limite_registrazione.consentito(chiave)
    if not passa:
        raise _troppi(attesa)

    utente = Utente(
        email=dati.email,
        nome=dati.nome,
        hash_password=sicurezza.cifra(dati.password),
    )
    db.add(utente)
    try:
        # A decidere se l'email e' libera dev'essere il vincolo del database,
        # non una SELECT prima dell'INSERT: fra le due c'e' spazio perche' due
        # registrazioni simultanee passino entrambe.
        await db.flush()
    except IntegrityError:
        await db.rollback()
        _limite_registrazione.segna(chiave)
        log.info("registrazione su email gia' presente", extra={"impronta": chiave})
        # Vedi la decisione 2 in testa al modulo: non si conferma l'esistenza.
        raise ErroreApi(
            status.HTTP_409_CONFLICT,
            "registrazione_non_completata",
            "Non è stato possibile completare la registrazione con questi dati. "
            "Se hai già un conto con questa email, prova ad accedere.",
        ) from None

    await _apri_sessione(db, utente, risposta, agente(richiesta))
    utente.ultimo_accesso = datetime.now(UTC)
    log.info("conto creato", extra={"utente": str(utente.id)})
    return utente


# ------------------------------------------------------------------ #
# Accesso                                                            #
# ------------------------------------------------------------------ #


@rotte.post("/accesso", response_model=UtenteOut, summary="Entra")
async def accesso(
    dati: AccessoIn,
    richiesta: Request,
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
) -> Utente:
    chiave = f"{impronta(richiesta)}|{dati.email}"
    passa, attesa = _limite_accesso.consentito(chiave)
    if not passa:
        raise _troppi(attesa)

    sbagliato = ErroreApi(
        status.HTTP_401_UNAUTHORIZED,
        "credenziali_non_valide",
        "Email o password non corretti.",
    )

    utente = (
        await db.execute(select(Utente).where(Utente.email == dati.email))
    ).scalar_one_or_none()

    if utente is None:
        # Stesso tempo, stessa risposta. Vedi la decisione 1.
        sicurezza.verifica_finta(dati.password)
        _limite_accesso.segna(chiave)
        raise sbagliato

    if not sicurezza.verifica(utente.hash_password, dati.password):
        _limite_accesso.segna(chiave)
        raise sbagliato

    if not utente.attivo:
        _limite_accesso.segna(chiave)
        raise sbagliato

    # I parametri di Argon2 cambiano nel tempo. Questo e' l'unico momento in
    # cui abbiamo la password in chiaro e possiamo rifare l'hash piu' forte.
    if sicurezza.da_riconiare(utente.hash_password):
        utente.hash_password = sicurezza.cifra(dati.password)

    _limite_accesso.azzera(chiave)
    await _apri_sessione(db, utente, risposta, agente(richiesta))
    utente.ultimo_accesso = datetime.now(UTC)
    return utente


# ------------------------------------------------------------------ #
# Rinnovo                                                            #
# ------------------------------------------------------------------ #


@rotte.post("/rinnovo", response_model=UtenteOut, summary="Rinnova la sessione")
async def rinnovo(
    richiesta: Request,
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
    centro_rinnovo: Annotated[str | None, Cookie()] = None,
) -> Utente:
    scaduta = ErroreApi(
        status.HTTP_401_UNAUTHORIZED,
        "sessione_scaduta",
        "La sessione è scaduta. Accedi di nuovo.",
    )
    if not centro_rinnovo:
        raise scaduta
    try:
        corpo = sicurezza.leggi(centro_rinnovo, "rinnovo")
        jti = uuid.UUID(corpo["jti"])
        id_utente = uuid.UUID(corpo["sub"])
    except (sicurezza.GettoneNonValido, KeyError, ValueError) as exc:
        raise scaduta from exc

    riga = await db.get(SessioneDb, jti)
    if riga is None or riga.utente_id != id_utente:
        # Gettone valido nella firma ma senza riga: o e' gia' stato ruotato,
        # o e' di una sessione chiusa. In entrambi i casi non vale piu'.
        togli_cookie(risposta)
        raise scaduta
    if _con_fuso(riga.scade) < datetime.now(UTC):
        await db.delete(riga)
        togli_cookie(risposta)
        raise scaduta

    utente = await db.get(Utente, id_utente)
    if utente is None or not utente.attivo:
        await db.delete(riga)
        togli_cookie(risposta)
        raise scaduta

    # ROTAZIONE: la vecchia riga muore, ne nasce una nuova. Vedi decisione 3.
    await db.delete(riga)
    await _apri_sessione(db, utente, risposta, agente(richiesta))
    return utente


# ------------------------------------------------------------------ #
# Uscita                                                             #
# ------------------------------------------------------------------ #


@rotte.post("/uscita", response_model=Fatto, summary="Esci da questo browser")
async def uscita(
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
    centro_rinnovo: Annotated[str | None, Cookie()] = None,
) -> Fatto:
    """Cancella i cookie SEMPRE, anche se il gettone era gia' marcio.

    Un «esci» che fallisce perche' la sessione era gia' scaduta lascia
    l'utente con i cookie in mano e la sensazione di non essere uscito.
    """
    if centro_rinnovo:
        try:
            corpo = sicurezza.leggi(centro_rinnovo, "rinnovo")
            riga = await db.get(SessioneDb, uuid.UUID(corpo["jti"]))
            if riga is not None:
                await db.delete(riga)
        except (sicurezza.GettoneNonValido, KeyError, ValueError):
            pass
    togli_cookie(risposta)
    return Fatto()


@rotte.post(
    "/uscita-ovunque", response_model=Fatto, summary="Chiudi tutte le sessioni"
)
async def uscita_ovunque(
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
    utente: Annotated[Utente, Depends(utente_corrente)],
) -> Fatto:
    await db.execute(delete(SessioneDb).where(SessioneDb.utente_id == utente.id))
    # Non basta cancellare le sessioni: i gettoni d'accesso gia' emessi
    # varrebbero ancora per un quarto d'ora.
    utente.generazione += 1
    togli_cookie(risposta)
    return Fatto()


# ------------------------------------------------------------------ #
# Il conto                                                           #
# ------------------------------------------------------------------ #


@rotte.get("/io", response_model=UtenteOut, summary="Chi sono")
async def io(utente: Annotated[Utente, Depends(utente_corrente)]) -> Utente:
    return utente


@rotte.get("/sessioni", response_model=list[SessioneOut], summary="Dove sono collegato")
async def sessioni_aperte(
    db: Annotated[AsyncSession, Depends(sessione)],
    utente: Annotated[Utente, Depends(utente_corrente)],
    centro_rinnovo: Annotated[str | None, Cookie()] = None,
) -> list[SessioneOut]:
    righe = (
        (
            await db.execute(
                select(SessioneDb)
                .where(SessioneDb.utente_id == utente.id)
                .order_by(SessioneDb.creata.desc())
            )
        )
        .scalars()
        .all()
    )

    questa: uuid.UUID | None = None
    if centro_rinnovo:
        try:
            questa = uuid.UUID(sicurezza.leggi(centro_rinnovo, "rinnovo")["jti"])
        except (sicurezza.GettoneNonValido, KeyError, ValueError):
            questa = None

    return [
        SessioneOut(
            id=r.id, creata=r.creata, scade=r.scade, agente=r.agente, corrente=r.id == questa
        )
        for r in righe
    ]


@rotte.post("/password", response_model=Fatto, summary="Cambia password")
async def cambio_password(
    dati: CambioPasswordIn,
    richiesta: Request,
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
    utente: Annotated[Utente, Depends(utente_corrente)],
) -> Fatto:
    if not sicurezza.verifica(utente.hash_password, dati.password_attuale):
        raise ErroreApi(
            status.HTTP_403_FORBIDDEN,
            "password_attuale_errata",
            "La password attuale non è corretta.",
        )
    if dati.password_nuova == dati.password_attuale:
        raise ErroreApi(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "password_invariata",
            "La nuova password è uguale a quella di adesso.",
        )

    utente.hash_password = sicurezza.cifra(dati.password_nuova)

    # CAMBIARE PASSWORD CACCIA FUORI TUTTI GLI ALTRI, SUBITO. E' il motivo per
    # cui uno la cambia: se qualcuno era entrato, deve smettere di essere
    # dentro adesso, non fra quindici minuti.
    #
    # Servono ENTRAMBE le righe. La prima toglie i gettoni di rinnovo; senza la
    # seconda i gettoni d'ACCESSO gia' emessi resterebbero validi fino alla
    # scadenza, e l'altro browser continuerebbe a leggere. Misurato con un
    # browser vero: la prova su HTTP diretto non lo vedeva.
    await db.execute(delete(SessioneDb).where(SessioneDb.utente_id == utente.id))
    utente.generazione += 1

    # Poi si riapre subito QUESTA sessione, cosi' chi l'ha cambiata non si
    # ritrova buttato fuori dal proprio stesso gesto: il gettone nuovo porta
    # gia' la generazione nuova, perche' `_apri_sessione` la legge adesso.
    await _apri_sessione(db, utente, risposta, agente(richiesta))
    log.info("password cambiata", extra={"utente": str(utente.id)})
    return Fatto()


@rotte.post("/chiusura", response_model=Fatto, summary="Chiudi il conto")
async def chiusura(
    dati: ChiusuraContoIn,
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
    utente: Annotated[Utente, Depends(utente_corrente)],
) -> Fatto:
    """CANCELLA DAVVERO, non disattiva.

    Un conto «chiuso» che resta in tabella con un flag e' un archivio di dati
    personali che nessuno ha piu' motivo di conservare, ed e' esattamente la
    cosa che il GDPR chiama trattamento senza base giuridica. Le sessioni se ne
    vanno con lui per la cascata sulla chiave esterna.
    """
    if not sicurezza.verifica(utente.hash_password, dati.password):
        raise ErroreApi(
            status.HTTP_403_FORBIDDEN,
            "password_attuale_errata",
            "La password non è corretta.",
        )
    id_perso = str(utente.id)
    await db.delete(utente)
    togli_cookie(risposta)
    log.info("conto chiuso", extra={"utente": id_perso})
    return Fatto()
