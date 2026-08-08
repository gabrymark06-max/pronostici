"""Test dell'appaiamento fra football-data e the-odds-api.

E' il punto in cui il job `finalize` puo' rompersi in silenzio: appaiare la
partita sbagliata significa costruire il pronostico definitivo sulle quote di
un'altra partita. Meglio nessun appaiamento che uno sbagliato, ed e' cio' che
questi test fissano.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from pronostici.matching import normalize, pair_events, similarity


@dataclass(frozen=True)
class FakeMatch:
    match_id: int
    home_name: str
    away_name: str
    date: datetime


@dataclass(frozen=True)
class FakeEvent:
    home_team: str
    away_team: str
    commence_time: str


KICKOFF = datetime(2026, 8, 22, 16, 30, tzinfo=UTC)
KICKOFF_ISO = "2026-08-22T16:30:00Z"


class TestNormalize:
    def test_toglie_sigle_e_cifre(self):
        assert normalize("Como 1907") == "como"
        assert normalize("FC Internazionale Milano") == "internazionale milano"

    def test_toglie_gli_accenti(self):
        assert normalize("Bayern München") == "bayern munchen"

    def test_non_tocca_le_parole_che_distinguono(self):
        assert "united" in normalize("Manchester United FC")
        assert "city" in normalize("Manchester City FC")


class TestSimilarity:
    @pytest.mark.parametrize(
        ("odds_name", "fd_name"),
        [
            ("Inter Milan", "FC Internazionale Milano"),
            ("Man City", "Manchester City FC"),
            ("Wolves", "Wolverhampton Wanderers FC"),
            ("Como", "Como 1907"),
            ("Bayern Munich", "FC Bayern München"),
            ("Paris Saint Germain", "Paris Saint-Germain FC"),
            ("Atletico Madrid", "Club Atlético de Madrid"),
        ],
    )
    def test_la_stessa_squadra_si_riconosce(self, odds_name, fd_name):
        assert similarity(odds_name, fd_name) >= 0.60

    @pytest.mark.parametrize(
        ("a", "b"),
        [
            ("Man City", "Manchester United FC"),
            ("Inter Milan", "AC Milan"),
            ("Real Madrid", "Real Sociedad"),
        ],
    )
    def test_due_squadre_diverse_restano_diverse(self, a, b):
        assert similarity(a, b) < similarity(a, a)

    def test_il_confronto_con_se_stessa_vale_uno(self):
        assert similarity("Como 1907", "Como 1907") == pytest.approx(1.0)


class TestPairEvents:
    MATCHES = [
        FakeMatch(1, "Udinese Calcio", "Como 1907", KICKOFF),
        FakeMatch(2, "FC Internazionale Milano", "AC Monza", KICKOFF),
        FakeMatch(3, "Genoa CFC", "US Lecce", KICKOFF + timedelta(days=1)),
    ]

    def test_appaiamento_normale(self):
        events = [
            FakeEvent("Inter Milan", "Monza", KICKOFF_ISO),
            FakeEvent("Udinese", "Como", KICKOFF_ISO),
        ]
        pairs, unmatched = pair_events(self.MATCHES, events)
        assert pairs == {2: 0, 1: 1}
        assert unmatched == []

    def test_evento_di_un_altro_giorno_non_si_appaia(self):
        events = [FakeEvent("Udinese", "Como", "2026-09-30T16:30:00Z")]
        pairs, unmatched = pair_events(self.MATCHES, events)
        assert pairs == {}
        assert "finestra temporale" in unmatched[0]["reason"]

    def test_squadre_sconosciute_non_si_appaiano(self):
        events = [FakeEvent("Real Madrid", "Barcelona", KICKOFF_ISO)]
        pairs, unmatched = pair_events(self.MATCHES, events)
        assert pairs == {}
        assert len(unmatched) == 1

    def test_appaiamento_uno_a_uno(self):
        """Due eventi non possono finire sulla stessa partita: vince quello
        con il punteggio migliore, l'altro viene riportato."""
        events = [
            FakeEvent("Udinese", "Como", KICKOFF_ISO),
            FakeEvent("Udinese Calcio", "Como 1907", KICKOFF_ISO),
        ]
        pairs, unmatched = pair_events(self.MATCHES, events)
        assert len(pairs) == 1
        assert len(unmatched) == 1

    def test_l_inversione_casa_trasferta_non_si_appaia(self):
        """Se la partita e' la stessa ma i lati sono invertiti, appaiarla
        significherebbe leggere le quote al contrario."""
        events = [FakeEvent("Como", "Udinese", KICKOFF_ISO)]
        pairs, _ = pair_events(self.MATCHES, events)
        assert pairs == {}

    def test_nessun_evento(self):
        assert pair_events(self.MATCHES, []) == ({}, [])
