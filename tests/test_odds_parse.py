"""Test della lettura delle quote.

Nessuna rete: si legge la fixture su disco, come impone il brief 6.3
("in sviluppo e nei test: mai la rete").
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pronostici.sources.odds_parse import event_probabilities, parse_league

FIXTURE = Path(__file__).parent / "fixtures" / "odds_serie_a.json"


@pytest.fixture(scope="module")
def events() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestEventProbabilities:
    def test_1x2_e_una_partizione(self, events):
        snap = event_probabilities(events[0])
        total = (
            snap.probabilities["1x2_home"]
            + snap.probabilities["1x2_draw"]
            + snap.probabilities["1x2_away"]
        )
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_over_e_under_si_completano(self, events):
        snap = event_probabilities(events[0])
        for line in (1.5, 2.5):
            assert snap.probabilities[f"over_{line}"] + snap.probabilities[
                f"under_{line}"
            ] == pytest.approx(1.0, abs=1e-9)

    def test_le_linee_fuori_catalogo_sono_ignorate(self, events):
        """2.75 e' una linea asiatica: non esiste una maschera binaria per
        lei, quindi non deve entrare nel riferimento."""
        snap = event_probabilities(events[0])
        assert not any(k.endswith("2.75") for k in snap.probabilities)

    def test_lato_mancante_non_produce_una_linea_a_meta(self, events):
        """Over 4.5 quotato senza il suo Under: senza entrambi i lati non si
        puo' sgonfiare, e mezza linea nel riferimento sarebbe peggio di
        nessuna linea."""
        snap = event_probabilities(events[0])
        assert "over_4.5" not in snap.probabilities
        assert any("4.5" in d for d in snap.dropped)

    def test_il_devig_e_power_non_ingenuo(self, events):
        """beta > 1 su un mercato con margine: e' la firma del metodo power."""
        snap = event_probabilities(events[1])
        assert snap.devig["h2h"]["beta"] > 1.0
        assert snap.devig["h2h"]["overround"] > 1.0

    def test_il_longshot_e_compresso_rispetto_al_naive(self, events):
        """Monza a 12,00 in un mercato con margine: la probabilita' equa deve
        essere sotto la semplice inversa normalizzata."""
        snap = event_probabilities(events[1])
        inv = [1 / 1.26, 1 / 6.45, 1 / 11.75]
        naive_away = inv[2] / sum(inv)
        assert snap.probabilities["1x2_away"] < naive_away

    def test_un_solo_bookmaker_non_e_un_consenso(self, events):
        snap = event_probabilities(events[2])
        assert not snap.is_usable
        assert snap.probabilities == {}
        assert snap.dropped

    def test_evento_vuoto_non_solleva(self):
        snap = event_probabilities({"id": "x", "bookmakers": []})
        assert not snap.is_usable

    def test_i_bookmaker_sono_contati(self, events):
        assert event_probabilities(events[0]).n_bookmakers == 3


class TestParseLeague:
    def test_ritorna_uno_snapshot_per_evento(self, events):
        snaps = parse_league(events)
        assert len(snaps) == len(events)

    def test_le_chiavi_sono_le_nostre(self, events):
        """Il resto del sistema non deve sapere che esiste the-odds-api."""
        snap = parse_league(events)[0]
        assert set(snap.probabilities) >= {
            "1x2_home", "1x2_draw", "1x2_away", "over_2.5", "under_2.5",
        }

    def test_serializzabile(self, events):
        payload = parse_league(events)[0].to_dict()
        assert json.loads(json.dumps(payload))["n_bookmakers"] == 3
