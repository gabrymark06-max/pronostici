"""Configurazione: segreti solo da ambiente, mai da letterali.

Il repository e' pubblico. Nessuna chiave puo' comparire in questo file,
in `data/`, o in una fixture di test. `.env` e' in `.gitignore` e viene letto
solo in sviluppo; in CI i valori arrivano da GitHub Actions Secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# Radice del repository: .../pronostici
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
DOCS = ROOT / "docs"

# Sottocartelle del contratto con il frontend (vedi docs/schema.md).
ARCHIVE_DIR = DATA / "archive"
LEAGUES_DIR = DATA / "leagues"
FIXTURES_DIR = DATA / "fixtures"
LEDGER_DIR = DATA / "ledger"
CACHE_DIR = DATA / "cache"  # in .gitignore: risposte grezze, non e' il ledger
TEST_FIXTURES_DIR = ROOT / "tests" / "fixtures"


def _load_dotenv() -> None:
    """Carica `.env` se esiste, senza sovrascrivere l'ambiente reale.

    Il file scritto su Windows ha spesso un BOM: si legge con utf-8-sig,
    altrimenti la prima chiave si chiamerebbe '\\ufeffFOOTBALL_DATA_API_KEY'.
    """
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    """Valori di ambiente, risolti una volta sola.

    Nessun default e' un segreto: le due chiavi valgono "" quando mancano, e il
    codice a valle deve degradare, non sollevare, quando la chiave delle quote
    non c'e' (brief 6.4).
    """

    football_data_api_key: str
    odds_api_key: str
    odds_credit_cap: int

    @property
    def has_football_data(self) -> bool:
        return bool(self.football_data_api_key)

    @property
    def has_odds(self) -> bool:
        """False finche' l'utente non registra la key: il job quote si spegne
        da solo e il pronostico resta 'solo modello'."""
        return bool(self.odds_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()
    raw_cap = os.environ.get("ODDS_CREDIT_CAP", "250").strip() or "250"
    try:
        cap = int(raw_cap)
    except ValueError as exc:  # configurazione errata: meglio forte e subito
        raise ValueError(f"ODDS_CREDIT_CAP non e' un intero: {raw_cap!r}") from exc
    return Settings(
        football_data_api_key=os.environ.get("FOOTBALL_DATA_API_KEY", "").strip(),
        odds_api_key=os.environ.get("ODDS_API_KEY", "").strip(),
        odds_credit_cap=cap,
    )
