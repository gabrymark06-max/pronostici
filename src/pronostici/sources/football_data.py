"""Client football-data.org.

Tre proprieta' non negoziabili:

1. **Rate limit rispettato.** Il piano gratuito e' nell'ordine di 10 richieste
   al minuto; il client serializza le chiamate con un intervallo minimo e
   legge gli header di risposta per correggersi. Su 429 aspetta il reset
   dichiarato dal server invece di ritentare a caso.
2. **Nessuna rete nei test.** Ogni risposta grezza finisce su disco. Con
   `offline=True` il client legge solo la cache e solleva se manca: i test
   girano sempre e solo su fixture.
3. **La chiave non compare mai** nei file scritti (ne' in cache, ne' nei
   metadati). Il repository e' pubblico.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from ..config import CACHE_DIR, get_settings

log = logging.getLogger(__name__)

BASE_URL = "https://api.football-data.org/v4"

# 10 req/min dichiarate -> 6.5 s di intervallo tiene ~9/min con margine.
MIN_INTERVAL_S = 6.5
MAX_RETRIES = 4


class FootballDataError(RuntimeError):
    """Errore di trasporto o di quota. Contiene lo status, mai la chiave."""


class CacheMiss(FootballDataError):
    """Richiesto un endpoint non in cache mentre offline=True."""


@dataclass
class RateLimitObservation:
    """Cosa il server ha detto davvero sul rate limit, per misurarlo."""

    requests_available_minute: int | None = None
    counter_reset_s: int | None = None
    observed_at: float = 0.0


@dataclass
class FootballDataClient:
    offline: bool = False
    cache_dir: Path = CACHE_DIR
    min_interval_s: float = MIN_INTERVAL_S
    _last_call: float = field(default=0.0, repr=False)
    _session: requests.Session | None = field(default=None, repr=False)
    last_rate_limit: RateLimitObservation = field(
        default_factory=RateLimitObservation, repr=False
    )
    request_count: int = 0

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ cache

    def _cache_path(self, path: str, params: dict[str, Any] | None) -> Path:
        key = path + "?" + json.dumps(params or {}, sort_keys=True)
        digest = hashlib.sha256(key.encode()).hexdigest()[:16]
        slug = path.strip("/").replace("/", "_")
        return self.cache_dir / f"{slug}_{digest}.json"

    # ------------------------------------------------------------- trasporto

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_call
        if self._last_call and elapsed < self.min_interval_s:
            time.sleep(self.min_interval_s - elapsed)
        self._last_call = time.monotonic()

    def _headers(self) -> dict[str, str]:
        settings = get_settings()
        if not settings.has_football_data:
            raise FootballDataError(
                "FOOTBALL_DATA_API_KEY non impostata. In sviluppo va in .env, "
                "in CI nei GitHub Actions Secrets."
            )
        return {"X-Auth-Token": settings.football_data_api_key}

    def _record_rate_limit(self, response: requests.Response) -> None:
        def _as_int(name: str) -> int | None:
            raw = response.headers.get(name)
            try:
                return int(raw) if raw is not None else None
            except ValueError:
                return None

        self.last_rate_limit = RateLimitObservation(
            requests_available_minute=_as_int("X-Requests-Available-Minute"),
            counter_reset_s=_as_int("X-RequestCounter-Reset"),
            observed_at=time.time(),
        )

    def get(
        self, path: str, params: dict[str, Any] | None = None, *, refresh: bool = False
    ) -> dict[str, Any]:
        """GET con cache su disco. Idempotente: la stessa richiesta non paga
        due volte il rate limit nella stessa giornata di lavoro."""
        cache_file = self._cache_path(path, params)
        if cache_file.exists() and not refresh:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        if self.offline:
            raise CacheMiss(
                f"offline=True e nessuna fixture per {path} {params}. "
                f"Attesa in {cache_file}"
            )

        if self._session is None:
            self._session = requests.Session()

        last_error: str = ""
        for attempt in range(MAX_RETRIES):
            self._throttle()
            response = self._session.get(
                f"{BASE_URL}{path}",
                params=params,
                headers=self._headers(),
                timeout=30,
            )
            self.request_count += 1
            self._record_rate_limit(response)

            if response.status_code == 200:
                payload = response.json()
                cache_file.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
                )
                return payload

            if response.status_code == 429:
                wait = self.last_rate_limit.counter_reset_s or 60
                log.warning(
                    "429 su %s: attendo %ss (tentativo %d/%d)",
                    path,
                    wait,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(wait + 1)
                last_error = "429 rate limit"
                continue

            if response.status_code in (500, 502, 503, 504):
                backoff = 2 ** attempt
                log.warning("%s su %s: backoff %ss", response.status_code, path, backoff)
                time.sleep(backoff)
                last_error = f"HTTP {response.status_code}"
                continue

            # 403/404: non ritentabili. Il messaggio non riporta la chiave.
            raise FootballDataError(
                f"HTTP {response.status_code} su {path} params={params}"
            )

        raise FootballDataError(f"esauriti i tentativi su {path}: {last_error}")

    # ----------------------------------------------------------------- API

    def competition_matches(
        self,
        code: str,
        season: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        *,
        refresh: bool = False,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if season is not None:
            params["season"] = season
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        payload = self.get(f"/competitions/{code}/matches", params, refresh=refresh)
        return payload.get("matches", [])
