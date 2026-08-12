"""Migrazione una tantum — 12 agosto 2026, rimozione dell'handicap asiatico.

    python scripts/migrazione_2026_08_12_handicap_asiatico.py --dry-run
    python scripts/migrazione_2026_08_12_handicap_asiatico.py

COSA E' SUCCESSO. L'handicap asiatico e' stato tolto dal catalogo dei mercati
(`model/markets.py`, sezione 6). Togliere una famiglia non cambia solo i
pronostici che ERANO asiatici: le linee asiatiche entravano nei gruppi di
mercati correlati, quindi cambia anche quale rappresentante viene scelto in
partite il cui pronostico era gia' un altro. Rigenerare i pronostici e' quindi
necessario su tutte le partite future, non solo sulle 24 asiatiche.

IL PROBLEMA CHE QUESTO SCRIPT RISOLVE. `ledger.append` ignora le righe con un
`prediction_id` gia' presente — e' cio' che rende i job idempotenti. Ottimo
sempre, tranne qui: rigenerando i fixture senza toccare il registro, il sito
mostrerebbe un pronostico e il registro ne conterrebbe un altro. Il registro e'
l'unica prova che il pronostico e' stato scritto PRIMA della partita: se diverge
dal sito, il prodotto ha perso la cosa su cui si regge.

LA REGOLA CHE NON SI VIOLA. Non si cancella mai una riga che sia stata giudicata,
e nemmeno una su cui la partita sia gia' cominciata: quella e' una previsione
pubblica che aspetta il proprio verdetto, e farla sparire perche' scomoda e'
esattamente cio' che questo prodotto rimprovera agli altri.

Quindi si rimuovono SOLO le righe che soddisfano tutte e tre le condizioni:

  1. `outcome` assente — nessun verdetto e' mai stato registrato;
  2. calcio d'inizio nel futuro — la partita non e' nemmeno cominciata;
  3. fase preliminare — il definitivo si scrive una volta sola e non si rifa'.

Al 12 agosto 2026 erano 260 righe su 293. Le 33 restanti — fra cui le 14 con
esito — non vengono toccate, e i numeri di `accuracy.json`, che si calcolano
sulle sole righe giudicate, restano identici al bit.

Dopo questo script va rieseguito `python -m pronostici.jobs.score --days 30`,
che riscrive i preliminari col catalogo nuovo.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
LEDGER = RADICE / "data" / "ledger"


def rimovibile(riga: dict, adesso: datetime) -> bool:
    if riga.get("outcome") is not None:
        return False
    if riga.get("phase") != "preliminary":
        return False
    try:
        inizio = datetime.fromisoformat(riga["utc_date"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return False
    return inizio > adesso


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    adesso = datetime.now(UTC)
    totale_prima = totale_dopo = 0
    per_file: list[tuple[Path, list[dict], int]] = []

    for percorso in sorted(LEDGER.glob("*.jsonl")):
        righe = [
            json.loads(r) for r in percorso.read_text(encoding="utf-8").splitlines() if r
        ]
        tenute = [r for r in righe if not rimovibile(r, adesso)]
        totale_prima += len(righe)
        totale_dopo += len(tenute)
        per_file.append((percorso, tenute, len(righe) - len(tenute)))

    rimosse = totale_prima - totale_dopo
    for percorso, tenute, quante in per_file:
        print(f"{percorso.name}: {len(tenute)} righe tenute, {quante} rimosse")
        if args.dry_run or quante == 0:
            continue
        testo = "".join(
            json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in tenute
        )
        percorso.write_text(testo, encoding="utf-8", newline="\n")

    giudicate = sum(
        1
        for _, tenute, _ in per_file
        for r in tenute
        if r.get("outcome") is not None
    )
    print(f"\ntotale: {totale_prima} -> {totale_dopo} ({rimosse} rimosse)")
    print(f"righe con esito conservate: {giudicate}")
    if args.dry_run:
        print("(dry run: niente scritto)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
