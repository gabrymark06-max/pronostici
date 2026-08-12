"""Partite inserite a mano, per ciò che la fonte gratuita non espone.

PERCHE' ESISTE QUESTO MODULO, che è una concessione e va trattata come tale.

`football-data.org` sul piano gratuito dà tredici competizioni. Non ci sono la
Supercoppa UEFA, l'Europa League, la Conference, né i turni preliminari delle
coppe: verificato interrogando la chiave, che il 13 agosto 2026 vede due sole
partite in tutto il mondo, entrambe di Copa Libertadores.

La Supercoppa è però l'unico caso in cui l'assenza è solo di CALENDARIO e non
di dati: si gioca fra la vincitrice di Champions e quella di Europa League, che
sono quasi sempre due squadre di cui abbiamo lo storico europeo. Nel 2026 sono
Paris Saint-Germain (34 partite di Champions in archivio) e Aston Villa (12).
Il modello sa valutarle entrambe; gli manca solo di sapere che si incontrano.

Le qualificazioni alle coppe NON si risolvono così, e non si proverà: mettono
in campo club di una cinquantina di campionati di cui non abbiamo una riga di
storico. Il calendario da solo non basta quando mancano i dati.

--- LE TRE REGOLE CHE RENDONO ACCETTABILE UNA RIGA SCRITTA A MANO -------------

1. **La fonte è obbligatoria e sta nel file.** Ogni partita porta il campo
   `fonte`. Una riga senza provenienza in un prodotto che si vanta di essere
   verificabile è peggio di una riga assente, e `carica()` la scarta gridando.

2. **Vale la stessa competizione, quindi la stessa scala.** La Supercoppa entra
   come `CL`, non come una competizione a sé: i parametri di attacco e difesa
   sono stimati DENTRO una competizione, e un attacco misurato in Ligue 1 non è
   confrontabile con una difesa misurata in Premier. La Champions è l'unico
   fit in cui quelle due squadre convivono già.

3. **Il risultato si scrive quando è successo, non prima.** `ft_home` e
   `ft_away` restano `null` finché la partita non è finita. Riempirli in
   anticipo — anche "per comodità" — significherebbe che il registro non prova
   più niente.

Le partite di qui entrano in `archive.load_all`, quindi le vedono tutti e
quattro i job: `score` le pronostica, `quote` ci attacca i prezzi, `settle` le
giudica quando il risultato c'è, `retrain` le usa nel fit come qualunque altra
partita conclusa. Quest'ultimo è deliberato: un risultato vero è un risultato
vero, e escluderlo perché è arrivato a mano sarebbe una distinzione senza
differenza. Il prezzo è che un punteggio sbagliato battuto a tastiera entra nel
modello — per una partita su migliaia l'effetto è trascurabile, ma è la ragione
per cui la regola 1 non è negoziabile.
"""

from __future__ import annotations

import logging
from typing import Any

from .archive import Match
from .config import MANUALI_DIR
from .storage import read_json

log = logging.getLogger("manuali")

# I `match_id` di football-data stanno sotto il milione. Partendo da nove
# milioni una collisione richiederebbe che loro moltiplichino per dieci il
# proprio spazio di identificatori, e ce ne accorgeremmo molto prima.
ID_MINIMO = 9_000_000


def _valida(riga: dict[str, Any], file: str) -> bool:
    if not riga.get("fonte"):
        log.error("%s: partita %s senza `fonte`, la salto", file, riga.get("match_id"))
        return False
    if int(riga.get("match_id", 0)) < ID_MINIMO:
        log.error(
            "%s: match_id %s sotto %s, rischia di collidere con la fonte",
            file,
            riga.get("match_id"),
            ID_MINIMO,
        )
        return False
    return True


def carica(competition: str) -> list[Match]:
    """Le partite scritte a mano per questa competizione. `[]` se non ce ne sono."""
    percorso = MANUALI_DIR / f"{competition}.json"
    payload = read_json(percorso, default=None)
    if not payload:
        return []

    fuori: list[Match] = []
    for riga in payload.get("matches", []):
        if not _valida(riga, percorso.name):
            continue
        # `fonte` è metadato nostro, non un campo di `Match`: si toglie prima
        # di costruire, così il tipo resta esattamente quello dell'archivio e
        # nessun consumatore deve sapere da dove viene la riga.
        campi = {k: v for k, v in riga.items() if k != "fonte"}
        try:
            fuori.append(Match(**campi))
        except TypeError as exc:
            log.error(
                "%s: partita %s non valida (%s)",
                percorso.name,
                riga.get("match_id"),
                exc,
            )
    return fuori
