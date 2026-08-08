"""Job 2 — `retrain`: fit Dixon-Coles + 300 bootstrap, per campionato.

    python -m pronostici.jobs.retrain --competitions SA

E' il passo costoso, ed e' O(campionati), non O(partite): i 300 draw si fanno
per campionato e si persistono. Scorare una fixture poi costa millisecondi.
Fondere questo job con `score` e' l'errore che renderebbe il sistema lento e
fragile (brief 5.1).

Gira **solo per i campionati con nuovi risultati**: l'impronta della lista di
partite concluse decide se rifittare o saltare.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import UTC, datetime

from ..archive import load_all
from ..competitions import ACTIVE_CODES, get
from ..config import LEAGUES_DIR
from ..model.baserates import compute_base_rates
from ..model.bootstrap import DEFAULT_DRAWS, run_bootstrap
from ..model.dataset import build_dataset, half_time_ratio
from ..model.dixon_coles import effective_sample_size
from ..storage import SCHEMA_VERSION, read_json, write_json

log = logging.getLogger("retrain")


def results_fingerprint(matches: list) -> str:
    """Impronta delle sole partite concluse: cambia solo con nuovi risultati."""
    finished = sorted(
        (m.match_id, m.ft_home, m.ft_away) for m in matches if m.is_finished
    )
    return hashlib.sha256(json.dumps(finished).encode()).hexdigest()[:16]


def params_path(code: str):
    return LEAGUES_DIR / code / "params.json"


def run(
    competitions: list[str],
    *,
    draws: int = DEFAULT_DRAWS,
    force: bool = False,
    as_of: datetime | None = None,
) -> dict:
    as_of = as_of or datetime.now(UTC)
    started = time.monotonic()
    trained: list[dict] = []
    skipped: list[str] = []
    failed: list[dict] = []

    archives = {}
    for code in competitions:
        matches = load_all(code)
        if matches:
            archives[code] = matches

    if not archives:
        raise SystemExit("nessun archivio: esegui prima `ingest`")

    # Base rate: calcolati insieme per tutti i campionati, perche' lo
    # shrinkage e' verso la media multi-campionato.
    base_rates = compute_base_rates(archives, as_of=as_of)

    for code, matches in archives.items():
        fingerprint = results_fingerprint(matches)
        existing = read_json(params_path(code), default=None)
        if (
            not force
            and existing
            and existing.get("results_fingerprint") == fingerprint
            and existing.get("draws") == draws
        ):
            log.info("%s: nessun nuovo risultato, salto", code)
            skipped.append(code)
            continue

        try:
            data = build_dataset(matches, as_of=as_of)
        except ValueError as exc:
            log.warning("%s: %s", code, exc)
            failed.append({"competition": code, "error": str(exc)})
            continue

        t0 = time.monotonic()
        boot = run_bootstrap(data, draws=draws)
        elapsed = time.monotonic() - t0

        payload = {
            "schema_version": SCHEMA_VERSION,
            "competition": code,
            "name": get(code).name,
            "trained_at": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "results_fingerprint": fingerprint,
            "draws": draws,
            "half_life_days": 365,
            "dataset": {
                "matches": data.n_matches,
                "teams": data.n_teams,
                "effective_sample_size": round(effective_sample_size(data.weights), 1),
            },
            "half_time_ratio": half_time_ratio(matches),
            "base_rates": {k: round(v, 5) for k, v in base_rates[code].items()},
            "seconds": round(elapsed, 2),
            "bootstrap": boot.to_dict(),
        }
        changed = write_json(params_path(code), payload)
        log.info(
            "%s: %d partite, %d squadre, %d draw in %.1fs (%d/%d convergiti)%s",
            code,
            data.n_matches,
            data.n_teams,
            draws,
            elapsed,
            boot.converged,
            draws,
            "" if changed else " [invariato]",
        )
        trained.append(
            {
                "competition": code,
                "matches": data.n_matches,
                "teams": data.n_teams,
                "seconds": round(elapsed, 2),
                "converged": boot.converged,
                "file_changed": changed,
            }
        )

    return {
        "seconds": round(time.monotonic() - started, 1),
        "trained": trained,
        "skipped": skipped,
        "failed": failed,
        "changed": any(t["file_changed"] for t in trained),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competitions", nargs="*", default=list(ACTIVE_CODES))
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument(
        "--force", action="store_true", help="rifitta anche senza novita'"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(args.competitions, draws=args.draws, force=args.force)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
