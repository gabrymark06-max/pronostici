"""Test di `settle`: l'esito, lo skill realizzato, e l'idempotenza.

Lo skill realizzato e' la metrica di testa del progetto (ricerca 10.1). Il
test che conta piu' di tutti e' l'ultimo: su previsioni **calibrate per
costruzione**, la media dello skill realizzato deve avvicinarsi alla media
dello score dichiarato. Se questa relazione non vale nel codice, non vale
neanche nella pagina "Come stiamo andando", e quella pagina e' il prodotto.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pytest

from pronostici import ledger
from pronostici.jobs.settle import (
    bucket_of,
    build_accuracy,
    outcome_of,
    realized_skill,
    run,
)
from pronostici.model.selection import directional_score, kl_binary
from tests.test_ledger import FakeMatch, candidate, selection


@dataclass(frozen=True)
class FinishedMatch:
    match_id: int
    competition: str = "SA"
    season: int = 2026
    utc_date: str = "2026-08-22T16:30:00Z"
    home_name: str = "Udinese Calcio"
    away_name: str = "Como 1907"
    ft_home: int = 2
    ft_away: int = 1

    @property
    def is_finished(self) -> bool:
        return True


class TestOutcome:
    @pytest.mark.parametrize(
        ("key", "home", "away", "expected"),
        [
            ("over_1.5", 2, 1, 1),
            ("over_2.5", 2, 1, 1),  # 3 gol
            ("over_2.5", 1, 1, 0),  # 2 gol
            ("under_2.5", 1, 1, 1),
            ("1x2_home", 2, 1, 1),
            ("1x2_draw", 1, 1, 1),
            ("1x2_away", 0, 3, 1),
            ("dc_1x", 1, 1, 1),
            ("dc_1x", 0, 1, 0),
            ("btts_yes", 2, 1, 1),
            ("btts_no", 2, 0, 1),
            ("cs_2_1", 2, 1, 1),
        ],
    )
    def test_si_legge_dalla_stessa_maschera_della_previsione(
        self, key, home, away, expected
    ):
        assert outcome_of(key, home, away) == expected

    def test_un_risultato_enorme_non_esce_dalla_griglia(self):
        assert outcome_of("over_4.5", 13, 0) == 1

    def test_mercato_sconosciuto(self):
        assert outcome_of("mercato_inventato", 1, 0) is None


class TestSkillRealizzato:
    def test_evento_uscito(self):
        assert realized_skill(0.75, 0.60, 1) == pytest.approx(math.log(0.75 / 0.60))

    def test_evento_non_uscito(self):
        assert realized_skill(0.75, 0.60, 0) == pytest.approx(
            math.log(0.25 / 0.40)
        )

    def test_uno_sbaglio_costa(self):
        assert realized_skill(0.75, 0.60, 0) < 0

    def test_la_media_sotto_p_e_lo_score_dichiarato(self):
        """L'identita' su cui poggia tutta la misurazione: lo score dichiarato
        e' esattamente il valore atteso dello skill realizzato sotto p."""
        p, b = 0.72, 0.61
        atteso = p * realized_skill(p, b, 1) + (1 - p) * realized_skill(p, b, 0)
        assert atteso == pytest.approx(kl_binary(p, b))
        assert atteso == pytest.approx(directional_score(p, b))

    def test_bucket(self):
        assert bucket_of(0.55) == "0.50-0.65"
        assert bucket_of(0.72) == "0.65-0.80"
        assert bucket_of(0.95) == "0.80-1.00"
        assert bucket_of(0.30) is None


class TestJobSettle:
    @staticmethod
    def _seed(match_id: int = 1001, key: str = "over_1.5") -> None:
        ledger.append(
            2026,
            [
                ledger.make_row(
                    phase=ledger.PHASE_PRELIMINARY,
                    match=FakeMatch(match_id=match_id),
                    selection=selection(candidate(key)),
                    model_weight=1.0,
                    source="model_only",
                )
            ],
        )

    @staticmethod
    def _patch_archive(monkeypatch, matches):
        import pronostici.jobs.settle as mod

        monkeypatch.setattr(mod, "load_all", lambda code: matches if code == "SA" else [])

    def test_riempie_esito_e_skill(self, data_dir, monkeypatch):
        self._seed()
        self._patch_archive(monkeypatch, [FinishedMatch(1001)])
        report = run(["SA"])
        assert report["rows_settled"] == 1
        row = ledger.load_season(2026)[0]
        assert row["outcome"] == 1  # 2-1 -> Over 1.5 uscito
        assert row["ft_home"] == 2
        assert row["skill_realized"] == pytest.approx(
            math.log(row["p"] / row["reference"]), abs=1e-5
        )

    def test_idempotente(self, data_dir, monkeypatch):
        self._seed()
        self._patch_archive(monkeypatch, [FinishedMatch(1001)])
        run(["SA"])
        before = ledger.load_season(2026)
        second = run(["SA"])
        assert second["rows_settled"] == 0
        assert second["ledger_rows_changed"] == 0
        assert ledger.load_season(2026) == before

    def test_partita_non_ancora_giocata_resta_aperta(self, data_dir, monkeypatch):
        self._seed()
        self._patch_archive(monkeypatch, [])
        report = run(["SA"])
        assert report["rows_settled"] == 0
        assert report["awaiting_result"] == 1
        assert ledger.load_season(2026)[0]["outcome"] is None

    def test_una_riga_di_silenzio_non_ha_esito_ma_e_contata(self, data_dir, monkeypatch):
        ledger.append(
            2026,
            [
                ledger.make_row(
                    phase=ledger.PHASE_PRELIMINARY,
                    match=FakeMatch(match_id=2002),
                    selection=selection(None, "S_min"),
                    model_weight=1.0,
                    source="model_only",
                )
            ],
        )
        self._patch_archive(monkeypatch, [FinishedMatch(2002)])
        report = run(["SA"])
        row = ledger.load_season(2026)[0]
        assert row["outcome"] is None
        assert row["ft_home"] == 2  # il risultato c'e' comunque
        assert report["silence"]["preliminary"]["rate"] == 1.0
        assert report["silence"]["preliminary"]["by_reason"] == {"S_min": 1}

    def test_dry_run_non_scrive(self, data_dir, monkeypatch):
        self._seed()
        self._patch_archive(monkeypatch, [FinishedMatch(1001)])
        run(["SA"], dry_run=True)
        assert ledger.load_season(2026)[0]["outcome"] is None


class TestCalibrazione:
    def test_dichiarato_e_realizzato_coincidono_su_previsioni_calibrate(self):
        """La verifica della ricerca 10.1, in piccolo.

        Si generano esiti **dalla stessa p** che dichiariamo: se il conto e'
        giusto, le due medie devono coincidere entro l'errore standard. Se un
        giorno la pagina "Come stiamo andando" mostrera' un divario, sara' un
        difetto del modello, non di questa aritmetica.
        """
        rng = np.random.default_rng(20260808)
        n = 20000
        p = rng.uniform(0.52, 0.92, n)
        b = np.clip(p - rng.uniform(0.02, 0.15, n), 0.05, 0.95)
        outcomes = rng.random(n) < p

        coppie = list(zip(p, b, strict=True))
        dichiarato = float(np.mean([kl_binary(pi, bi) for pi, bi in coppie]))
        realizzato = float(
            np.mean(
                [
                    realized_skill(pi, bi, int(o))
                    for pi, bi, o in zip(p, b, outcomes, strict=True)
                ]
            )
        )
        assert realizzato == pytest.approx(dichiarato, abs=0.005)

    def test_la_sovraconfidenza_si_vede(self):
        """Previsioni gonfiate: il realizzato crolla sotto il dichiarato. E'
        il segnale che lo shrinkage e' troppo debole."""
        rng = np.random.default_rng(1)
        n = 20000
        vera = rng.uniform(0.45, 0.80, n)
        dichiarata = np.clip(vera * 1.25, 0.01, 0.99)
        b = np.clip(vera - 0.08, 0.05, 0.95)
        outcomes = rng.random(n) < vera

        coppie = list(zip(dichiarata, b, strict=True))
        dichiarato = float(np.mean([kl_binary(pi, bi) for pi, bi in coppie]))
        realizzato = float(
            np.mean(
                [
                    realized_skill(pi, bi, int(o))
                    for pi, bi, o in zip(dichiarata, b, outcomes, strict=True)
                ]
            )
        )
        assert realizzato < dichiarato * 0.7


class TestAccuracy:
    def test_il_registro_dal_vivo_non_si_mescola_con_altro(self, data_dir):
        ledger.append(
            2026,
            [
                ledger.make_row(
                    phase=ledger.PHASE_PRELIMINARY,
                    match=FakeMatch(match_id=i),
                    selection=selection(candidate("over_1.5", p=0.70)),
                    model_weight=1.0,
                    source="model_only",
                )
                for i in range(1, 6)
            ],
        )
        payload = build_accuracy(ledger.load_all_seasons())
        assert payload["live"]["n"] == 0  # nessuno ancora chiuso
        assert payload["progress_to_500"] == {"published": 5, "target": 500}
        assert "backtest" not in payload


class TestEsitoSulleSchede:
    """`settle` scrive l'esito anche nei file giornalieri: e' l'unica
    scrittura ammessa dopo il fischio d'inizio."""

    @staticmethod
    def _riga(match_id: int, phase: str, key: str):
        return ledger.make_row(
            phase=phase,
            match=FakeMatch(match_id=match_id),
            selection=selection(candidate(key)),
            model_weight=1.0 if phase == ledger.PHASE_PRELIMINARY else 0.35,
            source="model_only",
        )

    def test_l_esito_stampato_e_quello_della_fase_mostrata(self, data_dir, monkeypatch):
        """La partita ha due righe con mercati diversi. La scheda mostra il
        definitivo, quindi l'esito stampato deve essere quello del definitivo:
        stampare l'altro sarebbe un numero vero sotto un pronostico diverso.
        """
        import pronostici.jobs.settle as mod
        from pronostici import fixtures as fx

        # preliminare: Over 2.5 (con 2-1 esce);  definitivo: Under 2.5 (non esce)
        ledger.append(
            2026,
            [
                self._riga(3003, ledger.PHASE_PRELIMINARY, "over_2.5"),
                self._riga(3003, ledger.PHASE_DEFINITIVE, "under_2.5"),
            ],
        )
        fx.upsert_day(
            "2026-08-22",
            [
                {
                    "match_id": 3003,
                    "utc_date": "2026-08-22T16:30:00Z",
                    "phase": ledger.PHASE_DEFINITIVE,
                    "prediction": {"key": "under_2.5"},
                    "silence": None,
                }
            ],
        )
        monkeypatch.setattr(mod, "load_all", lambda code: [FinishedMatch(3003)])
        mod.run(["SA"])

        entry = fx.load_day("2026-08-22")["fixtures"][0]
        assert entry["result"] == {"home": 2, "away": 1}
        # 2-1 = 3 gol: Under 2.5 NON esce.
        assert entry["outcome"] == 0
