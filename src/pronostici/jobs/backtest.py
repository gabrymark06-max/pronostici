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

---

**Addendum 2026-08-11 — i bracci.** Il job valuta piu' configurazioni nella
**stessa** passata walk-forward, riusando gli stessi 300 draw: il braccio
primario e' quello che va in produzione, gli altri servono a mostrare da dove
si viene. Il numero di configurazioni e' scritto in `configurations_tried` e
nel protocollo, come chiede Bailey et al.

Sempre da questo addendum, il job misura il log loss **per famiglia** contro il
base rate su due quantita' diverse:

* `p_hat`, la stima grezza — e' quello che il backtest del 2026-08-08 misurava
  su Over 2.5, ed e' un numero che il prodotto non mostra e non usa;
* `p_tilde`, la stima dopo lo shrinkage — e' quella con cui il sistema
  **decide** e che l'utente vede.

Misurare solo la prima e concludere sul sistema era un errore di attribuzione:
lo shrinkage esiste apposta per correggere una dispersione troppo larga.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import numpy as np

from ..archive import Match, load_all
from ..competitions import ACTIVE_CODES
from ..config import DATA, ROOT
from ..model import markets as mk
from ..model.baserates import compute_base_rates
from ..model.bootstrap import DEFAULT_DRAWS, run_bootstrap
from ..model.dataset import build_dataset
from ..model.selection import (
    NON_SELECTABLE_FAMILIES,
    P_MIN,
    RHO_MAX,
    S_MIN,
    SIGMA_MAX,
    TAU_DEFAULT,
)
from ..model.tau import load_tau_by_family
from ..pipeline import score_fixture
from ..storage import SCHEMA_VERSION, write_json
from .settle import BUCKETS, bucket_of, realized_skill

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


@dataclass(frozen=True)
class ArmSpec:
    """Una configurazione valutata in questa passata.

    `excluded_families` non e' un filtro di comodo: e' il rimedio previsto dal
    protocollo 4.2 e 5 quando una famiglia non porta informazione. Si restringe
    lo scope, non si abbassa il criterio.
    """

    name: str
    tau: float | dict[str, float]
    excluded_families: frozenset[str] = NON_SELECTABLE_FAMILIES
    note: str = ""

    def describe(self) -> dict:
        return {
            "name": self.name,
            "tau": (
                self.tau
                if isinstance(self.tau, float)
                else dict(sorted(self.tau.items()))
            ),
            "excluded_families": sorted(self.excluded_families),
            "note": self.note,
        }


class FamilyLosses:
    """Log loss per famiglia contro il base rate, su grezza e su shrinkata.

    Le due colonne rispondono a due domande diverse, e confonderle e' il difetto
    che questo addendum corregge: `p_hat` dice se il **modello** ha risoluzione,
    `p_tilde` dice se il **sistema** — modello piu' shrinkage — batte il base
    rate. La seconda e' quella che decide se una famiglia puo' restare fra i
    candidati.
    """

    def __init__(self) -> None:
        self.n: dict[str, int] = defaultdict(int)
        self.raw: dict[str, float] = defaultdict(float)
        self.shrunk: dict[str, float] = defaultdict(float)
        self.base: dict[str, float] = defaultdict(float)
        # Differenza appaiata shrinkata-base, per l'errore standard.
        self.diff2: dict[str, float] = defaultdict(float)

    def add(self, family: str, p_hat: float, p_tilde: float, ref: float, y: int) -> None:
        lm = _log_loss(p_hat, y)
        ls = _log_loss(p_tilde, y)
        lb = _log_loss(ref, y)
        self.n[family] += 1
        self.raw[family] += lm
        self.shrunk[family] += ls
        self.base[family] += lb
        self.diff2[family] += (ls - lb) ** 2

    def payload(self) -> dict:
        out: dict[str, dict] = {}
        for family, n in sorted(self.n.items()):
            raw = self.raw[family] / n
            shrunk = self.shrunk[family] / n
            base = self.base[family] / n
            delta = shrunk - base
            var = max(self.diff2[family] / n - delta * delta, 0.0)
            se = (var / n) ** 0.5 if n > 1 else None
            out[family] = {
                "n": n,
                "p_hat": round(raw, 5),
                "p_tilde": round(shrunk, 5),
                "base_rate": round(base, 5),
                "delta_shrunk": round(delta, 5),
                "delta_shrunk_se": round(se, 5) if se else None,
                "shrunk_better": bool(delta < 0),
                "raw_better": bool(raw < base),
            }
        return out


@dataclass
class ArmStats:
    """Gli accumulatori di un braccio: uno solo va nel corpo del rapporto."""

    spec: ArmSpec
    picks: list[dict] = field(default_factory=list)
    max_safe_scores: list[float] = field(default_factory=list)
    filter_bites: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    silence_reasons: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    per_competition: dict[str, dict] = field(
        default_factory=lambda: defaultdict(
            lambda: {"evaluated": 0, "with_prediction": 0, "hits": 0}
        )
    )
    families: FamilyLosses = field(default_factory=FamilyLosses)

    def observe(self, code: str, match: Match, scored, outcomes: dict[str, int]) -> None:
        self.per_competition[code]["evaluated"] += 1
        selection = scored.selection

        safe_scores = [0.0]
        for candidate in scored.all_candidates:
            y = outcomes.get(candidate.key)
            if y is not None:
                self.families.add(
                    candidate.family,
                    candidate.p_hat,
                    candidate.p_tilde,
                    candidate.reference,
                    y,
                )
            if (
                candidate.selectable
                and candidate.passes_p_min
                and candidate.passes_sigma_max
            ):
                safe_scores.append(candidate.score)
        self.max_safe_scores.append(max(safe_scores))

        for name, count in selection.filter_bites.items():
            self.filter_bites[name] += count

        if selection.is_silent:
            self.silence_reasons[selection.silence_reason or "?"] += 1
            return

        pick = selection.pick
        outcome = outcomes.get(pick.key)
        if outcome is None:
            return
        self.per_competition[code]["with_prediction"] += 1
        self.per_competition[code]["hits"] += outcome
        self.picks.append(
            {
                "competition": code,
                "utc_date": match.utc_date,
                "market_key": pick.key,
                "family": pick.family,
                "p": pick.p_tilde,
                "sigma": pick.sigma,
                "reference": pick.reference,
                "declared": pick.score,
                "realized": realized_skill(pick.p_tilde, pick.reference, outcome),
                "outcome": outcome,
            }
        )

    def summary(self) -> dict:
        """Il riassunto di un braccio non primario: silenzio e calibrazione."""
        curve = silence_curve(self.max_safe_scores)
        at_code = (
            round(
                sum(1 for s in self.max_safe_scores if s < S_MIN)
                / len(self.max_safe_scores),
                4,
            )
            if self.max_safe_scores
            else None
        )
        return {
            **self.spec.describe(),
            "with_prediction": len(self.picks),
            "silence_rate_at_s_min_in_code": at_code,
            "silence_by_reason": dict(sorted(self.silence_reasons.items())),
            "skill": skill_summary(self.picks),
            "skill_by_family": skill_by_family(self.picks),
            "buckets": bucket_summary(self.picks),
            "filter_bites": dict(sorted(self.filter_bites.items())),
            "log_loss_by_family": self.families.payload(),
            "silence_curve_head": curve[:10],
        }


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
    tau: float | dict[str, float] | None = None,
    min_train_matches: int = MIN_TRAIN_MATCHES,
    excluded_families: frozenset[str] | None = None,
    comparison_arms: list[ArmSpec] | None = None,
) -> dict:
    """Il walk-forward. `tau=None` significa "quello misurato dal backtest".

    I `tau` per famiglia si leggono da `data/backtest.json`, cioe' dal file che
    questo job riscrive. Non e' un cerchio: `tau^2` si stima da `p_hat`, `sigma`
    e base rate, che **non dipendono** dal `tau` in ingresso. Il valore e' un
    punto fisso, e rieseguire il job lo lascia dov'e'.
    """
    started = time.monotonic()
    codes = list(competitions or ACTIVE_CODES)
    step = timedelta(days=step_days)

    tau_value, tau_origin = (
        load_tau_by_family() if tau is None else (tau, {"source": "explicit"})
    )
    primary = ArmSpec(
        name="primary",
        tau=tau_value,
        excluded_families=(
            NON_SELECTABLE_FAMILIES if excluded_families is None else excluded_families
        ),
        note="la configurazione che va in produzione",
    )
    arms = [ArmStats(primary)] + [ArmStats(a) for a in (comparison_arms or [])]

    archives = {c: load_all(c) for c in codes}
    archives = {c: m for c, m in archives.items() if m}
    if not archives:
        raise SystemExit("nessun archivio: esegui prima `ingest`")

    # Una sola griglia per tutti: cosi' i base rate si calcolano una volta per
    # data invece che una volta per campionato.
    all_matches = [m for ms in archives.values() for m in ms]
    grid = _weeks(all_matches, step)

    # --- accumulatori -------------------------------------------------------
    # `tau^2` non dipende dal braccio: si stima su `p_hat` e `sigma`, che sono
    # gli stessi per tutti. Si accumula una volta sola, dal braccio primario.
    tau_by_family: dict[str, Accumulator] = defaultdict(Accumulator)
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
                outcomes = mk.outcomes(match.ft_home, match.ft_away)
                scored_by_arm = []
                for arm in arms:
                    try:
                        scored = score_fixture(
                            match,
                            boot,
                            base_rates[code],
                            tau=arm.spec.tau,
                            model_weight=1.0,
                            excluded_families=arm.spec.excluded_families,
                            # I candidati esclusi restano nella lista, marcati:
                            # e' cosi' che una famiglia esclusa continua a farsi
                            # misurare invece di sparire dal rapporto.
                            include_unselectable=True,
                        )
                    except KeyError:
                        scored_by_arm = []
                        break
                    scored_by_arm.append((arm, scored))
                if not scored_by_arm:
                    skipped += 1
                    continue

                evaluated += 1
                for arm, scored in scored_by_arm:
                    arm.observe(code, match, scored, outcomes)

                # tau^2 per famiglia: su TUTTI i candidati, non solo il
                # vincitore. E' la dispersione a priori della famiglia.
                for candidate in scored_by_arm[0][1].all_candidates:
                    tau_by_family[candidate.family].add(
                        candidate.p_hat, candidate.sigma, candidate.reference
                    )

                # Log loss su Over 2.5: un mercato sempre definito, che si puo'
                # confrontare con la sua baseline su ogni partita. E' il primo
                # numero negativo che il progetto abbia pubblicato, e resta qui
                # nella stessa forma perche' i due backtest siano confrontabili.
                p_model = scored_by_arm[0][1].market_probabilities.get("over_2.5")
                b_ref = base_rates[code].get("over_2.5")
                if p_model is not None and b_ref is not None:
                    y = outcomes["over_2.5"]
                    loss_model.append(_log_loss(p_model, y))
                    loss_base.append(_log_loss(b_ref, y))

        log.info(
            "%s: %d partite valutate, %d pronostici",
            day.date(),
            evaluated,
            len(arms[0].picks),
        )

    head = arms[0]
    picks = head.picks
    curve = silence_curve(head.max_safe_scores)
    chosen, reason = choose_s_min(curve)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "protocol": "docs/protocollo-backtest.md",
        "code_commit": code_commit(),
        # Il numero centrale del paper di Bailey et al.: senza, il backtest
        # non e' interpretabile.
        "configurations_tried": len(arms),
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
            "tau": (
                tau_value
                if isinstance(tau_value, float)
                else dict(sorted(tau_value.items()))
            ),
            "tau_origin": tau_origin,
            "excluded_families": sorted(primary.excluded_families),
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
                sum(1 for s in head.max_safe_scores if s < S_MIN)
                / len(head.max_safe_scores),
                4,
            )
            if head.max_safe_scores
            else None,
        },
        "silence": {
            "curve": curve,
            "target": TARGET_SILENCE,
            "band": list(SILENCE_BAND),
            "chosen_s_min": chosen,
            "decision": reason,
            "by_reason": dict(sorted(head.silence_reasons.items())),
        },
        "skill": skill_summary(picks),
        "skill_by_family": skill_by_family(picks),
        "log_loss_over_2_5": {
            "model": round(float(np.mean(loss_model)), 5) if loss_model else None,
            "base_rate": round(float(np.mean(loss_base)), 5) if loss_base else None,
            "n": len(loss_model),
            "model_better": (
                bool(np.mean(loss_model) < np.mean(loss_base)) if loss_model else None
            ),
        },
        "log_loss_by_family": head.families.payload(),
        "buckets": bucket_summary(picks),
        "filter_bites": dict(sorted(head.filter_bites.items())),
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
            for code, stats in sorted(head.per_competition.items())
        },
        "arms_compared": [arm.summary() for arm in arms[1:]],
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


def skill_by_family(picks: list[dict]) -> dict:
    """Dichiarato contro realizzato, **per famiglia del pronostico scelto**.

    E' la prova che decide se una famiglia merita di restare fra i candidati, e
    non coincide col log loss di famiglia: il log loss misura tutti i mercati
    della famiglia, questo misura **quelli che abbiamo davvero consigliato**.
    La differenza e' la maledizione dell'ottimizzatore: una famiglia senza
    risoluzione ha log loss identico al base rate (lo shrinkage la neutralizza)
    ma continua a vincere l'argmax quando il rumore la spinge in alto, e li'
    consegna meno di quello che aveva promesso.
    """
    by_family: dict[str, list[dict]] = defaultdict(list)
    for pick in picks:
        by_family[pick["family"]].append(pick)
    return {
        family: skill_summary(rows) for family, rows in sorted(by_family.items())
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
    parser.add_argument(
        "--tau",
        type=float,
        default=None,
        help="tau unico per tutte le famiglie; senza, si usa quello misurato",
    )
    parser.add_argument("--min-train", type=int, default=MIN_TRAIN_MATCHES)
    parser.add_argument(
        "--exclude-families",
        nargs="*",
        default=None,
        help=(
            "famiglie che non concorrono alla scelta (restano calcolate e "
            f"mostrate). Senza, quelle di produzione: "
            f"{sorted(NON_SELECTABLE_FAMILIES)}"
        ),
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help=(
            "aggiunge i bracci di confronto: la configurazione precedente "
            f"(tau = {TAU_DEFAULT}, nessuna esclusione), la stessa con i tau "
            "misurati, e quella con tutte le famiglie dei soli gol totali fuori"
        ),
    )
    parser.add_argument("--out", default=str(BACKTEST_FILE))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    measured, _ = load_tau_by_family()
    comparison = (
        [
            ArmSpec(
                name="legacy_tau_0.08",
                tau=TAU_DEFAULT,
                excluded_families=frozenset(),
                note=(
                    "la configurazione del backtest 2026-08-08: tau unico per "
                    "tutte le famiglie e nessuna esclusione"
                ),
            ),
            ArmSpec(
                name="tau_misurati_senza_esclusioni",
                tau=measured,
                excluded_families=frozenset(),
                note="isola l'effetto dei soli tau per famiglia",
            ),
            ArmSpec(
                name="fuori_tutti_i_totali",
                tau=measured,
                excluded_families=frozenset({"over_under", "multigoal", "btts"}),
                note=(
                    "le tre famiglie che dipendono dai soli gol totali: serve a "
                    "sapere cosa costerebbe togliere anche le altre due"
                ),
            ),
        ]
        if args.compare
        else []
    )
    payload = run(
        args.competitions,
        step_days=args.step_days,
        draws=args.draws,
        tau=args.tau,
        min_train_matches=args.min_train,
        excluded_families=(
            None if args.exclude_families is None else frozenset(args.exclude_families)
        ),
        comparison_arms=comparison,
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
    summary["log_loss_by_family"] = payload["log_loss_by_family"]
    summary["skill_by_family"] = payload["skill_by_family"]
    summary["per_competition"] = payload["per_competition"]
    summary["arms_compared"] = [
        {k: v for k, v in arm.items() if k not in ("silence_curve_head", "tau")}
        for arm in payload["arms_compared"]
    ]
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
