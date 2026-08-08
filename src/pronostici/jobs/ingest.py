"""Job 1 — `ingest`: calendario e risultati da football-data.org.

    python -m pronostici.jobs.ingest --competitions SA --seasons 2024 2025

Idempotente: rieseguirlo non duplica righe e non cambia il passato (vedi
`archive.merge_season`). Ogni partita vista viene archiviata per sempre, anche
quando la finestra gratuita di due stagioni scorrera' oltre (rischio 7).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone

from ..archive import merge_season, parse_match
from ..competitions import ACTIVE_CODES, get
from ..sources.football_data import FootballDataClient, FootballDataError

log = logging.getLogger("ingest")

# Stagione corrente e precedente: e' tutto cio' che il piano gratuito espone.
def default_seasons(today: datetime | None = None) -> list[int]:
    now = today or datetime.now(timezone.utc)
    # Le stagioni europee sono etichettate con l'anno di inizio.
    current = now.year if now.month >= 7 else now.year - 1
    return [current - 1, current]


def run(
    competitions: list[str],
    seasons: list[int],
    *,
    offline: bool = False,
    refresh: bool = False,
) -> dict:
    client = FootballDataClient(offline=offline)
    started = time.monotonic()
    results: list[dict] = []
    errors: list[dict] = []

    for code in competitions:
        competition = get(code)
        for season in seasons:
            try:
                payload = client.competition_matches(
                    code, season=season, refresh=refresh
                )
            except FootballDataError as exc:
                # Una stagione fuori finestra risponde 403: non e' un guasto,
                # e' il limite del piano. Il job prosegue.
                log.warning("%s %s non disponibile: %s", code, season, exc)
                errors.append({"competition": code, "season": season, "error": str(exc)})
                continue
            matches = [parse_match(m, code, season) for m in payload]
            summary = merge_season(code, season, matches)
            summary["name"] = competition.name
            results.append(summary)
            log.info(
                "%s %s: %d partite (%d nuove, %d aggiornate)%s",
                code,
                season,
                summary["total"],
                summary["added"],
                summary["updated"],
                "" if summary["file_changed"] else " [invariato]",
            )

    observed = client.last_rate_limit
    return {
        "seconds": round(time.monotonic() - started, 1),
        "http_requests": client.request_count,
        "rate_limit_available_minute": observed.requests_available_minute,
        "rate_limit_reset_s": observed.counter_reset_s,
        "seasons": results,
        "errors": errors,
        "changed": any(r["file_changed"] for r in results),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competitions", nargs="*", default=list(ACTIVE_CODES))
    parser.add_argument("--seasons", nargs="*", type=int, default=None)
    parser.add_argument("--offline", action="store_true", help="solo cache, mai rete")
    parser.add_argument("--refresh", action="store_true", help="ignora la cache")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    seasons = args.seasons or default_seasons()
    report = run(
        args.competitions, seasons, offline=args.offline, refresh=args.refresh
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
