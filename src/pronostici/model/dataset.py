"""Dall'archivio ai vettori del fit.

Un solo posto in cui si decide **quali** partite entrano nel fit e con quale
peso, cosi' che backtest e produzione non possano divergere in silenzio.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from ..archive import Match
from .dixon_coles import MatchData, time_weights


def build_dataset(
    matches: list[Match],
    *,
    as_of: datetime,
    half_life_days: float = 365.0,
    window_days: float = 730.0,
    min_matches_per_team: int = 3,
) -> MatchData:
    """Costruisce i vettori del fit dalle partite **concluse prima di `as_of`**.

    Il taglio stretto (`<` e non `<=`) e' cio' che rende onesto il walk-forward:
    una partita non puo' mai contribuire alla propria previsione.
    """
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    usable = [
        m
        for m in matches
        if m.is_finished
        and m.date < as_of
        and (as_of - m.date).days <= window_days
    ]
    if not usable:
        raise ValueError(f"nessuna partita conclusa prima di {as_of.isoformat()}")

    # Le squadre con pochissime partite nella finestra rendono il fit
    # instabile; restano fuori e semplicemente non sono pronosticabili.
    counts: dict[str, int] = {}
    for m in usable:
        counts[m.home_name] = counts.get(m.home_name, 0) + 1
        counts[m.away_name] = counts.get(m.away_name, 0) + 1
    keep = {t for t, c in counts.items() if c >= min_matches_per_team}
    usable = [m for m in usable if m.home_name in keep and m.away_name in keep]
    if not usable:
        raise ValueError("nessuna partita dopo il filtro sulle squadre")

    teams = tuple(sorted({m.home_name for m in usable} | {m.away_name for m in usable}))
    index = {t: i for i, t in enumerate(teams)}

    ages = np.array([(as_of - m.date).total_seconds() / 86400.0 for m in usable])
    return MatchData(
        home_idx=np.array([index[m.home_name] for m in usable], dtype=np.intp),
        away_idx=np.array([index[m.away_name] for m in usable], dtype=np.intp),
        home_goals=np.array([m.ft_home for m in usable], dtype=float),
        away_goals=np.array([m.ft_away for m in usable], dtype=float),
        weights=time_weights(ages, half_life_days),
        teams=teams,
    )


def half_time_ratio(matches: list[Match]) -> float | None:
    """Rapporto misurato fra gol del primo tempo e gol totali.

    La ricerca (11) segnala `lambda_HT ~ 0,45 lambda_FT` come **non
    verificato**. Qui non si assume: si misura dai punteggi HT reali, che
    football-data espone. Ritorna None se non ci sono punteggi HT.
    """
    ht = [m for m in matches if m.is_finished and m.ht_home is not None]
    if not ht:
        return None
    ht_goals = sum(m.ht_home + m.ht_away for m in ht)
    ft_goals = sum(m.ft_home + m.ft_away for m in ht)
    if ft_goals == 0:
        return None
    return ht_goals / ft_goals
