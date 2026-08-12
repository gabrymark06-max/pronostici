"""Job 4-bis — `quote`: attacca i PREZZI di mercato alle partite future.

    python -m pronostici.jobs.quote --window-days 6

PERCHE' ESISTE UN JOB A PARTE, invece di allargare la finestra di `finalize`.

`finalize` fa due cose che sembrano una sola e non lo sono:

  1. prende le quote e le fonde col modello, poi RIDECIDE il pronostico e
     scrive la riga definitiva nel registro. E' una DECISIONE, ed e' irripetibile
     per costruzione: una sola finalizzazione per partita, per sempre. Va fatta
     il piu' tardi possibile, perche' le quote a T-36h sono le piu' informative
     che avremo mai;
  2. lascia nel file, come effetto collaterale, i dati delle quote.

Il sito mostra la quota di mercato accanto al pronostico. Con la sola `finalize`
quel numero compariva su 10 partite su 283 — e su nessuna di quelle 10, perche'
la fonte gratuita quota 1X2 e Over/Under mentre il pronostico scelto era quasi
sempre un altro mercato. Il risultato pratico: una colonna sempre vuota.

Allargare la finestra di `finalize` avrebbe risolto la copertura peggiorando la
decisione — si finalizza cinque giorni prima, con quote peggiori, e si perde
proprio la revisione che e' il pezzo piu' raro del prodotto. Le due cose vanno
separate: qui si attacca un PREZZO, che e' informazione e si puo' rifare ogni
giorno; li' si prende una DECISIONE, che si prende una volta sola.

COSA QUESTO JOB NON FA, MAI:

* non tocca `prediction`, `silence`, `phase`, `source`, `model_weight`, le
  `reasons`, il registro. Scrive un solo campo, `odds`, e nient'altro;
* non tocca i giorni passati. Il fischio d'inizio congela la riga, e una quota
  scritta dopo la partita sarebbe una quota che nessuno avrebbe potuto giocare;
* non spende crediti per un campionato che non gioca entro la finestra.

Il costo e' lo stesso della `finalize` — una chiamata per campionato, in cache
condivisa — e viene contato sullo stesso budget mensile.
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
from ..archive import load_all
from ..competitions import ACTIVE_CODES, get
from ..matching import pair_events
from ..pipeline import market_references
from ..sources.odds_api import (
    MARKETS,
    SECONDARY_LEAGUES,
    OddsClient,
    OddsUnavailable,
    load_budget,
    reconcile_budget,
    save_budget,
)
from ..sources.odds_parse import parse_league

log = logging.getLogger("quote")

# Sei giorni: copre il fine settimana successivo da qualunque giorno si guardi,
# che e' l'orizzonte in cui il calendario del sito e' popolato. Oltre, i
# bookmaker spesso non hanno ancora aperto il mercato e la chiamata torna vuota.
WINDOW_DAYS = 6


def leagues_with_matches(
    competitions: list[str], as_of: datetime, window: timedelta
) -> dict[str, list]:
    """I campionati che giocano davvero entro la finestra, con le loro partite.

    Prima si guardano i fixture, poi si decide chi chiamare: mai una chiamata
    per un campionato fermo. A differenza di `finalize` NON si esclude chi e'
    gia' stato finalizzato — un prezzo si aggiorna, una decisione no.
    """
    out: dict[str, list] = {}
    horizon = as_of + window
    for code in competitions:
        if get(code).odds_key is None:
            continue
        due = [
            m for m in load_all(code) if not m.is_finished and as_of < m.date <= horizon
        ]
        if due:
            out[code] = due
    return out


def run(
    competitions: list[str],
    *,
    window_days: int = WINDOW_DAYS,
    as_of: datetime | None = None,
    offline: bool = False,
    refresh: bool = False,
    max_age_s: float = 6 * 3600,
    dry_run: bool = False,
    reconcile: bool = False,
) -> dict:
    as_of = as_of or datetime.now(UTC)
    started = time.monotonic()
    budget = load_budget()
    client = OddsClient(offline=offline)

    riconciliazione = None
    if reconcile and not offline:
        riconciliazione = reconcile_budget(budget)
        save_budget(budget)

    step = budget.degradation_step()
    report: dict = {
        "as_of": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reconciled": riconciliazione,
        "window_days": window_days,
        "degradation_step": step,
        "credits_before": budget.used,
        "leagues": [],
        "quoted": 0,
        "days_written": [],
    }

    if step == "model_only":
        report["skipped_reason"] = "quota esaurita: nessun prezzo da mostrare"
        report["seconds"] = round(time.monotonic() - started, 1)
        return report

    due = leagues_with_matches(competitions, as_of, timedelta(days=window_days))
    if step in ("secondary_leagues", "totals_market"):
        dropped = [c for c in due if c in SECONDARY_LEAGUES]
        for code in dropped:
            due.pop(code)
        report["dropped_for_budget"] = dropped
    markets = ("h2h",) if step == "totals_market" else MARKETS
    report["markets"] = list(markets)

    credits_spent = 0
    # giorno -> match_id -> blocco `odds` da scrivere
    patch: dict[str, dict[int, dict]] = defaultdict(dict)

    for code, matches in sorted(due.items()):
        competition = get(code)
        try:
            events, meta = client.fetch_league_cached(
                competition.odds_key,
                budget,
                max_age_s=max_age_s,
                refresh=refresh,
                markets=markets,
            )
        except OddsUnavailable as exc:
            # Degradazione, non guasto: le partite restano senza prezzo.
            log.warning("%s: quote non disponibili (%s)", code, exc)
            report["leagues"].append(
                {"competition": code, "status": "unavailable", "detail": str(exc)}
            )
            continue

        credits_spent += int(meta["credits"])
        snapshots = [s for s in parse_league(events) if s.prices]
        pairs, unmatched = pair_events(matches, snapshots)
        report["leagues"].append(
            {
                "competition": code,
                "status": "ok",
                "odds_source": meta["source"],
                "credits": meta["credits"],
                "events": len(events),
                "with_prices": len(snapshots),
                "matches_due": len(matches),
                "paired": len(pairs),
                "unmatched": len(unmatched),
            }
        )

        by_id = {m.match_id: m for m in matches}
        for match_id, event_index in pairs.items():
            snapshot = snapshots[event_index]
            giorno = by_id[match_id].utc_date[:10]
            # LE PROBABILITA' DI MERCATO, ESTESE.
            #
            # La fonte gratuita quota 1X2 e Over/Under, ma da quei cinque
            # numeri il mercato ne DETERMINA altri sei in modo esatto: le tre
            # doppie chance sono somme di esiti 1X2, l'handicap europeo +-1 e
            # il multigol 0-2 hanno la stessa maschera di un mercato gia'
            # coperto. Undici chiavi invece di cinque, senza approssimare
            # niente - e' la stessa funzione che usa il modello per scegliere.
            #
            # Serve perche' il pronostico consigliato quasi mai E' un 1X2: su
            # 21 partite quotate, zero. Sono doppie chance, gol di squadra,
            # handicap. Con la sola tabella dei prezzi la colonna «mercato»
            # restava vuota anche dove il mercato aveva parlato chiarissimo.
            patch[giorno][match_id] = {
                "n_bookmakers": snapshot.n_bookmakers,
                "markets": sorted(snapshot.probabilities),
                "prices": {k: round(v, 2) for k, v in snapshot.prices.items()},
                "market_p": {
                    k: round(v, 5)
                    for k, v in market_references(snapshot.probabilities).items()
                },
                "price_scope": snapshot.price_scope,
                "price_books": snapshot.price_books,
                "fetched": meta["source"],
            }

    report["credits_spent"] = credits_spent
    report["credits_after"] = budget.used

    oggi = as_of.strftime("%Y-%m-%d")
    for giorno, per_match in sorted(patch.items()):
        # Cintura di sicurezza: la finestra parte da `as_of`, quindi un giorno
        # passato non dovrebbe mai arrivare fin qui. Se ci arriva, il problema
        # e' altrove e non si scrive comunque — una quota su una partita
        # giocata e' una quota che nessuno avrebbe potuto giocare.
        if giorno < oggi:
            log.warning("%s e' passato: non lo tocco", giorno)
            continue

        esistente = fx.load_day(giorno)
        if not esistente:
            continue

        aggiornate = []
        for entry in esistente.get("fixtures", []):
            blocco = per_match.get(int(entry["match_id"]))
            if blocco is None:
                continue
            # Su una partita gia' finalizzata `odds` porta anche `devig`, che e'
            # il margine misurato al momento della decisione: si conserva.
            precedente = entry.get("odds") or {}
            unito = {**precedente, **blocco}
            if unito == precedente:
                continue
            aggiornate.append({**entry, "odds": unito})

        if not aggiornate:
            continue
        report["quoted"] += len(aggiornate)
        if dry_run:
            continue
        if fx.upsert_day(giorno, aggiornate, generated_at=as_of):
            report["days_written"].append(giorno)

    # IL CONTATORE SI SALVA SEMPRE, ANCHE IN DRY RUN.
    # `--dry-run` significa «non scrivere i fixture», non «non spendere»: le
    # chiamate di rete sono gia' partite e i crediti sono gia' andati. Saltare
    # il salvataggio faceva divergere il nostro contatore da quello del
    # fornitore, e la divergenza metteva in pausa il job — cioe' un dry run
    # arrivava a spegnere le quote in produzione.
    save_budget(budget)
    report["seconds"] = round(time.monotonic() - started, 1)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Attacca le quote di mercato")
    parser.add_argument("--competitions", nargs="*", default=None)
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--max-age-s", type=float, default=6 * 3600)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="riallinea il contatore a quello del fornitore e toglie la pausa",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    report = run(
        args.competitions or list(ACTIVE_CODES),
        window_days=args.window_days,
        offline=args.offline,
        refresh=args.refresh,
        max_age_s=args.max_age_s,
        dry_run=args.dry_run,
        reconcile=args.reconcile,
    )
    json.dump(report, sys.stdout, ensure_ascii=False, indent=1, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
