"""Le due decisioni del job che non si vedono guardando l'output.

Il resto — scaricare, agganciare, scrivere — e' provato altrove o si vede da
solo quando manca. Queste due no: sbagliano producendo un risultato plausibile.
"""

from __future__ import annotations

from pronostici.jobs import formazioni as job
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
