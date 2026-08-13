"""Job 4-ter — `sofascore`: attacca formazioni, arbitro e quote estese.

    python -m pronostici.jobs.sofascore --window-days 4
    python -m pronostici.jobs.sofascore --dry-run

COSA SCRIVE. Un solo campo, `sofascore`, su ogni partita futura che riesce ad
agganciare. Dentro ci sono tre cose che il resto della pipeline non ha:

  * l'ARBITRO designato, con il suo storico disciplinare;
  * le FORMAZIONI, con scritto se sono probabili o gia' ufficiali;
  * le QUOTE su mercati che la fonte attuale non copre — cartellini nella
    partita, calci d'angolo, prima squadra a segnare, primo tempo.

COSA NON TOCCA, MAI. `prediction`, `silence`, `phase`, `source`,
`model_weight`, `reasons`, il registro. Non partecipa alla decisione: quella
resta dove sta, sul modello e sulle quote di mercato gia' cablate. Qui si
aggiunge contesto, e il contesto non vota.

PERCHE' LE FORMAZIONI VANNO RIPRESE PIU' VOLTE. Compaiono come PROBABILI e
diventano UFFICIALI vicino al calcio d'inizio. Il campo `confermate` dice quale
delle due si sta guardando, e questo job va fatto girare piu' di una volta al
giorno per le partite imminenti se si vuole la versione definitiva.

QUANDO L'AGGANCIO FALLISCE. La partita resta senza il campo `sofascore` e il
motivo finisce nel report. Non si inventa niente per riempire il buco: una
scheda senza formazioni e' onesta, una scheda con le formazioni di un'altra
partita e' un disastro invisibile.
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
from ..sources import sofascore as sf

log = logging.getLogger("pronostici.sofascore")

# Pausa fra una partita e l'altra. Sofascore non pubblica un limite di
# frequenza; questa e' cortesia, non obbligo, e tiene il job lontano da
# qualunque soglia non dichiarata.
PAUSA_S = 0.4

# Oltre questa distanza le formazioni non esistono ancora e l'arbitro spesso
# nemmeno: si spenderebbero chiamate per riscrivere blocchi vuoti.
FINESTRA_DEFAULT = 4


def _giorni(finestra: int, oggi: str) -> list[str]:
    base = datetime.strptime(oggi, "%Y-%m-%d").replace(tzinfo=UTC)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(finestra + 1)]


def _senza_ora(blocco: dict) -> dict:
    """Il blocco senza `letto`, per confrontare la sostanza e non il momento."""
    return {k: v for k, v in blocco.items() if k != "letto"}


def _blocco(
    scheda: dict, evento_id: int, torneo: str, as_of: str, *, ore_prima: float | None = None
) -> dict:
    """Riduce la scheda del CLI al blocco che finisce nel file.

    Si tiene poco e con criterio: la scheda grezza porta anche cose che la
    pagina non usa, e un file di fixture non e' un archivio della fonte.
    """
    blocco: dict = {
        "evento_id": evento_id,
        "torneo": torneo,
        "letto": as_of,
    }

    arbitro = scheda.get("arbitro")
    if isinstance(arbitro, dict) and arbitro.get("nome"):
        blocco["arbitro"] = {
            "nome": arbitro["nome"],
            "paese": arbitro.get("paese"),
            "partite": arbitro.get("partite_arbitrate"),
            "gialli": arbitro.get("cartellini_gialli"),
            "rossi": arbitro.get("cartellini_rossi"),
            "gialli_per_partita": arbitro.get("gialli_per_partita"),
        }
        if arbitro.get("stadio"):
            blocco["stadio"] = arbitro["stadio"]

    form = scheda.get("formazioni")
    if isinstance(form, dict) and (form.get("casa") or {}).get("titolari"):
        # QUANTO PRIMA sono state lette. Sofascore pubblica formazioni PREVISTE
        # con giorni d'anticipo, e le marca `confermate: false` esattamente come
        # quelle probabili di un'ora prima del fischio. Lo stesso campo copre
        # due gradi di affidabilita' molto diversi: una previsione a tre giorni
        # e' un'ipotesi sulla rosa, una a un'ora e' quasi la formazione vera.
        #
        # Il numero si registra QUI, che e' il momento in cui e' vero. La pagina
        # lo usa per dire «probabili, lette tre giorni prima» invece di
        # appiattire tutto su «probabili».
        blocco["formazioni"] = {
            "confermate": bool(form.get("confermate")),
            "ore_prima": round(ore_prima, 1) if ore_prima is not None else None,
            "casa": {
                "modulo": (form.get("casa") or {}).get("modulo"),
                "titolari": (form.get("casa") or {}).get("titolari", []),
                "panchina": (form.get("casa") or {}).get("panchina", []),
            },
            "ospiti": {
                "modulo": (form.get("ospiti") or {}).get("modulo"),
                "titolari": (form.get("ospiti") or {}).get("titolari", []),
                "panchina": (form.get("ospiti") or {}).get("panchina", []),
            },
        }

    quote = scheda.get("quote")
    if isinstance(quote, dict) and quote.get("mercati"):
        blocco["quote"] = {
            "n_mercati": quote.get("n_mercati"),
            "mercati": quote.get("mercati", []),
        }

    mancanti = scheda.get("parti_mancanti")
    if isinstance(mancanti, dict) and mancanti:
        blocco["parti_mancanti"] = mancanti
    return blocco


def run(
    *,
    finestra: int = FINESTRA_DEFAULT,
    dry_run: bool = False,
    oggi: str | None = None,
) -> dict:
    started = time.monotonic()
    adesso = datetime.now(UTC)
    oggi = oggi or adesso.strftime("%Y-%m-%d")
    as_of = adesso.strftime("%Y-%m-%dT%H:%M:%SZ")

    report: dict = {
        "generated_at": as_of,
        "finestra_giorni": finestra,
        "esaminate": 0,
        "agganciate": 0,
        "con_formazioni": 0,
        "con_arbitro": 0,
        "con_quote": 0,
        "non_agganciate": [],
        "days_written": [],
        "dry_run": dry_run,
    }

    if not sf.disponibile():
        report["errore"] = (
            f"binario Sofascore assente ({sf.percorso_cli()}): il job si spegne senza scrivere"
        )
        log.warning(report["errore"])
        report["seconds"] = round(time.monotonic() - started, 1)
        return report

    cache = sf._carica_cache()
    per_giorno: dict[str, list[dict]] = defaultdict(list)

    for giorno in _giorni(finestra, oggi):
        esistente = fx.load_day(giorno)
        if not esistente:
            continue
        for entry in esistente.get("fixtures", []):
            # Il fischio d'inizio congela: dopo, formazioni e quote non sono
            # piu' informazione pre-partita e non vanno riscritte.
            try:
                calcio = datetime.fromisoformat(entry["utc_date"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if calcio <= adesso:
                continue

            report["esaminate"] += 1
            aggancio = sf.aggancia(
                entry["home"]["name"], entry["away"]["name"], entry["utc_date"], cache=cache
            )
            time.sleep(PAUSA_S)

            if aggancio.evento_id is None:
                report["non_agganciate"].append(
                    {
                        "match_id": entry["match_id"],
                        "partita": f"{entry['home']['name']} - {entry['away']['name']}",
                        "motivo": aggancio.motivo,
                    }
                )
                continue

            try:
                scheda = sf.scheda(aggancio.evento_id)
            except sf.SofascoreNonDisponibile as exc:
                report["non_agganciate"].append(
                    {
                        "match_id": entry["match_id"],
                        "partita": f"{entry['home']['name']} - {entry['away']['name']}",
                        "motivo": f"scheda non letta: {exc}",
                    }
                )
                continue
            time.sleep(PAUSA_S)

            blocco = _blocco(
                scheda,
                aggancio.evento_id,
                aggancio.torneo,
                as_of,
                ore_prima=(calcio - adesso).total_seconds() / 3600,
            )
            report["agganciate"] += 1
            if "formazioni" in blocco:
                report["con_formazioni"] += 1
            if "arbitro" in blocco:
                report["con_arbitro"] += 1
            if "quote" in blocco:
                report["con_quote"] += 1

            # Si riscrive solo se e' cambiato qualcosa di SOSTANZA. `letto`
            # cambia a ogni giro per costruzione e non e' una novita': se
            # entrasse nel confronto, ogni esecuzione riscriverebbe tutti i
            # file e il registro delle modifiche diventerebbe illeggibile.
            precedente = entry.get("sofascore") or {}
            if _senza_ora(blocco) == _senza_ora(precedente):
                continue
            per_giorno[giorno].append({**entry, "sofascore": blocco})

    sf._salva_cache(cache)

    if not dry_run:
        for giorno, aggiornate in per_giorno.items():
            # `generated_at` vuole un datetime: serve a `upsert_day` per
            # decidere quali partite sono gia' iniziate, non come etichetta.
            if aggiornate and fx.upsert_day(giorno, aggiornate, generated_at=adesso):
                report["days_written"].append(giorno)

    report["seconds"] = round(time.monotonic() - started, 1)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Formazioni, arbitro e quote estese da Sofascore")
    parser.add_argument("--window-days", type=int, default=FINESTRA_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--today", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(finestra=args.window_days, dry_run=args.dry_run, oggi=args.today)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if not report.get("errore") else 1


if __name__ == "__main__":
    raise SystemExit(main())
