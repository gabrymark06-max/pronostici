"""Il passaggio dalla strada economica a quella che funziona.

Dal 23 agosto 2026 l'API di Sofascore vuole due header che si ottengono solo
dentro un browser vero (`X-Captcha`, legato all'IP e alla connessione, e
`X-Requested-With`). `curl_cffi` resta la strada di partenza perche' costa una
frazione, ma quando il muro e' confermato il giro deve **passare** al browser,
non arrendersi.

Qui non si apre nessun Chrome: si prova la logica del passaggio e la
traduzione delle risposte, che sono le due cose che possono rompersi da sole.
"""

from __future__ import annotations

import pytest

from pronostici.sources import sofascore_cdp as cdp
from pronostici.sources import sofascore_http as http


class _SessioneFinta:
    """Un browser che risponde quello che gli si dice."""

    def __init__(self, risposte):
        self.risposte = list(risposte)
        self.chiesti: list[str] = []

    def prendi(self, percorso):
        self.chiesti.append(percorso)
        return self.risposte.pop(0) if self.risposte else (200, {"ok": True})


class _Risposta403:
    status_code = 403

    def json(self):  # pragma: no cover - non ci si arriva mai
        return {}


@pytest.fixture(autouse=True)
def _pulizia(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    http.azzera_blocco()
    http.azzera_trasporto()
    yield
    http.azzera_blocco()
    http.azzera_trasporto()


@pytest.fixture
def _muro(monkeypatch):
    """Tutte le richieste HTTP muoiono sul 403, come fa Sofascore adesso."""

    class _S:
        @staticmethod
        def get(*_, **__):
            return _Risposta403()

    monkeypatch.setattr(http, "_sessione", lambda: _S)


def test_col_muro_si_passa_al_browser(monkeypatch, _muro):
    finta = _SessioneFinta([(200, {"evento": 1})])
    monkeypatch.setattr(cdp, "sessione", lambda: finta)

    # Le prime richieste esauriscono i tentativi e alzano il conto del muro.
    for _ in range(http.BLOCCHI_PER_ARRENDERSI - 1):
        with pytest.raises(http.SofascoreNonRaggiungibile):
            http.prendi("/evento/1")

    assert http.prendi("/evento/2") == {"evento": 1}
    assert finta.chiesti == ["/evento/2"], "la richiesta rifatta e' quella giusta"


def test_dopo_il_passaggio_non_si_ritenta_la_via_morta(monkeypatch, _muro):
    finta = _SessioneFinta([(200, {"a": 1}), (200, {"b": 2}), (200, {"c": 3})])
    monkeypatch.setattr(cdp, "sessione", lambda: finta)

    for _ in range(http.BLOCCHI_PER_ARRENDERSI - 1):
        with pytest.raises(http.SofascoreNonRaggiungibile):
            http.prendi("/x")
    http.prendi("/uno")
    http.prendi("/due")
    http.prendi("/tre")

    assert finta.chiesti == ["/uno", "/due", "/tre"]


def test_senza_chrome_esce_il_muro_col_motivo(monkeypatch, _muro):
    def _niente_chrome():
        raise cdp.ChromeNonDisponibile("non l'ho trovato")

    monkeypatch.setattr(cdp, "sessione", _niente_chrome)

    for _ in range(http.BLOCCHI_PER_ARRENDERSI - 1):
        with pytest.raises(http.SofascoreNonRaggiungibile):
            http.prendi("/x")

    with pytest.raises(http.SofascoreCiBlocca) as errore:
        http.prendi("/x")

    testo = str(errore.value)
    assert "X-Captcha" in testo, "il muro spiega ancora cosa manca"
    assert "non l'ho trovato" in testo, "e anche perche' il ripiego non e' andato"


@pytest.mark.parametrize(
    "stato, atteso",
    [(404, "404 su"), (500, "500 su"), (403, "403 su")],
)
def test_il_browser_traduce_gli_errori_come_prima(monkeypatch, stato, atteso):
    """404 resta 404: le regole di chi chiama non cambiano col trasporto."""
    finta = _SessioneFinta([(stato, None)])
    with pytest.raises(http.SofascoreNonRaggiungibile) as errore:
        http._dal_browser(finta, "/evento/9")
    assert atteso in str(errore.value)


def test_un_200_senza_json_non_passa_per_buono():
    finta = _SessioneFinta([(200, None)])
    with pytest.raises(http.SofascoreNonRaggiungibile) as errore:
        http._dal_browser(finta, "/evento/9")
    assert "non JSON" in str(errore.value)
