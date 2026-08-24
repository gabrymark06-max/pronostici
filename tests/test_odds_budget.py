"""Il tetto dei crediti deve essere UNO.

`quote` e `finalize` scrivono sullo stesso contatore e avevano due tetti
diversi: 450 nel primo workflow, 250 nel secondo. Appena `quote` superava 250,
`finalize` leggeva lo stesso file, calcolava «quota finita» e saltava il giro —
producendo pronostici solo-modello per il resto del mese senza che niente
diventasse rosso.

Due numeri per la stessa cosa non erano due impostazioni: erano un guasto in
attesa di un mese abbastanza pieno.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def test_nessun_workflow_scrive_il_tetto_a_mano() -> None:
    colpevoli = []
    for f in sorted(WORKFLOWS.glob("*.yml")):
        for riga in f.read_text(encoding="utf-8").splitlines():
            if re.match(r"\s*ODDS_CREDIT_CAP\s*:", riga):
                colpevoli.append(f"{f.name}: {riga.strip()}")
    assert not colpevoli, "il tetto sta in config.py, non nei workflow: " + "; ".join(
        colpevoli
    )


def test_il_tetto_sta_sotto_quello_del_fornitore() -> None:
    """Il piano gratuito ne da' 500 al mese.

    Il nostro sta sotto apposta: e' quello che fa scattare la degradazione
    mentre c'e' ancora margine, invece di lasciare che sia il fornitore a dire
    di no a meta' di un giro.
    """
    from pronostici.config import get_settings

    get_settings.cache_clear()
    assert 0 < get_settings().odds_credit_cap < 500
