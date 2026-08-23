"""Isolamento dei test dal `data/` vero.

Nessun test deve poter scrivere nel registro pubblicato, e nessun test deve
poter toccare la rete. La prima e' garantita qui reindirizzando le tre
cartelle di scrittura su una temporanea; la seconda dai client, che in
`offline=True` sollevano invece di chiamare.
"""

from __future__ import annotations

import pytest

from pronostici import fixtures as fx
from pronostici import ledger
from pronostici.jobs import settle as settle_job
from pronostici.sources import sofascore_cdp, sofascore_http


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Registro, fixture giornaliere e accuracy su una cartella temporanea."""
    monkeypatch.setattr(ledger, "LEDGER_DIR", tmp_path / "ledger")
    monkeypatch.setattr(fx, "FIXTURES_DIR", tmp_path / "fixtures")
    monkeypatch.setattr(settle_job, "ACCURACY_FILE", tmp_path / "accuracy.json")
    return tmp_path


@pytest.fixture(autouse=True)
def niente_browser(monkeypatch):
    """Nessun test puo' aprire un Chrome vero.

    `sources/sofascore_http.prendi` passa al browser quando l'API alza il muro:
    e' la strada giusta in esercizio, ma in un test vorrebbe dire lanciare
    Chrome e chiamare Sofascore davvero — la stessa cosa che i client evitano
    con `offline=True`. Qui la porta e' chiusa per tutti; un test che vuole
    provare il passaggio sostituisce `sofascore_cdp.sessione` con il suo.
    """

    def _vietato():
        raise sofascore_cdp.ChromeNonDisponibile(
            "i test non aprono browser: sostituisci `sofascore_cdp.sessione`"
        )

    monkeypatch.setattr(sofascore_cdp, "sessione", _vietato)
    sofascore_http.azzera_trasporto()
    sofascore_http.azzera_blocco()
