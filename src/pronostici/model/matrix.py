"""La matrice congiunta dei gol: l'unica fonte di tutti i mercati.

Ogni mercato dello scope si legge come somma di celle di questa matrice.
E' cio' che rende gli undici mercati **mutuamente coerenti per costruzione**:
non e' una proprieta' da testare a valle, e' l'architettura.

La massa troncata (i risultati con piu' di `max_goals` gol) viene misurata e
riportata, non nascosta: l'audit del tentativo precedente segnalava
`max_goals=8` senza alcuna verifica.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import poisson

# 12 invece degli 8 del tentativo precedente: serve per handicap alti e
# multigol estesi. La massa troncata viene comunque misurata.
MAX_GOALS = 12


@dataclass(frozen=True)
class GoalMatrix:
    """P(gol_casa = i, gol_ospite = j), normalizzata a 1."""

    matrix: np.ndarray  # (max_goals+1, max_goals+1)
    lam_home: float
    lam_away: float
    rho: float
    truncated_mass: float  # massa persa oltre max_goals, PRIMA di normalizzare
    tau_mass_shift: float  # quanto la correzione DC sposta la massa totale

    @property
    def max_goals(self) -> int:
        return self.matrix.shape[0] - 1

    def probability(self, mask: np.ndarray) -> float:
        """Probabilita' di un evento espresso come maschera booleana."""
        return float(self.matrix[mask].sum())


def _tau_matrix(lam: float, mu: float, rho: float, size: int) -> np.ndarray:
    """Correzione Dixon-Coles sulle quattro celle dei punteggi bassi."""
    tau = np.ones((size, size))
    tau[0, 0] = 1.0 - lam * mu * rho
    tau[0, 1] = 1.0 + lam * rho
    tau[1, 0] = 1.0 + mu * rho
    tau[1, 1] = 1.0 - rho
    # Una tau negativa produrrebbe probabilita' negative: si taglia a zero e
    # la normalizzazione finale rimette a posto il totale.
    return np.clip(tau, 0.0, None)


def build_matrix(
    lam_home: float, lam_away: float, rho: float = 0.0, max_goals: int = MAX_GOALS
) -> GoalMatrix:
    """Costruisce la matrice congiunta da (lambda_casa, lambda_ospite, rho)."""
    if lam_home <= 0 or lam_away <= 0:
        raise ValueError(f"lambda devono essere positivi: {lam_home}, {lam_away}")
    size = max_goals + 1
    goals = np.arange(size)
    p_home = poisson.pmf(goals, lam_home)
    p_away = poisson.pmf(goals, lam_away)

    # Massa oltre la troncatura, misurata sulle Poisson esatte.
    truncated = float(1.0 - p_home.sum() * p_away.sum())

    joint = np.outer(p_home, p_away)
    tau = _tau_matrix(lam_home, lam_away, rho, size)
    corrected = joint * tau
    tau_shift = float(corrected.sum() - joint.sum())

    total = corrected.sum()
    if total <= 0:
        raise ValueError(f"matrice degenere per lam={lam_home},{lam_away},rho={rho}")
    return GoalMatrix(
        matrix=corrected / total,
        lam_home=lam_home,
        lam_away=lam_away,
        rho=rho,
        truncated_mass=truncated,
        tau_mass_shift=tau_shift,
    )


def build_matrices(
    lam_home: np.ndarray,
    lam_away: np.ndarray,
    rho: np.ndarray,
    max_goals: int = MAX_GOALS,
) -> np.ndarray:
    """B matrici in una passata vettorizzata, per i draw del bootstrap.

    Ritorna un array (B, size, size) normalizzato. Scorare una fixture con
    300 draw deve costare millisecondi (brief 5.1): qui non si itera in
    Python sui draw se non per le quattro celle della correzione.
    """
    lam_home = np.asarray(lam_home, dtype=float)
    lam_away = np.asarray(lam_away, dtype=float)
    rho = np.asarray(rho, dtype=float)
    size = max_goals + 1
    goals = np.arange(size)

    # (B, size) per lato, poi prodotto esterno vettorizzato.
    p_home = poisson.pmf(goals[None, :], lam_home[:, None])
    p_away = poisson.pmf(goals[None, :], lam_away[:, None])
    joint = p_home[:, :, None] * p_away[:, None, :]

    joint[:, 0, 0] *= np.clip(1.0 - lam_home * lam_away * rho, 0.0, None)
    joint[:, 0, 1] *= np.clip(1.0 + lam_home * rho, 0.0, None)
    joint[:, 1, 0] *= np.clip(1.0 + lam_away * rho, 0.0, None)
    joint[:, 1, 1] *= np.clip(1.0 - rho, 0.0, None)

    totals = joint.sum(axis=(1, 2), keepdims=True)
    return joint / totals


def half_time_matrices(
    lam_home: float, lam_away: float, ht_ratio: float, max_goals: int = 8
) -> tuple[np.ndarray, np.ndarray]:
    """Matrici del primo e del secondo tempo, indipendenti.

    `ht_ratio` e' **misurato** dai punteggi HT reali di football-data
    (`dataset.half_time_ratio`), non assunto a 0,45: la ricerca segnala quel
    valore come non verificato.
    """
    if not 0.0 < ht_ratio < 1.0:
        raise ValueError(f"ht_ratio fuori da (0,1): {ht_ratio}")
    size = max_goals + 1
    goals = np.arange(size)
    first = np.outer(
        poisson.pmf(goals, lam_home * ht_ratio),
        poisson.pmf(goals, lam_away * ht_ratio),
    )
    second = np.outer(
        poisson.pmf(goals, lam_home * (1 - ht_ratio)),
        poisson.pmf(goals, lam_away * (1 - ht_ratio)),
    )
    return first / first.sum(), second / second.sum()
