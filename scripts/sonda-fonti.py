"""Sonda: quali fonti di formazioni rispondono, e da dove.

Lo stesso file gira in locale (IP residenziale) e su un runner di GitHub (IP
Azure). Il confronto fra le due colonne e' l'unica cosa che conta: una fonte
che funziona qui e non li' e' inutile quanto Sofascore.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)

CANDIDATI: list[tuple[str, str, tuple[str, ...]]] = [
    # nome, url, spie da cercare nel corpo
    ("espn/scoreboard", "https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard", ("events",)),
    ("espn/summary", "", ("rosters", "officials")),  # url riempita dopo
    ("365scores", "https://webws.365scores.com/web/games/current/?appTypeId=5&langId=1&competitions=11", ("games",)),
    ("thesportsdb", "https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php?id=4332", ("events",)),
    ("fotmob/matches", "https://www.fotmob.com/api/matches?date=20260825", ("leagues",)),
    ("besoccer", "https://www.besoccer.com/livescore", ("match", "alineac")),
    ("sportsgambler/PL", "https://www.sportsgambler.com/lineups/football/england-premier-league/", ("predicted", "formation")),
    ("sportsgambler/BSA", "https://www.sportsgambler.com/lineups/football/brazil-serie-a/", ("predicted", "formation")),
    ("sportsgambler", "https://www.sportsgambler.com/lineups/football/", ("lineup", "formation")),
    ("rotowire", "https://www.rotowire.com/soccer/lineups.php", ("lineup", "is-pct")),
    ("sofascore (controllo)", "https://api.sofascore.com/api/v1/sport/football/scheduled-events/2026-08-25", ("events",)),
]


def prova(url: str, spie: tuple[str, ...]) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            corpo = r.read(400_000).decode("utf-8", "replace")
            trovate = [s for s in spie if s.lower() in corpo.lower()]
            return f"{r.status} {len(corpo) // 1024}KB spie={len(trovate)}/{len(spie)}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return f"KO {type(e).__name__}"


def main() -> int:
    # L'id di una partita ESPN vera, per provare `summary` che e' quello che
    # contiene formazioni e arbitro.
    try:
        req = urllib.request.Request(CANDIDATI[0][1], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=25) as r:
            eventi = json.loads(r.read())["events"]
        ev = eventi[0]["id"]
        CANDIDATI[1] = (
            "espn/summary",
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/summary?event={ev}",
            CANDIDATI[1][2],
        )
    except Exception as e:  # noqa: BLE001
        print(f"(id ESPN non ottenuto: {type(e).__name__})", file=sys.stderr)
        CANDIDATI[1] = ("espn/summary", CANDIDATI[0][1], CANDIDATI[1][2])

    for nome, url, spie in CANDIDATI:
        print(f"{nome:24} {prova(url, spie)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
