"""Il trasporto verso Sofascore, in Python e senza sottoprocessi.

PERCHE' ESISTE QUESTO FILE. Fino a ieri questa sorgente parlava con Sofascore
attraverso un CLI in Go che viveva SOLO sul portatile di chi ha scritto il
progetto: non in questo repository, non in nessun repository, e non pubblicato.
Conseguenza pratica: il job delle formazioni e dell'arbitro non poteva girare
su GitHub Actions come tutti gli altri, e girava su un'attivita' pianificata di
Windows. Se il computer era spento, formazioni e arbitro di quei giorni non si
recuperavano piu' — e non si recuperano davvero, perche' quei dati esistono
solo prima del fischio d'inizio.

Erano ventimila righe di Go per sei operazioni, quasi tutte impalcatura mai
usata. Qui ce ne sono trecento, e sono le sei.

L'IMPRONTA TLS E' IL PUNTO. L'API di Sofascore risponde 403 a `requests` e a
`urllib` per come stringono la mano in TLS, non per un header mancante: non si
aggira fingendo uno `User-Agent`. `curl_cffi` presenta l'impronta di Chrome, ed
e' l'unica dipendenza che questo file aggiunge — un pacchetto pip, installabile
in due secondi su un runner, che e' esattamente cio' che il binario Go non era.

LE FORME IN USCITA SONO QUELLE DEL CLI, campo per campo. Non e' nostalgia: e'
che `jobs/sofascore.py` e `jobs/giocatori.py` leggono quelle chiavi, ed erano
gia' provati contro dati veri. Cambiare trasporto e forma insieme avrebbe
voluto dire non sapere piu' quale delle due cose ha rotto qualcosa.
`tests/test_sofascore_http.py` confronta le due strade sullo stesso evento.
"""

from __future__ import annotations

import logging
import time
from typing import Any

# ATTENZIONE, 23 agosto 2026: IL SITO NON USA PIU' QUESTO HOST.
#
# Guardando il traffico di `www.sofascore.com` con un browser vero, le sue
# chiamate dati vanno a `https://www.sofascore.com/api/v1/...` — stesso
# percorso, host diverso. `api.sofascore.com` e' l'indirizzo di prima.
#
# Non e' stato cambiato qui perche' oggi rispondono 403 tutti e due allo stesso
# modo, quindi la sostituzione non e' verificabile: si cambierebbe una costante
# sperando, e la prossima persona non saprebbe se il valore nuovo e' provato o
# indovinato. Quando l'accesso torna, provare prima `www.` — e' quello che usa
# il sito.
BASE = "https://api.sofascore.com/api/v1"
TIMEOUT = 30

# QUANTE VOLTE RIPROVARE, E QUANTO ASPETTARE.
#
# Sofascore risponde 403 quando lo si chiama troppo in fretta. Non e' un
# blocco: e' una frenata, e passa da sola. Ma senza attesa il job moriva al
# primo 403 e buttava via TUTTE le partite gia' lette in quel giro — che e' il
# modo peggiore di reagire a un problema temporaneo.
#
# Le pause crescono: 2, poi 6, poi 18 secondi. Un ritmo che rallenta e' anche
# la cosa educata da fare verso chi ci sta dicendo di rallentare.
TENTATIVI = 3
PAUSA_BASE = 2.0

# Gli stessi valori predefiniti dei flag del CLI (`statistiche.go`), perche' i
# numeri gia' pubblicati non cambino sotto i piedi al primo ricalcolo.
STAGIONI = 3
TORNEI = 2
DECADIMENTO = 0.6

log = logging.getLogger(__name__)


class SofascoreNonRaggiungibile(RuntimeError):
    """Rete assente, 403, o risposta illeggibile. Rumorosa apposta."""


class SofascoreCiBlocca(RuntimeError):
    """Non e' una frenata: e' un muro, e insistere non lo abbatte.

    NON eredita da `SofascoreNonRaggiungibile`, ed e' deliberato. Chi chiama
    cattura quella per partita e prosegue col giro — giusto, quando a mancare
    e' una scheda sola. Qui non manca una scheda: manca l'accesso, e proseguire
    vuol dire ripetere lo stesso muro per ogni partita che resta. Restando
    fuori da quella gerarchia questa attraversa i `except` esistenti e ferma il
    giro, che e' l'unica reazione sensata.
    """


# QUANDO SMETTERE DI PROVARE.
#
# Il 403 di cui sopra passa da solo, e per quello bastano i tre tentativi. Ma
# esiste un altro 403 che non passa mai: `api.sofascore.com` risponde
# `{"error": {"code": 403, "reason": "challenge"}}` a chi non esegue
# JavaScript. Il 22 e il 23 agosto 2026 il job e' stato ucciso due volte dal
# timeout di 25 minuti senza scrivere niente, perche' pagava otto secondi di
# attese per ognuna delle centinaia di richieste di un giro.
#
# Tre richieste di fila esaurite tutte sul 403 non sono piu' una frenata: e'
# quel muro. Si smette dopo ~24 secondi invece che dopo 25 minuti, e si dice
# perche'. Una risposta qualunque che arrivi davvero — anche un 404 — dimostra
# che il muro non c'e' e azzera il conto.
BLOCCHI_PER_ARRENDERSI = 3
MURO = (
    "Sofascore rifiuta ogni richiesta ({ultimo}): {quanti} di fila esaurite "
    "su {tentativi} tentativi.\n"
    "Il sito manda due header che da qui non possiamo produrre: `X-Captcha` "
    "— un JWT firmato da loro, legato all'IP e valido circa un'ora — e "
    "`X-Requested-With`. Il token non si puo' nemmeno riusare fuori: preso "
    "dal browser e passato a `curl_cffi` resta 403, perche' e' legato "
    "anche alla connessione che lo ha ottenuto.\n"
    "La strada che funziona e' `sofascore_cdp`: le stesse chiamate fatte "
    "da dentro un Chrome vero. Qui non e' stata praticabile."
)
_falliti_di_fila = 0

# QUALE STRADA SI STA USANDO.
#
# Si parte sempre da `curl_cffi`, che costa una frazione. Quando scatta il muro
# non si molla: si passa al browser, una volta sola, e il resto del giro va da
# li'. Se Sofascore riapre la porta, la strada economica torna a funzionare da
# sola, senza toccare niente.
_via_browser = False


def chiudi_trasporto() -> None:
    """Spegne il browser, se ne era stato aperto uno.

    Va chiamata alla fine di un giro. Senza, il Chrome avviato dal trasporto
    resta vivo dopo che il job e' finito: tiene la porta 9222, e il giro
    successivo ci si riattacca invece di avviarne uno pulito. Trovato con due
    Chrome e due python di due esecuzioni diverse ancora in memoria un'ora
    dopo, e il job nuovo appeso su quello vecchio.
    """
    from . import sofascore_cdp as cdp

    cdp.chiudi()
    azzera_trasporto()


def azzera_trasporto() -> None:
    """Rimette la strada economica. Serve ai test, e a chi rilancia."""
    global _via_browser
    _via_browser = False


def azzera_blocco() -> None:
    """Rimette a zero il contatore del muro. Serve ai test, e a chi rilancia."""
    global _falliti_di_fila
    _falliti_di_fila = 0


def _sessione():
    """La sessione `curl_cffi`, importata QUI e non in testa al modulo.

    Il resto della pipeline non ha bisogno di Sofascore: importarla in testa
    farebbe fallire l'avvio di `jobs.score` su una macchina che non ha
    `curl_cffi`, per una dipendenza che a quel job non serve.
    """
    try:
        from curl_cffi import requests  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise SofascoreNonRaggiungibile(
            "manca `curl_cffi`. Installalo con: pip install curl_cffi\n"
            "Serve perche' Sofascore risponde solo a chi presenta l'impronta TLS "
            "di un browser: nessun header lo sostituisce."
        ) from exc
    return requests


def prendi(percorso: str) -> Any:
    """Una GET, e il JSON.

    RIPROVA SOLO SU CIO' CHE PUO' PASSARE DA SOLO: 403 e 429 sono una frenata,
    i guasti di rete un incidente. Un 404 no — quello e' una risposta, e
    riprovarla darebbe lo stesso 404 tre volte piu' lentamente.
    """
    if _via_browser:
        from . import sofascore_cdp as cdp

        return _dal_browser(cdp.sessione(), percorso)

    requests = _sessione()
    ultimo: str = ""

    for tentativo in range(TENTATIVI):
        if tentativo:
            attesa = PAUSA_BASE * (3**(tentativo - 1))
            log.info("Sofascore frena (%s): aspetto %.0fs", ultimo, attesa)
            time.sleep(attesa)
        try:
            r = requests.get(f"{BASE}{percorso}", impersonate="chrome", timeout=TIMEOUT)
        except Exception as exc:
            ultimo = str(exc)[:80]
            continue

        if r.status_code == 404:
            # Un 404 e' un'informazione, non un guasto: la squadra esiste ma non
            # ha calendario, l'evento non ha ancora formazioni. Chi chiama decide,
            # e non si riprova. Ed e' una risposta vera: il muro non c'e'.
            azzera_blocco()
            raise SofascoreNonRaggiungibile(f"404 su {percorso}")
        if r.status_code in (403, 429):
            ultimo = f"{r.status_code}"
            continue
        if r.status_code != 200:
            raise SofascoreNonRaggiungibile(f"{r.status_code} su {percorso}")

        try:
            corpo = r.json()
        except Exception as exc:
            raise SofascoreNonRaggiungibile(f"risposta non JSON su {percorso}") from exc
        azzera_blocco()
        return corpo

    global _falliti_di_fila
    if ultimo in ("403", "429"):
        _falliti_di_fila += 1
        if _falliti_di_fila >= BLOCCHI_PER_ARRENDERSI:
            return _passa_al_browser(percorso, ultimo)
    else:
        azzera_blocco()

    raise SofascoreNonRaggiungibile(
        f"{ultimo or 'nessuna risposta'} su {percorso} dopo {TENTATIVI} tentativi"
    )


def _passa_al_browser(percorso: str, ultimo: str) -> Any:
    """Il muro e' confermato: si prova la strada che lo attraversa.

    Non e' un ripiego silenzioso. Se il browser non c'e', l'errore che esce e'
    quello del muro, con dentro la diagnosi e il motivo per cui nemmeno questa
    strada era percorribile.
    """
    global _via_browser
    from . import sofascore_cdp as cdp

    try:
        sessione = cdp.sessione()
    except cdp.ChromeNonDisponibile as exc:
        raise SofascoreCiBlocca(
            MURO.format(ultimo=ultimo, quanti=_falliti_di_fila, tentativi=TENTATIVI)
            + chr(10)
            + f"Motivo: {exc}"
        ) from exc

    log.info("Passo al browser: da qui in poi il giro va da li'.")
    _via_browser = True
    azzera_blocco()
    return _dal_browser(sessione, percorso)


def _dal_browser(sessione: Any, percorso: str) -> Any:
    """Traduce la risposta del browser nelle stesse regole di `prendi`."""
    stato, corpo = sessione.prendi(percorso)
    if stato == 404:
        raise SofascoreNonRaggiungibile(f"404 su {percorso}")
    if stato != 200:
        raise SofascoreNonRaggiungibile(f"{stato} su {percorso} (browser)")
    if corpo is None:
        raise SofascoreNonRaggiungibile(f"risposta non JSON su {percorso} (browser)")
    return corpo


def _numero(v: Any) -> float:
    return float(v) if isinstance(v, (int, float)) else 0.0


def _arrotonda(v: float, cifre: int) -> float:
    """L'arrotondamento del CLI: mezzo punto sempre verso l'alto in valore
    assoluto. `round()` di Python arrotonda al pari piu' vicino — 2,5 diventa 2
    — e su un confronto campo per campo con l'uscita del CLI quella differenza
    si vede."""
    m = 10**cifre
    return int(v * m + 0.5) / m if v >= 0 else int(v * m - 0.5) / m


# --------------------------------------------------------------------------- #
# Ricerca e calendario                                                         #
# --------------------------------------------------------------------------- #


def ricerca(query: str) -> dict[str, Any]:
    """Forma del CLI: `{"results": [...]}` con dentro `{type, entity}`."""
    dati = prendi(f"/search/all?q={query}")
    return {"results": dati.get("results", []) if isinstance(dati, dict) else []}


def eventi_squadra(team_id: int, *, futuri: bool = True) -> dict[str, Any]:
    verso = "next" if futuri else "last"
    dati = prendi(f"/team/{team_id}/events/{verso}/0")
    return {"events": dati.get("events", []) if isinstance(dati, dict) else []}


# --------------------------------------------------------------------------- #
# La scheda: arbitro, formazioni, quote                                        #
# --------------------------------------------------------------------------- #


def _evento(event_id: int) -> dict[str, Any]:
    """Arbitro, stadio e i nomi delle due squadre: una chiamata sola.

    Lo stadio sta DENTRO `arbitro` e non al primo livello, perche' e' li' che
    `jobs.sofascore` lo legge. Sembra il posto sbagliato ed e' il posto giusto:
    l'unica cosa che la pagina ne fa e' scriverlo accanto al nome dell'arbitro.
    """
    dati = prendi(f"/event/{event_id}")
    e = dati.get("event") or {}
    venue = e.get("venue") or {}
    stadio = (venue.get("stadium") or {}).get("name")
    citta = (venue.get("city") or {}).get("name")

    fuori: dict[str, Any] = {
        "casa": (e.get("homeTeam") or {}).get("name", ""),
        "ospiti": (e.get("awayTeam") or {}).get("name", ""),
    }

    a = e.get("referee") or {}
    if a.get("name"):
        partite = int(a.get("games") or 0)
        gialli = int(a.get("yellowCards") or 0)
        arbitro: dict[str, Any] = {
            "partita_id": event_id,
            "nome": a.get("name", ""),
            "paese": (a.get("country") or {}).get("name"),
            "partite_arbitrate": partite,
            "cartellini_gialli": gialli,
            "cartellini_rossi": int(a.get("redCards") or 0),
            "gialli_per_partita": _arrotonda(gialli / partite, 2) if partite else None,
            "stadio": stadio,
        }
        if citta:
            arbitro["citta"] = citta
        fuori["arbitro"] = arbitro
    return fuori


def _lato(squadra: dict[str, Any]) -> dict[str, Any]:
    titolari, panchina = [], []
    for g in squadra.get("players") or []:
        persona = g.get("player") or {}
        voce = {
            "id": int(persona.get("id") or 0),
            "nome": persona.get("name", ""),
            "maglia": str(g.get("shirtNumber") or persona.get("jerseyNumber") or ""),
            "ruolo": persona.get("position", ""),
            "titolare": not g.get("substitute", False),
        }
        (panchina if g.get("substitute") else titolari).append(voce)
    modulo = squadra.get("formation")
    return {
        "modulo": modulo,
        "titolari": titolari,
        "panchina": panchina,
        "n_titolari": len(titolari),
    }


def _formazioni(event_id: int) -> dict[str, Any] | None:
    dati = prendi(f"/event/{event_id}/lineups")
    if not isinstance(dati, dict) or not dati.get("home"):
        return None
    return {
        "partita_id": event_id,
        "confermate": bool(dati.get("confirmed")),
        "stato": "confermate" if dati.get("confirmed") else "probabili",
        "casa": _lato(dati.get("home") or {}),
        "ospiti": _lato(dati.get("away") or {}),
    }


def _decimale(frazionaria: str) -> float | None:
    """`"3/4"` -> `1.75`. La forma in cui Sofascore serve le quote."""
    if "/" not in frazionaria:
        return None
    a, _, b = frazionaria.partition("/")
    try:
        num, den = float(a), float(b)
    except ValueError:
        return None
    if den == 0:
        return None
    return num / den + 1.0


def _quote(event_id: int) -> dict[str, Any]:
    dati = prendi(f"/event/{event_id}/odds/1/all")
    mercati = []
    for m in (dati.get("markets") or []) if isinstance(dati, dict) else []:
        esiti, somma = [], 0.0
        for ch in m.get("choices") or []:
            fraz = ch.get("fractionalValue") or ""
            dec = _decimale(fraz)
            if dec is None:
                esiti.append({"esito": ch.get("name", ""), "frazionaria": fraz})
                continue
            p = 1.0 / dec
            esiti.append(
                {
                    "esito": ch.get("name", ""),
                    "frazionaria": fraz,
                    "decimale": _arrotonda(dec, 2),
                    "probabilita_implicita": _arrotonda(p, 4),
                }
            )
            somma += p
        voce: dict[str, Any] = {"mercato": m.get("marketName", "")}
        if m.get("choiceGroup"):
            voce["linea"] = m["choiceGroup"]
        voce["esiti"] = esiti
        voce["margine_percento"] = _arrotonda((somma - 1) * 100, 2)
        voce["somma_probabilita"] = _arrotonda(somma, 4)
        mercati.append(voce)
    return {"partita_id": event_id, "n_mercati": len(mercati), "mercati": mercati}


def scheda(event_id: int) -> dict[str, Any]:
    """Arbitro, formazioni e quote. Una parte che manca si dichiara e non
    fa sparire le altre — come faceva il CLI."""
    fuori: dict[str, Any] = {"partita_id": event_id}
    mancanti: dict[str, str] = {}

    try:
        fuori.update(_evento(event_id))
    except SofascoreNonRaggiungibile as exc:
        mancanti["arbitro"] = str(exc)

    try:
        form = _formazioni(event_id)
        if form:
            fuori["formazioni"] = form
    except SofascoreNonRaggiungibile as exc:
        mancanti["formazioni"] = str(exc)

    try:
        q = _quote(event_id)
        if q["mercati"]:
            fuori["quote"] = q
    except SofascoreNonRaggiungibile as exc:
        mancanti["quote"] = str(exc)

    if mancanti:
        fuori["parti_mancanti"] = mancanti
    return fuori


# --------------------------------------------------------------------------- #
# Statistiche di un giocatore                                                  #
# --------------------------------------------------------------------------- #


def stagioni_giocatore(player_id: int) -> dict[str, Any]:
    return prendi(f"/player/{player_id}/statistics/seasons")


def statistiche_giocatore(player_id: int) -> dict[str, Any]:
    """Totali e tassi per 90 minuti, sommando piu' stagioni e piu' tornei.

    LA PONDERAZIONE E' SUL TEMPO, NON SULLA COMPETIZIONE: campionato e coppa
    dello stesso anno pesano uguale. E i tassi pesati dividono una somma pesata
    di eventi per una somma pesata di novantesimi — i pesi si semplificano,
    quindi esce un tasso e non una media di tassi, e una stagione con pochi
    minuti conta poco anche a parita' di peso temporale.
    """
    try:
        elenco = stagioni_giocatore(player_id)
    except SofascoreNonRaggiungibile:
        return {}

    tornei = (elenco or {}).get("uniqueTournamentSeasons") or []
    # I tornei con piu' stagioni per primi: e' la competizione principale.
    tornei = sorted(
        tornei, key=lambda t: len(t.get("seasons") or []), reverse=True
    )[:TORNEI]

    tot = dict.fromkeys(
        ("presenze", "minuti", "gol", "assist", "gialli", "rossi", "falli",
         "tiri_in_porta", "tiri_totali"), 0
    )
    pesati = dict.fromkeys(("minuti", "gol", "assist", "gialli", "falli", "tiri"), 0.0)
    usati_tornei: list[str] = []
    anni: list[str] = []

    for torneo in tornei:
        ut = (torneo.get("uniqueTournament") or {}).get("id")
        nome = (torneo.get("uniqueTournament") or {}).get("name", "")
        stagioni = (torneo.get("seasons") or [])[:STAGIONI]
        if not ut or not stagioni:
            continue
        quante = 0
        for i, se in enumerate(stagioni):
            peso = DECADIMENTO**i
            try:
                dati = prendi(
                    f"/player/{player_id}/unique-tournament/{ut}"
                    f"/season/{se.get('id')}/statistics/overall"
                )
            except SofascoreNonRaggiungibile:
                # Una stagione che non risponde non ferma le altre: si perde
                # campione, non si perde tutto.
                continue
            s = (dati or {}).get("statistics") or {}
            if not s.get("appearances") and not s.get("minutesPlayed"):
                continue
            quante += 1
            # Gli anni si elencano UNA VOLTA SOLA. Lo stesso 24/25 entra da due
            # tornei diversi — campionato e coppa — e ripeterlo direbbe «cinque
            # stagioni» dove ce ne sono quattro. Interessa QUALI anni sono
            # entrati, non quante volte.
            anno = str(se.get("year", ""))
            if anno not in anni:
                anni.append(anno)

            tot["presenze"] += int(s.get("appearances") or 0)
            tot["minuti"] += int(s.get("minutesPlayed") or 0)
            tot["gol"] += int(s.get("goals") or 0)
            tot["assist"] += int(s.get("assists") or 0)
            tot["gialli"] += int(s.get("yellowCards") or 0)
            tot["rossi"] += int(s.get("redCards") or 0)
            tot["falli"] += int(s.get("fouls") or 0)
            tot["tiri_in_porta"] += int(s.get("shotsOnTarget") or 0)
            tot["tiri_totali"] += int(s.get("totalShots") or 0)

            pesati["minuti"] += peso * _numero(s.get("minutesPlayed"))
            pesati["gol"] += peso * _numero(s.get("goals"))
            pesati["assist"] += peso * _numero(s.get("assists"))
            pesati["gialli"] += peso * _numero(s.get("yellowCards"))
            pesati["falli"] += peso * _numero(s.get("fouls"))
            pesati["tiri"] += peso * _numero(s.get("shotsOnTarget"))
        if quante:
            usati_tornei.append(nome)

    if not anni:
        return {
            "giocatore_id": player_id,
            "nota": "nessuna stagione leggibile per questo giocatore",
        }

    novantesimi_pesati = pesati["minuti"] / 90.0

    def per90(chiave: str) -> float | None:
        if novantesimi_pesati <= 0:
            return None
        return _arrotonda(pesati[chiave] / novantesimi_pesati, 3)

    fuori: dict[str, Any] = {
        "giocatore_id": player_id,
        "torneo": " + ".join(usati_tornei),
        "stagione": ", ".join(anni),
        "presenze": tot["presenze"],
        "minuti": tot["minuti"],
        "novantesimi": _arrotonda(tot["minuti"] / 90.0, 2),
        "gol": tot["gol"],
        "assist": tot["assist"],
        "gialli": tot["gialli"],
        "rossi": tot["rossi"],
        "falli": tot["falli"],
        "tiri_in_porta": tot["tiri_in_porta"],
        "tiri_totali": tot["tiri_totali"],
        "gol_per_90": per90("gol"),
        "assist_per_90": per90("assist"),
        "gialli_per_90": per90("gialli"),
        "falli_per_90": per90("falli"),
        "tiri_in_porta_per_90": per90("tiri"),
    }
    if tot["presenze"] < 10:
        fuori["nota"] = (
            f"campione sottile: {tot['presenze']} presenze in {len(anni)} stagioni"
        )
    return fuori
