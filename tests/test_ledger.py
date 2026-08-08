"""Test del registro: le due verita', e l'immutabilita' del passato.

Il prodotto promette una cosa sola che nessun concorrente promette: quello che
abbiamo detto prima della partita e' quello che riportiamo dopo. Qui si fissa
in codice, perche' una promessa senza test e' una buona intenzione.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import pytest

from pronostici import ledger
from pronostici.model.selection import Candidate, Selection


@dataclass(frozen=True)
class FakeMatch:
    match_id: int = 1001
    competition: str = "SA"
    season: int = 2026
    utc_date: str = "2026-08-22T16:30:00Z"
    home_name: str = "Udinese Calcio"
    away_name: str = "Como 1907"


def candidate(key: str = "over_1.5", p: float = 0.72, score: float = 0.03) -> Candidate:
    return Candidate(
        key=key,
        family="over_under",
        label=f"etichetta {key}",
        p_hat=p + 0.02,
        sigma=0.05,
        p5=p - 0.06,
        p95=p + 0.06,
        p_tilde=p,
        alpha=0.8,
        reference=0.60,
        score=score,
        passes_p_min=True,
        passes_sigma_max=True,
        passes_s_min=True,
    )


def selection(pick: Candidate | None, reason: str | None = None) -> Selection:
    return Selection(
        pick=pick,
        silence_reason=reason,
        n_candidates=90,
        n_clusters=5,
        cluster_members=[],
        filter_bites={"p_min": 60, "sigma_max": 0, "S_min": 25},
    )


class TestDueRighePermanenti:
    def test_preliminare_e_definitivo_convivono(self, data_dir):
        match = FakeMatch()
        ledger.append(
            2026,
            [
                ledger.make_row(
                    phase=ledger.PHASE_PRELIMINARY,
                    match=match,
                    selection=selection(candidate("over_1.5")),
                    model_weight=1.0,
                    source="model_only",
                )
            ],
        )
        previous = ledger.load_season(2026)[0]
        ledger.append(
            2026,
            [
                ledger.make_row(
                    phase=ledger.PHASE_DEFINITIVE,
                    match=match,
                    selection=selection(candidate("dc_1x", p=0.80)),
                    model_weight=0.35,
                    source="blended_with_odds",
                    previous=previous,
                )
            ],
        )
        rows = ledger.load_season(2026)
        assert len(rows) == 2
        # Il preliminare non e' stato toccato: e' il punto di tutto.
        assert rows[0]["market_key"] == "over_1.5"
        assert rows[0]["model_weight"] == 1.0
        assert rows[1]["market_key"] == "dc_1x"
        assert rows[1]["previous_market_key"] == "over_1.5"
        assert rows[1]["transition"] == ledger.TRANSITION_CHANGED

    def test_riesecuzione_non_duplica(self, data_dir):
        match = FakeMatch()
        row = ledger.make_row(
            phase=ledger.PHASE_PRELIMINARY,
            match=match,
            selection=selection(candidate()),
            model_weight=1.0,
            source="model_only",
        )
        assert ledger.append(2026, [row]) == 1
        assert ledger.append(2026, [row]) == 0
        assert len(ledger.load_season(2026)) == 1

    def test_una_sola_finalizzazione_per_partita(self, data_dir):
        match = FakeMatch()
        ledger.append(
            2026,
            [
                ledger.make_row(
                    phase=ledger.PHASE_DEFINITIVE,
                    match=match,
                    selection=selection(candidate()),
                    model_weight=0.35,
                    source="blended_with_odds",
                )
            ],
        )
        assert ledger.has_phase(2026, match.match_id, ledger.PHASE_DEFINITIVE)
        assert not ledger.has_phase(2026, match.match_id, ledger.PHASE_PRELIMINARY)

    def test_lo_score_dichiarato_e_lo_skill_atteso(self, data_dir):
        row = ledger.make_row(
            phase=ledger.PHASE_PRELIMINARY,
            match=FakeMatch(),
            selection=selection(candidate(score=0.0412)),
            model_weight=1.0,
            source="model_only",
        )
        assert row.skill_declared == row.score == pytest.approx(0.0412)


class TestTransizioni:
    def test_prima_volta(self):
        assert (
            ledger.classify_transition(None, selection(candidate()))
            == ledger.TRANSITION_FIRST
        )

    def test_confermato(self):
        previous = {"market_key": "over_1.5"}
        assert (
            ledger.classify_transition(previous, selection(candidate("over_1.5")))
            == ledger.TRANSITION_CONFIRMED
        )

    def test_cambiato(self):
        previous = {"market_key": "over_2.5"}
        assert (
            ledger.classify_transition(previous, selection(candidate("over_1.5")))
            == ledger.TRANSITION_CHANGED
        )

    def test_da_pronostico_a_silenzio(self):
        """La transizione che, secondo il brief, guadagna piu' fiducia di
        qualunque altra schermata del prodotto."""
        previous = {"market_key": "over_2.5"}
        assert (
            ledger.classify_transition(previous, selection(None, "S_min"))
            == ledger.TRANSITION_TO_SILENCE
        )

    def test_da_silenzio_a_pronostico(self):
        previous = {"market_key": None, "silence_reason": "S_min"}
        assert (
            ledger.classify_transition(previous, selection(candidate()))
            == ledger.TRANSITION_FROM_SILENCE
        )

    def test_silenzio_confermato(self):
        previous = {"market_key": None, "silence_reason": "S_min"}
        assert (
            ledger.classify_transition(previous, selection(None, "S_min"))
            == ledger.TRANSITION_STILL_SILENT
        )


class TestImmutabilita:
    def _seed(self) -> None:
        ledger.append(
            2026,
            [
                ledger.make_row(
                    phase=ledger.PHASE_PRELIMINARY,
                    match=FakeMatch(),
                    selection=selection(candidate()),
                    model_weight=1.0,
                    source="model_only",
                )
            ],
        )

    def test_settle_riempie_solo_i_campi_vuoti(self, data_dir):
        self._seed()
        pid = ledger.prediction_id(1001, ledger.PHASE_PRELIMINARY)
        assert ledger.apply_settlements(
            2026, {pid: {"outcome": 1, "ft_home": 2, "ft_away": 1}}
        ) == 1
        row = ledger.load_season(2026)[0]
        assert (row["outcome"], row["ft_home"], row["ft_away"]) == (1, 2, 1)

    def test_un_esito_gia_registrato_non_cambia(self, data_dir):
        self._seed()
        pid = ledger.prediction_id(1001, ledger.PHASE_PRELIMINARY)
        ledger.apply_settlements(2026, {pid: {"outcome": 1}})
        # Secondo passaggio con un esito diverso: deve essere una non-azione.
        assert ledger.apply_settlements(2026, {pid: {"outcome": 0}}) == 0
        assert ledger.load_season(2026)[0]["outcome"] == 1

    def test_settle_non_puo_toccare_il_pronostico(self, data_dir):
        self._seed()
        pid = ledger.prediction_id(1001, ledger.PHASE_PRELIMINARY)
        with pytest.raises(ledger.LedgerImmutabilityError):
            ledger.apply_settlements(2026, {pid: {"p": 0.99}})
        with pytest.raises(ledger.LedgerImmutabilityError):
            ledger.apply_settlements(2026, {pid: {"market_key": "over_4.5"}})

    def test_le_altre_righe_restano_byte_per_byte(self, data_dir):
        self._seed()
        match_b = replace(FakeMatch(), match_id=1002)
        ledger.append(
            2026,
            [
                ledger.make_row(
                    phase=ledger.PHASE_PRELIMINARY,
                    match=match_b,
                    selection=selection(candidate("btts_yes")),
                    model_weight=1.0,
                    source="model_only",
                )
            ],
        )
        before = ledger.load_season(2026)[1]
        ledger.apply_settlements(
            2026,
            {ledger.prediction_id(1001, ledger.PHASE_PRELIMINARY): {"outcome": 1}},
        )
        assert ledger.load_season(2026)[1] == before
