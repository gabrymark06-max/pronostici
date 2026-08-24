"""Quanti bookmaker mostra betexplorer, e da cosa dipende.

Da un IP italiano la tabella dei gol totali ha undici operatori con licenza
ADM; da un runner di GitHub ne ha tre, e con tre la mediana di ogni linea
cade sotto la soglia — la partita esce con due mercati invece di otto.

Qui si prova se la lingua, il paese o un cookie cambiano la lista, o se
dipende solo dall'indirizzo di chi chiede.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request

BASE = "https://www.betexplorer.com"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)


def prova(evento: str, etichetta: str, url: str, cookie: str = "") -> None:
    testate = {
        "User-Agent": UA,
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE}/football/italy/serie-a/",
    }
    if cookie:
        testate["Cookie"] = cookie
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=testate), timeout=30
        ) as r:
            dentro = json.loads(r.read().decode("utf-8", "replace")).get("odds", "")
    except Exception as e:  # noqa: BLE001
        print(f"{etichetta:34} KO {type(e).__name__}")
        return
    libri = sorted(set(re.findall(r'data-bookie="([^"]*)"', dentro)))
    linee = sorted(set(re.findall(r'data-hcp="E-\d-\d-\d-([\d.]+)-', dentro)))
    print(f"{etichetta:34} {len(libri):2} bookmaker, {len(linee):2} linee")
    print(f"{'':34} {libri[:8]}")


def main() -> int:
    evento = sys.argv[1]
    base = f"{BASE}/match-odds/{evento}/1"
    for lang in ("1", "2", "3", "8"):
        prova(evento, f"ou lang={lang}", f"{base}/ou/odds/?lang={lang}")
    prova(evento, "ou cookie be_lang=it", f"{base}/ou/odds/?lang=2", "be_lang=it")
    prova(
        evento,
        "ou cookie geo=it",
        f"{base}/ou/odds/?lang=2",
        "be_lang=it; user_geo=it; geo=it",
    )
    prova(evento, "bestOdds lang=2", f"{base}/ou/bestOdds/?lang=2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
