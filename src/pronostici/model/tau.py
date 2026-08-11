"""I `tau` per famiglia, letti dal backtest.

`tau` e' la deviazione standard **a priori** della nostra previsione attorno al
base rate: e' il denominatore dello shrinkage di Smith & Winkler,
`alpha = 1/(1 + sigma^2/tau^2)`. Piu' tau e' piccolo, piu' la stima viene
riportata verso il riferimento.

La ricerca (5.3, 8.3) e' esplicita su come si ottiene: **non si inventa**, si
stima col metodo dei momenti su un backtest walk-forward,
`tau^2 = max(0, Var(p_hat - b) - media(sigma^2))`, **per famiglia di mercato**.
Il valore unico 0,08 era dichiarato come punto di partenza *finche' non c'era
il backtest*. Il backtest del 2026-08-08 esiste e ha misurato i dieci valori:
da 0,021 sul risultato esatto a 0,119 sull'1X2. Questo modulo e' il
collegamento che mancava.

Due regole, entrambe conservative:

* **ricaduta sul valore unico.** Una famiglia senza misura (catalogo nuovo,
  backtest vecchio) prende `TAU_DEFAULT`. Meglio il valore di partenza che una
  chiave mancante che fa esplodere un job notturno.
* **una famiglia senza risoluzione non prende un tau.** Se `tau^2 <= 0` la
  dispersione attorno al base rate e' tutta rumore di stima: il protocollo 5
  dice che quella famiglia esce dai candidati, non che le si dia uno shrinkage
  aggressivo. Qui la si segnala; l'esclusione e' in `markets.py`.
"""

from __future__ import annotations

from pathlib import Path

from ..config import DATA
from ..storage import read_json
from .markets import catalog
from .selection import TAU_DEFAULT

BACKTEST_FILE = DATA / "backtest.json"


def families() -> tuple[str, ...]:
    """Le famiglie del catalogo, in ordine stabile."""
    seen: list[str] = []
    for definition in catalog(12):
        if definition.family not in seen:
            seen.append(definition.family)
    return tuple(seen)


def load_tau_by_family(
    path: Path | None = None, *, default: float = TAU_DEFAULT
) -> tuple[dict[str, float], dict]:
    """`(tau per famiglia, provenienza)`.

    La provenienza si ritorna insieme al valore e finisce nel rapporto del job:
    un numero che cambia lo shrinkage di tutto il sistema non puo' arrivare da
    un file senza che il job dica da dove viene e quante famiglie ha coperto.
    """
    payload = read_json(path or BACKTEST_FILE, default=None)
    measured: dict[str, float] = {}
    without_resolution: list[str] = []
    if payload:
        for family, entry in (payload.get("tau2_by_family") or {}).items():
            value = entry.get("tau")
            if not entry.get("has_resolution") or not value or value <= 0:
                without_resolution.append(family)
                continue
            measured[family] = float(value)

    out = {family: measured.get(family, default) for family in families()}
    fallback = sorted(f for f in out if f not in measured)
    return out, {
        "source": str((path or BACKTEST_FILE).name) if payload else None,
        "generated_at": (payload or {}).get("generated_at"),
        "measured_families": len(measured),
        "fallback_families": fallback,
        "fallback_value": default,
        "without_resolution": sorted(without_resolution),
    }


def resolve(
    tau: float | dict[str, float] | None, *, default: float = TAU_DEFAULT
) -> tuple[float | dict[str, float], dict]:
    """Cosa usare davvero, dato quello che ha chiesto la riga di comando.

    `None` significa "quello che dice il backtest": e' il default dei job.
    Un numero passato a mano resta un numero, e il rapporto lo dichiara — serve
    per riprodurre una corsa vecchia, non per l'uso normale.
    """
    if tau is None:
        return load_tau_by_family(default=default)
    if isinstance(tau, dict):
        return tau, {"source": "explicit_mapping", "measured_families": len(tau)}
    return tau, {"source": "explicit_scalar", "value": float(tau)}
