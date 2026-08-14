"""La pipeline giornaliera, a mano.

PERCHE' ESISTE. Normalmente questi job girano su GitHub Actions alle 03:00.
Finche' l'account e' sospeso non gira niente, e ogni giorno fermo e' un giorno
di pronostici che NON entra nel registro e non si recupera piu': i pronostici
si scrivono prima della partita, o non si scrivono.

Fa esattamente cio' che fa `daily.yml`, nello stesso ordine e con le stesse
dipendenze fra un passo e l'altro.

PERCHE' IN PYTHON E NON IN POWERSHELL. La prima versione era un `.ps1`, e
Windows si rifiuta di eseguirlo: la politica predefinita blocca gli script non
firmati. Si aggira con un comando piu' lungo o cambiando un'impostazione di
sistema — due modi di chiedere all'utente di convivere con un attrito. Un file
Python non ha quel problema, e in questo progetto Python c'e' gia'.

COME SI USA. Apri il terminale in VS Code e scrivi:

    python scripts/giornata.py

Ci mette qualche minuto. Alla fine dice cosa ha scritto e cosa fare dopo.

QUANDO GITHUB TORNA questo file non serve piu': i workflow ripartono da soli e
rifanno la stessa cosa ogni notte.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent

# I quattro passi di `daily.yml`, nello stesso ordine. Ognuno dipende dal
# precedente: `settle` ha bisogno delle partite che `ingest` ha portato,
# `retrain` dei risultati che `settle` ha chiuso, `score` dei parametri che
# `retrain` ha ricalcolato. Se uno salta, i successivi lavorerebbero su dati
# vecchi senza dirlo.
ESSENZIALI = [
    ("ingest", "calendario e risultati", []),
    ("settle", "esiti delle partite finite", []),
    ("retrain", "riaddestramento dei modelli", []),
    ("score", "pronostici di oggi", []),
]

# Il contorno. NON ferma la giornata se salta: il pronostico e' gia' scritto e
# si regge sul modello. Quote, formazioni e arbitro lo arricchiscono, non lo
# determinano.
CONTORNO = [
    ("quote", "quote di mercato", ["--window-days", "14"]),
    ("sofascore", "formazioni, arbitro e quote estese", ["--window-days", "4"]),
    ("giocatori", "stime sui singoli giocatori", ["--window-days", "4"]),
]


def carica_env() -> None:
    """Le chiavi da `.env`.

    Si legge a mano invece di aggiungere `python-dotenv`: sono tre righe, e una
    dipendenza in piu' per tre righe la pagherebbe anche chi questo script non
    lo usa. `utf-8-sig` perche' Windows ci mette il BOM davanti e senza quello
    la prima chiave si chiamerebbe `\\ufeffFOOTBALL_DATA_API_KEY`.
    """
    import os

    percorso = RADICE / ".env"
    if not percorso.exists():
        print("ATTENZIONE: manca .env — i job che hanno bisogno di chiavi falliranno.")
        return
    for riga in percorso.read_text(encoding="utf-8-sig").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        chiave, _, valore = riga.partition("=")
        os.environ.setdefault(chiave.strip(), valore.strip())


def esegui(nome: str, cosa: str, argomenti: list[str]) -> bool:
    print(f"\n--- {nome}: {cosa}", flush=True)
    esito = subprocess.run(
        [sys.executable, "-m", f"pronostici.jobs.{nome}", *argomenti], cwd=RADICE
    )
    return esito.returncode == 0


def main() -> int:
    carica_env()
    partito = time.monotonic()

    for nome, cosa, argomenti in ESSENZIALI:
        if not esegui(nome, cosa, argomenti):
            print(f"\nFERMO su «{nome}». I passi dopo dipendono da questo.")
            print(
                "Niente e' stato scritto a meta': "
                "ogni job scrive solo se arriva in fondo."
            )
            return 1

    saltati: list[str] = []
    for nome, cosa, argomenti in CONTORNO:
        if not esegui(nome, cosa, argomenti):
            saltati.append(nome)

    minuti = (time.monotonic() - partito) / 60
    print(f"\nFatto in {minuti:.1f} minuti. I dati sono in data/.")
    if saltati:
        print(
            f"Non sono riusciti: {', '.join(saltati)}. "
            "Il pronostico c'e' lo stesso — quelli sono contorno."
        )
    print('\nAdesso salva:  git add data && git commit -m "dati: giornata"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
