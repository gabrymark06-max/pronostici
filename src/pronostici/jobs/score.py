"""Job 3 — `score`: pronostico preliminare per le fixture dei prossimi giorni.

    python -m pronostici.jobs.score --days 7

Passo economico, O(partite): i 300 draw di parametri sono gia' su disco, qui
si costruiscono solo le matrici e si marginalizzano i mercati.

Scrive `data/fixtures/{data}.json` (il contratto col frontend) e aggiunge al
ledger la riga **preliminare**, con w = 1,0. La riga non viene mai riscritta:
se il definitivo cambiera' idea, sara' una riga in piu', non una modifica.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .. import ledger
from ..archive import load_all
from ..competitions import ACTIVE_CODES, get
from ..config import FIXTURES_DIR
from ..model.bootstrap import BootstrapResult
from ..pipeline import score_fixture
from ..storage import SCHEMA_VERSION, read_json, write_json
from .retrain import params_path

log = logging.getLogger("score")


def season_of(match) -> int:
    return match.season


def fixture_payload(scored, phase: str) -> dict:
    """La forma che il frontend consuma. Il silenzio e' un tipo di prima
    classe, non un ramo `else`: ha il suo motivo e le sue probabilita' grezze."""
    sel = scored.selection
    match = scored.match
    payload = {
        "match_id": match.match_id,
        "competition": match.competition,
        "utc_date": match.utc_date,
        "matchday": match.matchday,
        "home": {
            "name": match.home_name,
            "tla": match.home_tla,
            "crest": match.home_crest,
        },
        "away": {
            "name": match.away_name,
            "tla": match.away_tla,
            "crest": match.away_crest,
        },
        "phase": phase,
        "source": scored.source,
        "model_weight": scored.model_weight,
        "expected_goals": {
            "home": round(scored.lam_home, 3),
            "away": round(scored.lam_away, 3),
        },
        "reasons": scored.reasons,
        "diagnostics": {
            "n_candidates": sel.n_candidates,
            "n_clusters": sel.n_clusters,
            "filter_bites": sel.filter_bites,
            "truncated_mass": float(f"{scored.truncated_mass:.3e}"),
        },
        # Sempre presenti, anche quando si tace: sono "le probabilita', senza
        # consiglio" della card di silenzio (brief 8.4).
        "raw_probabilities": {
            key: round(scored.market_probabilities[key], 4)
            for key in (
                "1x2_home", "1x2_draw", "1x2_away",
                "over_2.5", "under_2.5", "btts_yes",
            )
            if key in scored.market_probabilities
        },
    }
    if sel.pick is not None:
        payload["prediction"] = {
            **sel.pick.to_dict(),
            "cluster_members": sel.cluster_members,
            "runners_up": [c.to_dict() for c in sel.runners_up],
        }
        payload["silence"] = None
    else:
        payload["prediction"] = None
        payload["silence"] = {"reason": sel.silence_reason}
    if scored.half_time:
        payload["half_time"] = {k: round(v, 4) for k, v in scored.half_time.items()}
    return payload


def run(
    competitions: list[str],
    *,
    days: int = 7,
    as_of: datetime | None = None,
    tau: float = 0.08,
) -> dict:
    as_of = as_of or datetime.now(timezone.utc)
    horizon = as_of + timedelta(days=days)
    started = time.monotonic()

    by_date: dict[str, list[dict]] = defaultdict(list)
    ledger_rows: dict[int, list] = defaultdict(list)
    scored_count = silent_count = 0
    skipped: list[dict] = []

    for code in competitions:
        payload = read_json(params_path(code), default=None)
        if not payload:
            log.warning("%s: nessun params.json, salto (esegui `retrain`)", code)
            continue
        boot = BootstrapResult.from_dict(payload["bootstrap"])
        base_rates = payload["base_rates"]
        ht_ratio = payload.get("half_time_ratio")

        upcoming = [
            m
            for m in load_all(code)
            if not m.is_finished and as_of <= m.date <= horizon
        ]
        for match in upcoming:
            try:
                scored = score_fixture(
                    match,
                    boot,
                    base_rates,
                    tau=tau,
                    ht_ratio=ht_ratio,
                    model_weight=1.0,
                )
            except KeyError as exc:
                # Squadra neopromossa senza storico: non e' un guasto.
                skipped.append({"match_id": match.match_id, "reason": str(exc)})
                continue

            day = match.utc_date[:10]
            by_date[day].append(fixture_payload(scored, ledger.PHASE_PRELIMINARY))
            if scored.selection.is_silent:
                silent_count += 1
            else:
                scored_count += 1

            ledger_rows[match.season].append(
                ledger.make_row(
                    phase=ledger.PHASE_PRELIMINARY,
                    match=match,
                    selection=scored.selection,
                    model_weight=1.0,
                    source=scored.source,
                    reasons=scored.reasons,
                )
            )

    files_changed = 0
    for day, fixtures in sorted(by_date.items()):
        fixtures.sort(key=lambda f: f["utc_date"])
        silent = sum(1 for f in fixtures if f["prediction"] is None)
        changed = write_json(
            FIXTURES_DIR / f"{day}.json",
            {
                "schema_version": SCHEMA_VERSION,
                "date": day,
                "generated_at": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
                # Il conteggio dichiarato in testa alla lista (brief 8.4):
                # un sito che conta i propri silenzi sembra severo.
                "silence_count": silent,
                "total": len(fixtures),
                "fixtures": fixtures,
            },
        )
        files_changed += int(changed)

    appended = 0
    for season, rows in ledger_rows.items():
        appended += ledger.append(season, rows)

    total = scored_count + silent_count
    return {
        "seconds": round(time.monotonic() - started, 1),
        "fixtures": total,
        "with_prediction": scored_count,
        "silent": silent_count,
        "silence_rate": round(silent_count / total, 3) if total else None,
        "ledger_rows_appended": appended,
        "files_changed": files_changed,
        "skipped": skipped[:10],
        "skipped_total": len(skipped),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competitions", nargs="*", default=list(ACTIVE_CODES))
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--tau", type=float, default=0.08)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(args.competitions, days=args.days, tau=args.tau)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
