"""Sonda: betexplorer regge da un IP di datacenter, e fino ai mercati?

Stessa domanda gia' fatta per sportsgambler, stessa ragione: Sofascore ha
insegnato che una fonte provata da una macchina di casa non e' provata. Qui la
catena e' di tre passi e ognuno puo' cadere da solo — la pagina delle partite,
l'endpoint dei mercati, e il fatto che quel mercato abbia davvero delle quote
dentro.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

BASE = "https://www.betexplorer.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)
LEGHE = {
    "PL": "england/premier-league",
    "SA": "italy/serie-a",
    "PD": "spain/laliga",
    "BL1": "germany/bundesliga",
    "FL1": "france/ligue-1",
    "DED": "netherlands/eredivisie",
    "PPL": "portugal/liga-portugal",
    "ELC": "england/championship",
    "BSA": "brazil/serie-a",
}
MERCATI = ("1x2", "ou", "bts", "dc", "ha")


def scarica(url: str, referer: str = "") -> str:
    testate = {"User-Agent": UA, "Accept": "*/*"}
    if referer:
        testate["Referer"] = referer
        testate["X-Requested-With"] = "XMLHttpRequest"
    with urllib.request.urlopen(
        urllib.request.Request(url, headers=testate), timeout=30
    ) as r:
        return r.read().decode("utf-8", "replace")


def main() -> int:
    rotti = 0
    for codice, percorso in LEGHE.items():
        pagina = f"{BASE}/football/{percorso}/fixtures/"
        try:
            html = scarica(pagina)
        except (urllib.error.URLError, OSError) as e:
            print(f"{codice:4} PAGINA KO — {e}")
            rotti += 1
            continue

        eventi = re.findall(r'href="/[a-z]{2}/football/[^"]+/([A-Za-z0-9]{8})/"', html)
        quote_in_elenco = len(re.findall(r'data-odd="([\d.]+)"', html))
        if not eventi:
            print(f"{codice:4} pagina 200 ma nessuna partita")
            rotti += 1
            continue

        # LA PRIMA E' LA PIU' VICINA nel tempo, ed e' quella che conta: su una
        # partita fra tre mesi i bookmaker non hanno ancora aperto i mercati e
        # una risposta vuota non direbbe niente sul fatto che l'endpoint viva.
        trovati = []
        for mercato in MERCATI:
            try:
                grezzo = scarica(
                    f"{BASE}/match-odds/{eventi[0]}/1/{mercato}/odds/?lang=2", pagina
                )
                dentro = json.loads(grezzo).get("odds", "")
            except (urllib.error.URLError, OSError, ValueError) as e:
                print(f"{codice:4} MERCATO {mercato} KO — {e}")
                rotti += 1
                continue
            quote = len(re.findall(r'data-odd="([\d.]+)"', dentro))
            trovati.append(f"{mercato}={quote}")

        n = len(set(eventi))
        riga = " ".join(trovati)
        print(f"{codice:4} partite={n:3} elenco={quote_in_elenco:3} | {riga}")

    print()
    print("ESITO:", "tutte le leghe rispondono" if rotti == 0 else f"{rotti} problemi")
    return 1 if rotti else 0


if __name__ == "__main__":
    raise SystemExit(main())
