"""Client the-odds-api con governo della quota.

500 crediti al mese, costo di una chiamata = mercati x regioni. Con `h2h` +
`totals` su regione `eu` una chiamata costa **2 crediti** e restituisce tutte
le partite imminenti di quel campionato (brief 6.1).

Il governo della quota e' la parte importante, non il trasporto:

* **contatore persistito** in `data/odds_budget.json`, per mese;
* **tetto hard** (default 250, meta' della quota): se lo tocchiamo c'e' un
  bug, non un picco di traffico;
* **riconciliazione con gli header** di risposta: se il nostro contatore e il
  loro divergono, vince il loro e il job si mette in pausa;
* **scala di degradazione a quattro gradini** che finisce su "solo modello",
  mai su una schermata di errore.

Senza `ODDS_API_KEY` il client non solleva: dichiara di essere spento e la
pipeline resta a w = 1,0. E' lo stato in cui il progetto si trova oggi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from ..config import DATA, get_settings
from ..storage import read_json, write_json

log = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"
BUDGET_FILE = DATA / "odds_budget.json"

MARKETS = ("h2h", "totals")  # niente `spreads`: +50% di costo per vincoli
REGIONS = ("eu",)  # quasi collineari a quelli che abbiamo gia'
CREDITS_PER_CALL = len(MARKETS) * len(REGIONS)

# Gradini di rinuncia quando la quota stringe (brief 6.4). Il gradino 4 non
# e' un errore: e' il prodotto che funziona con w = 1,0 ovunque.
DEGRADATION_LADDER = (
    "audit_clv",  # 1. salta l'audit CLV
    "secondary_leagues",  # 2. salta Brasileirao e Championship
    "totals_market",  # 3. solo h2h
    "model_only",  # 4. solo modello, e la scheda lo dichiara
)
SECONDARY_LEAGUES = ("BSA", "ELC")


class OddsUnavailable(RuntimeError):
    """Le quote non sono ottenibili adesso. Non e' un errore fatale:
    il chiamante deve degradare a 'solo modello'."""


@dataclass
class Budget:
    """Stato della quota per il mese corrente."""

    month: str
    used: int
    cap: int
    calls: list[dict[str, Any]]
    provider_remaining: int | None = None
    paused: bool = False
    pause_reason: str | None = None

    @property
    def remaining(self) -> int:
        return max(0, self.cap - self.used)

    def can_afford(self, cost: int) -> bool:
        return not self.paused and self.used + cost <= self.cap

    def degradation_step(self) -> str | None:
        """Quale gradino della scala e' attivo, in base a quanto resta."""
        ratio = self.remaining / self.cap if self.cap else 0.0
        if self.paused or ratio <= 0.0:
            return "model_only"
        if ratio < 0.10:
            return "totals_market"
        if ratio < 0.25:
            return "secondary_leagues"
        if ratio < 0.40:
            return "audit_clv"
        return None

    def to_dict(self) -> dict:
        return {
            "month": self.month,
            "used": self.used,
            "cap": self.cap,
            "remaining": self.remaining,
            "provider_remaining": self.provider_remaining,
            "paused": self.paused,
            "pause_reason": self.pause_reason,
            "degradation_step": self.degradation_step(),
            "calls": self.calls[-100:],  # non lasciamo crescere il file
        }


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def load_budget(cap: int | None = None) -> Budget:
    """Carica il contatore. Il mese nuovo azzera l'uso, non la storia."""
    settings = get_settings()
    cap = cap if cap is not None else settings.odds_credit_cap
    payload = read_json(BUDGET_FILE, default=None)
    month = _current_month()
    if not payload or payload.get("month") != month:
        return Budget(month=month, used=0, cap=cap, calls=[])
    return Budget(
        month=payload["month"],
        used=int(payload.get("used", 0)),
        cap=cap,
        calls=list(payload.get("calls", [])),
        provider_remaining=payload.get("provider_remaining"),
        paused=bool(payload.get("paused", False)),
        pause_reason=payload.get("pause_reason"),
    )


def save_budget(budget: Budget) -> bool:
    return write_json(BUDGET_FILE, budget.to_dict(), indent=2)


@dataclass
class OddsClient:
    offline: bool = False
    _session: requests.Session | None = None

    @property
    def enabled(self) -> bool:
        """False finche' l'utente non registra la key: il job si spegne da
        solo e ogni partita resta con il pronostico da solo modello."""
        return get_settings().has_odds

    def fetch_league(self, odds_key: str, budget: Budget) -> list[dict[str, Any]]:
        """Una chiamata per campionato. Aggiorna il contatore **prima** di
        spendere, cosi' un crash a meta' non fa perdere il conto."""
        if not self.enabled:
            raise OddsUnavailable(
                "ODDS_API_KEY non impostata: si procede con il solo modello"
            )
        if not budget.can_afford(CREDITS_PER_CALL):
            raise OddsUnavailable(
                f"tetto crediti raggiunto ({budget.used}/{budget.cap}): "
                f"degradazione a {budget.degradation_step()}"
            )
        if self.offline:
            raise OddsUnavailable("offline=True: nessuna chiamata di rete")

        if self._session is None:
            self._session = requests.Session()
        response = self._session.get(
            f"{BASE_URL}/sports/{odds_key}/odds",
            params={
                "apiKey": get_settings().odds_api_key,
                "regions": ",".join(REGIONS),
                "markets": ",".join(MARKETS),
                "oddsFormat": "decimal",
            },
            timeout=30,
        )

        budget.used += CREDITS_PER_CALL
        budget.calls.append(
            {
                "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "league": odds_key,
                "cost": CREDITS_PER_CALL,
                "status": response.status_code,
            }
        )

        # Riconciliazione: se il loro contatore e il nostro divergono, vince
        # il loro e il job si ferma finche' qualcuno non guarda.
        remaining = response.headers.get("x-requests-remaining")
        if remaining is not None:
            try:
                budget.provider_remaining = int(float(remaining))
            except ValueError:
                pass
        used_header = response.headers.get("x-requests-used")
        if used_header is not None:
            try:
                provider_used = int(float(used_header))
                if provider_used > budget.used + 2 * CREDITS_PER_CALL:
                    budget.paused = True
                    budget.pause_reason = (
                        f"contatore divergente: nostro {budget.used}, "
                        f"loro {provider_used}"
                    )
            except ValueError:
                pass

        if response.status_code != 200:
            raise OddsUnavailable(f"HTTP {response.status_code} da the-odds-api")
        return response.json()
