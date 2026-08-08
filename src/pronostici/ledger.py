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

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import LEDGER_DIR
from .storage import SCHEMA_VERSION, append_jsonl, read_jsonl

PHASE_PRELIMINARY = "preliminary"
PHASE_DEFINITIVE = "definitive"
PHASE_SETTLEMENT = "settlement"


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
    outcome: int | None = None  # riempito solo dalle righe di settlement
    ft_home: int | None = None
    ft_away: int | None = None


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


def append(season: int, rows: list[LedgerRow]) -> int:
    """Aggiunge righe nuove. Le righe gia' presenti vengono ignorate, non
    sovrascritte: e' cio' che rende il job idempotente senza toccare il
    passato."""
    known = existing_ids(season)
    fresh = [asdict(r) for r in rows if r.prediction_id not in known]
    return append_jsonl(ledger_path(season), fresh)


def make_row(
    *,
    phase: str,
    match,
    selection,
    model_weight: float,
    source: str,
    reasons: list[str] | None = None,
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
        written_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    )
