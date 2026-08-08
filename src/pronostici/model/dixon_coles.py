"""Dixon-Coles (1997) con decadimento esponenziale, vettorizzato.

Tre scelte deliberate, ognuna corregge un difetto verificato del tentativo
precedente (`docs/orchestrator-findings.md`):

1. **Nessun ciclo Python sulle partite.** La log-verosimiglianza e' un
   calcolo numpy su vettori. La versione precedente iterava in Python dentro
   `_log_likelihood`, chiamata da L-BFGS-B senza gradiente: nell'ordine di
   20 milioni di iterazioni interpretate per lega.
2. **Gradiente analitico.** Con 2n+1 parametri (49 per la Serie A) un
   gradiente numerico costa 50 valutazioni per passo. Quello analitico ne
   costa una. E' il singolo intervento che rende sostenibili 300 bootstrap.
3. **Vincolo di identificabilita' imposto DENTRO la verosimiglianza.**
   L'attacco dell'ultima squadra e' `-somma(gli altri)`, quindi
   l'ottimizzatore lavora su un problema identificato. Normalizzare dopo il
   fit (come faceva la versione precedente) lascia l'ottimizzatore su un
   continuum di soluzioni equivalenti: funziona per caso, grazie ai bound.

Parametrizzazione, standard:

    log lambda_casa   = attacco[casa]   + difesa[ospite] + vantaggio_campo
    log lambda_ospite = attacco[ospite] + difesa[casa]

`difesa` e' **libera in segno** e sommata: una squadra puo' concedere piu'
della media, non solo meno. La versione precedente forzava `exp()` e
sottraeva, cioe' ogni difesa poteva solo ridurre i gol dell'avversario.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

# Sotto questa soglia la correzione tau e' numericamente inaffidabile.
TAU_FLOOR = 1e-6
# Peso della penalita' esatta che tiene tau positiva. Non e' un iperparametro
# del modello: all'ottimo la penalita' vale zero.
TAU_PENALTY = 1e4
# rho e' limitato per tenere tau positiva, non come parametro da tarare.
RHO_BOUND = 0.4


@dataclass(frozen=True)
class MatchData:
    """I dati di fit, gia' indicizzati. Costruita una volta, riusata da tutti
    i rifit del bootstrap."""

    home_idx: np.ndarray  # int, (m,)
    away_idx: np.ndarray  # int, (m,)
    home_goals: np.ndarray  # int, (m,)
    away_goals: np.ndarray  # int, (m,)
    weights: np.ndarray  # float, (m,) pesi di decadimento temporale
    teams: tuple[str, ...]

    @property
    def n_teams(self) -> int:
        return len(self.teams)

    @property
    def n_matches(self) -> int:
        return len(self.home_idx)

    def with_goals(self, home_goals: np.ndarray, away_goals: np.ndarray) -> MatchData:
        """Stessi accoppiamenti e stessi pesi, punteggi nuovi.
        E' cio' che serve al bootstrap parametrico."""
        return MatchData(
            home_idx=self.home_idx,
            away_idx=self.away_idx,
            home_goals=home_goals,
            away_goals=away_goals,
            weights=self.weights,
            teams=self.teams,
        )


@dataclass(frozen=True)
class DCParams:
    """Un punto nello spazio dei parametri: il fit puntuale o un draw."""

    attack: np.ndarray  # (n,)
    defence: np.ndarray  # (n,)
    home_adv: float
    rho: float
    teams: tuple[str, ...]

    def index(self, team: str) -> int:
        return self.teams.index(team)

    def rates(self, home: str, away: str) -> tuple[float, float]:
        """(lambda_casa, lambda_ospite) attesi per un accoppiamento."""
        h, a = self.index(home), self.index(away)
        return (
            math.exp(self.attack[h] + self.defence[a] + self.home_adv),
            math.exp(self.attack[a] + self.defence[h]),
        )

    def to_dict(self) -> dict:
        return {
            "teams": list(self.teams),
            "attack": [round(float(v), 6) for v in self.attack],
            "defence": [round(float(v), 6) for v in self.defence],
            "home_adv": round(float(self.home_adv), 6),
            "rho": round(float(self.rho), 6),
        }

    @classmethod
    def from_dict(cls, payload: dict) -> DCParams:
        return cls(
            attack=np.asarray(payload["attack"], dtype=float),
            defence=np.asarray(payload["defence"], dtype=float),
            home_adv=float(payload["home_adv"]),
            rho=float(payload["rho"]),
            teams=tuple(payload["teams"]),
        )


def time_weights(ages_days: np.ndarray, half_life_days: float = 365.0) -> np.ndarray:
    """Peso esponenziale: una partita di `half_life_days` fa pesa la meta'.

    Emivita iniziale 365 giorni (tabella dei parametri, ricerca 8.3).
    """
    if half_life_days <= 0:
        raise ValueError("half_life_days deve essere positivo")
    xi = math.log(2.0) / half_life_days
    return np.exp(-xi * np.asarray(ages_days, dtype=float))


def effective_sample_size(weights: np.ndarray) -> float:
    """n_eff di Kish: (sum w)^2 / sum w^2. Il numero che la ricerca 1.2 stima
    a 65,8 per squadra e chiede di sostituire con quello vero."""
    w = np.asarray(weights, dtype=float)
    return float(w.sum() ** 2 / np.square(w).sum())


def _unpack(theta: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray, float, float]:
    """theta -> (attacco, difesa, vantaggio_campo, rho).

    L'attacco dell'ultima squadra e' determinato dagli altri: e' qui che il
    vincolo di identificabilita' entra nella verosimiglianza."""
    free_attack = theta[: n - 1]
    attack = np.empty(n)
    attack[: n - 1] = free_attack
    attack[n - 1] = -free_attack.sum()
    defence = theta[n - 1 : 2 * n - 1]
    return attack, defence, float(theta[-2]), float(theta[-1])


def _tau_terms(
    lam: np.ndarray,
    mu: np.ndarray,
    rho: float,
    m00: np.ndarray,
    m01: np.ndarray,
    m10: np.ndarray,
    m11: np.ndarray,
) -> np.ndarray:
    """Correzione Dixon-Coles sui quattro punteggi bassi, vettorizzata."""
    tau = np.ones_like(lam)
    tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
    tau[m01] = 1.0 + lam[m01] * rho
    tau[m10] = 1.0 + mu[m10] * rho
    tau[m11] = 1.0 - rho
    return tau


class DixonColesLikelihood:
    """Verosimiglianza pesata e il suo gradiente. Le maschere dei punteggi
    bassi e il termine log(x!) si calcolano una volta sola."""

    def __init__(self, data: MatchData):
        self.data = data
        x, y = data.home_goals, data.away_goals
        self.m00 = (x == 0) & (y == 0)
        self.m01 = (x == 0) & (y == 1)
        self.m10 = (x == 1) & (y == 0)
        self.m11 = (x == 1) & (y == 1)
        # Costante rispetto ai parametri, ma la teniamo: il valore della
        # log-verosimiglianza serve per confrontare fit fra loro.
        self.log_factorials = gammaln(x + 1.0) + gammaln(y + 1.0)

    def _rates(self, theta: np.ndarray) -> tuple:
        d = self.data
        attack, defence, home_adv, rho = _unpack(theta, d.n_teams)
        log_lam = attack[d.home_idx] + defence[d.away_idx] + home_adv
        log_mu = attack[d.away_idx] + defence[d.home_idx]
        return attack, defence, home_adv, rho, np.exp(log_lam), np.exp(log_mu)

    def _tau_derivatives(
        self, lam: np.ndarray, mu: np.ndarray, rho: float
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Derivate di tau (non di log tau) rispetto a log(lambda), log(mu), rho.

        Tenerle separate dalla divisione per tau e' cio' che permette di
        trattare correttamente sia il ramo normale sia quello penalizzato.
        """
        prod = lam * mu
        d_loglam = np.zeros_like(lam)
        d_logmu = np.zeros_like(lam)
        d_rho = np.zeros_like(lam)

        d_loglam[self.m00] = -prod[self.m00] * rho
        d_logmu[self.m00] = -prod[self.m00] * rho
        d_rho[self.m00] = -prod[self.m00]

        d_loglam[self.m01] = lam[self.m01] * rho
        d_rho[self.m01] = lam[self.m01]

        d_logmu[self.m10] = mu[self.m10] * rho
        d_rho[self.m10] = mu[self.m10]

        d_rho[self.m11] = -1.0
        return d_loglam, d_logmu, d_rho

    def value_and_gradient(self, theta: np.ndarray) -> tuple[float, np.ndarray]:
        """Valore e gradiente della negative log-likelihood, in una passata.

        La correzione Dixon-Coles puo' rendere tau <= 0 per combinazioni
        estreme di (lambda, mu, rho). In quel caso si usa una **penalita'
        esatta** quadratica, e la sua derivata e' inclusa qui: un gradiente
        che ignorasse la penalita' renderebbe L-BFGS-B incoerente proprio
        nella regione in cui il vincolo morde.
        """
        d = self.data
        n = d.n_teams
        _, _, _, rho, lam, mu = self._rates(theta)

        tau_raw = _tau_terms(lam, mu, rho, self.m00, self.m01, self.m10, self.m11)
        violating = tau_raw < TAU_FLOOR
        tau_eff = np.where(violating, TAU_FLOOR, tau_raw)

        log_terms = d.weights * (
            np.log(tau_eff)
            + d.home_goals * np.log(lam)
            - lam
            + d.away_goals * np.log(mu)
            - mu
            - self.log_factorials
        )
        violation = np.where(violating, TAU_FLOOR - tau_raw, 0.0)
        penalty = TAU_PENALTY * float(np.square(violation).sum())
        value = -float(log_terms.sum()) + penalty

        d_loglam, d_logmu, d_rho = self._tau_derivatives(lam, mu, rho)

        # Ramo normale: d log(tau)/d. = (d tau/d.)/tau.
        # Ramo penalizzato: log(tau_eff) e' costante, resta solo la penalita'.
        safe = ~violating
        log_tau_loglam = np.where(safe, d_loglam / tau_eff, 0.0)
        log_tau_logmu = np.where(safe, d_logmu / tau_eff, 0.0)
        log_tau_rho = np.where(safe, d_rho / tau_eff, 0.0)

        # d(penalita')/d. = 2 * k * violation * (-d tau/d.)
        pen_factor = -2.0 * TAU_PENALTY * violation

        # Gradiente della NLL rispetto a log(lambda) e log(mu).
        g_log_lam = -d.weights * (d.home_goals - lam + log_tau_loglam)
        g_log_lam += pen_factor * d_loglam
        g_log_mu = -d.weights * (d.away_goals - mu + log_tau_logmu)
        g_log_mu += pen_factor * d_logmu

        # Attacco: da casa via lambda, da trasferta via mu.
        g_attack = np.bincount(d.home_idx, g_log_lam, minlength=n) + np.bincount(
            d.away_idx, g_log_mu, minlength=n
        )
        # Difesa: la difesa ospite entra in lambda, quella di casa in mu.
        g_defence = np.bincount(d.away_idx, g_log_lam, minlength=n) + np.bincount(
            d.home_idx, g_log_mu, minlength=n
        )
        g_home_adv = float(g_log_lam.sum())
        g_rho = float((-d.weights * log_tau_rho + pen_factor * d_rho).sum())

        # Catena del vincolo: attacco[n-1] = -somma(liberi).
        g_free_attack = g_attack[: n - 1] - g_attack[n - 1]
        grad = np.concatenate([g_free_attack, g_defence, [g_home_adv], [g_rho]])
        return value, grad

    def negative_log_likelihood(self, theta: np.ndarray) -> float:
        return self.value_and_gradient(theta)[0]

    def gradient(self, theta: np.ndarray) -> np.ndarray:
        return self.value_and_gradient(theta)[1]


def fit(
    data: MatchData,
    *,
    start: DCParams | None = None,
    max_iter: int = 500,
) -> tuple[DCParams, dict]:
    """Stima di massima verosimiglianza pesata.

    `start` abilita il **warm start**: ogni rifit bootstrap parte dal fit
    puntuale, a cui e' vicino per costruzione (brief 5.3, gradino 2).
    """
    n = data.n_teams
    like = DixonColesLikelihood(data)

    if start is not None and start.teams == data.teams:
        theta0 = np.concatenate(
            [
                start.attack[: n - 1],
                start.defence,
                [start.home_adv],
                [start.rho],
            ]
        )
    else:
        # Partenza neutra: forze nulle, vantaggio campo e rho tipici.
        mean_goals = float(
            np.average(data.home_goals + data.away_goals, weights=data.weights)
        )
        base = math.log(max(mean_goals, 0.5) / 2.0)
        theta0 = np.concatenate(
            [np.zeros(n - 1), np.full(n, base), [0.25], [-0.05]]
        )

    bounds = [(-3.0, 3.0)] * (n - 1) + [(-3.0, 3.0)] * n
    bounds += [(-1.0, 1.5), (-RHO_BOUND, RHO_BOUND)]

    # jac=True: valore e gradiente in una sola passata numpy.
    result = minimize(
        like.value_and_gradient,
        theta0,
        jac=True,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": max_iter, "ftol": 1e-10, "gtol": 1e-7},
    )

    attack, defence, home_adv, rho = _unpack(result.x, n)
    params = DCParams(
        attack=attack,
        defence=defence,
        home_adv=home_adv,
        rho=rho,
        teams=data.teams,
    )
    info = {
        "converged": bool(result.success),
        "log_likelihood": -float(result.fun),
        "iterations": int(result.nit),
        "function_evaluations": int(result.nfev),
        "message": str(result.message),
    }
    return params, info
