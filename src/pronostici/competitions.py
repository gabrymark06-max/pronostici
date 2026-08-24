"""Le competizioni in scope, da docs/decisioni.md.

Un solo posto in cui esistono i codici: i job non li scrivono a mano.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Competition:
    code: str  # codice football-data.org
    name: str
    odds_key: str | None  # chiave the-odds-api, None = solo modello per sempre
    teams: int


# I dodici codici TIER_ONE verificati in docs/research/fonti-dati.md 8.
COMPETITIONS: tuple[Competition, ...] = (
    Competition("PL", "Premier League", "soccer_epl", 20),
    Competition("SA", "Serie A", "soccer_italy_serie_a", 20),
    Competition("PD", "La Liga", "soccer_spain_la_liga", 20),
    Competition("BL1", "Bundesliga", "soccer_germany_bundesliga", 18),
    Competition("FL1", "Ligue 1", "soccer_france_ligue_one", 18),
    # DUE LEGHE CHE ERANO «SOLO MODELLO PER SEMPRE», e non lo sono piu'.
    # La decisione risaliva a quando the-odds-api non le copriva. Il 25
    # agosto 2026 il suo catalogo le da' entrambe attive, verificato
    # chiamando `/v4/sports` (che non costa crediti): senza chiave, le loro
    # partite restavano senza nessun prezzo di mercato e il pronostico si
    # reggeva sul solo modello.
    Competition("DED", "Eredivisie", "soccer_netherlands_eredivisie", 18),
    Competition("PPL", "Primeira Liga", "soccer_portugal_primeira_liga", 18),
    Competition("ELC", "Championship", "soccer_efl_champ", 24),
    Competition("BSA", "Brasileirao", "soccer_brazil_campeonato", 20),
    Competition("CL", "Champions League", "soccer_uefa_champs_league", 36),
    # Nazionali: nel piano dati, ma senza partite fino al 2028 (brief 10).
    Competition("WC", "Mondiali", None, 48),
    Competition("EC", "Europei", None, 24),
)

BY_CODE: dict[str, Competition] = {c.code: c for c in COMPETITIONS}

# Competizioni che hanno davvero partite oggi: i job girano su queste.
ACTIVE_CODES: tuple[str, ...] = tuple(
    c.code for c in COMPETITIONS if c.code not in {"WC", "EC"}
)


def get(code: str) -> Competition:
    try:
        return BY_CODE[code]
    except KeyError as exc:
        valid = ", ".join(sorted(BY_CODE))
        raise KeyError(f"competizione sconosciuta: {code!r}. Valide: {valid}") from exc
