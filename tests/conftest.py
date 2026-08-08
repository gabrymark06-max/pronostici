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


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Registro, fixture giornaliere e accuracy su una cartella temporanea."""
    monkeypatch.setattr(ledger, "LEDGER_DIR", tmp_path / "ledger")
    monkeypatch.setattr(fx, "FIXTURES_DIR", tmp_path / "fixtures")
    monkeypatch.setattr(settle_job, "ACCURACY_FILE", tmp_path / "accuracy.json")
    return tmp_path
