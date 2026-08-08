"""Test del motore di selezione.

Il primo test copre il bug che ha morso davvero: la KL nuda e' positiva **in
entrambe le direzioni**, quindi usarla come punteggio consiglia eventi che il
modello ritiene *meno* probabili del riferimento. Kelly dice esplicitamente
"non scommettere" quando p <= q.
"""

from __future__ import annotations

import numpy as np
import pytest

from pronostici.model.selection import (
    P_MIN,
    S_MIN,
    directional_score,
    kl_binary,
    market_correlation,
    shrink,
    single_linkage_clusters,
)


class TestDirectionalScore:
    def test_evento_meno_probabile_del_riferimento_vale_zero(self):
        """Il caso che ha prodotto il bug: p=0,777 contro riferimento 0,861.

        La KL nuda lo premiava; il punteggio direzionale lo azzera, e il filtro
        S_min lo elimina.
        """
        p, q = 0.777, 0.861
        assert kl_binary(p, q) > S_MIN, "la KL nuda lo avrebbe consigliato"
        assert directional_score(p, q) == 0.0
        assert directional_score(p, q) < S_MIN

    def test_evento_piu_probabile_conserva_il_punteggio_kl(self):
        p, q = 0.72, 0.60
        assert directional_score(p, q) == pytest.approx(kl_binary(p, q))

    def test_al_punto_di_indifferenza_vale_zero(self):
        assert directional_score(0.5, 0.5) == 0.0

    def test_vettoriale(self):
        p = np.array([0.30, 0.50, 0.80])
        q = np.array([0.50, 0.50, 0.60])
        out = directional_score(p, q)
        assert out[0] == 0.0  # sotto il riferimento
        assert out[1] == 0.0  # uguale al riferimento
        assert out[2] > 0.0  # sopra

    def test_il_vincolo_di_prodotto_e_nella_matematica(self):
        """A parita' di vantaggio relativo, il punteggio crolla sui longshot.

        E' la ragione per cui "se e' difficile che esca non lo consigliamo" non
        ha bisogno di una soglia arbitraria.
        """
        edge = 1.10
        alto = directional_score(0.75, 0.75 / edge)
        basso = directional_score(0.02, 0.02 / edge)
        assert alto / basso > 100

    def test_pronostico_banale_non_supera_la_soglia(self):
        """Over 0.5 al 97% con base rate 96,5%: confidenza altissima, zero informazione."""
        assert directional_score(0.97, 0.965) < S_MIN
        assert directional_score(0.62, 0.55) > S_MIN


class TestShrink:
    def test_sigma_grande_tira_verso_il_riferimento(self):
        p_tilde, alpha = shrink(0.80, sigma=0.30, q_ref=0.50, tau=0.08)
        assert alpha < 0.10
        assert p_tilde < 0.55

    def test_sigma_nulla_lascia_la_stima_intatta(self):
        p_tilde, alpha = shrink(0.80, sigma=0.0, q_ref=0.50, tau=0.08)
        assert alpha == pytest.approx(1.0)
        assert p_tilde == pytest.approx(0.80)

    def test_shrinkage_riduce_sempre_lo_scarto_dal_riferimento(self):
        for sigma in (0.02, 0.05, 0.10, 0.20):
            p_tilde, _ = shrink(0.85, sigma=sigma, q_ref=0.60, tau=0.08)
            assert 0.60 <= p_tilde <= 0.85

    def test_p_min_e_una_garanzia_non_una_soglia_arbitraria(self):
        """Sotto P_MIN non consigliamo: esiti meno probabili che no."""
        p_tilde, _ = shrink(0.48, sigma=0.05, q_ref=0.40, tau=0.08)
        assert p_tilde < P_MIN


class TestCorrelazione:
    @staticmethod
    def _matrice_uniforme(n: int = 5) -> np.ndarray:
        m = np.ones((n, n))
        return m / m.sum()

    def test_mercato_con_se_stesso_vale_uno(self):
        m = self._matrice_uniforme()
        mask = np.zeros_like(m, dtype=bool)
        mask[0, :] = True
        assert market_correlation(m, mask, mask) == pytest.approx(1.0)

    def test_mercati_annidati_sono_molto_correlati(self):
        """Over 1.5 contiene Over 2.5: la correlazione deve essere alta.

        E' il motivo per cui la correlazione si calcola esatta dalla matrice e
        non si stima dallo storico.
        """
        n = 6
        m = self._matrice_uniforme(n)
        idx = np.add.outer(np.arange(n), np.arange(n))
        over15 = idx >= 2
        over25 = idx >= 3
        assert market_correlation(m, over15, over25) > 0.5

    def test_mercati_disgiunti_sono_correlati_negativamente(self):
        m = self._matrice_uniforme()
        idx = np.add.outer(np.arange(5), np.arange(5))
        assert market_correlation(m, idx <= 1, idx >= 4) < 0.0

    def test_mercato_certo_non_rompe_la_divisione(self):
        m = self._matrice_uniforme()
        tutto = np.ones_like(m, dtype=bool)
        assert market_correlation(m, tutto, tutto) == 0.0


class TestClustering:
    def test_mercati_molto_correlati_finiscono_insieme(self):
        corr = np.array([[1.0, 0.9, 0.1], [0.9, 1.0, 0.1], [0.1, 0.1, 1.0]])
        clusters = single_linkage_clusters(corr, threshold=0.80)
        assert len(clusters) == 2
        assert [0, 1] in clusters

    def test_correlazione_negativa_forte_accorpa_comunque(self):
        """Si accorpa su |rho|: due mercati opposti dicono la stessa cosa."""
        corr = np.array([[1.0, -0.95], [-0.95, 1.0]])
        assert len(single_linkage_clusters(corr, threshold=0.80)) == 1

    def test_nessuna_correlazione_lascia_tutti_separati(self):
        corr = np.eye(4)
        assert len(single_linkage_clusters(corr, threshold=0.80)) == 4

    def test_il_clustering_riduce_le_prove_effettive(self):
        """E' il meccanismo che limita la maledizione dell'ottimizzatore."""
        corr = np.full((11, 11), 0.85)
        np.fill_diagonal(corr, 1.0)
        assert len(single_linkage_clusters(corr, threshold=0.80)) == 1
