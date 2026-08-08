"""Bootstrap parametrico: l'incertezza dei parametri, per campionato.

L'osservazione che dimensiona tutto (brief 5.1): i 300 draw **non si fanno
per partita, si fanno per campionato**. Il costo sta nel rifit, e il rifit
dipende solo dai risultati del campionato. Si persistono i 300 vettori di
parametri; scorare una fixture significa poi costruire 300 matrici, che sono
prodotti esterni di Poisson: millisecondi.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .dixon_coles import DCParams, MatchData, fit

DEFAULT_DRAWS = 300


@dataclass(frozen=True)
class BootstrapResult:
    point: DCParams
    attack: np.ndarray  # (B, n)
    defence: np.ndarray  # (B, n)
    home_adv: np.ndarray  # (B,)
    rho: np.ndarray  # (B,)
    teams: tuple[str, ...]
    converged: int
    seed: int

    @property
    def draws(self) -> int:
        return len(self.home_adv)

    def rates(self, home: str, away: str) -> tuple[np.ndarray, np.ndarray]:
        """(lambda_casa, lambda_ospite) per tutti i draw, vettorizzato."""
        h = self.teams.index(home)
        a = self.teams.index(away)
        return (
            np.exp(self.attack[:, h] + self.defence[:, a] + self.home_adv),
            np.exp(self.attack[:, a] + self.defence[:, h]),
        )

    def to_dict(self) -> dict:
        return {
            "teams": list(self.teams),
            "draws": self.draws,
            "converged": self.converged,
            "seed": self.seed,
            "point": self.point.to_dict(),
            # 5 decimali: la sd bootstrap non ha piu' cifre significative di
            # cosi', e il file finisce in un repository pubblico.
            "attack": np.round(self.attack, 5).tolist(),
            "defence": np.round(self.defence, 5).tolist(),
            "home_adv": np.round(self.home_adv, 5).tolist(),
            "rho": np.round(self.rho, 5).tolist(),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> BootstrapResult:
        return cls(
            point=DCParams.from_dict(payload["point"]),
            attack=np.asarray(payload["attack"], dtype=float),
            defence=np.asarray(payload["defence"], dtype=float),
            home_adv=np.asarray(payload["home_adv"], dtype=float),
            rho=np.asarray(payload["rho"], dtype=float),
            teams=tuple(payload["teams"]),
            converged=int(payload["converged"]),
            seed=int(payload["seed"]),
        )


def run_bootstrap(
    data: MatchData,
    *,
    draws: int = DEFAULT_DRAWS,
    seed: int = 20260808,
    point: DCParams | None = None,
) -> BootstrapResult:
    """Rifitta il modello su `draws` ricampionamenti parametrici.

    Ogni rifit parte dal fit puntuale (**warm start**): i draw sono per
    definizione vicini al punto stimato, e questo e' l'intervento col
    rapporto guadagno/sforzo piu' alto fra quelli del brief 5.3.
    """
    if point is None:
        point, _ = fit(data)

    rng = np.random.default_rng(seed)
    lam = np.exp(
        point.attack[data.home_idx] + point.defence[data.away_idx] + point.home_adv
    )
    mu = np.exp(point.attack[data.away_idx] + point.defence[data.home_idx])

    n = data.n_teams
    attack = np.empty((draws, n))
    defence = np.empty((draws, n))
    home_adv = np.empty(draws)
    rho = np.empty(draws)
    converged = 0

    for b in range(draws):
        resampled = data.with_goals(
            rng.poisson(lam).astype(float), rng.poisson(mu).astype(float)
        )
        params, info = fit(resampled, start=point)
        attack[b] = params.attack
        defence[b] = params.defence
        home_adv[b] = params.home_adv
        rho[b] = params.rho
        converged += int(info["converged"])

    return BootstrapResult(
        point=point,
        attack=attack,
        defence=defence,
        home_adv=home_adv,
        rho=rho,
        teams=data.teams,
        converged=converged,
        seed=seed,
    )
