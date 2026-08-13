"""Le rotte dei profili.

    POST /profili/registrazione   crea il profilo e ti fa entrare
    POST /profili/accesso         entra
    POST /profili/rinnovo         rinnova i gettoni (rotazione)
    POST /profili/uscita          esce da questo browser
    POST /profili/uscita-ovunque  chiude tutte le sessioni
    GET  /profili/io              chi sono
    GET  /profili/sessioni        dove sono collegato
    POST /profili/password        cambia password
    POST /profili/chiusura        chiude il profilo e cancella tutto

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
   il profilo non viene creato e chi ha davvero sbagliato se ne accorge provando
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
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import posta, sicurezza
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
from ..modelli import GettoneEmail, Utente
from ..modelli import Sessione as SessioneDb
from ..schemi import (
    AccessoIn,
    CambioPasswordIn,
    ChiusuraProfiloIn,
    ConfermaRecuperoIn,
    ConfermaVerificaIn,
    Fatto,
    RecuperoIn,
    RegistrazioneIn,
    SessioneOut,
    UtenteOut,
)

log = logging.getLogger("centro.profili")
rotte = APIRouter(prefix="/profili", tags=["profili"])

_imp = impostazioni()
# I limitatori sono di MODULO, non dell'applicazione, ed e' voluto: devono
# sopravvivere a un `crea()` — altrimenti basterebbe far ricostruire l'app per
# azzerare i tentativi. Il prezzo e' che sopravvivono anche fra una prova e
# l'altra, e per questo `svuota_limiti()` esiste ed e' chiamata dalle prove.
_limite_accesso = Limitatore(_imp.tentativi_accesso, _imp.finestra_limite_s)
_limite_registrazione = Limitatore(_imp.tentativi_registrazione, _imp.finestra_limite_s)
_limite_posta = Limitatore(_imp.tentativi_posta, _imp.finestra_limite_s)

# L'elenco esiste perche' `svuota_limiti()` non se ne dimentichi uno.
_LIMITATORI = (_limite_accesso, _limite_registrazione, _limite_posta)


def svuota_limiti() -> None:
    """Solo per le prove. In esercizio non la chiama nessuno.

    DEVE ELENCARE TUTTI I LIMITATORI. `_limite_posta` e' stato aggiunto dopo e
    qui era stato dimenticato: le prove del recupero password fallivano a
    grappolo, e da sole passavano — il classico guasto che si prende per
    fragilita' delle prove invece che per quello che e', cioe' uno stato di
    modulo che sopravvive.
    """
    for limitatore in _LIMITATORI:
        limitatore._storia.clear()


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
    summary="Crea un profilo e apre subito la sessione",
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
            "Se hai già un profilo con questa email, prova ad accedere.",
        ) from None

    await _apri_sessione(db, utente, risposta, agente(richiesta))
    utente.ultimo_accesso = datetime.now(UTC)

    # L'email di conferma parte SUBITO, e se la spedizione fallisce la
    # registrazione riesce lo stesso: il profilo esiste, e il messaggio si puo'
    # chiedere di nuovo dalla pagina del profilo. Vedi `posta.spedisci`, che
    # non alza mai.
    await _spedisci_verifica(db, utente)

    log.info("profilo creato", extra={"utente": str(utente.id)})
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
# Il profilo                                                           #
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


@rotte.post("/chiusura", response_model=Fatto, summary="Chiudi il profilo")
async def chiusura(
    dati: ChiusuraProfiloIn,
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
    utente: Annotated[Utente, Depends(utente_corrente)],
) -> Fatto:
    """CANCELLA DAVVERO, non disattiva.

    Un profilo «chiuso» che resta in tabella con un flag e' un archivio di dati
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
    log.info("profilo chiuso", extra={"utente": id_perso})
    return Fatto()


# ------------------------------------------------------------------ #
# La posta: verifica dell'indirizzo e recupero della password        #
# ------------------------------------------------------------------ #
#
# DUE ROTTE CHE NON DICONO MAI SE UN INDIRIZZO ESISTE. `/recupero` risponde
# sempre allo stesso modo, che il profilo ci sia o no. E' la stessa decisione
# dell'accesso, applicata al punto in cui verrebbe piu' comodo tradirla: un
# «questa email non risulta» qui regalerebbe a chiunque un modo di verificare
# indirizzi uno per uno, senza nemmeno provare una password.
#
# IL GETTONE VIVE UNA VOLTA SOLA. Consumato, la riga sparisce. Un collegamento
# di recupero che funziona due volte e' un collegamento che funziona ancora
# quando l'email e' gia' stata letta da qualcun altro.
#
# CHIEDERNE UNO NUOVO CANCELLA IL VECCHIO. Due collegamenti vivi insieme
# raddoppiano la finestra in cui uno rubato apre, e non servono a niente.


ORE_GETTONE = _imp.ore_gettone_email


async def _crea_gettone(db: AsyncSession, utente: Utente, tipo: str) -> str:
    """Il gettone in chiaro, da mettere nell'email. Nel database va l'impronta."""
    await db.execute(
        delete(GettoneEmail).where(
            GettoneEmail.utente_id == utente.id, GettoneEmail.tipo == tipo
        )
    )
    grezzo, impronta_gettone = sicurezza.gettone_email()
    db.add(
        GettoneEmail(
            utente_id=utente.id,
            tipo=tipo,
            impronta=impronta_gettone,
            scade=datetime.now(UTC) + timedelta(hours=ORE_GETTONE),
        )
    )
    return grezzo


async def _consuma_gettone(db: AsyncSession, grezzo: str, tipo: str) -> Utente | None:
    """L'utente del gettone, e il gettone sparisce. `None` se non vale."""
    riga = (
        await db.execute(
            select(GettoneEmail).where(
                GettoneEmail.impronta == sicurezza.impronta_di(grezzo),
                GettoneEmail.tipo == tipo,
            )
        )
    ).scalar_one_or_none()
    if riga is None:
        return None

    scaduto = _con_fuso(riga.scade) < datetime.now(UTC)
    utente = await db.get(Utente, riga.utente_id)
    # Si cancella comunque: se e' scaduto non serve piu', se e' buono e' stato
    # usato adesso. In entrambi i casi non deve restare.
    await db.delete(riga)
    if scaduto or utente is None or not utente.attivo:
        return None
    return utente


async def _spedisci_verifica(db: AsyncSession, utente: Utente) -> None:
    grezzo = await _crea_gettone(db, utente, "verifica")
    m = posta.messaggio_verifica(
        utente.nome, f"{_imp.sito}/verifica/?g={grezzo}", ORE_GETTONE
    )
    await posta.spedisci(replace(m, a=utente.email))


@rotte.post(
    "/verifica/invio",
    response_model=Fatto,
    summary="Rispedisci l'email di conferma dell'indirizzo",
)
async def invio_verifica(
    db: Annotated[AsyncSession, Depends(sessione)],
    utente: Annotated[Utente, Depends(utente_corrente)],
) -> Fatto:
    if utente.email_verificata:
        raise ErroreApi(
            status.HTTP_409_CONFLICT,
            "email_gia_verificata",
            "Questo indirizzo è già confermato.",
        )
    chiave = f"verifica|{utente.id}"
    passa, attesa = _limite_posta.consentito(chiave)
    if not passa:
        raise _troppi(attesa)
    _limite_posta.segna(chiave)
    await _spedisci_verifica(db, utente)
    return Fatto()


@rotte.post("/verifica", response_model=UtenteOut, summary="Conferma l'indirizzo")
async def verifica(
    dati: ConfermaVerificaIn,
    db: Annotated[AsyncSession, Depends(sessione)],
) -> Utente:
    """NON richiede di essere collegati.

    Chi apre il collegamento puo' averlo aperto sul telefono, o in un altro
    browser, o dopo giorni. Chiedergli di accedere prima di poter confermare
    l'indirizzo e' un giro a vuoto: il gettone e' gia' la prova che quella
    casella e' sua, che e' esattamente la cosa che stiamo verificando.
    """
    utente = await _consuma_gettone(db, dati.gettone, "verifica")
    if utente is None:
        raise ErroreApi(
            status.HTTP_400_BAD_REQUEST,
            "gettone_non_valido",
            "Questo collegamento non vale più. "
            "Chiedine un altro dalla pagina del tuo profilo.",
        )
    utente.email_verificata = True
    log.info("email verificata", extra={"utente": str(utente.id)})
    return utente


@rotte.post(
    "/recupero", response_model=Fatto, summary="Chiedi di reimpostare la password"
)
async def recupero(
    dati: RecuperoIn,
    richiesta: Request,
    db: Annotated[AsyncSession, Depends(sessione)],
) -> Fatto:
    """Risponde SEMPRE allo stesso modo, che il profilo esista o no."""
    chiave = f"recupero|{impronta(richiesta)}"
    passa, attesa = _limite_posta.consentito(chiave)
    if not passa:
        raise _troppi(attesa)
    _limite_posta.segna(chiave)

    utente = (
        await db.execute(select(Utente).where(Utente.email == dati.email))
    ).scalar_one_or_none()

    if utente is not None and utente.attivo:
        grezzo = await _crea_gettone(db, utente, "recupero")
        m = posta.messaggio_recupero(
            utente.nome, f"{_imp.sito}/recupero/conferma/?g={grezzo}", ORE_GETTONE
        )
        await posta.spedisci(replace(m, a=utente.email))
        log.info("recupero chiesto", extra={"utente": str(utente.id)})
    else:
        log.info("recupero su indirizzo sconosciuto", extra={"impronta": chiave})

    return Fatto()


@rotte.post(
    "/recupero/conferma",
    response_model=Fatto,
    summary="Scegli la password nuova con il gettone ricevuto",
)
async def conferma_recupero(
    dati: ConfermaRecuperoIn,
    risposta: Response,
    db: Annotated[AsyncSession, Depends(sessione)],
) -> Fatto:
    utente = await _consuma_gettone(db, dati.gettone, "recupero")
    if utente is None:
        raise ErroreApi(
            status.HTTP_400_BAD_REQUEST,
            "gettone_non_valido",
            "Questo collegamento non vale più. "
            "Chiedine un altro dalla pagina di accesso.",
        )

    utente.hash_password = sicurezza.cifra(dati.password_nuova)

    # STESSA COSA DEL CAMBIO PASSWORD, e per la stessa ragione: chi reimposta
    # la password lo fa quasi sempre perche' teme che qualcuno sia entrato.
    # Tutte le sessioni cadono, e con la generazione cadono anche i gettoni
    # d'accesso gia' emessi.
    await db.execute(delete(SessioneDb).where(SessioneDb.utente_id == utente.id))
    utente.generazione += 1

    # NON si apre una sessione qui. Chi ha reimpostato deve entrare con la
    # password nuova: e' la prova che se l'e' segnata, e se il collegamento
    # fosse stato intercettato l'intruso non si troverebbe comunque una
    # sessione aperta in mano.
    togli_cookie(risposta)

    # L'indirizzo risulta confermato per forza: il gettone e' arrivato li'.
    utente.email_verificata = True
    log.info("password reimpostata", extra={"utente": str(utente.id)})
    return Fatto()
