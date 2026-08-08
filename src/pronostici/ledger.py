"""Ledger append-only dei pronostici.

Preliminare e definitivo sono **due righe permanenti**, non un aggiornamento
in place. E' la scelta che rende impossibile per costruzione il fallimento di
credibilita' del settore: in un repository pubblico con commit datati, quello
che abbiamo detto prima della partita e' verificabile da chiunque, e non
coincide con quello che riportiamo dopo per buona volonta' ma per struttura.

Regole dure (brief 7.2):

* una sola finalizzazione per partita;
* nessuna scrittura dopo il fischio d'inizio, mai;
* il preliminare non viene mai cancellato;
* `settle` scrive solo l'esito, su una riga propria.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import LEDGER_DIR
from .storage import SCHEMA_VERSION, append_jsonl, read_jsonl, write_text_atomic

PHASE_PRELIMINARY = "preliminary"
PHASE_DEFINITIVE = "definitive"
PHASE_SETTLEMENT = "settlement"

# Le transizioni fra le due verita' della stessa partita (brief 7.3). Le due
# che cambiano stato sono, per il brief, le schermate che guadagnano piu'
# fiducia dell'intero prodotto: un sistema che ritira pubblicamente un proprio
# consiglio non lo ha mai fatto nessuno.
TRANSITION_FIRST = "first"  # non c'era un preliminare da confrontare
TRANSITION_CONFIRMED = "confirmed"  # stesso mercato consigliato
TRANSITION_CHANGED = "changed"  # mercato diverso
TRANSITION_TO_SILENCE = "prediction_to_silence"
TRANSITION_FROM_SILENCE = "silence_to_prediction"
TRANSITION_STILL_SILENT = "still_silent"

# Gli unici campi che `settle` puo' scrivere su una riga gia' pubblicata, e
# solo quando valgono None. Tutto il resto e' immutabile: la riga di
# pronostico e' una dichiarazione datata, non un record modificabile.
SETTLEMENT_FIELDS = (
    "outcome",
    "ft_home",
    "ft_away",
    "skill_realized",
    "settled_at",
)


class LedgerImmutabilityError(RuntimeError):
    """Un tentativo di riscrivere il passato. Non e' un caso da gestire in
    silenzio: e' l'unica cosa che il prodotto promette di non fare."""


@dataclass(frozen=True)
class LedgerRow:
    prediction_id: str
    schema_version: int
    phase: str
    match_id: int
    competition: str
    utc_date: str
    home: str
    away: str
    written_at: str
    model_weight: float
    source: str  # "model_only" | "blended_with_odds"
    market_key: str | None
    market_label: str | None
    p: float | None
    p_raw: float | None
    sigma: float | None
    band_p5: float | None
    band_p95: float | None
    reference: float | None
    score: float | None
    silence_reason: str | None
    n_candidates: int = 0
    n_clusters: int = 0
    filter_bites: dict[str, int] = field(default_factory=dict)
    cluster_members: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    outcome: int | None = None  # riempito da `settle`, una volta sola
    ft_home: int | None = None
    ft_away: int | None = None
    # Confronto con la fase precedente: lo scrive `finalize`, ed e' cio' che
    # permette alla scheda di dire "fino a ieri dicevamo X".
    transition: str | None = None
    previous_market_key: str | None = None
    previous_market_label: str | None = None
    previous_p: float | None = None
    # Skill: `skill_declared` e' noto prima della partita (coincide con lo
    # score), `skill_realized` dopo. Se il sistema e' calibrato le due medie
    # devono coincidere: e' il cruscotto della ricerca 10.1.
    skill_declared: float | None = None
    skill_realized: float | None = None
    settled_at: str | None = None


def prediction_id(match_id: int, phase: str) -> str:
    """Identita' deterministica: rieseguire un job non crea una riga nuova."""
    return f"{match_id}:{phase}"


def ledger_path(season: int) -> Path:
    return LEDGER_DIR / f"{season}.jsonl"


def load_season(season: int) -> list[dict[str, Any]]:
    return read_jsonl(ledger_path(season))


def existing_ids(season: int) -> set[str]:
    return {row["prediction_id"] for row in load_season(season)}


def has_phase(season: int, match_id: int, phase: str) -> bool:
    """Serve a garantire 'una sola finalizzazione per partita'."""
    return prediction_id(match_id, phase) in existing_ids(season)


class PhaseIndex:
    """Gli identificativi gia' presenti, letti una volta sola.

    `has_phase` rilegge l'intero registro a ogni domanda: comodo per un test,
    inaccettabile in un job che la pone una volta per partita mentre il file
    cresce di qualche migliaio di righe a stagione. Qui si legge una volta per
    stagione e si risponde in memoria.
    """

    def __init__(self) -> None:
        self._by_season: dict[int, set[str]] = {}

    def _ids(self, season: int) -> set[str]:
        if season not in self._by_season:
            self._by_season[season] = existing_ids(season)
        return self._by_season[season]

    def has(self, season: int, match_id: int, phase: str) -> bool:
        return prediction_id(match_id, phase) in self._ids(season)


def append(season: int, rows: list[LedgerRow]) -> int:
    """Aggiunge righe nuove. Le righe gia' presenti vengono ignorate, non
    sovrascritte: e' cio' che rende il job idempotente senza toccare il
    passato."""
    known = existing_ids(season)
    fresh = [asdict(r) for r in rows if r.prediction_id not in known]
    return append_jsonl(ledger_path(season), fresh)


def load_all_seasons() -> dict[int, list[dict[str, Any]]]:
    """Tutto il registro, per stagione. Il volume e' di qualche migliaio di
    righe l'anno: leggerlo intero e' piu' semplice di qualunque indice."""
    out: dict[int, list[dict[str, Any]]] = {}
    if not LEDGER_DIR.exists():
        return out
    for path in sorted(LEDGER_DIR.glob("*.jsonl")):
        try:
            season = int(path.stem)
        except ValueError:
            continue
        out[season] = read_jsonl(path)
    return out


def apply_settlements(season: int, updates: dict[str, dict[str, Any]]) -> int:
    """Riempie i campi di esito sulle righe indicate. Ritorna quante ne cambia.

    E' l'unica scrittura non-append di tutto il sistema, e ha tre guardie:

    * puo' toccare solo i campi di `SETTLEMENT_FIELDS`;
    * solo se sulla riga valgono ancora `None` — un esito gia' registrato non
      si tocca, cosi' rieseguire `settle` e' un'operazione nulla;
    * se un aggiornamento tentasse di cambiare qualunque altro campo, solleva.

    Il resto della riga - il pronostico, la probabilita', l'ora in cui e'
    stato scritto - resta esattamente com'era, e la cronologia di git conserva
    comunque la versione precedente al riempimento.
    """
    unknown = {k for u in updates.values() for k in u} - set(SETTLEMENT_FIELDS)
    if unknown:
        raise LedgerImmutabilityError(
            f"`settle` non puo' scrivere questi campi: {sorted(unknown)}"
        )

    rows = load_season(season)
    changed = 0
    lines: list[str] = []
    for row in rows:
        update = updates.get(row["prediction_id"])
        if update:
            applied = {k: v for k, v in update.items() if row.get(k) is None}
            if applied:
                row.update(applied)
                changed += 1
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    if changed:
        write_text_atomic(ledger_path(season), "\n".join(lines) + "\n")
    return changed


def classify_transition(previous: dict[str, Any] | None, selection) -> str:
    """Come e' cambiato il consiglio fra preliminare e definitivo."""
    if previous is None:
        return TRANSITION_FIRST
    was_silent = previous.get("market_key") is None
    is_silent = selection.pick is None
    if was_silent and is_silent:
        return TRANSITION_STILL_SILENT
    if was_silent:
        return TRANSITION_FROM_SILENCE
    if is_silent:
        return TRANSITION_TO_SILENCE
    return (
        TRANSITION_CONFIRMED
        if previous.get("market_key") == selection.pick.key
        else TRANSITION_CHANGED
    )


def make_row(
    *,
    phase: str,
    match,
    selection,
    model_weight: float,
    source: str,
    reasons: list[str] | None = None,
    previous: dict[str, Any] | None = None,
    transition: str | None = None,
) -> LedgerRow:
    """Costruisce la riga da una `Selection`, silenzio incluso."""
    pick = selection.pick
    return LedgerRow(
        prediction_id=prediction_id(match.match_id, phase),
        schema_version=SCHEMA_VERSION,
        phase=phase,
        match_id=match.match_id,
        competition=match.competition,
        utc_date=match.utc_date,
        home=match.home_name,
        away=match.away_name,
        written_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        model_weight=model_weight,
        source=source,
        market_key=pick.key if pick else None,
        market_label=pick.label if pick else None,
        p=round(pick.p_tilde, 4) if pick else None,
        p_raw=round(pick.p_hat, 4) if pick else None,
        sigma=round(pick.sigma, 4) if pick else None,
        band_p5=round(pick.p5, 4) if pick else None,
        band_p95=round(pick.p95, 4) if pick else None,
        reference=round(pick.reference, 4) if pick else None,
        score=round(pick.score, 6) if pick else None,
        silence_reason=selection.silence_reason,
        n_candidates=selection.n_candidates,
        n_clusters=selection.n_clusters,
        filter_bites=selection.filter_bites,
        cluster_members=selection.cluster_members,
        reasons=reasons or [],
        transition=transition or classify_transition(previous, selection),
        previous_market_key=(previous or {}).get("market_key"),
        previous_market_label=(previous or {}).get("market_label"),
        previous_p=(previous or {}).get("p"),
        # Lo score dichiarato **e'** lo skill atteso sotto la nostra
        # probabilita': non e' una seconda quantita', e' la stessa. Si copia
        # qui perche' `settle` confronti due colonne omogenee.
        skill_declared=round(pick.score, 6) if pick else None,
    )
