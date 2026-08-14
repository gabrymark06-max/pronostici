"""Job 4-quater — `giocatori`: stime sui singoli, dalle formazioni probabili.

    python -m pronostici.jobs.giocatori --window-days 3
    python -m pronostici.jobs.giocatori --dry-run

DIPENDE DA `jobs.sofascore`, che deve girare prima: senza formazioni non c'e'
nessuno di cui stimare qualcosa.

QUESTE STIME NON SONO MISURATE. Il perche' sta in `model/giocatori.py` e non si
ripete qui. Vale pero' la conseguenza operativa: quanto esce da questo job
finisce sotto `sofascore.giocatori`, **non** in `prediction`, **non** nel
registro, e la pagina lo tiene in una sezione dichiarata. Un giorno, con
abbastanza partite raccolte, potranno entrare anche loro nel registro; quel
giorno questa riga si cancella e si data.

LA CACHE. Le statistiche di stagione cambiano al massimo una volta a settimana.
Rileggerle a ogni giro costerebbe circa milleduecento chiamate: si tengono in
`data/sofascore/giocatori.json` con la data di lettura, e si rinfrescano solo
quando invecchiano.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .. import fixtures as fx
from ..model.giocatori import moltiplicatore_arbitro, stime_giocatore
from ..sources import sofascore as sf

log = logging.getLogger("pronostici.giocatori")

CACHE_GIOCATORI = Path("data/sofascore/giocatori.json")
ETA_CACHE_GIORNI = 7
PAUSA_S = 0.25
FINESTRA_DEFAULT = 3


def _carica() -> dict:
    if not CACHE_GIOCATORI.exists():
        return {}
    try:
        return json.loads(CACHE_GIOCATORI.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _salva(cache: dict) -> None:
    CACHE_GIOCATORI.parent.mkdir(parents=True, exist_ok=True)
    CACHE_GIOCATORI.write_text(
        json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )


def _fresco(voce: dict, adesso: datetime) -> bool:
    letto = voce.get("letto")
    if not letto:
        return False
    try:
        quando = datetime.fromisoformat(letto.replace("Z", "+00:00"))
    except ValueError:
        return False
    return (adesso - quando) < timedelta(days=ETA_CACHE_GIORNI)


def _tassi(pid: int, cache: dict, adesso: datetime, report: dict) -> dict:
    chiave = str(pid)
    voce = cache.get(chiave)
    if voce and _fresco(voce, adesso):
        report["da_cache"] += 1
        return voce.get("tassi") or {}
    try:
        tassi = sf.statistiche_giocatore(pid)
    except sf.SofascoreNonDisponibile as exc:
        report["errori_lettura"] += 1
        log.warning("statistiche non lette per %s: %s", pid, exc)
        return (voce or {}).get("tassi") or {}
    time.sleep(PAUSA_S)
    report["letti"] += 1
    cache[chiave] = {"letto": adesso.strftime("%Y-%m-%dT%H:%M:%SZ"), "tassi": tassi}
    return tassi


def run(
    *,
    finestra: int = FINESTRA_DEFAULT,
    dry_run: bool = False,
    oggi: str | None = None,
    max_partite: int | None = None,
) -> dict:
    started = time.monotonic()
    adesso = datetime.now(UTC)
    oggi = oggi or adesso.strftime("%Y-%m-%d")

    report: dict = {
        "generated_at": adesso.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "partite_con_formazioni": 0,
        "partite_stimate": 0,
        "giocatori_stimati": 0,
        "giocatori_saltati_campione": 0,
        "letti": 0,
        "da_cache": 0,
        "errori_lettura": 0,
        "days_written": [],
        "dry_run": dry_run,
    }

    if not sf.disponibile():
        report["errore"] = f"binario Sofascore assente ({sf.percorso_cli()})"
        report["seconds"] = round(time.monotonic() - started, 1)
        return report

    cache = _carica()
    base = datetime.strptime(oggi, "%Y-%m-%d").replace(tzinfo=UTC)
    giorni = [
        (base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(finestra + 1)
    ]
    per_giorno: dict[str, list[dict]] = defaultdict(list)
    fatte = 0

    for giorno in giorni:
        esistente = fx.load_day(giorno)
        if not esistente:
            continue
        for entry in esistente.get("fixtures", []):
            blocco = entry.get("sofascore") or {}
            form = blocco.get("formazioni") or {}
            if not (form.get("casa") or {}).get("titolari"):
                continue
            try:
                calcio = datetime.fromisoformat(entry["utc_date"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if calcio <= adesso:
                continue

            report["partite_con_formazioni"] += 1
            if max_partite is not None and fatte >= max_partite:
                continue
            fatte += 1

            arb = blocco.get("arbitro") or {}
            molt = moltiplicatore_arbitro(
                arb.get("gialli_per_partita"), arb.get("partite")
            )

            squadre: dict[str, list[dict]] = {}
            for lato in ("casa", "ospiti"):
                elenco: list[dict] = []
                # SOLO I TITOLARI. Per un subentrato i minuti attesi sarebbero
                # inventati, e i minuti attesi sono il termine che domina.
                for g in (form.get(lato) or {}).get("titolari", []):
                    pid = g.get("id")
                    if not pid:
                        continue
                    tassi = _tassi(int(pid), cache, adesso, report)
                    if not tassi:
                        continue
                    stime = stime_giocatore(tassi, molt_cartellini=molt)
                    if not stime:
                        report["giocatori_saltati_campione"] += 1
                        continue
                    report["giocatori_stimati"] += 1
                    elenco.append(
                        {
                            "id": pid,
                            "nome": g.get("nome"),
                            "ruolo": g.get("ruolo"),
                            "presenze": tassi.get("presenze"),
                            "torneo": tassi.get("torneo"),
                            "stime": [
                                {
                                    "mercato": s.mercato,
                                    "etichetta": s.etichetta,
                                    "p": s.p,
                                    "base": s.base,
                                }
                                for s in stime
                            ],
                        }
                    )
                squadre[lato] = elenco

            if not (squadre.get("casa") or squadre.get("ospiti")):
                continue

            report["partite_stimate"] += 1
            nuovo = {
                **blocco,
                "giocatori": {
                    "misurato": False,
                    "nota": (
                        "Stime non misurate: non esiste una quota di mercato "
                        "su questi esiti "
                        "ne' uno storico per verificarle. Non entrano nel registro."
                    ),
                    "moltiplicatore_arbitro": round(molt, 3),
                    "minuti_attesi_titolare": 76,
                    "casa": squadre.get("casa", []),
                    "ospiti": squadre.get("ospiti", []),
                },
            }
            per_giorno[giorno].append({**entry, "sofascore": nuovo})

    _salva(cache)
    if not dry_run:
        for giorno, aggiornate in per_giorno.items():
            if aggiornate and fx.upsert_day(giorno, aggiornate, generated_at=adesso):
                report["days_written"].append(giorno)

    report["seconds"] = round(time.monotonic() - started, 1)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stime sui giocatori dalle formazioni probabili"
    )
    parser.add_argument("--window-days", type=int, default=FINESTRA_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--today", default=None)
    parser.add_argument(
        "--max-partite",
        type=int,
        default=None,
        help="limite di partite, per provare senza attendere",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(
        finestra=args.window_days,
        dry_run=args.dry_run,
        oggi=args.today,
        max_partite=args.max_partite,
    )
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if not report.get("errore") else 1


if __name__ == "__main__":
    raise SystemExit(main())
