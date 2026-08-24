"""Mercati estesi da betexplorer.com, per HTTP semplice.

PERCHE' ESISTE. Fino al 23 agosto 2026 la sezione «Altri mercati» di ogni
scheda partita veniva da Sofascore: sedici mercati con i prezzi. Sofascore ha
chiuso la porta a chi non ha un IP residenziale, e quella sezione si e'
svuotata. Questa fonte non ha lucchetti — HTML pubblico, nessuna chiave — ed e'
stata provata dai runner di GitHub, non da una macchina di casa.

COSA DA'. Sei mercati per partita, con le quote di ogni bookmaker:

    1x2   esito finale            dc    doppia chance
    ou    gol totali, ogni linea  ha    draw no bet
    bts   entrambe segnano        ah    handicap asiatico (non lo leggiamo)

E i bookmaker sono quelli con licenza italiana — SNAI, Sisal, Eurobet,
Lottomatica, GoldBet, Planetwin365 — che e' lo stesso `price_scope: "it"` che
il progetto preferisce gia' per le quote principali.

DUE COSE CHE SI VEDONO SOLO PROVANDO DA UN DATACENTER, e che sono costate un
giro di sonda ciascuna:

  · IL PREFISSO DI LINGUA NON C'E' SEMPRE. Da un IP italiano gli URL sono
    `/it/football/...`, da un runner americano `/football/...`. Una regex che
    pretende il prefisso trova zero partite su una pagina piena.
  · RISPONDE 429 SE SI CORRE. Va tenuto un passo lento, e un 429 va aspettato
    invece che contato come «questa partita non ha quote».

COME E' FATTO IL SITO. Due passi:

    /football/<paese>/<lega>/fixtures/     l'elenco, con hash, squadre e 1X2
    /match-odds/<hash>/1/<mercato>/odds/   la tabella di un mercato, in JSON

L'elenco copre l'intera stagione, quindi una coppia casa-ospiti compare una
volta sola: si abbina sui nomi, senza bisogno della data.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from statistics import median

from ..matching import canonical, contenimento
from ..model.devig import DevigError, devig_power

log = logging.getLogger(__name__)

BASE = "https://www.betexplorer.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)

# I NOSTRI codici competizione verso i loro percorsi.
LEGHE: dict[str, str] = {
    "PL": "england/premier-league",
    "ELC": "england/championship",
    "SA": "italy/serie-a",
    "PD": "spain/laliga",
    "BL1": "germany/bundesliga",
    "FL1": "france/ligue-1",
    "DED": "netherlands/eredivisie",
    "PPL": "portugal/liga-portugal",
    "BSA": "brazil/serie-a",
}

# I mercati che leggiamo, e come si chiamano da noi. L'ordine delle colonne e'
# quello della tabella e non e' deducibile dal markup: sta scritto qui perche'
# e' l'unico posto in cui possa stare.
#
# `ah` (handicap asiatico) resta fuori: le sue righe hanno una linea diversa
# per bookmaker e la tabella pesa il doppio di tutte le altre insieme, per un
# mercato che la scheda partita non ha mai mostrato.
# L'ULTIMO NUMERO E' QUANTI ESITI SI VERIFICANO, e non e' un dettaglio.
#
# Sgonfiare le quote vuol dire dividere per la somma delle inverse, e quella
# somma tende a 1 solo se gli esiti sono una PARTIZIONE — uno e uno solo si
# avvera. La doppia chance non lo e': "1X", "12" e "X2" coprono ogni risultato
# due volte, e la loro somma tende a 2. Trattandola come le altre usciva un
# margine del 113%, cioe' il banco che si prende piu' di quanto incassa.
MERCATI: dict[str, tuple[str, tuple[str, ...], int]] = {
    "1x2": ("Esito finale", ("1", "X", "2"), 1),
    "dc": ("Doppia chance", ("1X", "12", "X2"), 2),
    "ou": ("Gol totali", ("Over", "Under"), 1),
    "bts": ("Entrambe segnano", ("Sì", "No"), 1),
    # Draw no bet: il pareggio annulla la giocata, quindi restano due esiti e
    # uno solo si avvera.
    "ha": ("Draw no bet", ("1", "2"), 1),
}

# Betexplorer risponde 429 se si corre: misurato dai runner di GitHub il 24
# agosto 2026, due leghe su nove con due secondi di pausa. Tre, e si aspetta
# quando lo dice lui.
PAUSA_S = 3.0
ATTESE_429_S = (10, 30)

# Sotto questo numero di bookmaker la mediana non e' una mediana. La stessa
# soglia che il progetto usa per le quote principali sarebbe troppo alta qui:
# i mercati minori hanno meno operatori, e tre prezzi concordi valgono piu' di
# nessun prezzo.
BOOKMAKER_MINIMI = 3

SOGLIA_NOME = 0.72

# Alias verso betexplorer. Stessa regola di sportsgambler: si allunga
# misurando, non immaginando.
ALIAS: dict[str, str] = {}


class BetexplorerNonRaggiungibile(RuntimeError):
    """Il sito non ha risposto. La partita resta senza mercati estesi."""


@dataclass
class PartitaBX:
    """Una riga dell'elenco: l'hash serve a chiedere i mercati."""

    id: str
    casa: str
    ospiti: str
    # Le quote 1X2 stanno gia' nell'elenco: prenderle qui evita una richiesta
    # per partita per il mercato piu' importante.
    esito_finale: list[float] = field(default_factory=list)


def _chiave(nome: str) -> str:
    base = canonical(nome)
    return ALIAS.get(base, base)


def somiglianza(nostro: str, loro: str) -> float:
    return contenimento(_chiave(nostro), _chiave(loro))


def _scarica(percorso: str, referer: str = "") -> str:
    testate = {"User-Agent": UA, "Accept": "*/*"}
    if referer:
        testate["Referer"] = referer
        testate["X-Requested-With"] = "XMLHttpRequest"
    url = f"{BASE}{percorso}"

    for attesa in (*ATTESE_429_S, None):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=testate), timeout=30
            ) as risposta:
                corpo = risposta.read().decode("utf-8", "replace")
            time.sleep(PAUSA_S)
            return corpo
        except urllib.error.HTTPError as e:
            # UN 429 NON E' «NIENTE QUI»: e' «non adesso». Contarlo come una
            # partita senza mercati riempirebbe il sito di schede spoglie
            # senza che niente diventi rosso.
            if e.code == 429 and attesa is not None:
                log.warning("429 su %s: aspetto %ds", percorso, attesa)
                time.sleep(attesa)
                continue
            raise BetexplorerNonRaggiungibile(f"{percorso}: {e}") from e
        except (urllib.error.URLError, OSError) as e:
            raise BetexplorerNonRaggiungibile(f"{percorso}: {e}") from e
    raise BetexplorerNonRaggiungibile(f"{percorso}: 429 anche dopo le attese")


# Il prefisso di lingua lo mette la geo-localizzazione e da un datacenter non
# c'e'. Opzionale, sempre.
_RIGA = re.compile(
    r'href="(?:/[a-z]{2})?/football/[^"]+/([A-Za-z0-9]{8})/"[^>]*class="in-match"[^>]*>'
    r"(.*?)</a>",
    re.S,
)


def elenco(codice: str, *, html: str | None = None) -> list[PartitaBX]:
    """Le partite di una competizione, per l'intera stagione."""
    lega = LEGHE.get(codice)
    if lega is None:
        return []
    if html is None:
        html = _scarica(f"/football/{lega}/fixtures/")
    return _leggi_elenco(html)


def _leggi_elenco(html: str) -> list[PartitaBX]:
    partite: list[PartitaBX] = []
    for riga in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        trovato = _RIGA.search(riga)
        if not trovato:
            continue
        squadre = re.findall(r"<span>([^<]+)</span>", trovato.group(2))
        if len(squadre) < 2:
            continue
        quote = [float(x) for x in re.findall(r'data-odd="([\d.]+)"', riga)]
        partite.append(
            PartitaBX(
                id=trovato.group(1),
                casa=squadre[0].strip(),
                ospiti=squadre[1].strip(),
                esito_finale=quote[:3] if len(quote) >= 3 else [],
            )
        )
    return partite


def aggancia(partite: list[PartitaBX], casa: str, ospiti: str) -> PartitaBX | None:
    """La loro partita che corrisponde alla nostra, o `None`.

    NESSUN VINCOLO DI DATA, al contrario di sportsgambler: qui l'elenco e'
    l'intera stagione, e in un girone di andata e ritorno la coppia
    casa-ospiti nel verso giusto compare una volta sola. La data non
    aggiungerebbe nessuna discriminazione, e i due calendari a volte non
    concordano — pretenderla farebbe mancare le partite rinviate.
    """
    migliore: tuple[float, PartitaBX] | None = None
    for p in partite:
        s_casa = somiglianza(casa, p.casa)
        s_ospiti = somiglianza(ospiti, p.ospiti)
        if s_casa < SOGLIA_NOME or s_ospiti < SOGLIA_NOME:
            continue
        punteggio = s_casa + s_ospiti
        if migliore is None or punteggio > migliore[0]:
            migliore = (punteggio, p)
    return migliore[1] if migliore else None


def _linea(hcp: str) -> str | None:
    """La linea del mercato, dal campo che betexplorer chiama `data-hcp`.

    Il formato e' `E-2-2-0-0.5-0`, e la linea e' il quinto pezzo. Senza, i
    dodici mercati «gol totali» di una partita sono dodici righe identiche nel
    nome e indistinguibili: «Over» non vuol dire niente se non si sa sopra
    cosa.
    """
    pezzi = hcp.split("-")
    if len(pezzi) < 5:
        return None
    valore = pezzi[4]
    return valore if valore not in ("", "0") else None


def mercati(
    partita: PartitaBX, codice: str, *, frammenti: dict | None = None
) -> list[dict]:
    """I mercati estesi di una partita, con la mediana dei bookmaker.

    LA MEDIANA E NON IL PREZZO MIGLIORE. Il prezzo migliore e' quello di un
    operatore solo, spesso un fuori scala che nessun altro offre: mostrarlo
    come «la quota» direbbe al lettore che quel prezzo e' il mercato, e non lo
    e'. La mediana e' la stessa scelta che il progetto fa gia' per le quote
    principali.

    `frammenti` esiste per i test: il parsing e' la parte che si rompe quando
    il sito cambia, ed e' l'unica che ha senso provare su una pagina salvata.
    """
    lega = LEGHE.get(codice, "")
    riferimento = f"{BASE}/football/{lega}/"
    fuori: list[dict] = []

    for chiave, (nome, colonne, vincenti) in MERCATI.items():
        if frammenti is not None:
            html = frammenti.get(chiave)
            if html is None:
                continue
        else:
            try:
                grezzo = _scarica(
                    f"/match-odds/{partita.id}/1/{chiave}/odds/?lang=2", riferimento
                )
                html = json.loads(grezzo).get("odds", "")
            except (BetexplorerNonRaggiungibile, ValueError) as exc:
                log.warning("mercato %s di %s non letto: %s", chiave, partita.id, exc)
                continue
        fuori.extend(_leggi_mercato(html, nome, colonne, vincenti))

    return fuori


def _leggi_mercato(
    html: str, nome: str, colonne: tuple[str, ...], vincenti: int = 1
) -> list[dict]:
    """Una tabella di betexplorer verso i nostri mercati.

    Ogni `<tr>` e' un bookmaker; le celle `data-odd` stanno nell'ordine delle
    colonne, e `data-hcp` porta la linea. Le righe di uno stesso mercato con
    linee diverse — le dodici soglie dei gol totali — diventano dodici mercati
    distinti, uno per linea.
    """
    per_linea: dict[str | None, list[list[float]]] = {}

    for riga in re.split(r"<tr[ >]", html):
        quote = re.findall(r'data-odd="([\d.]+)"', riga)
        if len(quote) < len(colonne):
            continue
        hcp = re.search(r'data-hcp="([^"]*)"', riga)
        linea = _linea(hcp.group(1)) if hcp else None
        try:
            valori = [float(x) for x in quote[: len(colonne)]]
        except ValueError:
            continue
        if any(v <= 1.0 for v in valori):
            # Una quota decimale non puo' valere meno di 1: e' una cella vuota
            # letta male, e una sola basterebbe a falsare la mediana.
            continue
        per_linea.setdefault(linea, []).append(valori)

    fuori: list[dict] = []
    for linea, righe in sorted(per_linea.items(), key=lambda kv: (kv[0] is None, kv[0])):
        if len(righe) < BOOKMAKER_MINIMI:
            continue
        if linea is None and len(colonne) == 2 and nome == "Gol totali":
            # «Over» senza sapere sopra cosa non e' un mercato: e' la riga di
            # intestazione della tabella, letta come se fosse un bookmaker.
            continue
        mediane = [median(r[i] for r in righe) for i in range(len(colonne))]
        mercato = _mercato(nome, linea, colonne, mediane, len(righe), vincenti)
        if mercato is not None:
            fuori.append(mercato)
    return fuori


def _mercato(
    nome: str,
    linea: str | None,
    colonne: tuple[str, ...],
    mediane: list[float],
    n_bookmaker: int,
    vincenti: int,
) -> dict | None:
    """Un mercato con le probabilita' gia' sgonfiate del margine.

    Si usa `devig_power`, lo stesso metodo delle quote principali, e non la
    proporzione semplice: dividere ogni inversa per la somma sposta piu'
    probabilita' sui favoriti di quanta ne tolga agli sfavoriti, ed e'
    esattamente dove il margine del banco NON sta.

    Torna `None` sulle quote che il de-vig rifiuta — somma sotto il numero di
    esiti vincenti, cioe' un margine negativo. E' una cella letta male, e
    mostrarla come mercato significherebbe pubblicare un numero inventato.
    """
    try:
        esito = devig_power(mediane, n_winners=vincenti)
    except DevigError as exc:
        log.warning("%s linea %s: quote scartate (%s)", nome, linea, exc)
        return None

    return {
        "fonte": "betexplorer",
        "mercato": nome,
        "linea": linea,
        "n_bookmaker": n_bookmaker,
        "esiti": [
            {
                "esito": colonna,
                "decimale": round(quota, 2),
                "probabilita_implicita": round(float(p), 4),
            }
            for colonna, quota, p in zip(
                colonne, mediane, esito.probabilities, strict=True
            )
        ],
        "somma_probabilita": round(esito.overround, 4),
        # Il margine e' l'eccesso rispetto a quanti esiti si avverano, non
        # rispetto a uno: con la doppia chance la somma sana e' 2, quindi
        # 2,1373 e' un margine del 6,9% — non del 114%, e nemmeno della sua
        # meta'.
        "margine_percento": round((esito.overround / vincenti - 1.0) * 100, 2),
    }
