"""Il trasporto verso Sofascore, provato senza toccare la rete.

I CAMPIONI SONO RISPOSTE GREZZE, non nostre uscite gia' trasformate: stanno in
`tests/dati_sofascore/` e sono quello che l'API ha risposto davvero il 14
agosto 2026. Partire da li' significa che queste prove verificano la
TRASFORMAZIONE — l'unica cosa che questo modulo fa — invece di confrontare un
nostro file con se stesso.

PERCHE' NON SI CHIAMA LA RETE. Una prova che chiama Sofascore fallisce quando
Sofascore e' lento, quando il runner non ha rete, e quando cambia un risultato:
tre modi di diventare rumore. Quando cambiera' la FORMA delle risposte queste
prove continueranno a passare mentre il codice vero si rompe — ed e' un limite
che si accetta sapendolo, perche' l'alternativa e' una suite che fallisce per
ragioni che non riguardano il codice.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pronostici.sources import sofascore_http as h

DATI = Path(__file__).parent / "dati_sofascore"


def campione(nome: str) -> dict:
    return json.loads((DATI / nome).read_text(encoding="utf-8"))


@pytest.fixture
def senza_rete(monkeypatch):
    """Sostituisce `prendi` con i campioni. Un percorso non previsto ALZA,
    invece di restituire vuoto: cosi' una chiamata nuova e non registrata si
    vede subito, invece di far passare la prova con meno dati."""
    mappa = {
        "/event/16450754": "evento.json",
        "/event/16450754/lineups": "lineups.json",
        "/event/16450754/odds/1/all": "odds.json",
        "/player/253809/statistics/seasons": "stagioni.json",
    }

    def finto(percorso: str):
        if percorso not in mappa:
            raise AssertionError(f"percorso non registrato nei campioni: {percorso}")
        return campione(mappa[percorso])

    monkeypatch.setattr(h, "prendi", finto)


# ------------------------------------------------------------------ #
# Le conversioni pure                                                #
# ------------------------------------------------------------------ #


@pytest.mark.parametrize(
    "frazionaria, atteso",
    [
        ("3/4", 1.75),
        ("1/1", 2.0),
        ("10/1", 11.0),
        ("1/20", 1.05),
    ],
)
def test_le_quote_frazionarie_diventano_decimali(frazionaria, atteso):
    """Sofascore serve SOLO frazionarie. In quel formato non ci fai un calcolo."""
    assert h._decimale(frazionaria) == pytest.approx(atteso)


@pytest.mark.parametrize("brutta", ["", "niente", "3/0", "a/b"])
def test_una_frazione_illeggibile_non_diventa_un_numero(brutta):
    """Meglio nessuna quota che una inventata: chi chiama tiene il valore
    grezzo visibile e non ci calcola sopra."""
    assert h._decimale(brutta) is None


def test_l_arrotondamento_e_quello_del_cli():
    """Mezzo punto va SEMPRE verso l'alto in valore assoluto.

    `round()` di Python arrotonda al pari piu' vicino — `round(2.5)` fa 2, e
    `round(3.5)` fa 4 — e su una quota o su un tasso per 90 quella differenza
    si vede al confronto con i numeri gia' pubblicati dal CLI.

    NON SI PROVA `1.005` -> `1.01`, e la ragione merita una riga: `1.005` in
    virgola mobile e' gia' un pelo MENO di 1,005, quindi `1.005 * 100 + 0.5`
    non arriva a 101 e il risultato e' 1,00. Il CLI in Go fa la stessa
    aritmetica sugli stessi float64 e da' lo stesso 1,00. Pretendere 1,01
    sarebbe pretendere che questa funzione sia piu' precisa di quella che deve
    riprodurre — e i numeri gia' pubblicati sono quelli dell'altra.
    """
    assert h._arrotonda(2.5, 0) == 3
    assert round(2.5) == 2, "e' proprio da questo che ci stiamo difendendo"
    assert h._arrotonda(-2.5, 0) == -3
    assert h._arrotonda(1.7549, 2) == 1.75


# ------------------------------------------------------------------ #
# La scheda                                                          #
# ------------------------------------------------------------------ #


def test_la_scheda_porta_arbitro_formazioni_e_quote(senza_rete):
    s = h.scheda(16450754)
    assert s["partita_id"] == 16450754
    assert s["casa"] and s["ospiti"]
    assert s["arbitro"]["nome"]
    assert s["formazioni"]["casa"]["titolari"]
    assert s["quote"]["mercati"]


def test_i_gialli_per_partita_sono_calcolati_non_copiati(senza_rete):
    a = h.scheda(16450754)["arbitro"]
    if a["partite_arbitrate"]:
        atteso = h._arrotonda(a["cartellini_gialli"] / a["partite_arbitrate"], 2)
        assert a["gialli_per_partita"] == atteso


def test_lo_stadio_sta_dentro_l_arbitro(senza_rete):
    """Sembra il posto sbagliato ed e' quello giusto: `jobs.sofascore` lo legge
    da li', e l'unica cosa che la pagina ne fa e' scriverlo accanto al nome."""
    s = h.scheda(16450754)
    assert "stadio" in s["arbitro"]
    assert "stadio" not in s


def test_titolari_e_panchina_sono_separati(senza_rete):
    casa = h.scheda(16450754)["formazioni"]["casa"]
    assert all(g["titolare"] for g in casa["titolari"])
    assert not any(g["titolare"] for g in casa["panchina"])
    assert casa["n_titolari"] == len(casa["titolari"])


def test_ogni_giocatore_in_campo_porta_il_proprio_id(senza_rete):
    """Senza l'id non si possono chiedere le sue statistiche, e il blocco delle
    stime sui giocatori non esiste."""
    casa = h.scheda(16450754)["formazioni"]["casa"]
    assert all(g["id"] > 0 for g in casa["titolari"])


def test_la_linea_dei_mercati_over_under_c_e(senza_rete):
    """Senza, «Oltre» non vuol dire niente: la fonte manda nove mercati «Match
    goals» identici nel nome, distinti solo dalla linea."""
    mercati = h.scheda(16450754)["quote"]["mercati"]
    gol = [m for m in mercati if m["mercato"] == "Match goals"]
    assert len(gol) > 1
    assert all(m.get("linea") for m in gol)
    assert len({m["linea"] for m in gol}) == len(gol)


def test_il_margine_e_coerente_con_la_somma(senza_rete):
    for m in h.scheda(16450754)["quote"]["mercati"]:
        atteso = h._arrotonda((m["somma_probabilita"] - 1) * 100, 2)
        assert abs(m["margine_percento"] - atteso) < 0.02, m["mercato"]


def test_una_parte_che_manca_non_fa_sparire_le_altre(monkeypatch):
    """Se le formazioni non ci sono, arbitro e quote devono arrivare lo stesso."""

    def finto(percorso: str):
        if percorso.endswith("/lineups"):
            raise h.SofascoreNonRaggiungibile("404 su /lineups")
        nomi = {
            "/event/16450754": "evento.json",
            "/event/16450754/odds/1/all": "odds.json",
        }
        return campione(nomi[percorso])

    monkeypatch.setattr(h, "prendi", finto)
    s = h.scheda(16450754)
    assert "formazioni" not in s
    assert s["arbitro"]["nome"]
    assert s["quote"]["mercati"]
    assert "formazioni" in s["parti_mancanti"]


# ------------------------------------------------------------------ #
# Le statistiche di un giocatore                                     #
# ------------------------------------------------------------------ #


def test_gli_anni_non_si_ripetono(monkeypatch):
    """Lo stesso 24/25 entra da due tornei — campionato e coppa — e ripeterlo
    direbbe «cinque stagioni» dove ce ne sono quattro."""
    stagioni = campione("stagioni.json")

    def finto(percorso: str):
        if percorso.endswith("/statistics/seasons"):
            return stagioni
        return {"statistics": {"appearances": 10, "minutesPlayed": 900, "goals": 2}}

    monkeypatch.setattr(h, "prendi", finto)
    v = h.statistiche_giocatore(253809)
    anni = v["stagione"].split(", ")
    assert len(anni) == len(set(anni))


def test_un_giocatore_senza_stagioni_non_diventa_uno_che_non_segna_mai(monkeypatch):
    """Restituire zeri farebbe sembrare un esordiente uno che ha sempre
    fallito. Si restituisce l'assenza, e chi chiama la salta."""

    def finto(percorso: str):
        return {"uniqueTournamentSeasons": []}

    monkeypatch.setattr(h, "prendi", finto)
    v = h.statistiche_giocatore(1)
    assert "gol_per_90" not in v
    assert "nessuna stagione" in v["nota"]


def test_il_campione_sottile_e_dichiarato(monkeypatch):
    stagioni = campione("stagioni.json")

    def finto(percorso: str):
        if percorso.endswith("/statistics/seasons"):
            return stagioni
        return {"statistics": {"appearances": 1, "minutesPlayed": 90, "goals": 1}}

    monkeypatch.setattr(h, "prendi", finto)
    v = h.statistiche_giocatore(253809)
    assert "campione sottile" in v.get("nota", "")


def test_il_tasso_per_90_e_un_tasso_non_una_media_di_tassi(monkeypatch):
    """Due stagioni: una da 900 minuti con 10 gol, una da 90 con 0.

    La media dei tassi darebbe 0,5 per 90. Il tasso vero, pesato sui minuti e
    con il decadimento del tempo, resta vicino a 1: una stagione con pochi
    minuti conta poco, ed e' giusto cosi'.
    """
    chiamate = {"n": 0}

    def finto(percorso: str):
        if percorso.endswith("/statistics/seasons"):
            return {
                "uniqueTournamentSeasons": [
                    {
                        "uniqueTournament": {"id": 1, "name": "Prova"},
                        "seasons": [
                            {"id": 10, "year": "25/26"},
                            {"id": 11, "year": "24/25"},
                        ],
                    }
                ]
            }
        chiamate["n"] += 1
        if chiamate["n"] == 1:
            return {"statistics": {"appearances": 10, "minutesPlayed": 900, "goals": 10}}
        return {"statistics": {"appearances": 1, "minutesPlayed": 90, "goals": 0}}

    monkeypatch.setattr(h, "prendi", finto)
    v = h.statistiche_giocatore(1)
    assert v["gol"] == 10
    assert v["gol_per_90"] > 0.9


# ------------------------------------------------------------------ #
# La frenata                                                         #
# ------------------------------------------------------------------ #


class _Risposta:
    def __init__(self, stato: int, corpo: dict | None = None):
        self.status_code = stato
        self._corpo = corpo or {}

    def json(self):
        return self._corpo


def test_un_403_si_riprova_e_poi_passa(monkeypatch):
    """Sofascore frena quando lo si chiama in fretta. E' temporaneo, e
    arrendersi al primo colpo butta via il giro intero."""
    risposte = [_Risposta(403), _Risposta(403), _Risposta(200, {"ok": True})]
    chiamate = {"n": 0}

    class FintoRequests:
        @staticmethod
        def get(*_, **__):
            r = risposte[chiamate["n"]]
            chiamate["n"] += 1
            return r

    monkeypatch.setattr(h, "_sessione", lambda: FintoRequests)
    monkeypatch.setattr(h.time, "sleep", lambda _: None)

    assert h.prendi("/qualcosa") == {"ok": True}
    assert chiamate["n"] == 3


def test_un_404_non_si_riprova(monkeypatch):
    """Un 404 e' una risposta, non un incidente: riprovarlo darebbe lo stesso
    404 tre volte piu' lentamente."""
    chiamate = {"n": 0}

    class FintoRequests:
        @staticmethod
        def get(*_, **__):
            chiamate["n"] += 1
            return _Risposta(404)

    monkeypatch.setattr(h, "_sessione", lambda: FintoRequests)
    with pytest.raises(h.SofascoreNonRaggiungibile, match="404"):
        h.prendi("/qualcosa")
    assert chiamate["n"] == 1


def test_dopo_i_tentativi_si_arrende_dicendolo(monkeypatch):
    class FintoRequests:
        @staticmethod
        def get(*_, **__):
            return _Risposta(403)

    monkeypatch.setattr(h, "_sessione", lambda: FintoRequests)
    monkeypatch.setattr(h.time, "sleep", lambda _: None)
    with pytest.raises(h.SofascoreNonRaggiungibile, match="tentativi"):
        h.prendi("/qualcosa")
