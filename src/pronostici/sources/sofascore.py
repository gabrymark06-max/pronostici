"""Sofascore come fonte di formazioni, arbitro, quote e statistiche giocatore.

IL TRASPORTO STA IN `sofascore_http.py`. Qui c'e' solo la parte che decide:
quale squadra e' quale, quale evento corrisponde a quale nostra partita, e
quando NON agganciare.

PERCHE' NON PASSA PIU' DA UN CLI. Fino al 14 agosto 2026 questa sorgente
invocava `sofascore-pp-cli`, un binario Go che viveva solo sul portatile di chi
ha scritto il progetto — non in questo repository, non pubblicato da nessuna
parte. Conseguenza: questo job era l'unico che non poteva girare su GitHub
Actions, e girava su un'attivita' pianificata di Windows. A computer spento,
formazioni e arbitro di quei giorni erano persi per sempre: sono dati che
esistono solo prima del fischio d'inizio.

Adesso il trasporto e' `curl_cffi`, un pacchetto pip. L'impronta TLS di Chrome
serve ancora — Sofascore risponde 403 a chi non ce l'ha, e non e' un header —
ma adesso e' una dipendenza che si installa, non un binario che deve esistere.

COSA NON FA. Non decide niente. Porta dentro dati grezzi e l'appaiamento con
le nostre partite; il modello sui giocatori sta altrove, e la separazione fra
cio' che e' misurato e cio' che non lo e' e' una scelta di presentazione, non
di questa sorgente.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..matching import canonical, similarity
from . import sofascore_http as http

# Alias validi SOLO verso Sofascore, che chiama alcune squadre in modo che
# nessuna similarita' puo' colmare. La regola e' la stessa di `matching.py`:
# un alias accorcia o sostituisce, non allunga. Chiave e valore sono gia'
# normalizzati, cioe' come li restituisce `canonical`.
#
#   "sporting portugal" contro "sporting cp"  -> 0,61: sotto soglia
#   "nec" contro "nec nijmegen"               -> 0,43: sotto soglia
ALIAS_SOFASCORE: dict[str, str] = {
    "sporting portugal": "sporting cp",
    "sporting lisbon": "sporting cp",
    "nec": "nec nijmegen",
    "psv": "psv eindhoven",
    "az": "az alkmaar",
}


def _chiave(nome: str) -> str:
    """Nome normalizzato, con l'alias verso Sofascore gia' applicato."""
    base = canonical(nome)
    return ALIAS_SOFASCORE.get(base, base)


def _somiglianza(nostro: str, loro: str) -> float:
    """Somiglianza fra un nome nostro e uno di Sofascore, applicando gli alias
    a entrambi i lati prima di confrontarli."""
    a, b = _chiave(nostro), _chiave(loro)
    if a == b:
        return 1.0
    return similarity(a, b)

# Cache degli id squadra. Cercare per nome costa una chiamata e il risultato non
# cambia mai: si risolve una volta e si tiene.
CACHE_SQUADRE = Path("data/sofascore/squadre.json")

# Soglia di somiglianza per accettare una squadra trovata per nome.
#
# E' BASSA APPOSTA, e non e' una scorciatoia. Questo filtro non decide niente
# da solo: serve solo a scegliere di chi chiedere il calendario. La decisione
# vera la prende `aggancia`, che accetta un evento solo se ENTRAMBE le squadre
# combaciano dentro tre ore dal nostro calcio d'inizio. Sbagliare qui produce
# un calendario inutile, non una partita sbagliata.
#
# A 0,72 fallivano nomi legittimi che nessun alias dovrebbe dover coprire:
#   "CA Mineiro" contro "Atletico Mineiro"        -> 0,64
#   "Feyenoord Rotterdam" contro "Feyenoord"      -> 0,64
SOGLIA_SQUADRA = 0.55

TIMEOUT = 60


# Lo stesso nome di prima: i job lo intercettano, e cambiarlo avrebbe voluto
# dire toccarli entrambi per una cosa che per loro non e' cambiata.
SofascoreNonDisponibile = http.SofascoreNonRaggiungibile


@dataclass(frozen=True)
class EventoSofascore:
    """Forma attesa da `matching.pair_events`: stessi tre attributi."""

    id: int
    commence_time: str
    home_team: str
    away_team: str
    torneo: str = ""


def disponibile() -> bool:
    """`True` quando il trasporto e' installabile e la rete risponde.

    Non prova la rete: prova solo che `curl_cffi` ci sia. Il job lo chiama
    all'avvio per spegnersi con un messaggio invece di fallire trenta volte di
    seguito su trenta partite.
    """
    try:
        http._sessione()
        return True
    except http.SofascoreNonRaggiungibile:
        return False


def _srotola(payload: Any) -> Any:
    """I comandi generati avvolgono in `{meta, results}`; quelli scritti a mano no.

    `results` a volte e' gia' la lista che serve, a volte l'oggetto che la
    contiene: entrambe le forme escono da comandi generati e non c'e' modo di
    saperlo dallo schema. Si srotola un livello e basta; a distinguere lista da
    oggetto ci pensa chi chiama.
    """
    if isinstance(payload, dict) and "results" in payload and "meta" in payload:
        return payload["results"]
    return payload


def _elenco(dati: Any, chiave: str) -> list[Any]:
    """Estrae una lista che puo' essere gia' srotolata o annidata sotto `chiave`."""
    if isinstance(dati, list):
        return dati
    if isinstance(dati, dict):
        valore = dati.get(chiave)
        if isinstance(valore, list):
            return valore
    return []


# --------------------------------------------------------------------------- #
# Squadre                                                                      #
# --------------------------------------------------------------------------- #


def _carica_cache() -> dict[str, int]:
    if not CACHE_SQUADRE.exists():
        return {}
    try:
        return json.loads(CACHE_SQUADRE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _salva_cache(cache: dict[str, int]) -> None:
    CACHE_SQUADRE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_SQUADRE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )


def id_squadra(nome: str, *, cache: dict[str, int] | None = None) -> int | None:
    """Id Sofascore di una squadra, cercandola per nome.

    Restituisce None quando nessun candidato supera la soglia. **None non e' un
    errore da ingoiare**: chi chiama deve riportarlo, perche' una squadra non
    risolta significa una partita senza formazioni ne' quote, e va vista.
    """
    propria = cache if cache is not None else _carica_cache()
    if nome in propria:
        return propria[nome]

    # Si cerca con il nome NORMALIZZATO, non con quello grezzo. Football-data
    # scrive "Telstar 1963" e la ricerca di Sofascore su quella stringa non
    # trova nulla; su "telstar" trova subito. Le cifre e le sigle societarie
    # sono rumore per un motore di ricerca esattamente come lo sono per noi.
    dati = http.ricerca(_chiave(nome) or nome)

    migliore_id: int | None = None
    migliore_chiave: tuple[float, int] = (0.0, -1)
    for voce in _elenco(dati, "results"):
        if not isinstance(voce, dict):
            continue
        if voce.get("type") != "team":
            continue
        ent = voce.get("entity") or {}
        candidato = ent.get("name") or ""
        if not candidato or not ent.get("id"):
            continue
        sport = ((ent.get("sport") or {}).get("name") or "").lower()
        if sport and sport != "football":
            continue

        # FILTRO DI GENERE, NON NEGOZIABILE.
        #
        # Sofascore chiama "RCD Espanyol de Barcelona" la squadra FEMMINILE, e
        # "Espanyol" quella maschile. Il nome di football-data e' identico al
        # primo: la somiglianza vale 1,00 e sceglie la squadra sbagliata.
        # Il risultato sarebbero le formazioni della Liga F sulla pagina di una
        # partita di Liga: sbagliato e invisibile.
        #
        # L'archivio del progetto contiene solo competizioni maschili, quindi
        # tutto cio' che non e' dichiarato "M" esce.
        if (ent.get("gender") or "M").upper() != "M":
            continue

        punteggio = _somiglianza(nome, candidato)
        if punteggio < SOGLIA_SQUADRA:
            continue

        # A parita' di nome vince la squadra piu' seguita. E' il modo piu'
        # affidabile per separare la prima squadra dalle riserve e dalle
        # giovanili, che condividono il nome quasi per intero: "Espanyol" ha
        # 184.895 follower, "Espanyol B" ne ha 2.411.
        seguito = int(ent.get("userCount") or 0)
        chiave = (round(punteggio, 2), seguito)
        if chiave > migliore_chiave:
            migliore_chiave = chiave
            migliore_id = int(ent["id"])

    if migliore_id is None:
        return None

    propria[nome] = migliore_id
    if cache is None:
        _salva_cache(propria)
    return migliore_id


def eventi_squadra(team_id: int, *, futuri: bool = True) -> list[EventoSofascore]:
    """Prossime (o ultime) partite di una squadra, gia' nella forma attesa
    da `matching.pair_events`."""
    try:
        dati = http.eventi_squadra(team_id, futuri=futuri)
    except SofascoreNonDisponibile as exc:
        # NE' UN 404 NE' UNA FRENATA FERMANO IL GIRO.
        #
        # Un 404 e' una squadra che Sofascore conosce ma di cui non espone il
        # calendario: dismesse, giovanili, doppioni d'archivio.
        #
        # Un 403 dopo i tentativi e' Sofascore che ci sta ancora frenando. Prima
        # sollevava, e il job moriva buttando via TUTTE le partite gia' lette in
        # quel giro: una frenata temporanea su una squadra costava l'intera
        # giornata di formazioni. Adesso salta quella partita, che restera' fra
        # le «non agganciate» con il suo motivo, e il resto si scrive.
        motivo = str(exc)
        if "404" in motivo or "403" in motivo or "429" in motivo:
            return []
        raise
    fuori: list[EventoSofascore] = []
    for e in _elenco(dati, "events"):
        if not isinstance(e, dict):
            continue
        ts = e.get("startTimestamp")
        if not ts:
            continue
        fuori.append(
            EventoSofascore(
                id=int(e.get("id", 0)),
                commence_time=datetime.fromtimestamp(int(ts), UTC).isoformat().replace(
                    "+00:00", "Z"
                ),
                home_team=(e.get("homeTeam") or {}).get("name", ""),
                away_team=(e.get("awayTeam") or {}).get("name", ""),
                torneo=(e.get("tournament") or {}).get("name", ""),
            )
        )
    return fuori


# --------------------------------------------------------------------------- #
# Partita                                                                      #
# --------------------------------------------------------------------------- #


def scheda(event_id: int) -> dict[str, Any]:
    """Arbitro, formazioni e quote in una chiamata sola.

    Il CLI fa le tre richieste in parallelo e, se una fallisce, la dichiara in
    `parti_mancanti` invece di far sparire tutta la scheda.
    """
    dati = http.scheda(event_id)
    return dati if isinstance(dati, dict) else {}


def statistiche_giocatore(player_id: int) -> dict[str, Any]:
    """Tassi per 90 minuti di un giocatore, gia' calcolati dal CLI.

    Vuoto quando il giocatore non ha una stagione con statistiche: un esordiente
    esiste ma non ha ancora un tasso, e restituire zeri lo farebbe sembrare uno
    che non segna mai.
    """
    dati = http.statistiche_giocatore(player_id)
    return dati if isinstance(dati, dict) else {}


def stagioni_giocatore(player_id: int) -> dict[str, Any]:
    dati = http.stagioni_giocatore(player_id)
    return dati if isinstance(dati, dict) else {}


# --------------------------------------------------------------------------- #
# Aggancio fra le nostre partite e gli eventi Sofascore                        #
# --------------------------------------------------------------------------- #

# Tolleranza sul calcio d'inizio, allineata alle 6 ore che `matching.py` usa
# gia' per le quote.
#
# Avevo provato con 3 ore pensando che entrambe le fonti avessero l'orario
# esatto. Non e' cosi': football-data pubblica orari PROVVISORI per le partite
# a piu' di due giorni, e li corregge avvicinandosi. Con 3 ore fallivano cinque
# partite su trenta, tutte a tre o quattro giorni di distanza.
#
# Allargare non indebolisce la difesa, perche' la difesa non e' la finestra:
# e' la conferma su ENTRAMBI i nomi. Due partite delle stesse due squadre a sei
# ore di distanza non esistono.
TOLLERANZA_ORE = 6

# Somiglianza minima sul nome dell'avversario, a parita' di orario. La finestra
# temporale ha gia' scremato quasi tutto: qui basta confermare.
SOGLIA_AVVERSARIO = 0.60


@dataclass(frozen=True)
class Aggancio:
    """Esito dell'aggancio. `motivo` e' pieno solo quando `evento_id` e' None,
    e serve a rendere visibile il fallimento invece di lasciarlo sparire."""

    evento_id: int | None
    motivo: str = ""
    torneo: str = ""


def _quando(iso: str) -> datetime | None:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def aggancia(
    nome_casa: str,
    nome_ospiti: str,
    utc_date: str,
    *,
    cache: dict[str, int] | None = None,
) -> Aggancio:
    """Trova l'evento Sofascore di una nostra partita.

    Tre filtri in ordine: la squadra di casa risolta per nome, la finestra
    temporale attorno al calcio d'inizio, la conferma sull'avversario. Il primo
    che fallisce dice perche'.

    Non ritorna mai un evento "probabile": senza conferma sull'avversario
    restituisce None con il motivo. Agganciare la partita sbagliata farebbe
    comparire in pagina le formazioni di un'altra gara, e nessuno se ne
    accorgerebbe.
    """
    nostro = _quando(utc_date)
    if nostro is None:
        return Aggancio(None, f"data non interpretabile: {utc_date!r}")

    # Si prova prima la squadra di casa, poi quella ospite. Le due danno lo
    # stesso calendario per questa partita, quindi il ripiego non allarga il
    # rischio: se un nome non si risolve, l'altro puo' bastare, e la conferma
    # su ENTRAMBE le squadre resta invariata.
    ancore: list[tuple[str, int]] = []
    for etichetta, nome in (("casa", nome_casa), ("ospite", nome_ospiti)):
        tid = id_squadra(nome, cache=cache)
        if tid is not None:
            ancore.append((etichetta, tid))
    if not ancore:
        return Aggancio(
            None,
            "nessuna delle due squadre risolta su Sofascore: "
            f"{nome_casa!r} / {nome_ospiti!r}",
        )

    candidati: list[EventoSofascore] = []
    for _, tid in ancore:
        candidati.extend(eventi_squadra(tid, futuri=True))
        candidati.extend(eventi_squadra(tid, futuri=False))
        if candidati:
            break
    if not candidati:
        return Aggancio(None, "nessun evento nel calendario delle due squadre")

    migliore: EventoSofascore | None = None
    migliore_punteggio = 0.0
    for e in candidati:
        loro = _quando(e.commence_time)
        if loro is None:
            continue
        if abs((loro - nostro).total_seconds()) > TOLLERANZA_ORE * 3600:
            continue
        # L'avversario e' quello dei due che NON e' la squadra di casa nostra.
        p_casa = _somiglianza(nome_casa, e.home_team)
        p_ospiti = _somiglianza(nome_ospiti, e.away_team)
        punteggio = min(p_casa, p_ospiti)
        if punteggio > migliore_punteggio:
            migliore_punteggio, migliore = punteggio, e

    if migliore is None:
        return Aggancio(None, f"nessun evento entro {TOLLERANZA_ORE}h da {utc_date}")
    if migliore_punteggio < SOGLIA_AVVERSARIO:
        return Aggancio(
            None,
            "orario compatibile ma squadre diverse: "
            f"{migliore.home_team} - {migliore.away_team} "
            f"(somiglianza {migliore_punteggio:.2f})",
        )
    return Aggancio(migliore.id, torneo=migliore.torneo)
