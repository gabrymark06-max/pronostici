"""La pipeline completa su una fixture: dai parametri al pronostico.

Mette insieme i passi 1-8 della ricerca 8.1. E' l'unico posto in cui si
compone il calcolo, cosi' che `score`, `finalize` e il backtest non possano
divergere: il backtest deve misurare **lo stesso** sistema che va in
produzione, altrimenti non misura niente.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .archive import Match
from .model import markets as mk
from .model.blend import MODEL_WEIGHT, blend_lambdas, solve_market_lambdas
from .model.bootstrap import BootstrapResult
from .model.matrix import MAX_GOALS, build_matrices
from .model.selection import Selection, build_candidates, select

# Mercati su cui the-odds-api ci da' un riferimento (h2h + totals).
ODDS_BACKED_KEYS = frozenset(
    {"1x2_home", "1x2_draw", "1x2_away"}
    | {f"over_{line}" for line in (0.5, 1.5, 2.5, 3.5, 4.5)}
    | {f"under_{line}" for line in (0.5, 1.5, 2.5, 3.5, 4.5)}
)


@dataclass
class FixtureScore:
    match: Match
    selection: Selection
    mean_matrix: np.ndarray
    lam_home: float
    lam_away: float
    model_weight: float
    source: str
    truncated_mass: float
    reasons: list[str] = field(default_factory=list)
    market_probabilities: dict[str, float] = field(default_factory=dict)
    half_time: dict[str, float] = field(default_factory=dict)


def _reasons(
    match: Match,
    lam_home: float,
    lam_away: float,
    selection: Selection,
    references: dict[str, float],
) -> list[str]:
    """Due o tre frasi generate dalla matrice: i due rate attesi, il base rate
    del campionato, e di quanto ci discostiamo. Mai "value bet", mai "edge",
    mai un importo (decisioni.md)."""
    out = [
        f"Gol attesi: {match.home_name} {lam_home:.2f}, "
        f"{match.away_name} {lam_away:.2f} (totale {lam_home + lam_away:.2f})."
    ]
    pick = selection.pick
    if pick is None:
        return out

    reference = references.get(pick.key, pick.reference)
    delta = (pick.p_tilde - reference) * 100
    direction = "sopra" if delta >= 0 else "sotto"
    out.append(
        f"{pick.label}: {pick.p_tilde * 100:.0f} su 100, "
        f"{abs(delta):.0f} punti {direction} la media di riferimento "
        f"({reference * 100:.0f} su 100)."
    )
    if pick.alpha < 0.7:
        out.append(
            f"Stima prudente: l'incertezza e' alta, il valore mostrato e' gia' "
            f"riportato verso la media (peso della stima {pick.alpha:.0%})."
        )
    else:
        out.append(
            f"Banda di incertezza: fra {pick.p5 * 100:.0f} e {pick.p95 * 100:.0f} su 100."
        )
    return out


def score_fixture(
    match: Match,
    boot: BootstrapResult,
    base_rates: dict[str, float],
    *,
    tau: float | dict[str, float] = 0.08,
    market_probabilities: dict[str, float] | None = None,
    model_weight: float = 1.0,
    ht_ratio: float | None = None,
    max_goals: int = MAX_GOALS,
) -> FixtureScore:
    """Scora una fixture. Con `market_probabilities` (gia' sgonfiate col
    metodo power) fonde modello e mercato e passa a w = 0,35."""
    if match.home_name not in boot.teams or match.away_name not in boot.teams:
        raise KeyError(
            f"squadra fuori dal modello: {match.home_name} / {match.away_name}"
        )

    lam_h, lam_a = boot.rates(match.home_name, match.away_name)
    rho = boot.rho
    source = "model_only"

    if market_probabilities:
        # I rate che riproducono il mercato si risolvono una volta, sul punto:
        # il mercato non ha incertezza nostra da propagare.
        usable = {
            k: v for k, v in market_probabilities.items() if k in ODDS_BACKED_KEYS
        }
        if len(usable) >= 2:
            fitted = solve_market_lambdas(usable, float(np.median(rho)), max_goals=max_goals)
            blended = [
                blend_lambdas((h, a), (fitted.lam_home, fitted.lam_away), model_weight)
                for h, a in zip(lam_h, lam_a, strict=True)
            ]
            lam_h = np.array([b[0] for b in blended])
            lam_a = np.array([b[1] for b in blended])
            source = "blended_with_odds"

    matrices = build_matrices(lam_h, lam_a, rho, max_goals=max_goals)
    probs_by_draw = mk.probabilities_batch(matrices)
    mean_matrix = matrices.mean(axis=0)

    # Riferimento: quota sgonfiata dove esiste, base rate dove non esiste.
    references = dict(base_rates)
    if market_probabilities:
        references.update(
            {k: v for k, v in market_probabilities.items() if k in ODDS_BACKED_KEYS}
        )

    candidates = build_candidates(
        probs_by_draw, references, tau=tau, max_goals=max_goals
    )
    selection = select(candidates, mean_matrix, max_goals=max_goals)

    lam_home_point = float(lam_h.mean())
    lam_away_point = float(lam_a.mean())

    half_time: dict[str, float] = {}
    if ht_ratio is not None:
        half_time = mk.half_time_probabilities(
            lam_home_point, lam_away_point, ht_ratio
        )

    # Massa troncata: si misura sulle Poisson esatte del punto, e si riporta.
    from scipy.stats import poisson

    goals = np.arange(max_goals + 1)
    truncated = float(
        1.0
        - poisson.pmf(goals, lam_home_point).sum() * poisson.pmf(goals, lam_away_point).sum()
    )

    return FixtureScore(
        match=match,
        selection=selection,
        mean_matrix=mean_matrix,
        lam_home=lam_home_point,
        lam_away=lam_away_point,
        model_weight=model_weight if source == "blended_with_odds" else 1.0,
        source=source,
        truncated_mass=truncated,
        reasons=_reasons(match, lam_home_point, lam_away_point, selection, references),
        market_probabilities={
            k: float(v.mean()) for k, v in probs_by_draw.items()
        },
        half_time=half_time,
    )
