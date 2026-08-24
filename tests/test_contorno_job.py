"""Le due decisioni del job che non si vedono guardando l'output.

Il resto — scaricare, agganciare, scrivere — e' provato altrove o si vede da
solo quando manca. Queste due no: sbagliano producendo un risultato plausibile.
"""

from __future__ import annotations

from pronostici.jobs import contorno as job
from pronostici.sources import sportsgambler as sg


def _formazione(confermate: bool) -> sg.Formazione:
    return sg.Formazione(
        casa=sg.Lato(modulo="4-3-3", titolari=[{"nome": "Skorupski", "maglia": "1"}]),
        ospiti=sg.Lato(modulo="3-5-2", titolari=[{"nome": "Mandas", "maglia": "35"}]),
        confermate=confermate,
    )


class TestConfermate:
    """Nel dubbio si dice la cosa piu' debole.

    L'elenco e il frammento non sempre concordano — Bologna-Lazio aveva il
    pulsante «Confirmed» e dentro «Predicted» — e non sappiamo quale dei due
    sia vecchio. Dire «probabile» su una formazione confermata costa
    un'imprecisione; dire «confermata» su una probabile significa affermare
    che quello e' l'undici che scende in campo, e non lo sappiamo.
    """

    def _blocco(self, frammento: bool, elenco: bool) -> dict:
        return job._blocco(
            _formazione(frammento),
            confermate_in_elenco=elenco,
            ore_prima=12.0,
            letto="2026-08-24T15:00:00Z",
            arbitro=None,
        )

    def test_confermata_solo_se_lo_dicono_entrambi(self) -> None:
        assert self._blocco(True, True)["formazioni"]["confermate"] is True

    def test_elenco_confermato_ma_frammento_no(self) -> None:
        assert self._blocco(False, True)["formazioni"]["confermate"] is False

    def test_frammento_confermato_ma_elenco_no(self) -> None:
        assert self._blocco(True, False)["formazioni"]["confermate"] is False

    def test_la_fonte_e_dichiarata(self) -> None:
        """Senza questo campo il dato e' indistinguibile da quello di Sofascore."""
        assert self._blocco(True, True)["formazioni"]["fonte"] == "sportsgambler"

    def test_panchina_vuota_e_non_assente(self) -> None:
        """Sportsgambler non la pubblica. Una lista vuota dice «non ce l'ho»."""
        blocco = self._blocco(False, False)
        assert blocco["formazioni"]["casa"]["panchina"] == []


class TestSenzaOra:
    """`letto` cambia a ogni giro e non e' una novita'.

    Se entrasse nel confronto, ogni esecuzione riscriverebbe tutti i file e il
    registro pubblico delle modifiche — che e' meta' del prodotto — diventerebbe
    illeggibile.
    """

    def test_due_giri_identici_non_sono_una_modifica(self) -> None:
        a = {"letto": "2026-08-24T07:00:00Z", "arbitro": {"nome": "Maresca"}}
        b = {"letto": "2026-08-24T17:00:00Z", "arbitro": {"nome": "Maresca"}}
        assert job._senza_ora(a) == job._senza_ora(b)

    def test_un_arbitro_nuovo_invece_lo_e(self) -> None:
        a = {"letto": "2026-08-24T07:00:00Z", "arbitro": {"nome": "Maresca"}}
        b = {"letto": "2026-08-24T07:00:00Z", "arbitro": {"nome": "Orsato"}}
        assert job._senza_ora(a) != job._senza_ora(b)


class TestGuardiaSulParsing:
    """Il guasto tipico di una fonte letta dall'HTML e' silenzioso.

    Se cambia una classe CSS l'elenco risponde ancora 200, le partite si
    agganciano tutte e i frammenti arrivano — solo che non se ne cava piu' un
    giocatore. Senza questa guardia il job uscirebbe verde avendo scritto
    niente, e le formazioni di quei giorni sarebbero perse: esistono solo
    prima del fischio d'inizio.
    """

    def _report(self, agganciate: int, con_formazioni: int) -> dict:
        return {"agganciate": agganciate, "con_formazioni": con_formazioni}

    def test_molte_agganciate_e_zero_formazioni_e_un_guasto(self) -> None:
        r = self._report(job.SOGLIA_ALLARME, 0)
        assert job._allarme_parsing(r) is not None

    def test_poche_partite_puo_essere_vero(self) -> None:
        """Una finestra corta in pausa nazionali non ha niente da leggere."""
        r = self._report(job.SOGLIA_ALLARME - 1, 0)
        assert job._allarme_parsing(r) is None

    def test_una_formazione_sola_basta_a_dire_che_il_parsing_regge(self) -> None:
        r = self._report(80, 1)
        assert job._allarme_parsing(r) is None


class TestMercatiVersoLeNostreChiavi:
    """I mercati estesi devono parlare la lingua del resto del progetto.

    `market_p` riempie la colonna «il mercato» sulle partite che la fonte
    principale non copre: se le chiavi non combaciassero con quelle di `odds`,
    le due fonti vivrebbero in universi separati e nessuna pagina potrebbe
    confrontarle.
    """

    def _mercato(self, nome: str, esiti: list[tuple[str, float]], linea=None) -> dict:
        return {
            "mercato": nome,
            "linea": linea,
            "esiti": [{"esito": e, "probabilita_implicita": p} for e, p in esiti],
        }

    def test_esito_finale(self) -> None:
        m = [self._mercato("Esito finale", [("1", 0.38), ("X", 0.31), ("2", 0.31)])]
        assert job._market_p(m) == {
            "1x2_home": 0.38,
            "1x2_draw": 0.31,
            "1x2_away": 0.31,
        }

    def test_i_gol_totali_portano_la_linea_nella_chiave(self) -> None:
        """Senza, le dodici soglie diventerebbero dodici volte la stessa voce."""
        m = [
            self._mercato("Gol totali", [("Over", 0.68), ("Under", 0.32)], linea="1.5"),
            self._mercato("Gol totali", [("Over", 0.40), ("Under", 0.60)], linea="2.5"),
        ]
        assert job._market_p(m) == {
            "over_1.5": 0.68,
            "under_1.5": 0.32,
            "over_2.5": 0.40,
            "under_2.5": 0.60,
        }

    def test_un_mercato_che_non_sappiamo_tradurre_si_ignora(self) -> None:
        """Meglio non dirlo che dirlo con una chiave inventata."""
        m = [self._mercato("Handicap asiatico", [("1", 0.5), ("2", 0.5)])]
        assert job._market_p(m) == {}

    def test_entrambe_segnano(self) -> None:
        m = [self._mercato("Entrambe segnano", [("Sì", 0.48), ("No", 0.52)])]
        assert job._market_p(m) == {"btts_yes": 0.48, "btts_no": 0.52}
