"""De-vigorizzazione delle quote: **solo metodo power**.

La normalizzazione ingenua (dividere ogni 1/o per la loro somma) assume che
il margine sia proporzionale su tutti gli esiti. Non lo e': il
favourite-longshot bias e' misurato su 90.014 partite con costanti di potenza
fra 1,06 e 1,15 (ricerca 1.1). Normalizzare ingenuamente **sovrastima** la
probabilita' equa dei longshot, cioe' fabbrica vantaggio finto esattamente
dove il vantaggio e' piu' difficile da avere.

    q_i = (1/o_i)^beta   con beta tale che  somma(q_i) = 1

beta > 1 comprime i longshot. Con beta = 1 si ricade nel metodo ingenuo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

# beta plausibile: il paper misura 1,06-1,15. La staffa e' larga per non
# tagliare fuori mercati con margini anomali (totals con molte linee).
BETA_LO, BETA_HI = 0.2, 5.0


class DevigError(ValueError):
    """Le quote non ammettono una soluzione power valida."""


@dataclass(frozen=True)
class DevigResult:
    probabilities: np.ndarray
    beta: float
    overround: float  # somma delle inverse: 1,05 = margine del 5%

    @property
    def margin_pct(self) -> float:
        return (self.overround - 1.0) * 100.0


def devig_power(odds: list[float] | np.ndarray, n_winners: int = 1) -> DevigResult:
    """Converte quote decimali in probabilita' eque col metodo power.

    `n_winners` e' il numero di esiti che si verificano (1 per 1X2 e per un
    over/under, che sono partizioni dello spazio degli esiti).
    """
    inv = 1.0 / np.asarray(odds, dtype=float)
    if inv.ndim != 1 or inv.size < 2:
        raise DevigError("servono almeno due quote")
    if np.any(~np.isfinite(inv)) or np.any(inv <= 0):
        raise DevigError(f"quote non valide: {odds}")
    overround = float(inv.sum())
    if overround <= n_winners:
        # Nessun margine (o quote favorevoli): il power non ha soluzione > 0
        # sensata. E' un dato sospetto, non lo si aggiusta in silenzio.
        raise DevigError(
            f"overround {overround:.4f} <= n_winners {n_winners}: quote sospette"
        )

    def excess(beta: float) -> float:
        return float(np.power(inv, beta).sum()) - n_winners

    # excess e' monotona decrescente in beta quando tutte le inverse sono < 1.
    if excess(BETA_HI) > 0:
        raise DevigError(
            f"nessun beta in [{BETA_LO}, {BETA_HI}] normalizza queste quote: {odds}"
        )
    beta = float(brentq(excess, BETA_LO, BETA_HI, xtol=1e-12, rtol=1e-14))
    probabilities = np.power(inv, beta)
    # Residuo numerico: brentq chiude a 1e-12, la rinormalizzazione qui e'
    # dell'ordine dell'epsilon di macchina, non un secondo de-vig.
    probabilities = probabilities / probabilities.sum() * n_winners
    return DevigResult(probabilities=probabilities, beta=beta, overround=overround)


def devig_naive(odds: list[float] | np.ndarray, n_winners: int = 1) -> np.ndarray:
    """Normalizzazione proporzionale. **Non usare in produzione.**

    Esiste solo perche' i test possano dimostrare in che direzione sbaglia
    rispetto al metodo power sui longshot.
    """
    inv = 1.0 / np.asarray(odds, dtype=float)
    return inv / inv.sum() * n_winners
