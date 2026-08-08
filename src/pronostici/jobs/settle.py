"""Job 6 — `settle`: l'esito, e lo skill davvero realizzato.

    python -m pronostici.jobs.settle

A partita conclusa riempie l'esito sulle righe del registro e calcola lo
**skill realizzato** (ricerca 10.1):

    skill = ln(p/b)          se l'evento si e' verificato
          = ln((1-p)/(1-b))  altrimenti

Questa e' la metrica di testa del progetto, e la ragione e' che **lo score
dichiarato prima della partita e' la media di questo stesso numero** sotto la
nostra probabilita'. Se le previsioni sono calibrate le due medie coincidono;
se lo skill realizzato resta sotto quello dichiarato, siamo sovraconfidenti e
lo shrinkage e' troppo debole. Nella simulazione della ricerca la
sovraconfidenza produce 0,079 dichiarato contro 0,014 realizzato: un fattore
5,7, visibile con poche decine di pronostici.

Idempotenza: l'esito si scrive **una volta sola**. Rieseguire il job non
cambia nulla, e non puo' toccare nessun campo che non sia di esito (vedi
`ledger.apply_settlements`).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime

from .. import fixtures as fx
from .. import ledger
from ..archive import load_all
from ..competitions import ACTIVE_CODES
from ..config import DATA
from ..model.markets import catalog
from ..model.matrix import MAX_GOALS
from ..storage import SCHEMA_VERSION, write_json

log = logging.getLogger("settle")

ACCURACY_FILE = DATA / "accuracy.json"
EPS = 1e-9

# Bucket grossolani: con i nostri n, cinque punti di calibrazione sarebbero
# rumore travestito da curva (brief 9.4).
BUCKETS = ((0.50, 0.65), (0.65, 0.80), (0.80, 1.01))


def outcome_of(
    market_key: str, ft_home: int, ft_away: int, *, max_goals: int = MAX_GOALS
) -> int | None:
    """L'evento si e' verificato? Si legge dalla **stessa maschera** usata per
    prevederlo: previsione e verifica non possono divergere per una svista."""
    masks = {d.key: d.mask for d in catalog(max_goals)}
    mask = masks.get(market_key)
    if mask is None:
        return None
    h = min(max(int(ft_home), 0), max_goals)
    a = min(max(int(ft_away), 0), max_goals)
    return int(bool(mask[h, a]))


def realized_skill(p: float, reference: float, outcome: int) -> float:
    """`ln(p/b)` se l'evento esce, `ln((1-p)/(1-b))` altrimenti."""
    p = min(max(p, EPS), 1 - EPS)
    b = min(max(reference, EPS), 1 - EPS)
    return math.log(p / b) if outcome else math.log((1 - p) / (1 - b))


def bucket_of(p: float) -> str | None:
    for lo, hi in BUCKETS:
        if lo <= p < hi:
            return f"{lo:.2f}-{min(hi, 1.0):.2f}"
    return None


def _summary(rows: list[dict]) -> dict:
    """Skill dichiarato contro skill realizzato, piu' hit rate per bucket."""
    settled = [r for r in rows if r.get("outcome") is not None]
    if not settled:
        return {"n": 0}
    declared = [float(r["skill_declared"]) for r in settled]
    realized = [float(r["skill_realized"]) for r in settled]
    n = len(settled)
    mean_d = sum(declared) / n
    mean_r = sum(realized) / n
    # Errore standard della media realizzata: senza, il confronto fra le due
    # barre e' una differenza senza scala.
    var = sum((x - mean_r) ** 2 for x in realized) / (n - 1) if n > 1 else 0.0
    se = math.sqrt(var / n) if n > 1 else None

    buckets: dict[str, dict] = {}
    for row in settled:
        name = bucket_of(float(row["p"]))
        if name is None:
            continue
        entry = buckets.setdefault(name, {"n": 0, "hits": 0, "p_sum": 0.0})
        entry["n"] += 1
        entry["hits"] += int(row["outcome"])
        entry["p_sum"] += float(row["p"])
    for entry in buckets.values():
        entry["hit_rate"] = round(entry["hits"] / entry["n"], 4)
        entry["mean_p"] = round(entry["p_sum"] / entry["n"], 4)
        # Sotto 30 il numero c'e' ma non si legge come una misura: il
        # frontend lo mostra in grigio, non lo nasconde (brief 9.4).
        entry["enough"] = entry["n"] >= 30
        entry.pop("p_sum")

    return {
        "n": n,
        "skill_declared_mean": round(mean_d, 5),
        "skill_realized_mean": round(mean_r, 5),
        "skill_realized_se": round(se, 5) if se is not None else None,
        "calibration_gap": round(mean_d - mean_r, 5),
        "hit_rate": round(sum(r["outcome"] for r in settled) / n, 4),
        "buckets": dict(sorted(buckets.items())),
    }


def build_accuracy(all_rows: dict[int, list[dict]]) -> dict:
    """Il contenuto della pagina "Come stiamo andando", dal registro."""
    flat = [row for rows in all_rows.values() for row in rows]
    phases = (ledger.PHASE_PRELIMINARY, ledger.PHASE_DEFINITIVE)
    predictions = [r for r in flat if r["phase"] in phases]
    with_pick = [r for r in predictions if r.get("market_key")]

    by_phase = {
        phase: _summary([r for r in with_pick if r["phase"] == phase])
        for phase in (ledger.PHASE_PRELIMINARY, ledger.PHASE_DEFINITIVE)
    }

    silence: dict[str, dict] = {}
    for phase in (ledger.PHASE_PRELIMINARY, ledger.PHASE_DEFINITIVE):
        rows = [r for r in predictions if r["phase"] == phase]
        silent = sum(1 for r in rows if r.get("market_key") is None)
        by_reason: dict[str, int] = defaultdict(int)
        for r in rows:
            if r.get("silence_reason"):
                by_reason[r["silence_reason"]] += 1
        silence[phase] = {
            "n": len(rows),
            "silent": silent,
            "rate": round(silent / len(rows), 4) if rows else None,
            # Quale filtro ha morso, e quante volte: se `p_min` scarta il 40%
            # non stiamo applicando un vincolo di prodotto, stiamo nascondendo
            # che il modello punta su cose improbabili (ricerca 10.2).
            "by_reason": dict(sorted(by_reason.items())),
        }

    transitions: dict[str, int] = defaultdict(int)
    for row in flat:
        if row["phase"] == ledger.PHASE_DEFINITIVE and row.get("transition"):
            transitions[row["transition"]] += 1

    live = _summary(with_pick)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Un backtest non e' un track record: questa sezione contiene solo
        # pronostici pubblicati prima della partita, e non va mai aggregata
        # con `data/backtest.json`.
        "live": live,
        "by_phase": by_phase,
        "silence": silence,
        "transitions": dict(sorted(transitions.items())),
        "progress_to_500": {
            "published": len(with_pick),
            "target": 500,
        },
    }


def run(
    competitions: list[str] | None = None,
    *,
    as_of: datetime | None = None,
    dry_run: bool = False,
) -> dict:
    as_of = as_of or datetime.now(UTC)
    started = time.monotonic()
    codes = list(competitions or ACTIVE_CODES)

    finished: dict[int, object] = {}
    for code in codes:
        for match in load_all(code):
            if match.is_finished:
                finished[match.match_id] = match

    all_rows = ledger.load_all_seasons()
    settled = 0
    missing_result = 0
    per_season: dict[int, dict[str, dict]] = defaultdict(dict)

    for season, rows in all_rows.items():
        for row in rows:
            if row.get("outcome") is not None or row.get("settled_at") is not None:
                continue  # gia' chiuso: non si tocca
            match = finished.get(row["match_id"])
            if match is None:
                missing_result += 1
                continue
            update = {
                "ft_home": match.ft_home,
                "ft_away": match.ft_away,
                "settled_at": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            if row.get("market_key"):
                outcome = outcome_of(row["market_key"], match.ft_home, match.ft_away)
                if outcome is None:
                    log.warning("mercato sconosciuto: %s", row["market_key"])
                    continue
                update["outcome"] = outcome
                update["skill_realized"] = round(
                    realized_skill(float(row["p"]), float(row["reference"]), outcome), 6
                )
            per_season[season][row["prediction_id"]] = update
            settled += 1

    ledger_changed = 0
    if not dry_run:
        for season, updates in per_season.items():
            ledger_changed += ledger.apply_settlements(season, updates)

    all_rows = ledger.load_all_seasons()
    accuracy = build_accuracy(all_rows)
    accuracy_changed = False
    if not dry_run:
        accuracy_changed = write_json(ACCURACY_FILE, accuracy, indent=2)
        _stamp_fixtures(all_rows, finished)

    return {
        "seconds": round(time.monotonic() - started, 1),
        "rows_settled": settled,
        "ledger_rows_changed": ledger_changed,
        "awaiting_result": missing_result,
        "accuracy_file_changed": accuracy_changed,
        "accuracy": accuracy["live"],
        "silence": accuracy["silence"],
        "dry_run": dry_run,
    }


def _stamp_fixtures(all_rows: dict[int, list[dict]], finished: dict[int, object]) -> int:
    """Scrive l'esito nei file giornalieri, l'unica scrittura ammessa dopo il
    fischio d'inizio (brief 7.2)."""
    # La scheda mostra la fase **definitiva** quando esiste, quindi l'esito
    # stampato deve essere quello del mercato definitivo. Prendere la prima
    # riga utile scriverebbe l'esito del preliminare sotto un pronostico
    # diverso: due numeri veri che insieme dicono una cosa falsa.
    best: dict[int, dict] = {}
    for rows in all_rows.values():
        for row in rows:
            if row.get("outcome") is None or row["match_id"] not in finished:
                continue
            current = best.get(row["match_id"])
            if current is None or (
                row["phase"] == ledger.PHASE_DEFINITIVE
                and current["phase"] != ledger.PHASE_DEFINITIVE
            ):
                best[row["match_id"]] = row

    by_day: dict[str, list[dict]] = defaultdict(list)
    for match_id, row in best.items():
        match = finished[match_id]
        by_day[row["utc_date"][:10]].append(
            {
                "match_id": match_id,
                "result": {"home": match.ft_home, "away": match.ft_away},
                "outcome": row["outcome"],
                "phase": row["phase"],
                "skill_realized": row.get("skill_realized"),
            }
        )

    changed = 0
    for day, results in by_day.items():
        payload = fx.load_day(day)
        if not payload:
            continue
        index = {r["match_id"]: r for r in results}
        touched = False
        for entry in payload.get("fixtures", []):
            result = index.get(entry["match_id"])
            if result and entry.get("result") != result["result"]:
                entry["result"] = result["result"]
                # L'esito si stampa solo se riguarda la stessa fase che la
                # scheda mostra; il risultato della partita invece vale sempre.
                entry["outcome"] = (
                    result["outcome"] if entry.get("phase") == result["phase"] else None
                )
                touched = True
        if touched:
            changed += int(
                fx.upsert_day(
                    day,
                    payload["fixtures"],
                    allow_after_kickoff=True,
                )
            )
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competitions", nargs="*", default=list(ACTIVE_CODES))
    parser.add_argument("--dry-run", action="store_true", help="non scrive niente")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(args.competitions, dry_run=args.dry_run)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
