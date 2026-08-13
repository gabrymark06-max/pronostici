"""Spedire posta, o fingere di spedirla.

DUE MODI, E LO SI SCEGLIE CON UNA VARIABILE.

  * `finta` (predefinito) — il messaggio finisce nei log, per intero, con
    dentro il collegamento. In sviluppo e' quello che serve: si prova il giro
    completo — registrazione, verifica, recupero — senza un account SMTP e
    senza spedire niente a nessuno per sbaglio.
  * `smtp` — spedisce davvero.

PERCHE' LA FINTA E' IL PREDEFINITO E NON UN RIPIEGO. Il ripiego silenzioso e'
il difetto peggiore che questo modulo possa avere: un servizio che crede di
spedire e non spedisce lascia le persone ad aspettare una email che non
arrivera' mai, e nessun log dice niente perche' non c'e' stato nessun errore.
Qui la finta e' una scelta esplicita che si vede nei log a ogni messaggio, e
`smtp` va acceso a mano quando ci sono le credenziali.

LA SPEDIZIONE NON PUO' FAR FALLIRE LA RICHIESTA. Se il server di posta e' giu',
la registrazione deve comunque riuscire: il profilo esiste, l'email di verifica
si puo' chiedere di nuovo. Il contrario — registrazione fallita perche' non si
e' potuto spedire — perde un utente per un guasto che non lo riguarda.

SI SPEDISCE FUORI DAL GIRO DELLA RICHIESTA. `smtplib` e' bloccante: dentro una
rotta asincrona bloccherebbe l'intero processo per i secondi della consegna, e
con una connessione SMTP lenta significa che nessun altro viene servito. Va in
un thread.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

import anyio

from .impostazioni import impostazioni

log = logging.getLogger("centro.posta")


@dataclass(frozen=True)
class Messaggio:
    a: str
    oggetto: str
    testo: str


def _spedisci_davvero(m: Messaggio) -> None:
    imp = impostazioni()
    msg = EmailMessage()
    msg["From"] = imp.posta_da
    msg["To"] = m.a
    msg["Subject"] = m.oggetto
    msg.set_content(m.testo)

    with smtplib.SMTP(imp.smtp_host, imp.smtp_porta, timeout=15) as s:
        s.starttls()
        if imp.smtp_utente and imp.smtp_password:
            s.login(imp.smtp_utente, imp.smtp_password)
        s.send_message(msg)


async def spedisci(m: Messaggio) -> None:
    """Spedisce, e non alza mai.

    Un errore di consegna si logga e finisce li'. Chi chiama non ha un ramo da
    scrivere: la richiesta va avanti comunque, per la ragione in testa al
    modulo.
    """
    imp = impostazioni()

    if imp.posta_modo == "finta":
        # Il messaggio INTERO nei log, collegamento compreso: e' l'unica cosa
        # che rende provabile il giro in sviluppo.
        log.info(
            "POSTA FINTA — non e' stata spedita.\n"
            "  a:       %s\n"
            "  oggetto: %s\n"
            "-----------------------------------------\n%s\n"
            "-----------------------------------------",
            m.a,
            m.oggetto,
            m.testo,
        )
        return

    try:
        await anyio.to_thread.run_sync(_spedisci_davvero, m)
        log.info("posta spedita", extra={"oggetto": m.oggetto})
    except Exception:
        # Non si logga il destinatario a livello di errore: un log d'errore
        # finisce spesso in servizi terzi, e l'indirizzo e' un dato personale.
        log.exception("posta NON spedita", extra={"oggetto": m.oggetto})


# --------------------------------------------------------------------------- #
# I due messaggi                                                              #
# --------------------------------------------------------------------------- #
#
# SOLO TESTO, NIENTE HTML. Un messaggio di sola sicurezza fatto di testo si
# legge ovunque, non finisce nella posta indesiderata per il peso delle
# immagini, e soprattutto non nasconde l'indirizzo dietro un bottone: chi lo
# riceve VEDE dove sta per andare. Su un'email che chiede di cambiare una
# password questa e' la cosa piu' importante di tutte.


def messaggio_verifica(nome: str, collegamento: str, ore: int) -> Messaggio:
    return Messaggio(
        a="",  # lo mette chi chiama
        oggetto="Conferma il tuo indirizzo — Centro",
        testo=(
            f"Ciao {nome},\n\n"
            "per confermare che questo indirizzo e' tuo, apri:\n\n"
            f"{collegamento}\n\n"
            f"Il collegamento vale {ore} ore. Dopo, puoi chiederne un altro dalla\n"
            "pagina del tuo profilo.\n\n"
            "Se non ti sei registrato tu, ignora questo messaggio: senza aprire\n"
            "il collegamento non succede niente.\n\n"
            "— Centro\n"
        ),
    )


def messaggio_recupero(nome: str, collegamento: str, ore: int) -> Messaggio:
    return Messaggio(
        a="",
        oggetto="Reimposta la password — Centro",
        testo=(
            f"Ciao {nome},\n\n"
            "qualcuno ha chiesto di reimpostare la password di questo profilo.\n"
            "Se sei stato tu, apri:\n\n"
            f"{collegamento}\n\n"
            f"Il collegamento vale {ore} ore e si puo' usare una volta sola.\n\n"
            "Se non sei stato tu, ignora questo messaggio: la password resta\n"
            "quella di adesso e nessuno e' entrato. Il collegamento da solo non\n"
            "fa entrare nessuno, serve solo a scegliere una password nuova.\n\n"
            "— Centro\n"
        ),
    )
