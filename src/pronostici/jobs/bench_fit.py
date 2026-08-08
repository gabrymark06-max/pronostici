"""Task zero — cronometra un fit Dixon-Coles reale.

    python -m pronostici.jobs.bench_fit --competition SA

Da questo numero dipende il dimensionamento di tutti i job (brief 5.3).
Misura, nell'ordine: un fit a freddo, un fit con warm start, e un bootstrap
completo. Scrive il risultato in `data/benchmark_fit.json` perche' sia
verificabile e non riferito a memoria.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone

import numpy as np
import scipy

from ..archive import load_all
from ..config import DATA
from ..model.dataset import build_dataset
from ..model.dixon_coles import (
    DixonColesLikelihood,
    effective_sample_size,
    fit,
)
from ..storage import write_json


def _time_it(fn, repeats: int) -> tuple[float, float, object]:
    """Ritorna (mediana_s, minimo_s, ultimo_risultato)."""
    times: list[float] = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - start)
    return float(np.median(times)), float(min(times)), result


def run(competition: str, bootstrap: int, repeats: int) -> dict:
    matches = load_all(competition)
    if not matches:
        raise SystemExit(
            f"nessuna partita archiviata per {competition}. "
            f"Esegui prima: python -m pronostici.jobs.ingest --competitions {competition}"
        )
    as_of = datetime.now(timezone.utc)
    data = build_dataset(matches, as_of=as_of)

    n_params = 2 * data.n_teams + 1
    print(
        f"{competition}: {data.n_matches} partite, {data.n_teams} squadre, "
        f"{n_params} parametri liberi"
    )

    # Una singola valutazione di verosimiglianza e del suo gradiente.
    like = DixonColesLikelihood(data)
    theta = np.concatenate([np.zeros(data.n_teams - 1), np.zeros(data.n_teams), [0.25], [-0.05]])
    nll_median, _, _ = _time_it(lambda: like.negative_log_likelihood(theta), 200)
    grad_median, _, _ = _time_it(lambda: like.gradient(theta), 200)

    # Fit a freddo.
    cold_median, cold_min, (params, info) = _time_it(lambda: fit(data), repeats)
    print(
        f"  fit a freddo:      {cold_median * 1000:8.1f} ms  "
        f"(min {cold_min * 1000:.1f} ms, {info['iterations']} iterazioni, "
        f"{info['function_evaluations']} valutazioni)"
    )

    # Fit con warm start: e' cio' che fa ogni rifit del bootstrap.
    warm_median, warm_min, _ = _time_it(lambda: fit(data, start=params), repeats)
    print(f"  fit con warm start:{warm_median * 1000:8.1f} ms  (min {warm_min * 1000:.1f} ms)")

    # Bootstrap parametrico vero, con warm start.
    rng = np.random.default_rng(12345)
    lam = np.exp(
        params.attack[data.home_idx] + params.defence[data.away_idx] + params.home_adv
    )
    mu = np.exp(params.attack[data.away_idx] + params.defence[data.home_idx])

    def one_draw() -> None:
        resampled = data.with_goals(
            rng.poisson(lam).astype(float), rng.poisson(mu).astype(float)
        )
        fit(resampled, start=params)

    start = time.perf_counter()
    for _ in range(bootstrap):
        one_draw()
    boot_seconds = time.perf_counter() - start
    print(
        f"  {bootstrap} bootstrap:    {boot_seconds:8.1f} s   "
        f"({boot_seconds / bootstrap * 1000:.1f} ms per draw)"
    )

    per_league = cold_median + boot_seconds * (300 / bootstrap)
    report = {
        "measured_at": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "competition": competition,
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor() or "sconosciuto",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "dataset": {
            "matches": data.n_matches,
            "teams": data.n_teams,
            "free_parameters": n_params,
            "effective_sample_size_total": round(effective_sample_size(data.weights), 1),
            "effective_matches_per_team": round(
                effective_sample_size(data.weights) * 2 / data.n_teams, 1
            ),
        },
        "timings_seconds": {
            "single_nll_evaluation": round(nll_median, 6),
            "single_gradient_evaluation": round(grad_median, 6),
            "fit_cold_median": round(cold_median, 4),
            "fit_warm_median": round(warm_median, 4),
            "bootstrap_draws_measured": bootstrap,
            "bootstrap_total": round(boot_seconds, 2),
            "bootstrap_per_draw": round(boot_seconds / bootstrap, 4),
        },
        "projection": {
            "one_league_fit_plus_300_bootstrap_s": round(per_league, 1),
            "ten_leagues_s": round(per_league * 10, 1),
            "ten_leagues_minutes": round(per_league * 10 / 60, 1),
            "github_actions_job_limit_minutes": 360,
            "fits_within_limit": per_league * 10 / 60 < 360,
        },
        "fit": info,
        "notes": (
            "Gradiente analitico: senza, ogni passo di L-BFGS-B costerebbe "
            f"{n_params + 1} valutazioni della verosimiglianza invece di una."
        ),
    }
    write_json(DATA / "benchmark_fit.json", report, indent=2)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default="SA")
    parser.add_argument("--bootstrap", type=int, default=300)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args(argv)
    report = run(args.competition, args.bootstrap, args.repeats)
    print()
    print(json.dumps(report["projection"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
