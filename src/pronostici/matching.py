"""Appaiamento fra le partite di football-data e gli eventi di the-odds-api.

Le due fonti non condividono un identificativo, e nemmeno un nome: la stessa
partita e' "FC Internazionale Milano - AC Monza" per una e "Inter Milan -
Monza" per l'altra. L'appaiamento e' quindi la parte del job `finalize` che
puo' rompersi in silenzio, ed e' quella che va resa **rumorosa**: un evento
non appaiato viene riportato, non ignorato.

Tre livelli, in ordine:

1. **Finestra temporale.** Si confrontano solo partite il cui calcio d'inizio
   dista meno di poche ore dall'orario dell'evento. Da solo, questo riduce i
   candidati a una manciata e rende innocua l'ambiguita' sui nomi.
2. **Alias espliciti** per i casi che nessuna similarita' risolve bene
   ("Wolves" / "Wolverhampton Wanderers FC").
3. **Similarita' per token con prefisso**, che e' cio' che serve davvero:
   "inter" e' prefisso di "internazionale", "milan" di "milano".

L'appaiamento e' **uno a uno**: un evento non puo' finire su due partite, e
una partita non puo' ricevere due eventi.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# Sigle e parole che non distinguono un club dall'altro. "united", "city",
# "real", "athletic" NON sono qui: sono esattamente cio' che disambigua.
NOISE_TOKENS = frozenset(
    {
        "fc", "afc", "cf", "sc", "ac", "as", "ss", "ssc", "us", "usc", "sv",
        "tsv", "vfl", "vfb", "fsv", "bv", "sg", "rc", "ud", "cd", "ca", "ec",
        "sd", "rcd", "cr", "se", "afa", "af", "fbc", "fbpa", "club", "clube",
        "calcio", "futbol", "football", "fussball", "de", "do", "da", "the",
        "and",
    }
)

# Solo i casi che la similarita' non prende. Un alias che **allunga** il nome
# fa danno: "Gremio" espanso a "Gremio Foot Ball Porto Alegrense" smette di
# assomigliare al "Gremio FBPA" di football-data. La regola e' che un alias
# porta verso la forma piu' corta e piu' distintiva, mai verso quella lunga.
ALIASES: dict[str, str] = {
    "wolves": "wolverhampton wanderers",
    "spurs": "tottenham hotspur",
    "psg": "paris saint germain",
    "paris sg": "paris saint germain",
    "inter": "internazionale",
    "inter milan": "internazionale milano",
    "man city": "manchester city",
    "man utd": "manchester united",
    "man united": "manchester united",
    "borussia mgladbach": "borussia monchengladbach",
    "athletic bilbao": "athletic club",
    "sporting lisbon": "sporting cp",
    "az alkmaar": "az",
}

MIN_PREFIX = 3
TOKEN_RATIO = 0.75
# Sotto questa soglia si preferisce non appaiare: un pronostico definitivo
# costruito sulle quote della partita sbagliata e' molto peggio di nessuno.
MATCH_THRESHOLD = 0.60
# Quando i due nomi si contraddicono su un token lungo, il punteggio non puo'
# superare questo valore, per quanto lungo sia il token che condividono.
DISAGREEMENT_CAP = 0.45
# La partita giusta deve staccare la seconda migliore. Senza margine, una
# partita rinviata puo' far scivolare le sue quote su quella accanto.
MIN_MARGIN = 0.10
TIME_TOLERANCE = timedelta(hours=6)


def normalize(name: str) -> str:
    """Minuscolo, senza accenti, senza punteggiatura, senza sigle e cifre."""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t and not t.isdigit()]
    tokens = [t for t in tokens if t not in NOISE_TOKENS]
    return " ".join(tokens)


def canonical(name: str) -> str:
    """Normalizza e applica l'alias, se ce n'e' uno."""
    norm = normalize(name)
    return ALIASES.get(norm, norm)


def _token_match(a: str, b: str) -> str | None:
    """`"exact"`, `"prefix"`, `"fuzzy"` o None.

    Il tipo di corrispondenza conta quanto il fatto che ci sia: "atletico" e
    "athletic" si somigliano per l'87% dei caratteri e sono due club diversi.
    """
    if a == b:
        return "exact"
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= MIN_PREFIX and long_.startswith(short):
        return "prefix"
    if SequenceMatcher(None, a, b).ratio() >= TOKEN_RATIO:
        return "fuzzy"
    return None


def similarity(a: str, b: str) -> float:
    """Similarita' in [0,1] fra due nomi di squadra.

    Coefficiente di Dice sui **caratteri** dei token appaiati, non sul loro
    numero. La differenza e' quella che separa un appaiamento giusto da uno
    sbagliato: contando i token, "AC Milan" e "Inter Milan" condividono meta'
    del nome e passerebbero; contando i caratteri, "milan" contro
    "internazionale milano" pesa 5 su 25 e viene scartato.

    * "Remo" / "Clube do Remo"           -> 1,00  (appaiata)
    * "Man City" / "Manchester City"     -> 0,67  (appaiata)
    * "CA Mineiro" / "Atletico Mineiro"  -> 0,64  (appaiata)
    * "Real Madrid" / "Real Sociedad"    -> 0,35  (scartata)
    * "Man City" / "Manchester United"   -> 0,26  (scartata)
    * "Inter Milan" / "AC Milan"         -> 0,20  (scartata)
    """
    ta, tb = canonical(a).split(), canonical(b).split()
    if not ta or not tb:
        return 0.0

    used_right: set[int] = set()
    used_left: set[int] = set()
    matched_chars = 0
    has_solid_match = False
    for i, token in enumerate(ta):
        for j, other in enumerate(tb):
            kind = _token_match(token, other) if j not in used_right else None
            if kind:
                used_right.add(j)
                used_left.add(i)
                has_solid_match |= kind in ("exact", "prefix")
                # Un token corto che fa da prefisso a uno lungo porta solo la
                # sua evidenza: "man" non vale quanto "manchester".
                matched_chars += min(len(token), len(other))
                break

    total = sum(len(t) for t in ta) + sum(len(t) for t in tb)
    score = min(1.0, 2.0 * matched_chars / total)

    orphan_left = any(len(t) >= 4 for i, t in enumerate(ta) if i not in used_left)
    orphan_right = any(len(t) >= 4 for j, t in enumerate(tb) if j not in used_right)

    # Un token lungo condiviso non basta se **entrambi** i nomi portano un
    # altro token lungo senza riscontro: "Man City" e "Manchester United"
    # condividono "manchester" e differiscono proprio su cio' che li
    # distingue. E' il caso pericoloso, perche' le due partite possono essere
    # nello stesso turno e alla stessa ora.
    if orphan_left and orphan_right:
        return min(score, DISAGREEMENT_CAP)
    # E una somiglianza solo approssimativa non basta se qualcosa e' rimasto
    # scoperto: "Atletico Madrid" e "Athletic Club" condividono l'87% dei
    # caratteri della prima parola e sono due club diversi della stessa lega.
    if not has_solid_match and (orphan_left or orphan_right):
        return min(score, DISAGREEMENT_CAP)
    return score


@dataclass(frozen=True)
class Pairing:
    match_id: int
    event_index: int
    score: float
    home_similarity: float
    away_similarity: float


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def pair_events(
    matches: list,
    events: list,
    *,
    threshold: float = MATCH_THRESHOLD,
    tolerance: timedelta = TIME_TOLERANCE,
) -> tuple[dict[int, int], list[dict]]:
    """Appaia eventi (con `commence_time`, `home_team`, `away_team`) e partite.

    Ritorna `({match_id: indice_evento}, non_appaiati)`. Gli eventi non
    appaiati portano con se' il perche', cosi' che il job li possa riportare e
    l'alias mancante si veda subito.
    """
    scored: list[Pairing] = []
    reasons: dict[int, str] = {}

    for i, event in enumerate(events):
        kickoff = _parse_time(getattr(event, "commence_time", "") or "")
        home = getattr(event, "home_team", "") or ""
        away = getattr(event, "away_team", "") or ""
        candidates = [
            m
            for m in matches
            if kickoff is None or abs(m.date - kickoff) <= tolerance
        ]
        if not candidates:
            reasons[i] = "nessuna partita nella finestra temporale"
            continue

        ranked = sorted(
            (
                Pairing(
                    m.match_id,
                    i,
                    min(
                        similarity(home, m.home_name),
                        similarity(away, m.away_name),
                    ),
                    similarity(home, m.home_name),
                    similarity(away, m.away_name),
                )
                for m in candidates
            ),
            key=lambda p: -p.score,
        )
        best = ranked[0]
        if best.score < threshold:
            reasons[i] = f"nessun nome sopra soglia ({best.score:.2f} < {threshold})"
            continue
        if len(ranked) > 1 and best.score - ranked[1].score < MIN_MARGIN:
            reasons[i] = (
                f"due partite ugualmente plausibili "
                f"({best.score:.2f} contro {ranked[1].score:.2f})"
            )
            continue
        scored.append(best)

    # Assegnazione golosa sul punteggio: uno a uno in entrambe le direzioni.
    pairs: dict[int, int] = {}
    taken_events: set[int] = set()
    for pairing in sorted(scored, key=lambda p: -p.score):
        if pairing.match_id in pairs or pairing.event_index in taken_events:
            if pairing.event_index not in taken_events:
                reasons[pairing.event_index] = (
                    "partita gia' appaiata a un evento migliore"
                )
            continue
        pairs[pairing.match_id] = pairing.event_index
        taken_events.add(pairing.event_index)

    unmatched = [
        {
            "event": f"{getattr(events[i], 'home_team', '?')} - "
            f"{getattr(events[i], 'away_team', '?')}",
            "commence_time": getattr(events[i], "commence_time", ""),
            "reason": reason,
        }
        for i, reason in sorted(reasons.items())
        if i not in taken_events
    ]
    return pairs, unmatched


# ------------------------------------------------------------------ #
# Contenimento: per le fonti che scrivono i nomi PIU' CORTI dei nostri #
# ------------------------------------------------------------------ #

# Quanto due parole devono somigliarsi per contare come la stessa. Alta
# apposta: sotto, "united" e "unidos" passerebbero.
RATIO_PAROLA = 0.85

# Sotto le tre lettere un prefisso non dice niente: "in" sta in "inter" e in
# "internacional", che sono due club di due continenti diversi.
PREFISSO_MINIMO_PAROLA = 3


def _parola_simile(nostra: str, loro: str) -> bool:
    if nostra == loro:
        return True
    corta, lunga = sorted((nostra, loro), key=len)
    if len(corta) >= PREFISSO_MINIMO_PAROLA and lunga.startswith(corta):
        return True
    return SequenceMatcher(None, nostra, loro).ratio() >= RATIO_PAROLA


def contenimento(nostro: str, loro: str) -> float:
    """Quanta parte del LORO nome si ritrova nel nostro. Asimmetrica apposta.

    `similarity` qui sopra confronta due nomi alla pari, ed e' giusto quando le
    due fonti scrivono con lo stesso registro. Non e' il caso dei siti di quote
    e formazioni: noi prendiamo il nome ufficiale da football-data.org
    ("Borussia Dortmund", "Olympique Lyonnais", "Stade Brestois 29"), loro
    scrivono come si dice allo stadio ("Dortmund", "Lyon", "Brest").

    Con una somiglianza simmetrica le parole che loro non scrivono contano come
    differenze, e l'abbinamento GIUSTO scende sotto soglia. Misurato su
    sportsgambler il 24 agosto 2026: 49 partite agganciate su 174, e i
    candidati scartati erano quasi tutti quelli buoni. Con il contenimento,
    72 su 77 nella finestra utile.

    Qui si chiede solo che ogni parola del loro nome si ritrovi nel nostro.
    "Dortmund" dentro "Borussia Dortmund" vale 1; "Man City" contro
    "Manchester United" vale 0,5, perche' "city" non c'e' da nessuna parte —
    ed e' quello che tiene separati i due club della stessa citta'.

    Il vero argine ai falsi positivi non e' comunque questa soglia: e' che chi
    la usa pretende la conferma su ENTRAMBE le squadre.
    """
    nostre = nostro.split()
    loro_parole = loro.split()
    if not nostre or not loro_parole:
        return 0.0
    if nostro == loro:
        return 1.0
    trovate = sum(1 for w in loro_parole if any(_parola_simile(n, w) for n in nostre))
    return trovate / len(loro_parole)
