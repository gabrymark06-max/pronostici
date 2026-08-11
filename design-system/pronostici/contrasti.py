"""Ristampa i rapporti di contrasto della tavolozza, WCAG 2.1.

LEGGE `tokens.css`. Non contiene una copia dei colori, e questo e' il punto.

La versione precedente aveva la tavolozza scritta a mano nel sorgente. Quando
i token sono passati alla v4 lo script e' rimasto alla v2: zero valori in
comune fra le due, quindi stampava con sicurezza i rapporti di una tavolozza
che non esisteva piu', e i numeri citati nella specifica venivano da li'. Un
verificatore che verifica una copia non verifica niente, e mente con l'aria di
chi misura.

    python design-system/pronostici/contrasti.py

Esce con 1 se una coppia di testo scende sotto 4.5:1 o una non testuale sotto
3:1, cosi' puo' stare in una pipeline.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

TOKENS = Path(__file__).with_name("tokens.css")

# I ruoli che ci interessano, col nome che avranno nel resoconto.
RUOLI = {
    "--ground": "ground",
    "--surface": "surface",
    "--surface-2": "surface-2",
    "--surface-3": "surface-3",
    "--edge": "edge",
    "--edge-strong": "edge-strong",
    "--ink": "ink",
    "--ink-2": "ink-2",
    "--ink-3": "ink-3",
    "--segnale": "segnale",
    "--segnale-ink": "segnale-ink",
    "--rel-stroke": "steel",
    "--outcome-yes": "yes",
    "--outcome-no": "no",
    "--warn": "warn",
    "--prob-track": "track",
    "--prob-fill": "fill",
    "--prob-mercato": "tacca",
}

PIANI = ("ground", "surface", "surface-2", "surface-3")
INCHIOSTRI = ("ink", "ink-2", "ink-3", "steel", "yes", "no", "warn")

MIN_TESTO = 4.5
MIN_NON_TESTO = 3.0


def canale(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminanza(hex_colore: str) -> float:
    h = hex_colore.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * canale(r) + 0.7152 * canale(g) + 0.0722 * canale(b)


def rapporto(a: str, b: str) -> float:
    la, lb = luminanza(a), luminanza(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def elle(hex_colore: str) -> float:
    """L* di CIELAB: serve a vedere quanto distano DAVVERO due piani."""
    y = luminanza(hex_colore)
    return round(116 * (y ** (1 / 3)) - 16 if y > 0.008856 else 903.3 * y, 1)


def leggi_tavolozze(css: str) -> tuple[dict[str, str], dict[str, str]]:
    """Estrae i due temi dai due blocchi di `tokens.css`.

    Lo scuro sta in `:root`, il chiaro nel blocco che porta `data-theme`.
    Si divide sul secondo, cosi' non serve un parser CSS vero.
    """
    marcatore = re.search(r"[^\n]*data-theme[^\n]*\{", css)
    if not marcatore:
        raise SystemExit("tokens.css: blocco del tema chiaro non trovato")
    scuro_txt, chiaro_txt = css[: marcatore.start()], css[marcatore.start() :]

    def estrai(testo: str) -> dict[str, str]:
        fuori = {}
        for var, nome in RUOLI.items():
            m = re.search(rf"{re.escape(var)}\s*:\s*(#[0-9A-Fa-f]{{6}})", testo)
            if m:
                fuori[nome] = m.group(1)
        return fuori

    return estrai(scuro_txt), estrai(chiaro_txt)


def resoconto(nome: str, p: dict[str, str]) -> list[str]:
    """Stampa i rapporti e restituisce l'elenco delle violazioni."""
    guasti: list[str] = []
    print("=" * 70)
    print(nome)
    print(
        "piani L*: "
        + "  ".join(f"{k} {elle(p[k])}" for k in PIANI if k in p)
    )

    for sfondo in PIANI:
        if sfondo not in p:
            continue
        voci = []
        for inchiostro in INCHIOSTRI:
            if inchiostro not in p:
                continue
            r = rapporto(p[inchiostro], p[sfondo])
            voci.append(f"{inchiostro} {r}")
            if r < MIN_TESTO:
                guasti.append(f"{nome}: {inchiostro} su {sfondo} = {r} (< {MIN_TESTO})")
        print(f" TESTO su {sfondo:<10} " + "  ".join(voci))

    if "segnale" in p and "segnale-ink" in p:
        r = rapporto(p["segnale-ink"], p["segnale"])
        print(f" segnale-ink su segnale ....... {r}")
        if r < MIN_TESTO:
            guasti.append(f"{nome}: segnale-ink su segnale = {r} (< {MIN_TESTO})")

    for a, b, etichetta, minimo in (
        ("edge-strong", "surface", "bordo di controllo su surface", MIN_NON_TESTO),
        ("fill", "track", "riempimento barra su traccia", MIN_NON_TESTO),
        # La tacca del mercato sta SULLA traccia della barra: deve staccarsi da
        # essa, non dallo sfondo pagina. E' il confronto che porta il
        # significato (dove sta la quota rispetto alla nostra probabilita'),
        # quindi e' un elemento non testuale che veicola informazione: 3:1.
        ("tacca", "track", "tacca del mercato su traccia", MIN_NON_TESTO),
        # Il bersaglio — l'elemento firma — e' una forma piena in vermiglio
        # sulla lastra. Stessa regola: informazione, non decorazione.
        ("segnale", "surface", "bersaglio su surface", MIN_NON_TESTO),
    ):
        if a in p and b in p:
            r = rapporto(p[a], p[b])
            print(f" {etichetta} ....... {r}")
            if r < minimo:
                guasti.append(f"{nome}: {etichetta} = {r} (< {minimo})")

    return guasti


def main() -> int:
    if not TOKENS.exists():
        raise SystemExit(f"non trovo {TOKENS}")
    css = TOKENS.read_text(encoding="utf-8")
    scuro, chiaro = leggi_tavolozze(css)

    guasti = resoconto("SCURO", scuro) + resoconto("CHIARO", chiaro)

    print("=" * 70)
    if guasti:
        print(f"{len(guasti)} coppie sotto la soglia:")
        for g in guasti:
            print(f"  - {g}")
        return 1
    print("tutte le coppie sono a norma (testo >= 4.5:1, non testuale >= 3:1)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
