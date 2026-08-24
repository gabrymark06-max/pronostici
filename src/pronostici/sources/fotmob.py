"""Tassi per 90 minuti dei singoli giocatori, da fotmob.

PERCHE' ESISTE. La sezione «Giocatori» di ogni scheda partita stimava, per
ognuno degli undici, la probabilita' di segnare, servire un assist, prendere un
cartellino, commettere un fallo, tirare in porta. I tassi venivano da Sofascore,
che dal 23 agosto 2026 risponde solo a chi ha un IP residenziale: la sezione si
e' svuotata.

COSA SI E' PROVATO PRIMA, e perche' non bastava:

  · football-data.org, la chiave che gia' abbiamo, ha `/scorers`: il 24 agosto
    2026 restituiva 19 giocatori per la Serie A, tutti con un gol, quasi tutti
    senza assist. Copre i marcatori, non gli undici;
  · understat risponde 200 ma serve una pagina vuota a chi non e' un browser;
  · fbref e worldfootball rispondono 403.

FOTMOB INVECE PUBBLICA UN FILE PER STATISTICA con dentro TUTTI i giocatori
del campionato, non i primi dieci:

    https://data.fotmob.com/stats/<lega>/season/<stagione>/<statistica>.json

E ogni riga porta i MINUTI GIOCATI, non solo le presenze. E' il denominatore
giusto: un attaccante entrato dieci volte dalla panchina ha dieci presenze e
duecento minuti, e dividere per le presenze gli attribuirebbe un tasso quasi
quadruplo di quello vero.

LA STAGIONE NON SI SCRIVE A MANO. L'identificativo cambia ogni anno e non e'
deducibile; sta dentro la risposta di `/api/data/leagues`, che lo pubblica gia'
composto dentro `fetchAllUrl`. Si legge da li' ogni volta: cablarlo
significherebbe che a luglio prossimo il job continua a leggere i tassi
dell'anno scorso senza che niente diventi rosso.
"""

from __future__ import annotations

import gzip
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from ..matching import canonical

log = logging.getLogger(__name__)

INDICE = "https://www.fotmob.com/api/data/leagues?id={}"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)

# I NOSTRI codici competizione verso i loro identificativi. Verificati uno per
# uno il 24 agosto 2026 leggendo il nome che torna: non sono indovinati.
LEGHE: dict[str, int] = {
    "PL": 47,
    "ELC": 48,
    "SA": 55,
    "PD": 87,
    "BL1": 54,
    "FL1": 53,
    "DED": 57,
    "PPL": 61,
    "BSA": 268,
}

# Come si chiamano da loro le cinque statistiche che il modello sa usare, come
# le chiama `model/giocatori.py`, e SE SONO GIA' PER 90 MINUTI.
#
# QUEST'ULTIMO CAMPO E' IL PUNTO. Le unita' non sono le stesse e niente nel
# formato lo segnala: `goals` e `yellow_card` sono conteggi di stagione (15
# gol, 10 gialli), `fouls` e `ontarget_scoring_att` sono gia' medie per 90.
# Dividendo tutto per i minuti come se fosse un conteggio, il miglior
# attaccante del Brasileirao risultava a 0,04 falli e 0,07 tiri in porta ogni
# novanta minuti: numeri che nessun controllo avrebbe fermato, perche' sono
# plausibili come forma e assurdi solo se si sa cosa vogliono dire.
#
# L'unico posto dove la differenza e' scritta e' il titolo umano della lista —
# «Fouls committed per 90» contro «Top scorer» — e infatti `_accumula` lo
# confronta con quanto dichiarato qui: se un giorno cambiano unita', si vede.
STATISTICHE: dict[str, tuple[str, bool]] = {
    "goals": ("gol", False),
    "goal_assist": ("assist", False),
    "yellow_card": ("gialli", False),
    "fouls": ("falli", True),
    "ontarget_scoring_att": ("tiri_in_porta", True),
}

PAUSA_S = 0.5

# Sotto questi minuti un tasso per 90 non e' un tasso: e' un singolo episodio
# moltiplicato. Un giocatore con un giallo in ventun minuti risulterebbe a
# 4,3 gialli per 90, cioe' piu' di quattro espulsioni a partita.
MINUTI_MINIMI = 180


class FotmobNonRaggiungibile(RuntimeError):
    """Il sito non ha risposto. I giocatori restano senza stime."""


@dataclass
class Giocatore:
    nome: str
    squadra: str
    id_fotmob: int | None = None
    ruolo: str | None = None
    minuti: int = 0
    presenze: int = 0
    tassi: dict[str, float] = field(default_factory=dict)

    def per_il_modello(self) -> dict:
        """Nella forma che `model/giocatori.stime_giocatore` si aspetta."""
        return {"presenze": self.presenze, **self.tassi}


def _scarica(url: str) -> dict:
    richiesta = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=30) as risposta:
            grezzo = risposta.read()
    except (urllib.error.URLError, OSError) as e:
        raise FotmobNonRaggiungibile(f"{url}: {e}") from e
    # Il CDN manda gzip anche senza che lo si chieda, e `urllib` non lo
    # decomprime da solo: senza questa riga si prova a leggere JSON da byte
    # binari e l'errore che esce parla di «Expecting value», che manda a
    # cercare il problema nel posto sbagliato.
    if grezzo[:2] == b"\x1f\x8b":
        grezzo = gzip.decompress(grezzo)
    time.sleep(PAUSA_S)
    try:
        return json.loads(grezzo.decode("utf-8"))
    except ValueError as e:
        raise FotmobNonRaggiungibile(f"{url}: risposta non JSON ({e})") from e


def indirizzi_statistiche(codice: str, *, indice: dict | None = None) -> dict[str, str]:
    """Per ogni statistica che ci interessa, l'indirizzo del file completo.

    Torna un dizionario vuoto quando il campionato non ha ancora statistiche —
    a stagione appena cominciata `stats.players` e' `null`, ed e' un «non
    ancora», non un guasto. Misurato sulla Bundesliga il 24 agosto 2026.
    """
    lega = LEGHE.get(codice)
    if lega is None:
        return {}
    if indice is None:
        indice = _scarica(INDICE.format(lega))

    elenco = ((indice.get("stats") or {}).get("players")) or []
    trovati: dict[str, str] = {}
    for voce in elenco:
        nome = voce.get("name")
        url = voce.get("fetchAllUrl")
        if nome in STATISTICHE and url:
            trovati[nome] = url
    return trovati


def tassi_lega(
    codice: str, *, frammenti: dict[str, dict] | None = None
) -> dict[str, Giocatore]:
    """I tassi per 90 di ogni giocatore del campionato, per nome normalizzato.

    Cinque file, uno per statistica. Ogni riga porta il valore e i minuti, e i
    file si sovrappongono sullo stesso giocatore: si accumula.
    """
    indirizzi = {} if frammenti is not None else indirizzi_statistiche(codice)
    per_nome: dict[str, Giocatore] = {}

    fonti = frammenti if frammenti is not None else None
    for statistica, (nostra, gia_per_90) in STATISTICHE.items():
        if fonti is not None:
            dati = fonti.get(statistica)
            if dati is None:
                continue
        else:
            url = indirizzi.get(statistica)
            if url is None:
                continue
            try:
                dati = _scarica(url)
            except FotmobNonRaggiungibile as exc:
                log.warning("%s/%s non letta: %s", codice, statistica, exc)
                continue
        _accumula(per_nome, dati, nostra, gia_per_90)

    return {k: g for k, g in per_nome.items() if g.minuti >= MINUTI_MINIMI}


def _accumula(
    per_nome: dict[str, Giocatore], dati: dict, nostra: str, gia_per_90: bool
) -> None:
    for lista in dati.get("TopLists") or []:
        # LA CONTROPROVA SULL'UNITA'. Il titolo e' l'unico posto in cui fotmob
        # dice se il numero e' un totale o una media, e non e' un contratto:
        # e' testo per gli umani. Ma un disaccordo fra quel testo e quello che
        # abbiamo dichiarato in `STATISTICHE` significa che una delle due cose
        # e' cambiata, e continuare vorrebbe dire pubblicare tassi sbagliati di
        # un fattore venti senza accorgersene.
        titolo = str(lista.get("Title") or "")
        if titolo and ("per 90" in titolo.lower()) != gia_per_90:
            log.error(
                "unita' cambiata per %s: il titolo dice «%s» ma la tabella "
                "la dichiara %s. Statistica saltata.",
                nostra,
                titolo,
                "gia' per 90" if gia_per_90 else "un totale",
            )
            continue
        for riga in lista.get("StatList") or []:
            nome = (riga.get("ParticipantName") or "").strip()
            if not nome:
                continue
            chiave = canonical(nome)
            minuti = int(riga.get("MinutesPlayed") or 0)
            giocatore = per_nome.get(chiave)
            if giocatore is None:
                ruoli = riga.get("Positions") or []
                giocatore = Giocatore(
                    nome=nome,
                    squadra=riga.get("TeamName") or "",
                    id_fotmob=riga.get("ParticiantId"),
                    ruolo=(ruoli[0] if isinstance(ruoli, list) and ruoli else None),
                )
                per_nome[chiave] = giocatore
            # I MINUTI SONO GLI STESSI IN OGNI FILE, ma un giocatore compare
            # solo nei file delle statistiche in cui ha fatto almeno qualcosa:
            # si tiene il massimo visto, perche' un file che non lo elenca non
            # dice che ha giocato zero minuti — dice che non ha segnato.
            giocatore.minuti = max(giocatore.minuti, minuti)
            giocatore.presenze = max(
                giocatore.presenze, int(riga.get("MatchesPlayed") or 0)
            )
            valore = riga.get("StatValue")
            if valore is None:
                continue
            if gia_per_90:
                giocatore.tassi[f"{nostra}_per_90"] = round(float(valore), 4)
            elif minuti > 0:
                giocatore.tassi[f"{nostra}_per_90"] = round(
                    float(valore) * 90.0 / minuti, 4
                )


def cerca(tassi: dict[str, Giocatore], nome: str) -> Giocatore | None:
    """Il giocatore corrispondente a un nome di formazione, o `None`.

    Solo corrispondenza esatta sul nome normalizzato. NIENTE SOMIGLIANZA qui,
    al contrario che per le squadre: due compagni possono chiamarsi Silva e
    Silva Junior, e attribuire i cartellini dell'uno all'altro sarebbe un
    errore invisibile — il numero esce plausibile e riguarda la persona
    sbagliata. Meglio nessuna stima.
    """
    return tassi.get(canonical(nome))
