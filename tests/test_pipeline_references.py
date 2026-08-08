"""Test del riferimento quando ci sono le quote.

Copre il bug piu' costoso trovato girando `finalize` su dati veri: "Asiatico
casa -0.5" e "Vittoria casa" sono lo **stesso identico evento**, e venivano
confrontati con due riferimenti diversi — il primo col base rate storico, il
secondo con la quota sgonfiata. L'argmax sceglieva sistematicamente il
riferimento piu' comodo, cioe' fabbricava vantaggio da un cambio di nome.
"""

from __future__ import annotations

import numpy as np
import pytest

from pronostici.model.markets import catalog
from pronostici.pipeline import market_references

QUOTED = {
    "1x2_home": 0.5800,
    "1x2_draw": 0.2400,
    "1x2_away": 0.1800,
    "over_2.5": 0.5500,
    "under_2.5": 0.4500,
}

MASKS = {d.key: d.mask for d in catalog(12)}


class TestAlias:
    @pytest.mark.parametrize(
        ("alias", "originale"),
        [
            ("ah_home_-0.5", "1x2_home"),
            ("ah_away_-0.5", "1x2_away"),
            ("ah_home_0.5", "dc_1x"),
            ("ah_away_0.5", "dc_x2"),
            ("eh_1_home", "dc_1x"),
            ("mg_0_2", "under_2.5"),
        ],
    )
    def test_lo_stesso_evento_ha_lo_stesso_riferimento(self, alias, originale):
        # Prima la premessa: le due maschere sono davvero identiche.
        assert np.array_equal(MASKS[alias], MASKS[originale]), (
            f"{alias} e {originale} non sono lo stesso evento: il test e' sbagliato"
        )
        refs = market_references(QUOTED)
        assert refs[alias] == pytest.approx(refs[originale])

    def test_l_alias_prende_il_mercato_non_il_base_rate(self):
        refs = market_references(QUOTED)
        assert refs["ah_home_-0.5"] == pytest.approx(0.58)


class TestUnioni:
    def test_doppia_chance_si_somma_esattamente(self):
        refs = market_references(QUOTED)
        assert refs["dc_1x"] == pytest.approx(0.58 + 0.24)
        assert refs["dc_12"] == pytest.approx(0.58 + 0.18)
        assert refs["dc_x2"] == pytest.approx(0.24 + 0.18)

    def test_le_tre_doppie_chance_sommano_a_due(self):
        refs = market_references(QUOTED)
        totale = refs["dc_1x"] + refs["dc_12"] + refs["dc_x2"]
        assert totale == pytest.approx(2.0)

    def test_senza_1x2_completo_non_si_inventa_la_doppia_chance(self):
        refs = market_references({"over_2.5": 0.55, "under_2.5": 0.45})
        assert "dc_1x" not in refs


class TestNonEstensione:
    def test_il_mercato_non_dice_niente_su_btts(self):
        """L'estensione e' esatta o non e'. Su BTTS `h2h` + `totals` non
        determinano niente, e il riferimento deve restare il base rate."""
        refs = market_references(QUOTED)
        assert "btts_yes" not in refs
        assert "btts_no" not in refs

    def test_ne_su_un_risultato_esatto(self):
        assert "cs_2_1" not in market_references(QUOTED)

    def test_ne_su_un_multigol_non_allineato(self):
        assert "mg_1_3" not in market_references(QUOTED)

    def test_senza_quote_nessun_riferimento_di_mercato(self):
        assert market_references({}) == {}

    def test_chiavi_non_quotabili_vengono_ignorate(self):
        refs = market_references({"btts_yes": 0.9, "1x2_home": 0.5})
        assert "btts_yes" not in refs


class TestIntegrazioneConLaSelezione:
    def test_l_alias_non_puo_piu_battere_l_originale(self):
        """Con lo stesso riferimento, due nomi dello stesso evento hanno lo
        stesso punteggio: la scelta non dipende piu' da quale nome si guarda.
        """
        from pronostici.model.selection import directional_score

        refs = market_references(QUOTED)
        p = 0.6432  # la stessa p̃: e' lo stesso evento
        assert directional_score(p, refs["ah_home_-0.5"]) == pytest.approx(
            directional_score(p, refs["1x2_home"])
        )
