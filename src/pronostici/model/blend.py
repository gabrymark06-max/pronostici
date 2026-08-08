"""Fusione fra modello e mercato.

Il mercato batte i modelli: nel dataset di 32.000 partite di Hubacek et al. un
modello serio resta in svantaggio KL rispetto a Pinnacle. Dare al nostro
Dixon-Coles su 760 partite piu' di un terzo del peso non e' difendibile, da
cui **w = 0,35** (ricerca 8.3).

    log lambda_finale = w * log lambda_modello + (1 - w) * log lambda_mercato

La fusione avviene sui **rate**, non sulle probabilita': cosi' il risultato
resta una matrice congiunta legittima e tutti i mercati derivati restano
coerenti fra loro. Mediare le probabilita' mercato per mercato produrrebbe un
insieme di numeri che non corrisponde ad alcuna distribuzione.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from .markets import catalog
from .matrix import MAX_GOALS, build_matrix

MODEL_WEIGHT = 0.35


@dataclass(frozen=True)
class MarketFit:
    """I rate che riproducono al meglio le probabilita' del mercato."""

    lam_home: float
    lam_away: float
    residual: float  # scarto quadratico medio sulle probabilita'
    n_constraints: int


def solve_market_lambdas(
    targets: dict[str, float], rho: float, *, max_goals: int = MAX_GOALS
) -> MarketFit:
    """Trova (lambda_casa, lambda_ospite) che riproducono le probabilita' date.

    `targets` mappa chiavi di mercato (es. "1x2_home", "over_2.5") alle
    probabilita' gia' sgonfiate col metodo power. Bastano tre vincoli 1X2 piu'
    qualche linea di totals: il sistema e' sovradeterminato e si risolve ai
    minimi quadrati, come da ricerca 8.1.
    """
    masks = {d.key: d.mask for d in catalog(max_goals)}
    unknown = set(targets) - set(masks)
    if unknown:
        raise KeyError(f"mercati non riconosciuti: {sorted(unknown)}")
    if len(targets) < 2:
        raise ValueError("servono almeno due vincoli per identificare due rate")

    keys = sorted(targets)
    observed = np.array([targets[k] for k in keys])

    def residuals(log_lams: np.ndarray) -> np.ndarray:
        gm = build_matrix(
            math.exp(log_lams[0]), math.exp(log_lams[1]), rho, max_goals=max_goals
        )
        flat = gm.matrix.ravel()
        predicted = np.array([flat[masks[k].ravel()].sum() for k in keys])
        return predicted - observed

    start = np.log([1.4, 1.1])
    solution = least_squares(residuals, start, method="lm", xtol=1e-12, ftol=1e-12)
    lam_home, lam_away = np.exp(solution.x)
    rmse = float(np.sqrt(np.mean(solution.fun ** 2)))
    return MarketFit(
        lam_home=float(lam_home),
        lam_away=float(lam_away),
        residual=rmse,
        n_constraints=len(keys),
    )


def blend_lambdas(
    model: tuple[float, float],
    market: tuple[float, float],
    weight: float = MODEL_WEIGHT,
) -> tuple[float, float]:
    """Media geometrica pesata dei rate. `weight` e' il peso del **modello**."""
    if not 0.0 <= weight <= 1.0:
        raise ValueError(f"peso fuori da [0,1]: {weight}")
    return (
        math.exp(weight * math.log(model[0]) + (1 - weight) * math.log(market[0])),
        math.exp(weight * math.log(model[1]) + (1 - weight) * math.log(market[1])),
    )
