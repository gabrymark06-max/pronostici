"""Indagine sull'emivita del decadimento (protocollo, addendum 2026-08-11).

    python -m pronostici.jobs.halflife

**Perche' esiste.** `data/backtest.json` riporta, su 4.995 partite, log loss
0,69919 per il modello contro 0,68856 del base rate su Over 2.5: la stima
per-partita dei gol totali **non aggiunge informazione**. L'emivita di 365
giorni non e' mai stata verificata sui nostri dati — e' ereditata da fonti
secondarie su Dixon-Coles 1997 ed e' dichiarata *non verificata* nella ricerca
(12). Qui si misura, con lo stesso protocollo walk-forward, su una griglia
dichiarata **prima** di guardare i numeri.

**Cosa si prova, e quante configurazioni sono.** Sette, contate e scritte nel
protocollo perche' il backtest resti interpretabile (Bailey et al. 2014,
ricerca 7.2):

1-5. emivita 120 / 180 / 270 / 365 / 540 giorni;
6. a 365 giorni, la correzione Dixon-Coles spenta (`rho = 0`): verifica
   l'ipotesi che una correzione sui soli punteggi bassi non basti per la coda
   dei gol totali;
7. a 365 giorni, `max_goals = 18` invece di 12: verifica l'ipotesi che il
   troncamento sposti massa.

**Nessuna di queste corse puo' spostare `S_min`.** La soglia e' stata letta una
volta sola, dal backtest pre-registrato, e resta dov'e' (protocollo 4.3). Qui
si risponde a una domanda diagnostica, non si cerca una configurazione bella.

**Cosa cambia rispetto al backtest, e perche' e' lecito.** Qui non si fa il
bootstrap: la quantita' misurata e' `p_hat`, e nel backtest `p_hat` e' la media
dei 300 draw, che differisce dal valore nel punto stimato solo per la curvatura
(Jensen). Il job misura entrambe le cose a 365 giorni e riporta lo scarto, cosi'
che il lettore veda quanto vale l'approssimazione invece di doverla credere.
Senza questa scorciatoia la griglia costerebbe 2,5 ore invece di due minuti.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from ..archive import Match, load_all
from ..competitions import ACTIVE_CODES
from ..config import DATA
from ..model.baserates import compute_base_rates
from ..model.dataset import build_dataset
from ..model.dixon_coles import DCParams, fit
from ..model.markets import catalog
from ..model.matrix import MAX_GOALS, build_matrix
from ..storage import SCHEMA_VERSION, write_json
from .backtest import MIN_TRAIN_MATCHES, STEP_DAYS, WINDOW_DAYS, code_commit

log = logging.getLogger("halflife")

HALFLIFE_FILE = DATA / "halflife.json"

# La griglia, dichiarata prima di guardare i numeri.
HALF_LIFE_GRID = (120.0, 180.0, 270.0, 365.0, 540.0)
BASELINE_HALF_LIFE = 365.0

# Il mercato di testa: e' quello su cui il backtest ha misurato il fallimento.
HEADLINE_KEY = "over_2.5"

EPS = 1e-9


@dataclass(frozen=True)
class Arm:
    """Una configurazione della griglia. `rho_zero` e `max_goals` esistono per
    isolare le due ipotesi alternative all'emivita."""

    name: str
    half_life: float
    rho_zero: bool = False
    max_goals: int = MAX_GOALS


def default_arms() -> tuple[Arm, ...]:
    arms = [Arm(f"hl_{int(h)}", h) for h in HALF_LIFE_GRID]
    arms.append(Arm("hl_365_rho0", BASELINE_HALF_LIFE, rho_zero=True))
    arms.append(Arm("hl_365_maxgoals18", BASELINE_HALF_LIFE, max_goals=18))
    return tuple(arms)


@lru_cache(maxsize=4)
def _market_index(max_goals: int) -> tuple[tuple[str, ...], tuple[str, ...], np.ndarray]:
    """Chiavi, famiglie e maschere impilate: si costruiscono una volta sola."""
    defs = catalog(max_goals)
    keys = tuple(d.key for d in defs)
    families = tuple(d.family for d in defs)
    stack = np.stack([d.mask.ravel().astype(float) for d in defs])
    return keys, families, stack


def log_loss(p: np.ndarray, y: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


class MarketLosses:
    """Somme incrementali per mercato: modello, base rate e la loro differenza.

    La differenza si accumula anche al quadrato perche' il confronto senza il
    suo errore standard non e' una misura: con 4.995 partite uno scarto di
    0,003 nats e' rumore, uno di 0,010 no, e a occhio non si distinguono.
    """

    def __init__(self, keys: tuple[str, ...]) -> None:
        self.keys = keys
        n = len(keys)
        self.n = 0
        self.sum_model = np.zeros(n)
        self.sum_base = np.zeros(n)
        self.sum_diff2 = np.zeros(n)

    def add(self, p_model: np.ndarray, p_base: np.ndarray, y: np.ndarray) -> None:
        lm = log_loss(p_model, y)
        lb = log_loss(p_base, y)
        diff = lm - lb
        self.n += 1
        self.sum_model += lm
        self.sum_base += lb
        self.sum_diff2 += diff * diff

    def per_key(self) -> dict[str, dict]:
        if not self.n:
            return {}
        mean_model = self.sum_model / self.n
        mean_base = self.sum_base / self.n
        mean_diff = mean_model - mean_base
        var = np.maximum(self.sum_diff2 / self.n - mean_diff**2, 0.0)
        se = np.sqrt(var / self.n) if self.n > 1 else np.zeros_like(var)
        return {
            key: {
                "model": round(float(mean_model[i]), 5),
                "base_rate": round(float(mean_base[i]), 5),
                "delta": round(float(mean_diff[i]), 5),
                "delta_se": round(float(se[i]), 5),
                "model_better": bool(mean_diff[i] < 0),
            }
            for i, key in enumerate(self.keys)
        }

    def per_family(self, families: tuple[str, ...]) -> dict[str, dict]:
        """Media dei mercati della famiglia.

        Attenzione a come si legge: i mercati di una stessa famiglia sono
        misurati sulle **stesse** partite e sono fortemente correlati fra loro,
        quindi qui non si stampa un errore standard di famiglia — sarebbe
        ottimistico. L'errore standard onesto e' quello per singolo mercato.
        """
        if not self.n:
            return {}
        mean_model = self.sum_model / self.n
        mean_base = self.sum_base / self.n
        out: dict[str, dict] = {}
        for family in sorted(set(families)):
            idx = [i for i, f in enumerate(families) if f == family]
            m = float(mean_model[idx].mean())
            b = float(mean_base[idx].mean())
            out[family] = {
                "markets": len(idx),
                "model": round(m, 5),
                "base_rate": round(b, 5),
                "delta": round(m - b, 5),
                "model_better": bool(m < b),
            }
        return out


def platt_refit(p: np.ndarray, y: np.ndarray) -> dict:
    """Ricalibrazione logistica **in-sample** su `logit(p)`: e' una diagnosi.

    Non e' un calibratore da mettere in produzione (in v1 non ce n'e' uno,
    brief 10) e il fatto che sia in-sample e' voluto: da' il **limite
    superiore** di quello che il modello potrebbe fare se lo si ricalibrasse
    perfettamente. Serve a separare due cause che il solo log loss confonde:

    * `b` vicino a 0 -> il modello non ha risoluzione: nessuna calibrazione lo
      salva, e la famiglia deve uscire dalla selezione;
    * `b` vicino a 1 con `a` diverso da 0, oppure log loss ricalibrato ben
      sotto la baseline -> l'informazione c'e' ma e' mal tarata.
    """
    z = np.log(np.clip(p, EPS, 1 - EPS) / np.clip(1 - p, EPS, 1 - EPS))

    def objective(theta: np.ndarray) -> float:
        q = 1.0 / (1.0 + np.exp(-(theta[0] + theta[1] * z)))
        return float(log_loss(q, y).mean())

    result = minimize(objective, np.array([0.0, 1.0]), method="Nelder-Mead")
    a, b = (float(v) for v in result.x)
    q = 1.0 / (1.0 + np.exp(-(a + b * z)))
    return {
        "intercept": round(a, 4),
        "slope": round(b, 4),
        "log_loss_in_sample": round(float(log_loss(q, y).mean()), 5),
        "converged": bool(result.success),
    }


@dataclass
class ArmState:
    arm: Arm
    losses: MarketLosses
    headline_p: list[float] = field(default_factory=list)
    headline_base: list[float] = field(default_factory=list)
    headline_y: list[int] = field(default_factory=list)
    truncated: list[float] = field(default_factory=list)


def _grid_days(matches: list[Match], step: timedelta) -> list[datetime]:
    finished = [m for m in matches if m.is_finished]
    if not finished:
        return []
    start = min(m.date for m in finished).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = max(m.date for m in finished)
    out, current = [], start
    while current <= end:
        out.append(current)
        current += step
    return out


def _score_block(
    state: ArmState,
    params: DCParams,
    block: list[Match],
    base_rates: dict[str, float],
) -> int:
    """Valuta un blocco settimanale con i parametri gia' fittati."""
    arm = state.arm
    keys, _families, stack = _market_index(arm.max_goals)
    base_vec = np.array([base_rates.get(k, np.nan) for k in keys])
    if np.isnan(base_vec).any():
        raise ValueError("base rate mancante per un mercato del catalogo")

    size = arm.max_goals + 1
    headline = keys.index(HEADLINE_KEY)
    evaluated = 0
    for match in block:
        if match.home_name not in params.teams or match.away_name not in params.teams:
            continue
        lam_h, lam_a = params.rates(match.home_name, match.away_name)
        gm = build_matrix(
            lam_h,
            lam_a,
            0.0 if arm.rho_zero else params.rho,
            max_goals=arm.max_goals,
        )
        p_vec = stack @ gm.matrix.ravel()
        x = min(max(int(match.ft_home), 0), arm.max_goals)
        y = min(max(int(match.ft_away), 0), arm.max_goals)
        y_vec = stack[:, x * size + y]

        state.losses.add(p_vec, base_vec, y_vec)
        state.truncated.append(gm.truncated_mass)
        state.headline_p.append(float(p_vec[headline]))
        state.headline_base.append(float(base_vec[headline]))
        state.headline_y.append(int(y_vec[headline]))
        evaluated += 1
    return evaluated


def run(
    competitions: list[str] | None = None,
    *,
    step_days: int = STEP_DAYS,
    min_train_matches: int = MIN_TRAIN_MATCHES,
    arms: tuple[Arm, ...] | None = None,
) -> dict:
    started = time.monotonic()
    arms = arms or default_arms()
    codes = list(competitions or ACTIVE_CODES)
    step = timedelta(days=step_days)

    archives = {c: load_all(c) for c in codes}
    archives = {c: m for c, m in archives.items() if m}
    if not archives:
        raise SystemExit("nessun archivio: esegui prima `ingest`")

    all_matches = [m for ms in archives.values() for m in ms]
    grid = _grid_days(all_matches, step)

    states = {
        arm.name: ArmState(arm, MarketLosses(_market_index(arm.max_goals)[0]))
        for arm in arms
    }
    half_lives = sorted({arm.half_life for arm in arms})
    arms_by_half_life = {h: [a for a in arms if a.half_life == h] for h in half_lives}

    # Warm start per (campionato, emivita): il fit della settimana prima e'
    # vicino a quello di questa. Non cambia l'ottimo, cambia quanto ci si mette.
    warm: dict[tuple[str, float], DCParams] = {}
    fits = evaluated = skipped = 0

    for day in grid:
        window_end = day + step
        blocks = {
            code: [m for m in ms if m.is_finished and day <= m.date < window_end]
            for code, ms in archives.items()
        }
        blocks = {c: b for c, b in blocks.items() if b}
        if not blocks:
            continue
        try:
            base_rates = compute_base_rates(archives, as_of=day)
        except ValueError:
            continue

        for code, block in sorted(blocks.items()):
            for half_life in half_lives:
                try:
                    data = build_dataset(
                        archives[code],
                        as_of=day,
                        half_life_days=half_life,
                        window_days=WINDOW_DAYS,
                    )
                except ValueError:
                    if half_life == BASELINE_HALF_LIFE:
                        skipped += len(block)
                    continue
                if data.n_matches < min_train_matches:
                    if half_life == BASELINE_HALF_LIFE:
                        skipped += len(block)
                    continue

                params, _info = fit(data, start=warm.get((code, half_life)))
                warm[(code, half_life)] = params
                fits += 1
                for arm in arms_by_half_life[half_life]:
                    n = _score_block(states[arm.name], params, block, base_rates[code])
                    if arm.name == f"hl_{int(BASELINE_HALF_LIFE)}":
                        evaluated += n
        log.info("%s: %d fit, %d partite valutate", day.date(), fits, evaluated)

    results = {}
    for name, state in states.items():
        keys, families, _ = _market_index(state.arm.max_goals)
        per_key = state.losses.per_key()
        p = np.asarray(state.headline_p)
        b = np.asarray(state.headline_base)
        y = np.asarray(state.headline_y, dtype=float)
        results[name] = {
            "half_life_days": state.arm.half_life,
            "rho_zero": state.arm.rho_zero,
            "max_goals": state.arm.max_goals,
            "n_matches": state.losses.n,
            "headline": {
                "market": HEADLINE_KEY,
                **per_key.get(HEADLINE_KEY, {}),
                "mean_p_model": round(float(p.mean()), 5) if p.size else None,
                "mean_p_base": round(float(b.mean()), 5) if b.size else None,
                "realized_rate": round(float(y.mean()), 5) if y.size else None,
                "sd_p_model": round(float(p.std(ddof=1)), 5) if p.size > 1 else None,
                "recalibrated": platt_refit(p, y) if p.size > 10 else None,
            },
            "by_family": state.losses.per_family(families),
            "truncated_mass_mean": (
                float(f"{np.mean(state.truncated):.3e}") if state.truncated else None
            ),
        }

    baseline = f"hl_{int(BASELINE_HALF_LIFE)}"
    ranked = sorted(
        (
            n
            for n in results
            if not results[n]["rho_zero"] and results[n]["max_goals"] == MAX_GOALS
        ),
        key=lambda n: results[n]["headline"]["model"],
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": "docs/protocollo-backtest.md (addendum 2026-08-11)",
        "code_commit": code_commit(),
        "configurations_tried": len(arms),
        "measures": (
            "log loss per mercato del solo modello (p_hat nel punto stimato) "
            "contro il base rate del campionato, walk-forward"
        ),
        "not_measured": (
            "il bootstrap: qui il modello e' il fit puntuale. Lo scarto rispetto "
            "alla media dei 300 draw e' riportato in `bootstrap_check`"
        ),
        "parameters": {
            "grid": list(HALF_LIFE_GRID),
            "window_days": WINDOW_DAYS,
            "step_days": step_days,
            "min_train_matches": min_train_matches,
            "max_goals": MAX_GOALS,
        },
        "volume": {"fits": fits, "evaluated_at_baseline": evaluated, "skipped": skipped},
        "bootstrap_check": bootstrap_check(results.get(baseline, {})),
        "arms": results,
        "ranking_by_headline_log_loss": ranked,
        "verdict": _verdict(results, baseline, ranked),
        "seconds": round(time.monotonic() - started, 1),
    }


def bootstrap_check(baseline_arm: dict) -> dict:
    """Quanto costa la scorciatoia: fit puntuale qui, media di 300 draw la'.

    Confronta il braccio a 365 giorni con il numero gia' pubblicato in
    `data/backtest.json`, che e' la stessa quantita' misurata sullo stesso
    protocollo e sulle stesse partite ma con `p_hat` = media dei draw. Se i due
    numeri coincidono a meno di qualche millesimo di nat, la scorciatoia e'
    innocua e la griglia e' confrontabile con il backtest; se divergono, questo
    campo lo dice invece di nasconderlo.
    """
    from ..storage import read_json

    published = read_json(DATA / "backtest.json", default=None)
    if not published or not baseline_arm:
        return {"available": False}
    ref = published.get("log_loss_over_2_5") or {}
    head = baseline_arm.get("headline") or {}
    model = head.get("model")
    base = head.get("base_rate")
    return {
        "available": True,
        "source": "data/backtest.json",
        "backtest_bootstrap_mean": {
            "model": ref.get("model"),
            "base_rate": ref.get("base_rate"),
            "n": ref.get("n"),
        },
        "here_point_fit": {
            "model": model,
            "base_rate": base,
            "n": baseline_arm.get("n_matches"),
        },
        "model_gap": (
            round(model - ref["model"], 5)
            if model is not None and ref.get("model") is not None
            else None
        ),
        "base_rate_gap": (
            round(base - ref["base_rate"], 5)
            if base is not None and ref.get("base_rate") is not None
            else None
        ),
    }


def _verdict(results: dict, baseline: str, ranked: list[str]) -> dict:
    """La lettura, scritta dal codice e non a mano."""
    if not ranked:
        return {}
    best = ranked[0]
    head_best = results[best]["headline"]
    head_base = results[baseline]["headline"]
    beaten = head_best.get("model_better", False)
    return {
        "best_half_life": results[best]["half_life_days"],
        "best_arm": best,
        "baseline_arm": baseline,
        "headline_delta_best": head_best.get("delta"),
        "headline_delta_baseline": head_base.get("delta"),
        "base_rate_beaten_at_best": bool(beaten),
        "reading": (
            "l'emivita migliore batte il base rate su "
            f"{HEADLINE_KEY}: il difetto era la taratura"
            if beaten
            else (
                "nessuna emivita della griglia batte il base rate su "
                f"{HEADLINE_KEY}: la famiglia over/under non ha risoluzione "
                "dimostrabile e deve uscire dalla selezione"
            )
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competitions", nargs="*", default=list(ACTIVE_CODES))
    parser.add_argument("--step-days", type=int, default=STEP_DAYS)
    parser.add_argument("--min-train", type=int, default=MIN_TRAIN_MATCHES)
    parser.add_argument("--out", default=str(HALFLIFE_FILE))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    payload = run(
        args.competitions,
        step_days=args.step_days,
        min_train_matches=args.min_train,
    )
    write_json(Path(args.out), payload, indent=1)
    summary = {
        "volume": payload["volume"],
        "verdict": payload["verdict"],
        "headline": {
            name: arm["headline"] for name, arm in sorted(payload["arms"].items())
        },
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
