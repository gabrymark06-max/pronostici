"""`ingest` deve distinguere «non ho la chiave» da «quella stagione non c'e'».

Sono due errori della stessa fonte e finivano nella stessa lista, quindi il
job usciva verde in entrambi i casi. Ma sono opposti: senza chiave non si
scarica *niente* e il registro resta fermo mentre la CI dice che va tutto
bene; un 404 su una coppa non ancora pubblicata e' la normalita' di agosto, e
far fallire la pipeline ogni giorno per quello sarebbe peggio del male.
"""

from __future__ import annotations

import pytest

from pronostici.jobs import ingest as ingest_job
from pronostici.sources.football_data import FootballDataError, MissingApiKey


class _ClientSenzaChiave:
    """Come il client vero quando `FOOTBALL_DATA_API_KEY` non c'e'."""

    last_rate_limit = None
    request_count = 0

    def __init__(self, *_, **__):
        pass

    def competition_matches(self, *_, **__):
        raise MissingApiKey("FOOTBALL_DATA_API_KEY non impostata.")


class _ClientStagioneAssente:
    """La chiave c'e', ma quella competizione non e' pubblicata."""

    last_rate_limit = None
    request_count = 1

    def __init__(self, *_, **__):
        pass

    def competition_matches(self, code, season=None, refresh=False):
        raise FootballDataError(f"HTTP 404 su /competitions/{code}/matches")


@pytest.fixture
def _senza_rate_limit(monkeypatch):
    """`run` legge `last_rate_limit`: qui non c'e' un server che lo riempia."""

    class _Vuoto:
        requests_available_minute = None
        counter_reset_s = None

    monkeypatch.setattr(_ClientStagioneAssente, "last_rate_limit", _Vuoto())
    monkeypatch.setattr(_ClientSenzaChiave, "last_rate_limit", _Vuoto())


def test_senza_chiave_il_job_e_rosso(monkeypatch, capsys, _senza_rate_limit):
    monkeypatch.setattr(ingest_job, "FootballDataClient", _ClientSenzaChiave)

    codice = ingest_job.main(["--competitions", "PL", "SA", "--seasons", "2026"])

    assert codice == 1, "una chiave mancante non puo' produrre un job verde"
    rapporto = capsys.readouterr().out
    assert "fatal" in rapporto
    assert "FOOTBALL_DATA_API_KEY" in rapporto


def test_senza_chiave_non_insiste_su_ogni_campionato(monkeypatch, _senza_rate_limit):
    """Venti errori identici non aggiungono niente: si esce al primo."""
    chiamate = []

    class _Contato(_ClientSenzaChiave):
        def competition_matches(self, code, season=None, refresh=False):
            chiamate.append(code)
            raise MissingApiKey("FOOTBALL_DATA_API_KEY non impostata.")

    monkeypatch.setattr(ingest_job, "FootballDataClient", _Contato)

    with pytest.raises(MissingApiKey):
        ingest_job.run(["PL", "SA", "PD"], [2026])

    assert chiamate == ["PL"]


def test_una_stagione_assente_non_ferma_il_job(monkeypatch, _senza_rate_limit):
    monkeypatch.setattr(ingest_job, "FootballDataClient", _ClientStagioneAssente)

    rapporto = ingest_job.run(["PL", "SA"], [2026])

    assert [e["competition"] for e in rapporto["errors"]] == ["PL", "SA"]
    assert rapporto["changed"] is False


def test_una_stagione_assente_lascia_il_job_verde(monkeypatch, capsys, _senza_rate_limit):
    monkeypatch.setattr(ingest_job, "FootballDataClient", _ClientStagioneAssente)

    codice = ingest_job.main(["--competitions", "PL", "--seasons", "2026"])

    assert codice == 0, "un 404 di agosto non deve tingere di rosso ogni mattina"
    assert "fatal" not in capsys.readouterr().out
