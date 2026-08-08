"""Frequenze storiche dei mercati: il riferimento quando non ci sono quote.

Il punteggio KL misura quanta informazione portiamo **oltre** un riferimento.
Senza quote quel riferimento e' "chi non sa nulla di questa partita e usa la
frequenza storica del campionato" (ricerca 3.3).

Due trappole, entrambe segnalate dalla ricerca ed entrambe gestite qui:

* **Look-ahead.** Il base rate e' a sua volta un parametro stimato: si calcola
  solo su partite gia' giocate. Usare la frequenza dell'intero dataset e'
  look-ahead mascherato.
* **Base rate rumoroso.** Con 380 partite di una stagione la frequenza ha una
  sd di ~2,5 punti. Si accorcia verso la media multi-campionato con Bayes
  empirico (metodo dei momenti), non con un peso inventato.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from ..archive import Match
from .markets import catalog
from .matrix import MAX_GOALS


def observed_outcomes(
    matches: list[Match], *, max_goals: int = MAX_GOALS
) -> dict[str, np.ndarray]:
    """Per ogni mercato, il vettore 0/1 di quello che e' davvero successo.

    E' la stessa maschera usata per prevedere, applicata al risultato reale:
    previsione e verifica non possono divergere per una svista.
    """
    finished = [m for m in matches if m.is_finished]
    if not finished:
        return {}
    x = np.clip([m.ft_home for m in finished], 0, max_goals)
    y = np.clip([m.ft_away for m in finished], 0, max_goals)
    return {d.key: d.mask[x, y].astype(float) for d in catalog(max_goals)}


def raw_rates(matches: list[Match], *, as_of: datetime | None = None) -> dict:
    """Frequenza grezza per mercato, sulle sole partite concluse prima di `as_of`."""
    past = [m for m in matches if m.is_finished]
    if as_of is not None:
        past = [m for m in past if m.date < as_of]
    outcomes = observed_outcomes(past)
    return {
        "n": len(past),
        "rates": {key: float(vals.mean()) for key, vals in outcomes.items()},
    }


def empirical_bayes_shrink(
    per_competition: dict[str, dict], *, min_n: int = 20
) -> dict[str, dict[str, float]]:
    """Accorcia le frequenze di ogni campionato verso la media multi-campionato.

    Metodo dei momenti: la varianza fra campionati che eccede il rumore
    binomiale e' segnale, il resto e' rumore. `k = p(1-p)/tau_b^2` e' il peso
    a priori in "partite equivalenti"; con tau_b^2 -> 0 si tende al pooling
    completo, che e' la risposta corretta quando i campionati non differiscono.
    """
    codes = [c for c, v in per_competition.items() if v["n"] >= min_n]
    if not codes:
        raise ValueError("nessun campionato con abbastanza partite per il base rate")
    keys = sorted(per_competition[codes[0]]["rates"])

    out: dict[str, dict[str, float]] = {c: {} for c in per_competition}
    for key in keys:
        rates = np.array([per_competition[c]["rates"][key] for c in codes])
        counts = np.array([per_competition[c]["n"] for c in codes], dtype=float)
        grand = float(np.average(rates, weights=counts))

        if len(codes) > 1:
            observed_var = float(np.var(rates, ddof=1))
            noise = float(np.mean(grand * (1 - grand) / counts))
            tau_b2 = max(0.0, observed_var - noise)
        else:
            tau_b2 = 0.0

        if tau_b2 <= 1e-12 or grand <= 0.0 or grand >= 1.0:
            k = 1e6  # pooling completo: i campionati non si distinguono
        else:
            k = grand * (1 - grand) / tau_b2

        for code, values in per_competition.items():
            n = values["n"]
            p = values["rates"].get(key, grand)
            out[code][key] = float((k * grand + n * p) / (k + n))
    return out


def compute_base_rates(
    matches_by_competition: dict[str, list[Match]], *, as_of: datetime | None = None
) -> dict[str, dict[str, float]]:
    """Base rate accorciati, per campionato, solo su passato."""
    raw = {
        code: raw_rates(matches, as_of=as_of)
        for code, matches in matches_by_competition.items()
    }
    raw = {c: v for c, v in raw.items() if v["n"] > 0}
    if not raw:
        raise ValueError("nessuna partita conclusa per calcolare i base rate")
    return empirical_bayes_shrink(raw)
