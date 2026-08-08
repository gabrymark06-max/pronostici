"""Dalla risposta grezza di the-odds-api alle probabilita' eque.

Una risposta contiene, per ogni partita, N bookmaker x M mercati x quote.
Qui si fa una cosa sola, e si fa bene:

1. **consenso** fra bookmaker: mediana per esito. La mediana, non la media,
   perche' un solo bookmaker con una quota stantia o sbagliata non deve
   spostare il riferimento;
2. **de-vig col metodo power**, mai ingenuo (ricerca 11): il de-vig ingenuo
   gonfia la probabilita' equa dei longshot e fabbrica vantaggio finto
   esattamente dove il vantaggio e' piu' difficile da avere.

Le chiavi in uscita sono le **nostre** (`1x2_home`, `over_2.5`, ...), non le
loro: il resto del sistema non deve sapere che esiste the-odds-api.

Non si mostra mai un prezzo di un bookmaker nominato (rischio 5 del brief):
di qui esce solo la probabilita' implicita sgonfiata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Any

from ..model.devig import DevigError, devig_power
from ..model.markets import OU_LINES

# Solo le linee per cui esiste una maschera nel catalogo: una linea 3.25
# asiatica non ha un mercato binario corrispondente e va ignorata.
SUPPORTED_LINES = frozenset(OU_LINES)

# Sotto questa soglia il consenso e' un bookmaker solo travestito da mediana.
MIN_BOOKMAKERS = 2


@dataclass
class OddsSnapshot:
    """Le probabilita' eque di una partita, con la loro provenienza."""

    event_id: str
    commence_time: str
    home_team: str
    away_team: str
    probabilities: dict[str, float] = field(default_factory=dict)
    n_bookmakers: int = 0
    devig: dict[str, dict[str, float]] = field(default_factory=dict)
    dropped: list[str] = field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        """Servono almeno due vincoli per identificare due rate (blend)."""
        return len(self.probabilities) >= 2

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "commence_time": self.commence_time,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "n_bookmakers": self.n_bookmakers,
            "probabilities": {k: round(v, 5) for k, v in self.probabilities.items()},
            "devig": {
                k: {kk: round(vv, 4) for kk, vv in v.items()}
                for k, v in self.devig.items()
            },
            "dropped": self.dropped,
        }


H2H = dict[str, list[float]]
TOTALS = dict[tuple[float, str], list[float]]


def _median_prices(event: dict[str, Any]) -> tuple[H2H, TOTALS, int]:
    """Raccoglie le quote di tutti i bookmaker, senza ancora decidere niente."""
    home = event.get("home_team", "")
    away = event.get("away_team", "")
    h2h: dict[str, list[float]] = {"home": [], "draw": [], "away": []}
    totals: dict[tuple[float, str], list[float]] = {}
    books = event.get("bookmakers") or []

    for book in books:
        for market in book.get("markets") or []:
            key = market.get("key")
            for outcome in market.get("outcomes") or []:
                price = outcome.get("price")
                if not isinstance(price, (int, float)) or price <= 1.0:
                    continue
                name = (outcome.get("name") or "").strip()
                if key == "h2h":
                    if name == home:
                        h2h["home"].append(float(price))
                    elif name == away:
                        h2h["away"].append(float(price))
                    elif name.lower() == "draw":
                        h2h["draw"].append(float(price))
                elif key == "totals":
                    point = outcome.get("point")
                    if point is None or float(point) not in SUPPORTED_LINES:
                        continue
                    side = name.lower()
                    if side in ("over", "under"):
                        totals.setdefault((float(point), side), []).append(float(price))
    return h2h, totals, len(books)


def event_probabilities(
    event: dict[str, Any], *, min_bookmakers: int = MIN_BOOKMAKERS
) -> OddsSnapshot:
    """Probabilita' eque di una partita, dalle quote di tutti i bookmaker."""
    h2h_prices, totals_prices, n_books = _median_prices(event)
    snapshot = OddsSnapshot(
        event_id=str(event.get("id", "")),
        commence_time=str(event.get("commence_time", "")),
        home_team=str(event.get("home_team", "")),
        away_team=str(event.get("away_team", "")),
        n_bookmakers=n_books,
    )
    if n_books < min_bookmakers:
        snapshot.dropped.append(f"solo {n_books} bookmaker")
        return snapshot

    # --- 1X2: tre esiti, un vincitore ---------------------------------------
    if all(h2h_prices[k] for k in ("home", "draw", "away")):
        odds = [median(h2h_prices[k]) for k in ("home", "draw", "away")]
        try:
            result = devig_power(odds, n_winners=1)
        except DevigError as exc:
            snapshot.dropped.append(f"h2h: {exc}")
        else:
            for key, value in zip(
                ("1x2_home", "1x2_draw", "1x2_away"), result.probabilities, strict=True
            ):
                snapshot.probabilities[key] = float(value)
            snapshot.devig["h2h"] = {
                "beta": result.beta,
                "overround": result.overround,
                "margin_pct": result.margin_pct,
            }

    # --- Over/Under: una coppia per linea, indipendente dalle altre ----------
    lines = sorted({point for point, _ in totals_prices})
    for line in lines:
        over = totals_prices.get((line, "over"))
        under = totals_prices.get((line, "under"))
        if not over or not under:
            snapshot.dropped.append(f"totals {line}: lato mancante")
            continue
        try:
            result = devig_power([median(over), median(under)], n_winners=1)
        except DevigError as exc:
            snapshot.dropped.append(f"totals {line}: {exc}")
            continue
        snapshot.probabilities[f"over_{line}"] = float(result.probabilities[0])
        snapshot.probabilities[f"under_{line}"] = float(result.probabilities[1])
        snapshot.devig[f"totals_{line}"] = {
            "beta": result.beta,
            "overround": result.overround,
            "margin_pct": result.margin_pct,
        }

    return snapshot


def parse_league(
    events: list[dict[str, Any]], *, min_bookmakers: int = MIN_BOOKMAKERS
) -> list[OddsSnapshot]:
    """Tutte le partite di una risposta, gia' sgonfiate."""
    return [
        event_probabilities(event, min_bookmakers=min_bookmakers) for event in events
    ]
