"""Test del de-vig.

Il de-vig ingenuo e' "l'errore piu' costoso della lista dei gotcha" (ricerca
11): gonfia la probabilita' equa dei longshot e fabbrica vantaggio finto
esattamente dove il vantaggio e' piu' difficile da avere. Qui si dimostra in
che direzione sbaglia, su un overround noto.
"""

from __future__ import annotations

import numpy as np
import pytest

from pronostici.model.devig import DevigError, devig_naive, devig_power


class TestOverroundNoto:
    def test_somma_a_uno(self):
        result = devig_power([2.10, 3.50, 3.80])
        assert result.probabilities.sum() == pytest.approx(1.0, abs=1e-12)

    def test_overround_misurato_e_quello_vero(self):
        odds = [2.00, 4.00, 4.00]  # 0,5 + 0,25 + 0,25 = 1,0 -> +0% ... troppo
        odds = [1.90, 3.80, 3.80]  # 0,5263 + 0,2632 + 0,2632 = 1,0526
        result = devig_power(odds)
        assert result.overround == pytest.approx(1.05263, abs=1e-4)
        assert result.margin_pct == pytest.approx(5.263, abs=1e-2)

    def test_mercato_equo_e_sospetto_non_si_aggiusta_in_silenzio(self):
        """Overround <= 1 significa quote favorevoli: e' un dato sbagliato,
        non un regalo. Il de-vig si rifiuta invece di inventare un beta."""
        with pytest.raises(DevigError):
            devig_power([2.00, 4.00, 4.00])

    def test_quote_non_valide(self):
        with pytest.raises(DevigError):
            devig_power([-2.0, 3.0, 4.0])
        with pytest.raises(DevigError):
            devig_power([float("inf"), 3.0, 4.0])
        with pytest.raises(DevigError):
            devig_power([2.0])

    def test_due_esiti(self):
        """Over/Under e' una partizione a due: stessa formula, n_winners = 1."""
        result = devig_power([1.90, 1.95])
        assert result.probabilities.sum() == pytest.approx(1.0)
        assert result.probabilities[0] > result.probabilities[1]


class TestPowerControNaive:
    # Favorito netto, longshot vero, margine del 5,8%: e' la forma di mercato
    # in cui il bias favourite-longshot morde di piu'.
    ODDS = [1.25, 6.00, 11.00]

    def test_beta_maggiore_di_uno_su_un_mercato_con_margine(self):
        result = devig_power(self.ODDS)
        assert result.beta > 1.0

    def test_il_naive_sovrastima_il_longshot(self):
        """Il punto centrale: sul longshot il naive da' una probabilita' equa
        piu' alta, cioe' fabbrica vantaggio dove non ce n'e'."""
        power = devig_power(self.ODDS).probabilities
        naive = devig_naive(self.ODDS)
        assert naive[-1] > power[-1]
        assert naive[0] < power[0]  # e sottostima il favorito

    def test_lo_scarto_non_e_trascurabile(self):
        power = devig_power(self.ODDS).probabilities
        naive = devig_naive(self.ODDS)
        relativo = (naive[-1] - power[-1]) / power[-1]
        assert relativo > 0.02  # oltre due punti percentuali relativi

    def test_beta_uno_coincide_col_naive(self):
        """Con beta = 1 il metodo power *e'* il naive: la differenza fra i due
        e' tutta e sola nell'esponente."""
        inv = 1.0 / np.asarray(self.ODDS)
        assert np.allclose(inv / inv.sum(), devig_naive(self.ODDS))

    def test_ordine_conservato(self):
        power = devig_power(self.ODDS).probabilities
        assert list(power) == sorted(power, reverse=True)
