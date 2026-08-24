"""Sonda: la catena sportsgambler regge da un IP di datacenter?

La pagina di campionato risponde 200 dai runner di GitHub — gia' misurato. Ma
le formazioni non sono li': la pagina le carica dopo, da
`/lineups/lineups-load2.php?id=`, e un sito puo' benissimo servire l'indice a
tutti e proteggere il pezzo che conta. Questa sonda percorre la catena intera,
dalla pagina all'undici titolare, e va lanciata DA GITHUB: il successo da una
macchina di casa non dimostrerebbe niente, ed e' esattamente l'errore che
Sofascore ha gia' fatto pagare.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request

BASE = "https://www.sportsgambler.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)
LEGHE = {
    "PL": "england-premier-league",
    "SA": "italy-serie-a",
    "PD": "spain-la-liga",
    "BL1": "germany-bundesliga",
    "FL1": "france-ligue-1",
    "DED": "netherlands-eredivisie",
    "PPL": "portugal-primeira-liga",
    "ELC": "england-championship",
    "BSA": "brazil-serie-a",
}


def scarica(url: str, referer: str = "") -> str:
    testate = {"User-Agent": UA, "Accept": "*/*"}
    if referer:
        testate["Referer"] = referer
        testate["X-Requested-With"] = "XMLHttpRequest"
    req = urllib.request.Request(url, headers=testate)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    rotti = 0
    for codice, lega in LEGHE.items():
        pagina = f"{BASE}/lineups/football/{lega}/"
        try:
            html = scarica(pagina)
        except (urllib.error.URLError, OSError) as e:
            print(f"{codice:4} PAGINA KO — {e}")
            rotti += 1
            continue

        ids = re.findall(r'id="lineup(\d+)"', html)
        previste = html.count("Predicted Lineup")
        if not ids:
            print(f"{codice:4} pagina 200 ma nessuna partita in elenco")
            rotti += 1
            continue

        try:
            pezzo = scarica(f"{BASE}/lineups/lineups-load2.php?id={ids[0]}", pagina)
        except (urllib.error.URLError, OSError) as e:
            print(f"{codice:4} FRAMMENTO KO — {e}")
            rotti += 1
            continue

        modulo = re.search(r"\b\d-\d-\d(?:-\d)?\b", pezzo)
        maglie = len(re.findall(r"\b\d{1,2}\b\s*</?[a-z]", pezzo))
        stato = "ok" if modulo else "SENZA MODULO"
        if not modulo:
            rotti += 1
        mod = modulo.group(0) if modulo else "-"
        print(
            f"{codice:4} partite={len(ids):3} previste={previste:3} "
            f"frammento={len(pezzo) // 1024}KB modulo={mod} "
            f"numeri={maglie:3} {stato}"
        )

    print()
    esito = "tutti i campionati rispondono" if rotti == 0 else f"{rotti} problemi"
    print("ESITO:", esito)
    return 1 if rotti else 0


if __name__ == "__main__":
    raise SystemExit(main())
