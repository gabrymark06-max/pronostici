"""Quando Sofascore rifiuta *tutto*, il giro deve fermarsi in fretta.

Il 403 di una frenata passeggera passa da solo, e i tre tentativi con le pause
crescenti servono a quello. Ma esiste un 403 che non passa mai — `api.` risponde
`reason: challenge` a chi non esegue JavaScript — e il 22 e il 23 agosto 2026 il
job su GitHub Actions e' stato ucciso due volte dal timeout di 25 minuti senza
scrivere niente, perche' pagava otto secondi di attese per ognuna delle
centinaia di richieste del giro.

Qui si prova che dopo tre richieste esaurite di fila si smette, e che una
risposta vera — anche un 404 — rimette il contatore a zero.
"""

from __future__ import annotations

import pytest

from pronostici.sources import sofascore_http as http


class _Risposta:
    def __init__(self, status):
        self.status_code = status

    def json(self):
        return {"ok": True}


@pytest.fixture(autouse=True)
def _senza_attese_e_senza_memoria(monkeypatch):
    """Niente `sleep` nei test, e ogni test parte dal contatore a zero."""
    monkeypatch.setattr(http.time, "sleep", lambda _: None)
    http.azzera_blocco()
    yield
    http.azzera_blocco()


def _sessione(risposte):
    """Una finta sessione `curl_cffi` che restituisce gli status dati."""
    stato = {"chiamate": 0}

    class _S:
        @staticmethod
        def get(*_, **__):
            i = min(stato["chiamate"], len(risposte) - 1)
            stato["chiamate"] += 1
            return _Risposta(risposte[i])

    return _S, stato


def test_tre_richieste_murate_fermano_il_giro(monkeypatch):
    sessione, stato = _sessione([403])
    monkeypatch.setattr(http, "_sessione", lambda: sessione)

    for _ in range(http.BLOCCHI_PER_ARRENDERSI - 1):
        with pytest.raises(http.SofascoreNonRaggiungibile):
            http.prendi("/evento/1")

    with pytest.raises(http.SofascoreCiBlocca) as errore:
        http.prendi("/evento/1")

    assert "challenge" in str(errore.value)
    # Tre richieste da tre tentativi: non una di piu'.
    assert stato["chiamate"] == http.BLOCCHI_PER_ARRENDERSI * http.TENTATIVI


def test_il_muro_non_e_un_errore_da_saltare_per_partita():
    """Il job cattura `SofascoreNonDisponibile` partita per partita: se il muro
    ne ereditasse, verrebbe inghiottito e il giro proseguirebbe a vuoto."""
    assert not issubclass(http.SofascoreCiBlocca, http.SofascoreNonRaggiungibile)


def test_una_risposta_vera_azzera_il_conto(monkeypatch):
    sessione, _ = _sessione([403, 403, 403, 200])
    monkeypatch.setattr(http, "_sessione", lambda: sessione)

    with pytest.raises(http.SofascoreNonRaggiungibile):
        http.prendi("/evento/1")   # brucia i tre 403, contatore a 1
    assert http.prendi("/evento/2") == {"ok": True}

    sessione2, _ = _sessione([403])
    monkeypatch.setattr(http, "_sessione", lambda: sessione2)
    with pytest.raises(http.SofascoreNonRaggiungibile) as errore:
        http.prendi("/evento/3")
    assert not isinstance(errore.value, http.SofascoreCiBlocca), (
        "dopo una risposta buona il conto riparte da zero"
    )


def test_anche_un_404_dimostra_che_il_muro_non_ce(monkeypatch):
    sessione, _ = _sessione([403, 403, 403, 404])
    monkeypatch.setattr(http, "_sessione", lambda: sessione)

    with pytest.raises(http.SofascoreNonRaggiungibile):
        http.prendi("/evento/1")
    with pytest.raises(http.SofascoreNonRaggiungibile):
        http.prendi("/evento/2")   # 404: passa, e azzera

    assert http._falliti_di_fila == 0
