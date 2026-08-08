"""Backtest walk-forward, secondo `docs/protocollo-backtest.md`.

    python -m pronostici.jobs.backtest

Il protocollo e' stato scritto e datato **prima** di questa esecuzione, e
dichiara una sola configurazione provata. Qui non si cerca niente: si misura
il sistema con i parametri congelati e si **legge** dalla curva il valore di
`S_min` che porta al tasso di silenzio obiettivo.

Due proprieta' che rendono il numero interpretabile:

* si chiama `pipeline.score_fixture`, cioe' **lo stesso codice** che gira in
  produzione. Un backtest che misura un'altra pipeline non misura niente;
* il taglio temporale e' stretto (`<`, non `<=`) sia sul fit sia sui base
  rate, che sono a loro volta parametri stimati. Usare la frequenza
  dell'intero dataset sarebbe look-ahead mascherato.

Cosa **non** misura: il ramo con le quote (`w = 0,35`). Le quote storiche non
esistono nel nostro archivio e con 500 crediti al mese non possono esistere.
E' una limitazione dichiarata, non aggirata.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import numpy as np

from ..archive import Match, load_all
from ..competitions import ACTIVE_CODES
from ..config import DATA, ROOT
from ..model.baserates import compute_base_rates
from ..model.bootstrap import DEFAULT_DRAWS, run_bootstrap
from ..model.dataset import build_dataset
from ..model.selection import P_MIN, RHO_MAX, S_MIN, SIGMA_MAX, TAU_DEFAULT
from ..pipeline import score_fixture
from ..storage import SCHEMA_VERSION, write_json
from .settle import BUCKETS, bucket_of, outcome_of, realized_skill

log = logging.getLogger("backtest")

BACKTEST_FILE = DATA / "backtest.json"

# Protocollo 2.4: sotto questa soglia il campionato, in produzione, non
# avrebbe avuto un modello — quindi non si valuta e non si conta.
MIN_TRAIN_MATCHES = 200
STEP_DAYS = 7
HALF_LIFE_DAYS = 365.0
WINDOW_DAYS = 730.0

# Protocollo 4: la griglia su cui si legge S_min, e il bersaglio.
S_MIN_GRID = tuple(round(0.001 * i, 3) for i in range(1, 51))
TARGET_SILENCE = 0.25
SILENCE_BAND = (0.15, 0.30)

EPS = 1e-9


def code_commit() -> str | None:
    """L'hash del commit che ha prodotto questi numeri (protocollo 8)."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


class Accumulator:
    """Somme incrementali: 300k candidati non hanno bisogno di stare in RAM."""

    def __init__(self) -> None:
        self.n = 0
        self.sum_dev = 0.0  # somma di (p_hat - b)
        self.sum_dev2 = 0.0  # somma di (p_hat - b)^2
        self.sum_var = 0.0  # somma di sigma^2

    def add(self, p_hat: float, sigma: float, reference: float) -> None:
        dev = p_hat - reference
        self.n += 1
        self.sum_dev += dev
        self.sum_dev2 += dev * dev
        self.sum_var += sigma * sigma

    def tau2(self) -> float:
        """Metodo dei momenti: `max(0, Var(p_hat - b) - media(sigma^2))`.

        La dispersione delle nostre previsioni attorno al base rate che
        **eccede** il rumore di stima e' l'unico segnale dimostrabile. Se e'
        zero, la famiglia non ha risoluzione e deve uscire (protocollo 5).
        """
        if self.n < 2:
            return 0.0
        mean = self.sum_dev / self.n
        var = (self.sum_dev2 - self.n * mean * mean) / (self.n - 1)
        return max(0.0, var - self.sum_var / self.n)


def _weeks(matches: list[Match], step: timedelta) -> list[datetime]:
    """Le date di rifit: una ogni `step`, dalla prima all'ultima partita."""
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


def run(
    competitions: list[str] | None = None,
    *,
    step_days: int = STEP_DAYS,
    draws: int = DEFAULT_DRAWS,
    tau: float = TAU_DEFAULT,
    min_train_matches: int = MIN_TRAIN_MATCHES,
) -> dict:
    started = time.monotonic()
    codes = list(competitions or ACTIVE_CODES)
    step = timedelta(days=step_days)

    archives = {c: load_all(c) for c in codes}
    archives = {c: m for c, m in archives.items() if m}
    if not archives:
        raise SystemExit("nessun archivio: esegui prima `ingest`")

    # Una sola griglia per tutti: cosi' i base rate si calcolano una volta per
    # data invece che una volta per campionato.
    all_matches = [m for ms in archives.values() for m in ms]
    grid = _weeks(all_matches, step)

    # --- accumulatori -------------------------------------------------------
    picks: list[dict] = []  # una riga per partita con pronostico
    max_safe_scores: list[float] = []  # per la curva del silenzio
    tau_by_family: dict[str, Accumulator] = defaultdict(Accumulator)
    filter_bites: dict[str, int] = defaultdict(int)
    silence_reasons: dict[str, int] = defaultdict(int)
    per_competition: dict[str, dict] = defaultdict(
        lambda: {"evaluated": 0, "with_prediction": 0, "hits": 0}
    )
    loss_model: list[float] = []
    loss_base: list[float] = []
    evaluated = skipped = refits = 0

    for day in grid:
        window_end = day + step
        blocks = {
            code: [m for m in ms if m.is_finished and day <= m.date < window_end]
            for code, ms in archives.items()
        }
        blocks = {c: b for c, b in blocks.items() if b}
        if not blocks:
            continue

        # I base rate sono parametri stimati: solo passato, per campionato,
        # accorciati verso la media multi-campionato (protocollo 2.3).
        try:
            base_rates = compute_base_rates(archives, as_of=day)
        except ValueError:
            continue

        for code, block in sorted(blocks.items()):
            try:
                data = build_dataset(
                    archives[code],
                    as_of=day,
                    half_life_days=HALF_LIFE_DAYS,
                    window_days=WINDOW_DAYS,
                )
            except ValueError:
                skipped += len(block)
                continue
            if data.n_matches < min_train_matches:
                skipped += len(block)
                continue

            boot = run_bootstrap(data, draws=draws)
            refits += 1

            for match in block:
                try:
                    scored = score_fixture(
                        match, boot, base_rates[code], tau=tau, model_weight=1.0
                    )
                except KeyError:
                    skipped += 1
                    continue

                evaluated += 1
                per_competition[code]["evaluated"] += 1
                selection = scored.selection

                # tau^2 per famiglia: su TUTTI i candidati, non solo il
                # vincitore. E' la dispersione a priori della famiglia.
                safe_scores = [0.0]
                for candidate in scored.all_candidates:
                    tau_by_family[candidate.family].add(
                        candidate.p_hat, candidate.sigma, candidate.reference
                    )
                    if candidate.passes_p_min and candidate.passes_sigma_max:
                        safe_scores.append(candidate.score)
                max_safe_scores.append(max(safe_scores))

                for name, count in selection.filter_bites.items():
                    filter_bites[name] += count

                # Log loss su Over 2.5: un mercato sempre definito, che si puo'
                # confrontare con la sua baseline su ogni partita.
                p_model = scored.market_probabilities.get("over_2.5")
                b_ref = base_rates[code].get("over_2.5")
                if p_model is not None and b_ref is not None:
                    y = outcome_of("over_2.5", match.ft_home, match.ft_away)
                    loss_model.append(_log_loss(p_model, y))
                    loss_base.append(_log_loss(b_ref, y))

                if selection.is_silent:
                    silence_reasons[selection.silence_reason or "?"] += 1
                    continue

                pick = selection.pick
                outcome = outcome_of(pick.key, match.ft_home, match.ft_away)
                if outcome is None:
                    continue
                per_competition[code]["with_prediction"] += 1
                per_competition[code]["hits"] += outcome
                picks.append(
                    {
                        "competition": code,
                        "utc_date": match.utc_date,
                        "market_key": pick.key,
                        "family": pick.family,
                        "p": pick.p_tilde,
                        "sigma": pick.sigma,
                        "reference": pick.reference,
                        "declared": pick.score,
                        "realized": realized_skill(
                            pick.p_tilde, pick.reference, outcome
                        ),
                        "outcome": outcome,
                    }
                )

        log.info(
            "%s: %d partite valutate, %d pronostici", day.date(), evaluated, len(picks)
        )

    curve = silence_curve(max_safe_scores)
    chosen, reason = choose_s_min(curve)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": "docs/protocollo-backtest.md",
        "code_commit": code_commit(),
        # Il numero centrale del paper di Bailey et al.: senza, il backtest
        # non e' interpretabile.
        "configurations_tried": 1,
        "measures": "solo il pronostico preliminare, w = 1,0",
        "not_measured": (
            "il ramo con le quote (w = 0,35): le quote storiche non esistono "
            "nel nostro archivio e con 500 crediti al mese non possono esistere"
        ),
        "parameters": {
            "half_life_days": HALF_LIFE_DAYS,
            "window_days": WINDOW_DAYS,
            "draws": draws,
            "model_weight": 1.0,
            "tau": tau,
            "p_min": P_MIN,
            "sigma_max": SIGMA_MAX,
            "rho_max": RHO_MAX,
            "s_min_in_code": S_MIN,
            "step_days": step_days,
            "min_train_matches": min_train_matches,
        },
        "window": {
            "from": min(p["utc_date"] for p in picks)[:10] if picks else None,
            "to": max(p["utc_date"] for p in picks)[:10] if picks else None,
        },
        "volume": {
            "refits": refits,
            "evaluated": evaluated,
            "with_prediction": len(picks),
            "skipped_warmup_or_unknown_team": skipped,
            "silence_rate_at_s_min_in_code": round(
                sum(1 for s in max_safe_scores if s < S_MIN) / len(max_safe_scores), 4
            )
            if max_safe_scores
            else None,
        },
        "silence": {
            "curve": curve,
            "target": TARGET_SILENCE,
            "band": list(SILENCE_BAND),
            "chosen_s_min": chosen,
            "decision": reason,
            "by_reason": dict(sorted(silence_reasons.items())),
        },
        "skill": skill_summary(picks),
        "log_loss_over_2_5": {
            "model": round(float(np.mean(loss_model)), 5) if loss_model else None,
            "base_rate": round(float(np.mean(loss_base)), 5) if loss_base else None,
            "n": len(loss_model),
            "model_better": (
                bool(np.mean(loss_model) < np.mean(loss_base)) if loss_model else None
            ),
        },
        "buckets": bucket_summary(picks),
        "filter_bites": dict(sorted(filter_bites.items())),
        "tau2_by_family": {
            family: {
                "tau2": round(acc.tau2(), 6),
                "tau": round(acc.tau2() ** 0.5, 4),
                "n": acc.n,
                "has_resolution": acc.tau2() > 0.0,
            }
            for family, acc in sorted(tau_by_family.items())
        },
        "per_competition": {
            code: {
                **stats,
                "silence_rate": round(
                    1 - stats["with_prediction"] / stats["evaluated"], 4
                )
                if stats["evaluated"]
                else None,
                "hit_rate": round(stats["hits"] / stats["with_prediction"], 4)
                if stats["with_prediction"]
                else None,
            }
            for code, stats in sorted(per_competition.items())
        },
        "seconds": round(time.monotonic() - started, 1),
    }
    return payload


def _log_loss(p: float, y: int) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return -(np.log(p) if y else np.log(1 - p))


def silence_curve(max_safe_scores: list[float]) -> list[dict]:
    """Tasso di silenzio in funzione di `S_min`. E' una lettura, non una
    ricerca: una partita tace se nessun candidato sicuro supera la soglia."""
    if not max_safe_scores:
        return []
    values = np.asarray(max_safe_scores)
    return [
        {"s_min": s, "silence_rate": round(float((values < s).mean()), 4)}
        for s in S_MIN_GRID
    ]


def choose_s_min(curve: list[dict]) -> tuple[float, str]:
    """La regola del protocollo 4, applicata senza deroghe."""
    if not curve:
        return S_MIN, "nessun dato: S_min resta al valore iniziale"
    in_band = [
        p for p in curve if SILENCE_BAND[0] <= p["silence_rate"] <= SILENCE_BAND[1]
    ]
    if not in_band:
        return S_MIN, (
            "l'intera curva e' fuori dalla banda 15-30%: per il protocollo 4.2 "
            "S_min non si muove, si restringe lo scope"
        )
    best = min(in_band, key=lambda p: abs(p["silence_rate"] - TARGET_SILENCE))
    return best["s_min"], (
        f"tasso di silenzio {best['silence_rate']:.1%}, il piu' vicino al "
        f"{TARGET_SILENCE:.0%} sulla griglia dichiarata"
    )


def skill_summary(picks: list[dict]) -> dict:
    """Dichiarato contro realizzato: la metrica di testa (ricerca 10.1)."""
    if not picks:
        return {"n": 0}
    declared = np.array([p["declared"] for p in picks])
    realized = np.array([p["realized"] for p in picks])
    n = len(picks)
    se = float(realized.std(ddof=1) / np.sqrt(n)) if n > 1 else None
    gap = float(declared.mean() - realized.mean())
    return {
        "n": n,
        "declared_mean": round(float(declared.mean()), 5),
        "realized_mean": round(float(realized.mean()), 5),
        "realized_se": round(se, 5) if se else None,
        "gap": round(gap, 5),
        # Quante deviazioni standard separa il dichiarato dal realizzato: e'
        # la diagnosi diretta della sovraconfidenza.
        "gap_in_se": round(gap / se, 2) if se else None,
        "hit_rate": round(float(np.mean([p["outcome"] for p in picks])), 4),
        "mean_p": round(float(np.mean([p["p"] for p in picks])), 4),
    }


def bucket_summary(picks: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for lo, hi in BUCKETS:
        name = f"{lo:.2f}-{min(hi, 1.0):.2f}"
        out[name] = {"n": 0, "hits": 0, "p_sum": 0.0}
    for pick in picks:
        name = bucket_of(pick["p"])
        if name is None:
            continue
        out[name]["n"] += 1
        out[name]["hits"] += pick["outcome"]
        out[name]["p_sum"] += pick["p"]
    for entry in out.values():
        entry["hit_rate"] = round(entry["hits"] / entry["n"], 4) if entry["n"] else None
        entry["mean_p"] = round(entry["p_sum"] / entry["n"], 4) if entry["n"] else None
        entry["enough"] = entry["n"] >= 30
        entry.pop("p_sum")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competitions", nargs="*", default=list(ACTIVE_CODES))
    parser.add_argument("--step-days", type=int, default=STEP_DAYS)
    parser.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    parser.add_argument("--tau", type=float, default=TAU_DEFAULT)
    parser.add_argument("--min-train", type=int, default=MIN_TRAIN_MATCHES)
    parser.add_argument("--out", default=str(BACKTEST_FILE))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    payload = run(
        args.competitions,
        step_days=args.step_days,
        draws=args.draws,
        tau=args.tau,
        min_train_matches=args.min_train,
    )
    from pathlib import Path

    write_json(Path(args.out), payload, indent=1)
    summary = {
        k: payload[k]
        for k in ("volume", "skill", "log_loss_over_2_5", "buckets", "filter_bites")
    }
    summary["silence"] = {
        k: v for k, v in payload["silence"].items() if k != "curve"
    }
    summary["tau2_by_family"] = payload["tau2_by_family"]
    summary["per_competition"] = payload["per_competition"]
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
