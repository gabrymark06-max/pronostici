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
from datetime import UTC, datetime, timedelta

from .. import fixtures as fx
from .. import ledger
from ..archive import load_all
from ..competitions import ACTIVE_CODES
from ..model.bootstrap import BootstrapResult
from ..model.tau import resolve as resolve_tau
from ..pipeline import score_fixture
from ..storage import read_json
from .retrain import params_path

log = logging.getLogger("score")


def run(
    competitions: list[str],
    *,
    days: int = 7,
    as_of: datetime | None = None,
    tau: float | dict[str, float] | None = None,
) -> dict:
    """`tau=None` significa "quelli misurati dal backtest", che e' il default.

    Fino al 2026-08-11 qui c'era 0,08 per tutte le famiglie: il valore di
    partenza della ricerca 8.3, valido *finche' non c'era il backtest*. Il
    backtest c'e' dal 2026-08-08 e ha misurato i dieci valori; questo job li
    usa, e dichiara nel rapporto da dove vengono.
    """
    as_of = as_of or datetime.now(UTC)
    tau, tau_origin = resolve_tau(tau)
    horizon = as_of + timedelta(days=days)
    started = time.monotonic()

    # I PREZZI GIA' IN ARCHIVIO, per il filtro sulla quota minima.
    #
    # Questo giro non chiama nessuna fonte di quote — e' il preliminare, gira
    # alle 3 di notte — ma i prezzi ci sono lo stesso: `contorno` li ha scritti
    # il pomeriggio prima e `upsert_day` li conserva. Sono di qualche ora
    # prima, e per decidere se una scommessa paga almeno 1,30 bastano: una
    # quota non passa da 1,10 a 1,40 in una notte.
    #
    # Dove non ci sono, il filtro si accontenta di cio' che si deduce dalla
    # probabilita' — vedi `QUOTA_MINIMA` in model/selection.py.
    giorni_in_finestra = [
        (as_of + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days + 1)
    ]
    prezzi_noti = fx.prezzi_per_partita(giorni_in_finestra)

    by_date: dict[str, list[dict]] = defaultdict(list)
    ledger_rows: dict[int, list] = defaultdict(list)
    finalized = ledger.PhaseIndex()
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
            # Una partita gia' finalizzata non torna preliminare: la revisione
            # e' unica e non si annulla da sola la notte dopo (brief 7.2).
            if finalized.has(match.season, match.match_id, ledger.PHASE_DEFINITIVE):
                continue
            try:
                scored = score_fixture(
                    match,
                    boot,
                    base_rates,
                    tau=tau,
                    ht_ratio=ht_ratio,
                    model_weight=1.0,
                    prezzi=prezzi_noti.get(match.match_id),
                )
            except KeyError as exc:
                # Squadra neopromossa senza storico: non e' un guasto.
                skipped.append({"match_id": match.match_id, "reason": str(exc)})
                continue

            day = match.utc_date[:10]
            by_date[day].append(fx.build_payload(scored, ledger.PHASE_PRELIMINARY))
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
    for day, entries in sorted(by_date.items()):
        files_changed += int(fx.upsert_day(day, entries, generated_at=as_of))

    # DOPO AVER SCRITTO, si tolgono le voci rimaste nel giorno sbagliato.
    # Questo giro ha ricostruito tutto il cartellone, quindi e' l'unico punto
    # in cui si sa dove ogni partita si gioca davvero: `upsert_day` fonde
    # dentro un giorno solo e una partita rinviata resterebbe anche in quello
    # da cui e' partita.
    giorno_giusto = {
        int(e["match_id"]): day for day, entries in by_date.items() for e in entries
    }
    ripuliti = fx.rimuovi_fantasmi(giorno_giusto)
    files_changed += len(ripuliti)

    appended = 0
    for season, rows in ledger_rows.items():
        appended += ledger.append(season, rows)

    total = scored_count + silent_count
    return {
        "seconds": round(time.monotonic() - started, 1),
        "tau": tau_origin,
        "giorni_ripuliti": ripuliti,
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
    parser.add_argument(
        "--tau",
        type=float,
        default=None,
        help="tau unico per tutte le famiglie; senza, quelli misurati dal backtest",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(args.competitions, days=args.days, tau=args.tau)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
