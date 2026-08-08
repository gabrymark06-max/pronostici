"""Gli undici mercati, tutti come maschere sulla stessa matrice.

Un mercato qui e' un **evento binario** descritto da una maschera booleana
sulla griglia (gol_casa, gol_ospite). Da questo discendono gratis due cose:

* la coerenza reciproca (P(Over 2.5) <= P(Over 1.5) non e' un vincolo
  imposto, e' una conseguenza dell'inclusione fra maschere);
* la correlazione **esatta** fra due mercati, che la ricerca (8.4) richiede
  di calcolare dalla matrice invece di stimarla dallo storico.

`selectable=False` marca i mercati che si calcolano e si mostrano ma che non
concorrono alla scelta del consigliato: i mercati del primo tempo, rimandati
finche' `lambda_HT` non e' stimato (brief 10), e le linee asiatiche intere,
che hanno il rimborso e quindi non sono eventi binari.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from .matrix import GoalMatrix, half_time_matrices

OU_LINES = (0.5, 1.5, 2.5, 3.5, 4.5)
ASIAN_LINES_BINARY = (-2.5, -1.5, -0.5, 0.5, 1.5, 2.5)
ASIAN_LINES_PUSH = (-2.0, -1.0, 0.0, 1.0, 2.0)
EU_HANDICAPS = (-2, -1, 1, 2)
MULTIGOAL_RANGES = (
    (0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (1, 4),
    (2, 3), (2, 4), (2, 5), (3, 4), (3, 5), (4, 6),
)


@dataclass(frozen=True)
class MarketDef:
    key: str
    family: str
    label: str
    mask: np.ndarray
    selectable: bool = True


def _grids(size: int) -> tuple[np.ndarray, np.ndarray]:
    home = np.arange(size)[:, None] * np.ones((1, size), dtype=int)
    away = np.ones((size, 1), dtype=int) * np.arange(size)[None, :]
    return home, away


@lru_cache(maxsize=4)
def catalog(max_goals: int) -> tuple[MarketDef, ...]:
    """Costruisce le maschere una volta sola per dimensione di griglia."""
    size = max_goals + 1
    h, a = _grids(size)
    total = h + a
    margin = h - a
    out: list[MarketDef] = []

    # 1 - Esito finale
    out += [
        MarketDef("1x2_home", "1x2", "Vittoria casa", margin > 0),
        MarketDef("1x2_draw", "1x2", "Pareggio", margin == 0),
        MarketDef("1x2_away", "1x2", "Vittoria ospite", margin < 0),
    ]

    # 2 - Doppia chance
    out += [
        MarketDef("dc_1x", "double_chance", "1X (casa o pareggio)", margin >= 0),
        MarketDef("dc_12", "double_chance", "12 (nessun pareggio)", margin != 0),
        MarketDef("dc_x2", "double_chance", "X2 (pareggio o ospite)", margin <= 0),
    ]

    # 3 - Over/Under
    for line in OU_LINES:
        out += [
            MarketDef(f"over_{line}", "over_under", f"Over {line}", total > line),
            MarketDef(f"under_{line}", "over_under", f"Under {line}", total < line),
        ]

    # 4 - Entrambe segnano
    both = (h > 0) & (a > 0)
    out += [
        MarketDef("btts_yes", "btts", "Entrambe segnano", both),
        MarketDef("btts_no", "btts", "Non entrambe segnano", ~both),
    ]

    # 5 - Handicap europeo (tre esiti per linea)
    for hcp in EU_HANDICAPS:
        adjusted = margin + hcp
        sign = "+" if hcp > 0 else ""
        out += [
            MarketDef(
                f"eh_{hcp}_home", "handicap_eu", f"Handicap {sign}{hcp} casa", adjusted > 0
            ),
            MarketDef(
                f"eh_{hcp}_draw", "handicap_eu", f"Handicap {sign}{hcp} pareggio", adjusted == 0
            ),
            MarketDef(
                f"eh_{hcp}_away", "handicap_eu", f"Handicap {sign}{hcp} ospite", adjusted < 0
            ),
        ]

    # 6 - Handicap asiatico, solo linee a mezzo gol: senza rimborso sono
    #     eventi binari veri e possono entrare fra i candidati.
    for line in ASIAN_LINES_BINARY:
        sign = "+" if line > 0 else ""
        out += [
            MarketDef(
                f"ah_home_{line}", "handicap_asian",
                f"Asiatico casa {sign}{line}", margin + line > 0,
            ),
            MarketDef(
                f"ah_away_{line}", "handicap_asian",
                f"Asiatico ospite {sign}{line}", -margin + line > 0,
            ),
        ]

    # 7 - Multigol
    for lo, hi in MULTIGOAL_RANGES:
        out.append(
            MarketDef(
                f"mg_{lo}_{hi}", "multigoal", f"Multigol {lo}-{hi}",
                (total >= lo) & (total <= hi),
            )
        )

    # 8 - Combo esito + totale
    for res_key, res_label, res_mask in (
        ("1", "1", margin > 0),
        ("x2", "X2", margin <= 0),
        ("2", "2", margin < 0),
        ("1x", "1X", margin >= 0),
    ):
        for line in (1.5, 2.5):
            out += [
                MarketDef(
                    f"combo_{res_key}_over_{line}", "combo",
                    f"{res_label} + Over {line}", res_mask & (total > line),
                ),
                MarketDef(
                    f"combo_{res_key}_under_{line}", "combo",
                    f"{res_label} + Under {line}", res_mask & (total < line),
                ),
            ]

    # 9 - Risultato esatto. La ricerca (11) prevede che non vincano quasi mai
    #     il ranking: e' corretto e voluto, li teniamo fra i candidati e li
    #     lascia cadere il filtro p_min.
    for i in range(4):
        for j in range(4):
            out.append(
                MarketDef(
                    f"cs_{i}_{j}", "correct_score", f"Risultato esatto {i}-{j}",
                    (h == i) & (a == j),
                )
            )

    # 10 - Gol per squadra
    for line in (0.5, 1.5, 2.5):
        out += [
            MarketDef(f"hg_over_{line}", "team_goals", f"Casa Over {line}", h > line),
            MarketDef(f"hg_under_{line}", "team_goals", f"Casa Under {line}", h < line),
            MarketDef(f"ag_over_{line}", "team_goals", f"Ospite Over {line}", a > line),
            MarketDef(f"ag_under_{line}", "team_goals", f"Ospite Under {line}", a < line),
        ]

    return tuple(out)


@lru_cache(maxsize=4)
def _mask_stack(max_goals: int) -> tuple[tuple[str, ...], np.ndarray]:
    """Le maschere impilate come matrice (n_mercati, celle), per il batch."""
    defs = catalog(max_goals)
    keys = tuple(d.key for d in defs)
    stack = np.stack([d.mask.ravel().astype(float) for d in defs])
    return keys, stack


def probabilities(gm: GoalMatrix) -> dict[str, float]:
    """Probabilita' di tutti i mercati da una singola matrice."""
    keys, stack = _mask_stack(gm.max_goals)
    values = stack @ gm.matrix.ravel()
    return dict(zip(keys, (float(v) for v in values), strict=True))


def probabilities_batch(matrices: np.ndarray) -> dict[str, np.ndarray]:
    """Probabilita' di tutti i mercati per B matrici in un solo prodotto.

    E' il passo che rende lo scoring di una fixture questione di millisecondi:
    B matrici x ~90 mercati diventano una moltiplicazione matriciale.
    """
    b, size, _ = matrices.shape
    keys, stack = _mask_stack(size - 1)
    values = matrices.reshape(b, -1) @ stack.T  # (B, n_mercati)
    return {key: values[:, i] for i, key in enumerate(keys)}


def asian_push_lines(gm: GoalMatrix) -> dict[str, dict[str, float]]:
    """Linee asiatiche intere: vincita, rimborso, perdita.

    Non sono eventi binari, quindi non entrano fra i candidati; si calcolano
    perche' il frontend le mostra sotto la piega.
    """
    size = gm.max_goals + 1
    h, a = _grids(size)
    margin = h - a
    out: dict[str, dict[str, float]] = {}
    for line in ASIAN_LINES_PUSH:
        adjusted = margin + line
        out[f"ah_home_{line}"] = {
            "win": gm.probability(adjusted > 0),
            "push": gm.probability(adjusted == 0),
            "lose": gm.probability(adjusted < 0),
        }
    return out


def half_time_probabilities(
    lam_home: float, lam_away: float, ht_ratio: float
) -> dict[str, float]:
    """Mercati del primo tempo e HT/FT.

    Il secondo tempo e' modellato come Poisson indipendente con il
    complemento del rate, quindi HT e FT sono congiunti correttamente e non
    si somma un pareggio del primo tempo a un risultato finale incompatibile.

    Non concorrono alla selezione in v1: il rapporto HT e' misurato ma la sua
    incertezza non e' ancora propagata (brief 10, rimandato con grilletto).
    """
    first, second = half_time_matrices(lam_home, lam_away, ht_ratio)
    size = first.shape[0]
    h, a = _grids(size)
    total = h + a
    margin = h - a

    out: dict[str, float] = {}
    for line in (0.5, 1.5, 2.5):
        out[f"ht_over_{line}"] = float(first[total > line].sum())
        out[f"ht_under_{line}"] = float(first[total < line].sum())

    # HT/FT: si convolvono i due tempi per ottenere il margine finale.
    labels = {1: "1", 0: "X", -1: "2"}
    table = {f"htft_{labels[x]}{labels[y]}": 0.0 for x in (1, 0, -1) for y in (1, 0, -1)}
    ht_sign = np.sign(margin)
    for sh in range(size):
        for sa in range(size):
            weight = second[sh, sa]
            if weight < 1e-12:
                continue
            ft_sign = np.sign(margin + (sh - sa))
            for hs in (1, 0, -1):
                sel = ht_sign == hs
                if not sel.any():
                    continue
                for fs in (1, 0, -1):
                    mass = first[sel & (ft_sign == fs)].sum()
                    if mass:
                        table[f"htft_{labels[hs]}{labels[fs]}"] += float(weight * mass)
    out.update(table)
    return out
