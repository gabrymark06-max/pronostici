"""Test degli strumenti di lettura del backtest.

Nessuno di questi test guarda dei risultati: verificano che la **regola**
scritta in `docs/protocollo-backtest.md` sia applicata alla lettera, in
particolare il caso che conta di piu' — quello in cui la curva sta fuori
banda e la soglia **non si muove**.
"""

from __future__ import annotations

import numpy as np
import pytest

from pronostici.jobs.backtest import (
    SILENCE_BAND,
    TARGET_SILENCE,
    Accumulator,
    choose_s_min,
    silence_curve,
    skill_summary,
)
from pronostici.model.selection import S_MIN


class TestTau2:
    def test_solo_rumore_non_e_segnale(self):
        """Se la dispersione attorno al riferimento e' tutta rumore di stima,
        `tau^2` deve valere zero: la famiglia non ha risoluzione (protocollo 5).
        """
        rng = np.random.default_rng(0)
        acc = Accumulator()
        for _ in range(5000):
            sigma = 0.10
            acc.add(0.5 + rng.normal(0, sigma), sigma, 0.5)
        assert acc.tau2() == pytest.approx(0.0, abs=0.002)

    def test_segnale_vero_si_vede(self):
        rng = np.random.default_rng(1)
        acc = Accumulator()
        tau_vero, sigma = 0.15, 0.05
        for _ in range(20000):
            vero = 0.5 + rng.normal(0, tau_vero)
            acc.add(vero + rng.normal(0, sigma), sigma, 0.5)
        assert acc.tau2() == pytest.approx(tau_vero**2, rel=0.10)

    def test_non_diventa_mai_negativo(self):
        acc = Accumulator()
        acc.add(0.5, 0.4, 0.5)
        acc.add(0.5, 0.4, 0.5)
        assert acc.tau2() >= 0.0

    def test_pochi_dati(self):
        assert Accumulator().tau2() == 0.0


class TestCurvaDelSilenzio:
    def test_e_monotona_crescente(self):
        """Alzare la soglia non puo' far parlare di piu'."""
        rng = np.random.default_rng(2)
        curve = silence_curve(list(rng.exponential(0.02, 3000)))
        rates = [p["silence_rate"] for p in curve]
        assert rates == sorted(rates)

    def test_soglia_minima_quasi_nessun_silenzio(self):
        curve = silence_curve([0.05] * 100)
        assert curve[0]["silence_rate"] == 0.0

    def test_nessun_dato(self):
        assert silence_curve([]) == []


class TestSceltaDiSMin:
    def test_prende_il_piu_vicino_al_bersaglio(self):
        curve = [
            {"s_min": 0.005, "silence_rate": 0.10},
            {"s_min": 0.010, "silence_rate": 0.24},
            {"s_min": 0.015, "silence_rate": 0.29},
            {"s_min": 0.020, "silence_rate": 0.45},
        ]
        chosen, _ = choose_s_min(curve)
        assert chosen == 0.010

    def test_ignora_i_valori_fuori_banda_anche_se_piu_vicini(self):
        curve = [
            {"s_min": 0.010, "silence_rate": 0.31},  # fuori banda, ma vicino
            {"s_min": 0.008, "silence_rate": 0.16},  # in banda, piu' lontano
        ]
        chosen, _ = choose_s_min(curve)
        assert chosen == 0.008

    def test_curva_tutta_fuori_banda_non_muove_la_soglia(self):
        """Il caso che il protocollo 4.2 prevede esplicitamente: se il sistema
        tace troppo, non si abbassa il criterio — si restringe lo scope."""
        curve = [
            {"s_min": 0.001, "silence_rate": 0.55},
            {"s_min": 0.002, "silence_rate": 0.70},
        ]
        chosen, reason = choose_s_min(curve)
        assert chosen == S_MIN
        assert "scope" in reason

    def test_nessun_dato_non_muove_la_soglia(self):
        chosen, _ = choose_s_min([])
        assert chosen == S_MIN

    def test_la_banda_contiene_il_bersaglio(self):
        assert SILENCE_BAND[0] <= TARGET_SILENCE <= SILENCE_BAND[1]


class TestSkillSummary:
    def test_vuoto(self):
        assert skill_summary([]) == {"n": 0}

    def test_il_divario_e_dichiarato_meno_realizzato(self):
        picks = [
            {"declared": 0.05, "realized": 0.01, "outcome": 1, "p": 0.7},
            {"declared": 0.05, "realized": 0.03, "outcome": 0, "p": 0.7},
        ]
        out = skill_summary(picks)
        assert out["declared_mean"] == pytest.approx(0.05)
        assert out["realized_mean"] == pytest.approx(0.02)
        assert out["gap"] == pytest.approx(0.03)
        assert out["hit_rate"] == 0.5
