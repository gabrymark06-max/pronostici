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
from .model.blend import blend_lambdas, solve_market_lambdas
from .model.bootstrap import BootstrapResult
from .model.matrix import MAX_GOALS, build_matrices
from .model.selection import Selection, build_candidates, select

# Mercati su cui the-odds-api ci da' un riferimento diretto (h2h + totals).
ODDS_BACKED_KEYS = frozenset(
    {"1x2_home", "1x2_draw", "1x2_away"}
    | {f"over_{line}" for line in (0.5, 1.5, 2.5, 3.5, 4.5)}
    | {f"under_{line}" for line in (0.5, 1.5, 2.5, 3.5, 4.5)}
)

# Unioni di esiti 1X2: il mercato le determina **esattamente**, sommando.
UNIONS_OF_1X2 = {
    "dc_1x": ("1x2_home", "1x2_draw"),
    "dc_12": ("1x2_home", "1x2_away"),
    "dc_x2": ("1x2_draw", "1x2_away"),
}


def market_references(
    quoted: dict[str, float], *, max_goals: int = MAX_GOALS
) -> dict[str, float]:
    """Estende le probabilita' quotate a **tutti** i mercati che il mercato
    determina in modo esatto.

    Serve a chiudere un buco che fabbrica vantaggio dal nulla. "Asiatico casa
    -0.5" e "Vittoria casa" sono lo **stesso identico evento**: hanno la stessa
    maschera sulla matrice. Se il primo venisse confrontato col base rate
    storico e il secondo con la quota sgonfiata, l'argmax sceglierebbe
    sistematicamente il riferimento piu' comodo — che e' la maledizione
    dell'ottimizzatore applicata al riferimento invece che alla stima.

    Osservato su Palmeiras-Internacional del 2026-08-09: il punteggio del
    consigliato era 0,058 contro il base rate (0,474) invece che contro il
    mercato, e la scelta cadeva sull'alias.

    L'estensione e' **esatta**, non approssimata: si aggiungono solo le unioni
    di esiti 1X2 (che si sommano) e i mercati la cui maschera coincide con una
    gia' coperta. Tutto il resto resta al base rate, com'e' giusto: il mercato
    non ci dice niente su BTTS o sul multigol stretto.
    """
    references = {k: v for k, v in quoted.items() if k in ODDS_BACKED_KEYS}
    if not references:
        return {}

    for key, parts in UNIONS_OF_1X2.items():
        if all(p in references for p in parts):
            references[key] = sum(references[p] for p in parts)

    # Identita' di maschera: due chiavi diverse per lo stesso evento.
    defs = mk.catalog(max_goals)
    by_mask: dict[bytes, float] = {
        d.mask.tobytes(): references[d.key] for d in defs if d.key in references
    }
    for definition in defs:
        if definition.key in references:
            continue
        value = by_mask.get(definition.mask.tobytes())
        if value is not None:
            references[definition.key] = value
    return references


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
    # Tutti i candidati, non solo i sopravvissuti. Non finiscono ne' nel
    # registro ne' nei file giornalieri: servono al backtest, che stima
    # `tau^2` per famiglia sulla dispersione dell'intero insieme.
    all_candidates: list = field(default_factory=list)


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
            f"Stima prudente: l'incertezza è alta, il valore mostrato è già "
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
            fitted = solve_market_lambdas(
                usable, float(np.median(rho)), max_goals=max_goals
            )
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

    # Riferimento: quota sgonfiata dove il mercato determina l'evento, base
    # rate dove non lo determina. "Dove esiste" include gli alias: vedi
    # `market_references`, che e' cio' che impedisce di leggere due riferimenti
    # diversi per lo stesso identico evento.
    references = dict(base_rates)
    if market_probabilities:
        references.update(
            market_references(market_probabilities, max_goals=max_goals)
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
        - poisson.pmf(goals, lam_home_point).sum()
        * poisson.pmf(goals, lam_away_point).sum()
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
        all_candidates=candidates,
    )
