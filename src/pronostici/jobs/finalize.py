"""Job 4+5 — `finalize`: il pronostico definitivo, con le quote.

    python -m pronostici.jobs.finalize --window-hours 36

Scarica le quote **solo** per i campionati che giocano davvero entro la
finestra, le sgonfia col metodo power, le fonde con il modello a w = 0,35,
riscora e scrive la riga **definitiva** nel registro.

Le due regole che questo job non puo' violare (brief 7.2):

* **il preliminare non si tocca.** Preliminare e definitivo sono due righe
  permanenti, non un aggiornamento. Se il consiglio e' cambiato, la scheda lo
  mostra come contenuto: *"fino a ieri dicevamo X"*;
* **una sola finalizzazione per partita**, e nessuna scrittura dopo il fischio
  d'inizio. La variazione possibile e' limitata a esattamente una, per
  costruzione.

Il caso piu' prezioso e' quello in cui il consiglio **cambia** o si ritira:
un sistema che ritira pubblicamente un proprio consiglio non lo ha mai fatto
nessuno dei riferimenti analizzati (brief 7.3).
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
from ..competitions import ACTIVE_CODES, get
from ..matching import pair_events
from ..model.blend import MODEL_WEIGHT
from ..model.bootstrap import BootstrapResult
from ..pipeline import score_fixture
from ..sources.odds_api import (
    MARKETS,
    SECONDARY_LEAGUES,
    OddsClient,
    OddsUnavailable,
    load_budget,
    save_budget,
)
from ..sources.odds_parse import parse_league
from ..storage import read_json
from .retrain import params_path

log = logging.getLogger("finalize")

# T-36h: le quote piu' vicine al calcio d'inizio sono piu' informative, ma si
# muovono sulle formazioni, che noi non abbiamo (brief 7.4). E un consiglio
# che cambia tre ore prima e' inutile a chi ha letto ieri sera.
WINDOW_HOURS = 36


def transition_sentence(transition: str, previous: dict | None, selection) -> str | None:
    """La riga che la scheda mostra quando la fase cambia.

    Non e' una nota a pie' di pagina: e' contenuto. Le due transizioni che
    cambiano stato sono, per il brief, le schermate che guadagnano piu'
    fiducia dell'intero prodotto.
    """
    old = (previous or {}).get("market_label")
    new = selection.pick.label if selection.pick else None
    if transition == ledger.TRANSITION_CHANGED:
        return (
            f"Fino a ieri dicevamo {old}. Con l'arrivo delle quote la nostra "
            f"stima e' cambiata: ora diciamo {new}."
        )
    if transition == ledger.TRANSITION_TO_SILENCE:
        return (
            f"Fino a ieri dicevamo {old}. Le quote sono arrivate e dicono piu' "
            f"o meno quello che dicevamo noi: ritiriamo il pronostico, su "
            f"questa partita non abbiamo un vantaggio da raccontare."
        )
    if transition == ledger.TRANSITION_FROM_SILENCE:
        return (
            f"Prima delle quote non avevamo niente da dire su questa partita. "
            f"Dal confronto con il mercato e' emerso {new}."
        )
    if transition == ledger.TRANSITION_CONFIRMED:
        return f"Le quote confermano quello che dicevamo: restiamo su {new}."
    if transition == ledger.TRANSITION_STILL_SILENT:
        return "Anche con le quote non abbiamo niente da aggiungere su questa partita."
    return None


def leagues_to_quote(
    competitions: list[str], as_of: datetime, window: timedelta
) -> dict[str, list]:
    """I campionati che giocano davvero entro la finestra, con le loro partite.

    L'ordine e' quello del brief 6.3: prima si guardano i fixture, poi si
    decide chi chiamare. Mai una chiamata per un campionato fermo.
    """
    out: dict[str, list] = {}
    horizon = as_of + window
    seen = ledger.PhaseIndex()
    for code in competitions:
        if get(code).odds_key is None:
            continue
        due = [
            m
            for m in load_all(code)
            if not m.is_finished
            and as_of < m.date <= horizon
            # Una sola finalizzazione per partita, per sempre.
            and not seen.has(m.season, m.match_id, ledger.PHASE_DEFINITIVE)
        ]
        if due:
            out[code] = due
    return out


def run(
    competitions: list[str],
    *,
    window_hours: int = WINDOW_HOURS,
    as_of: datetime | None = None,
    tau: float = 0.08,
    offline: bool = False,
    refresh: bool = False,
    max_age_s: float = 6 * 3600,
    dry_run: bool = False,
) -> dict:
    as_of = as_of or datetime.now(UTC)
    started = time.monotonic()
    budget = load_budget()
    client = OddsClient(offline=offline)

    step = budget.degradation_step()
    report: dict = {
        "as_of": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_hours": window_hours,
        "degradation_step": step,
        "credits_before": budget.used,
        "leagues": [],
        "finalized": 0,
        "silent": 0,
        "transitions": defaultdict(int),
        "unmatched": [],
        "changed_examples": [],
    }

    if step == "model_only":
        # Gradino 4: non e' una schermata di errore, e' il prodotto che
        # funziona con w = 1,0 ovunque e lo dichiara.
        report["skipped_reason"] = "quota esaurita: si resta sul solo modello"
        report["transitions"] = dict(report["transitions"])
        report["seconds"] = round(time.monotonic() - started, 1)
        return report

    due = leagues_to_quote(competitions, as_of, timedelta(hours=window_hours))
    if step in ("secondary_leagues", "totals_market"):
        dropped = [c for c in due if c in SECONDARY_LEAGUES]
        for code in dropped:
            due.pop(code)
        report["dropped_for_budget"] = dropped
    markets = ("h2h",) if step == "totals_market" else MARKETS
    report["markets"] = list(markets)

    by_date: dict[str, list[dict]] = defaultdict(list)
    ledger_rows: dict[int, list] = defaultdict(list)
    preliminary_index: dict[int, dict[str, dict]] = {}
    credits_spent = 0

    for code, matches in sorted(due.items()):
        competition = get(code)
        params = read_json(params_path(code), default=None)
        if not params:
            log.warning("%s: nessun params.json, salto (esegui `retrain`)", code)
            report["leagues"].append({"competition": code, "status": "no_params"})
            continue

        try:
            events, meta = client.fetch_league_cached(
                competition.odds_key,
                budget,
                max_age_s=max_age_s,
                refresh=refresh,
                markets=markets,
            )
        except OddsUnavailable as exc:
            # Degradazione, non guasto: la partita resta col preliminare.
            log.warning("%s: quote non disponibili (%s)", code, exc)
            report["leagues"].append(
                {"competition": code, "status": "unavailable", "detail": str(exc)}
            )
            continue

        credits_spent += int(meta["credits"])
        snapshots = [s for s in parse_league(events) if s.is_usable]
        pairs, unmatched = pair_events(matches, snapshots)
        report["unmatched"].extend(
            {**u, "competition": code} for u in unmatched
        )
        report["leagues"].append(
            {
                "competition": code,
                "status": "ok",
                "odds_source": meta["source"],
                "credits": meta["credits"],
                "events": len(events),
                "usable": len(snapshots),
                "matches_due": len(matches),
                "paired": len(pairs),
            }
        )

        boot = BootstrapResult.from_dict(params["bootstrap"])
        base_rates = params["base_rates"]
        ht_ratio = params.get("half_time_ratio")
        by_id = {m.match_id: m for m in matches}

        for match_id, event_index in sorted(pairs.items()):
            match = by_id[match_id]
            snapshot = snapshots[event_index]
            try:
                scored = score_fixture(
                    match,
                    boot,
                    base_rates,
                    tau=tau,
                    market_probabilities=snapshot.probabilities,
                    model_weight=MODEL_WEIGHT,
                    ht_ratio=ht_ratio,
                )
            except KeyError as exc:
                log.warning("%s: %s", match_id, exc)
                continue
            if scored.source != "blended_with_odds":
                # Meno di due vincoli utilizzabili: non e' un definitivo.
                continue

            if match.season not in preliminary_index:
                preliminary_index[match.season] = {
                    row["prediction_id"]: row
                    for row in ledger.load_season(match.season)
                }
            previous = preliminary_index[match.season].get(
                ledger.prediction_id(match_id, ledger.PHASE_PRELIMINARY)
            )
            transition = ledger.classify_transition(previous, scored.selection)
            sentence = transition_sentence(transition, previous, scored.selection)
            if sentence:
                scored.reasons.insert(0, sentence)

            report["transitions"][transition] += 1
            if scored.selection.is_silent:
                report["silent"] += 1
            else:
                report["finalized"] += 1
            if transition in (
                ledger.TRANSITION_CHANGED,
                ledger.TRANSITION_TO_SILENCE,
                ledger.TRANSITION_FROM_SILENCE,
            ):
                report["changed_examples"].append(
                    {
                        "match": f"{match.home_name} - {match.away_name}",
                        "utc_date": match.utc_date,
                        "transition": transition,
                        "before": (previous or {}).get("market_label"),
                        "before_p": (previous or {}).get("p"),
                        "after": (
                            scored.selection.pick.label
                            if scored.selection.pick
                            else None
                        ),
                        "after_p": (
                            round(scored.selection.pick.p_tilde, 4)
                            if scored.selection.pick
                            else None
                        ),
                    }
                )

            by_date[match.utc_date[:10]].append(
                fx.build_payload(
                    scored,
                    ledger.PHASE_DEFINITIVE,
                    previous=previous,
                    transition=transition,
                    odds_meta={
                        "n_bookmakers": snapshot.n_bookmakers,
                        "markets": sorted(snapshot.probabilities),
                        "devig": {
                            k: round(v["beta"], 3) for k, v in snapshot.devig.items()
                        },
                        "fetched": meta["source"],
                    },
                )
            )
            ledger_rows[match.season].append(
                ledger.make_row(
                    phase=ledger.PHASE_DEFINITIVE,
                    match=match,
                    selection=scored.selection,
                    model_weight=MODEL_WEIGHT,
                    source=scored.source,
                    reasons=scored.reasons,
                    previous=previous,
                    transition=transition,
                )
            )

    files_changed = appended = 0
    if not dry_run:
        for day, entries in sorted(by_date.items()):
            files_changed += int(fx.upsert_day(day, entries, generated_at=as_of))
        for season, rows in ledger_rows.items():
            appended += ledger.append(season, rows)

    # Il contatore si salva **anche** a vuoto: `--dry-run` non scrive
    # pronostici, ma se ha chiamato la rete quei crediti sono stati spesi
    # davvero. Un contatore che li dimentica e' peggio di non averlo.
    if credits_spent or budget.paused:
        save_budget(budget)

    report.update(
        {
            "seconds": round(time.monotonic() - started, 1),
            "credits_spent": credits_spent,
            "credits_used_month": budget.used,
            "credits_cap": budget.cap,
            "provider_remaining": budget.provider_remaining,
            "ledger_rows_appended": appended,
            "files_changed": files_changed,
            "transitions": dict(report["transitions"]),
            "dry_run": dry_run,
        }
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competitions", nargs="*", default=list(ACTIVE_CODES))
    parser.add_argument("--window-hours", type=int, default=WINDOW_HOURS)
    parser.add_argument("--tau", type=float, default=0.08)
    parser.add_argument("--as-of", default=None, help="ISO 8601, per le prove")
    parser.add_argument("--offline", action="store_true", help="solo cache, mai rete")
    parser.add_argument("--refresh", action="store_true", help="ignora la cache")
    parser.add_argument(
        "--max-age-s",
        type=float,
        default=6 * 3600,
        help="eta' massima della cache prima di spendere un credito",
    )
    parser.add_argument("--dry-run", action="store_true", help="non scrive niente")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    as_of = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else None
    )
    report = run(
        args.competitions,
        window_hours=args.window_hours,
        as_of=as_of,
        tau=args.tau,
        offline=args.offline,
        refresh=args.refresh,
        max_age_s=args.max_age_s,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
