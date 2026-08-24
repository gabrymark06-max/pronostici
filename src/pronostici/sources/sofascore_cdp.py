"""Trasporto di riserva: le stesse chiamate, ma fatte da dentro un Chrome vero.

PERCHE' ESISTE. Dal 23 agosto 2026 `api.sofascore.com` risponde
`{"error": {"code": 403, "reason": "challenge"}}` a `curl_cffi`. La diagnosi,
per esclusione:

* non e' l'impronta TLS — provate tutte e 53 le firme di `curl_cffi`, nessuna
  passa;
* non e' l'IP — il sito aperto in un browser normale, sulla stessa macchina e
  nello stesso momento, mostra le partite;
* non e' il browser in se' — un Chrome guidato con i flag di automazione
  prende 403 anche lui, e la pagina di Sofascore resta vuota;
* non sono i cookie — quelli del sito, passati a `curl_cffi`, non cambiano
  niente.

E' che il sito manda **due header** che noi non mandavamo:

* `X-Captcha`, un JWT firmato da loro, **legato all'IP** e valido circa
  un'ora;
* `X-Requested-With`, un valore corto che accompagna il primo.

Con quei due header, e la richiesta partita da dentro la pagina, `/event/{id}`
torna 200. Con quei due header ma la richiesta fatta da `curl_cffi`, resta 403:
il token e' legato anche alla connessione che lo ha ottenuto, quindi non si
puo' portare fuori. Da qui la forma di questo modulo — il browser non serve
per *leggere* la pagina, serve per *essere* la connessione autorizzata.

COSA NON RISOLVE. Serve un Chrome installato, quindi su un runner di GitHub
questo non parte cosi' com'e'. Il token e' inoltre legato all'IP: se Sofascore
non ne emette uno per gli indirizzi da datacenter, non basterebbe nemmeno
installarci Chrome. Va provato, non dato per scontato.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

PORTA = int(os.environ.get("SOFASCORE_CDP_PORT", "9222"))
ORIGINE = "https://www.sofascore.com"
PAGINA = f"{ORIGINE}/football"

# DOVE SI PARCHEGGIA DOPO AVER PRESO IL TOKEN.
#
# Il sito e' un'applicazione a pagina singola: cambia rotta da sola mentre
# lavoriamo, e ogni cambio butta via il contesto JavaScript in cui girano le
# nostre `fetch` — CDP risponde «Inspected target navigated or closed» e il
# giro muore a meta'. Un file statico dello stesso dominio risolve entrambe le
# cose: l'origine resta quella giusta, quindi le chiamate sono same-origin e i
# cookie valgono, ma non c'e' nessuna applicazione che si muova sotto di noi.
PARCHEGGIO = f"{ORIGINE}/robots.txt"
PROFILO = Path.home() / ".pronostici" / "chrome-sofascore"

# Quanto aspettare che Chrome apra la porta di debug, e che la pagina faccia le
# sue prime chiamate: il token si cattura da quelle, non c'e' un endpoint che
# lo regali.
ATTESA_AVVIO_S = 30
ATTESA_TOKEN_S = 45

# QUANDO ARRIVA UN 403 DAL BROWSER.
#
# Non e' il muro di prima — quello si riconosce perche' non passa mai niente.
# Qui il token c'e' ed e' valido: e' la quota per IP che si e' esaurita, e si
# vede perche' anche le chiamate che funzionavano un minuto fa cominciano a
# rispondere 403 insieme.
#
# Misurato il 23 agosto 2026: un giro intero passa senza problemi, sei giri di
# fila no. Le cadenze vere sono due al giorno, quindi in esercizio il caso non
# si presenta; ma un rilancio a mano dopo un errore non deve mandare all'aria
# il giro successivo. Si aspetta, si rinnova il token, si riprova.
ATTESE_403_S = (20, 60)

# E QUANDO SI SMETTE DEL TUTTO.
#
# Le attese sopra hanno senso per un 403 isolato. Se pero' la quota e' finita
# davvero, ogni chiamata del giro paga venti secondi, un rinnovo, sessanta
# secondi e un altro rinnovo — circa tre minuti — e con qualche decina di
# chiamate si arriva al timeout del job senza scrivere niente. E' esattamente
# il difetto da venticinque minuti che il freno in `sofascore_http` aveva
# tolto, rimesso in piedi un livello piu' sotto.
#
# Due chiamate di fila che non passano nemmeno dopo le attese non sono
# sfortuna: e' la quota. Si esce subito e si dice perche'.
QUOTA_ESAURITA_DOPO = 2

# I posti dove Chrome sta su Windows, piu' quello che si porta dietro
# `agent-browser` — se il progetto lo usa gia' per il QA, e' inutile chiedere
# all'utente di installarne un altro.
CANDIDATI = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


class ChromeNonDisponibile(RuntimeError):
    """Non c'e' un Chrome da guidare, o non si e' fatto guidare."""


class QuotaEsaurita(RuntimeError):
    """La quota per IP e' finita: insistere costa tempo e non porta dati.

    NON eredita da `SofascoreNonRaggiungibile` per la stessa ragione del muro:
    chi chiama cattura quella per partita e prosegue col giro, e qui proseguire
    significa pagare le attese per ogni partita che resta.
    """


class ContestoPerso(RuntimeError):
    """La scheda su cui stavamo lavorando non e' piu' quella di prima.

    Succede da sola: il sito e' un'applicazione a pagina singola e cambia
    rotta mentre lavoriamo, e ogni cambio butta via il contesto JavaScript in
    cui le nostre `fetch` giravano. Non e' un guasto, e' un rinvio: si torna
    sulla pagina e si ricomincia da li'.
    """


def _trova_chrome() -> str:
    scelto = os.environ.get("SOFASCORE_CHROME")
    if scelto and Path(scelto).exists():
        return scelto
    for c in CANDIDATI:
        if Path(c).exists():
            return c
    for nome in ("google-chrome", "chromium", "chrome"):
        trovato = shutil.which(nome)
        if trovato:
            return trovato
    for c in sorted((Path.home() / ".agent-browser" / "browsers").glob("*/*/chrome*")):
        if c.is_file():
            return str(c)
    raise ChromeNonDisponibile(
        "Serve Google Chrome per raggiungere Sofascore, e non l'ho trovato. "
        "Installalo, oppure indica il percorso in SOFASCORE_CHROME."
    )


def _porta_viva(porta: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def _avvia_chrome() -> subprocess.Popen | None:
    """Apre Chrome sulla pagina di Sofascore, se non ce n'e' gia' uno in ascolto.

    I flag sono i minimi che servono, e nessuno di questi lo marchia come
    automatico: quello e' esattamente il punto — con `--enable-automation` la
    challenge non passa.
    """
    if _porta_viva(PORTA):
        log.info("Chrome gia' in ascolto sulla porta %d: lo riuso.", PORTA)
        return None

    PROFILO.mkdir(parents=True, exist_ok=True)
    argomenti = [
        _trova_chrome(),
        f"--remote-debugging-port={PORTA}",
        # Senza questo, Chrome rifiuta la connessione WebSocket da 127.0.0.1.
        "--remote-allow-origins=*",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={PROFILO}",
        PAGINA,
    ]
    log.info("Avvio Chrome per Sofascore (profilo in %s).", PROFILO)
    proc = subprocess.Popen(
        argomenti, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    scadenza = time.monotonic() + ATTESA_AVVIO_S
    while time.monotonic() < scadenza:
        if _porta_viva(PORTA):
            return proc
        time.sleep(0.5)
    proc.terminate()
    raise ChromeNonDisponibile(
        f"Chrome non ha aperto la porta {PORTA} entro {ATTESA_AVVIO_S}s."
    )


def _scheda() -> dict:
    try:
        grezzo = urllib.request.urlopen(
            f"http://127.0.0.1:{PORTA}/json", timeout=10
        ).read()
    except urllib.error.URLError as exc:
        raise ChromeNonDisponibile(
            f"CDP non risponde sulla porta {PORTA}: {exc}"
        ) from exc
    pagine = [t for t in json.loads(grezzo) if t.get("type") == "page"]
    if not pagine:
        raise ChromeNonDisponibile("Chrome e' aperto ma non ha nessuna scheda.")
    # Se una scheda e' gia' su Sofascore e' quella giusta: ha il contesto.
    for t in pagine:
        if "sofascore.com" in t.get("url", ""):
            return t
    return pagine[0]


class _Canale:
    """Il minimo di CDP che serve: valutare espressioni e leggere le richieste."""

    def __init__(self, url: str):
        try:
            import websocket  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover
            raise ChromeNonDisponibile(
                "manca `websocket-client`. Installalo con: "
                'pip install -e ".[sofascore]"'
            ) from exc
        self._ws = websocket.create_connection(
            url, timeout=90, origin="", suppress_origin=True
        )
        self._n = 0

    def comando(self, metodo: str, parametri: dict | None = None) -> int:
        self._n += 1
        self._ws.send(
            json.dumps({"id": self._n, "method": metodo, "params": parametri or {}})
        )
        return self._n

    def attendi(self, atteso: int) -> dict:
        while True:
            messaggio = json.loads(self._ws.recv())
            if messaggio.get("id") == atteso:
                return messaggio

    def eventi(self, secondi: float):
        """Gli eventi CDP che arrivano entro la finestra, uno alla volta."""
        scadenza = time.monotonic() + secondi
        while time.monotonic() < scadenza:
            self._ws.settimeout(2)
            try:
                yield json.loads(self._ws.recv())
            except Exception:
                continue

    def valuta(self, espressione: str) -> Any:
        atteso = self.comando(
            "Runtime.evaluate",
            {
                "expression": espressione,
                "awaitPromise": True,
                "returnByValue": True,
            },
        )
        messaggio = self.attendi(atteso)
        # CDP risponde in tre modi diversi, e vanno distinti: un errore del
        # protocollo (`error`) non e' un'eccezione nella pagina
        # (`exceptionDetails`), e nessuno dei due e' un risultato. Confonderli
        # significa vedere «risposta illeggibile» al posto della causa vera —
        # per esempio «Cannot find context with specified id», che vuol dire
        # che la pagina ha cambiato rotta sotto di noi.
        if "error" in messaggio:
            raise ContestoPerso(messaggio["error"].get("message", "errore CDP"))
        risultato = messaggio.get("result", {})
        if risultato.get("exceptionDetails"):
            testo = risultato["exceptionDetails"].get("text", "errore nella pagina")
            raise RuntimeError(f"CDP: {testo}")
        return risultato.get("result", {}).get("value")

    def chiudi(self) -> None:
        with contextlib.suppress(Exception):
            self._ws.close()


class Sessione:
    """Un Chrome aperto su Sofascore, con i suoi header validi.

    Si tiene viva per tutto il giro: il token dura circa un'ora e le richieste
    di un giro sono centinaia, quindi riaprire il browser ogni volta
    costerebbe piu' del giro stesso.
    """

    def __init__(self) -> None:
        self._proc = _avvia_chrome()
        self._canale = _Canale(_scheda()["webSocketDebuggerUrl"])
        self._intestazioni: dict[str, str] = {}
        self._403_di_fila = 0
        self._rinnova()

    def _rinnova(self) -> None:
        """Ricarica la pagina e cattura gli header dalle sue stesse chiamate.

        Non c'e' un endpoint che dia il token: lo si vede solo passare. Quindi
        si guarda il traffico che la pagina genera da sola all'avvio.
        """
        self._canale.comando("Network.enable")
        self._canale.comando("Page.enable")
        self._canale.comando("Page.navigate", {"url": PAGINA})
        for evento in self._canale.eventi(ATTESA_TOKEN_S):
            if evento.get("method") != "Network.requestWillBeSent":
                continue
            intestazioni = evento["params"]["request"].get("headers", {})
            if "X-Captcha" in intestazioni:
                self._intestazioni = {
                    k: v
                    for k, v in intestazioni.items()
                    if k.lower() in ("x-captcha", "x-requested-with")
                }
                log.info("Token di Sofascore catturato.")
                self._parcheggia()
                return
        raise ChromeNonDisponibile(
            "La pagina di Sofascore non ha prodotto nessun token entro "
            f"{ATTESA_TOKEN_S}s. Aprila a mano nel Chrome che si e' avviato e "
            "guarda se mostra le partite."
        )

    def _parcheggia(self) -> None:
        """Sposta la scheda su una pagina che non si muove.

        Il token e' gia' in mano: da qui in avanti l'applicazione non serve
        piu', e restarci significherebbe solo farsi cambiare il contesto sotto
        i piedi al primo cambio di rotta.
        """
        self._canale.comando("Page.navigate", {"url": PARCHEGGIO})
        atteso = PARCHEGGIO.rsplit("/", 1)[-1]
        scadenza = time.monotonic() + 15
        while time.monotonic() < scadenza:
            # Durante la navigazione il contesto muore e rinasce: qui le
            # eccezioni sono il decorso normale, non un guasto.
            with contextlib.suppress(Exception):
                if self._canale.valuta("location.pathname").endswith(atteso):
                    return
            time.sleep(0.5)
        log.warning("Non sono riuscito a parcheggiare: resto sull'applicazione.")

    def prendi(self, percorso: str) -> Any:
        """Una GET dall'interno della pagina, con gli header del sito.

        Restituisce `(stato, corpo)`: la traduzione in eccezioni la fa chi
        chiama, perche' le regole su 404 e 403 stanno gia' scritte li'.
        """
        ultimo: tuple[int, Any] = (0, None)
        for numero, attesa in enumerate((0, *ATTESE_403_S)):
            if attesa:
                log.info("403 dal browser: aspetto %ds e rinnovo il token.", attesa)
                time.sleep(attesa)
                self._rinnova()
            try:
                ultimo = self._chiama(percorso)
            except ContestoPerso as exc:
                if numero == len(ATTESE_403_S):
                    raise
                log.info("La pagina e' cambiata sotto di noi (%s): ci torno.", exc)
                self._riaggancia()
                continue
            if ultimo[0] != 403:
                self._403_di_fila = 0
                return ultimo

        # Neanche dopo le attese. Se ricapita subito, e' la quota, non un caso.
        self._403_di_fila += 1
        if self._403_di_fila >= QUOTA_ESAURITA_DOPO:
            raise QuotaEsaurita(
                f"Sofascore risponde 403 anche dopo le attese, "
                f"{self._403_di_fila} chiamate di fila: la quota per questo "
                "indirizzo e' finita. Il giro si ferma qui invece di pagare "
                "tre minuti di attese per ogni partita che resta. Riprovare al "
                "prossimo giro, non subito."
            )
        return ultimo

    def _riaggancia(self) -> None:
        """Riapre il canale sulla scheda buona e ripesca il token."""
        self._canale.chiudi()
        self._canale = _Canale(_scheda()["webSocketDebuggerUrl"])
        self._rinnova()

    def _chiama(self, percorso: str) -> tuple[int, Any]:
        indirizzo = json.dumps(f"{ORIGINE}/api/v1{percorso}")
        intestazioni = json.dumps(self._intestazioni)
        # Stato e corpo tornano in una stringa sola separati da NUL: `fetch`
        # non puo' restituire due valori, e un byte che non compare mai nel
        # JSON e' il separatore piu' sicuro.
        espressione = (
            f"fetch({indirizzo}, {{headers: {intestazioni}}})"
            f".then(r => r.text().then(t => r.status + {json.dumps(chr(0))} + t))"
        )
        grezzo = self._canale.valuta(espressione)
        if not isinstance(grezzo, str) or "\u0000" not in grezzo:
            raise RuntimeError(f"risposta CDP illeggibile su {percorso}")
        stato, _, testo = grezzo.partition("\u0000")
        try:
            return int(stato), json.loads(testo) if testo else None
        except ValueError:
            return int(stato), None

    def chiudi(self) -> None:
        """Spegne il browser, ma solo se e' nostro.

        Chiedere prima a Chrome di chiudersi da solo (`Browser.close`) e non
        limitarsi a `terminate()`: Chrome apre un processo per scheda e per
        servizio, e ammazzare il padre non sempre porta giu' i figli. Un
        processo rimasto tiene la porta 9222, e il giro dopo ci si riattacca
        credendo di aver avviato un browser nuovo — con la pagina dove l'aveva
        lasciata e, se la quota era finita, con il muro gia' in piedi.
        """
        if self._proc is not None:
            with contextlib.suppress(Exception):
                self._canale.comando("Browser.close")
                time.sleep(1)
        self._canale.chiudi()
        if self._proc is not None:
            with contextlib.suppress(Exception):
                self._proc.terminate()
                self._proc.wait(timeout=10)


_sessione: Sessione | None = None


def sessione() -> Sessione:
    """La sessione del processo, aperta alla prima richiesta."""
    global _sessione
    if _sessione is None:
        _sessione = Sessione()
    return _sessione


def chiudi() -> None:
    global _sessione
    if _sessione is not None:
        _sessione.chiudi()
        _sessione = None
