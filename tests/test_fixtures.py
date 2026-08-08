"""Test dei file giornalieri: il contratto col frontend.

Tre file diversi scrivono lo stesso file (`score`, `finalize`, `settle`), e
per il brief 7.2 c'e' una cosa che non deve poter succedere: che un `score`
notturno riporti a preliminare un pronostico gia' rivisto con le quote.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pronostici import fixtures as fx

DAY = "2026-08-22"
NOW = datetime(2026, 8, 21, 4, 0, tzinfo=UTC)


def entry(
    match_id: int, phase: str, label: str | None, utc: str = "2026-08-22T16:30:00Z"
) -> dict:
    return {
        "match_id": match_id,
        "utc_date": utc,
        "phase": phase,
        "prediction": {"key": "over_1.5", "label": label} if label else None,
        "silence": None if label else {"reason": "S_min"},
    }


class TestUpsertDay:
    def test_scrittura_iniziale(self, data_dir):
        assert fx.upsert_day(DAY, [entry(1, "preliminary", "Over 1.5")], generated_at=NOW)
        payload = fx.load_day(DAY)
        assert payload["total"] == 1
        assert payload["silence_count"] == 0

    def test_conteggio_dei_silenzi(self, data_dir):
        fx.upsert_day(
            DAY,
            [entry(1, "preliminary", "Over 1.5"), entry(2, "preliminary", None)],
            generated_at=NOW,
        )
        assert fx.load_day(DAY)["silence_count"] == 1

    def test_stessi_dati_non_riscrivono_il_file(self, data_dir):
        rows = [entry(1, "preliminary", "Over 1.5")]
        assert fx.upsert_day(DAY, rows, generated_at=NOW) is True
        assert fx.upsert_day(DAY, rows, generated_at=NOW) is False

    def test_il_solo_orario_di_generazione_non_e_un_cambiamento(self, data_dir):
        """Altrimenti ogni notte si produrrebbe un commit che non dice niente,
        e nella cronologia il cambiamento vero non si troverebbe piu'."""
        rows = [entry(1, "preliminary", "Over 1.5")]
        fx.upsert_day(DAY, rows, generated_at=NOW)
        dopo = datetime(2026, 8, 21, 10, 0, tzinfo=UTC)
        assert fx.upsert_day(DAY, rows, generated_at=dopo) is False
        assert fx.load_day(DAY)["generated_at"] == "2026-08-21T04:00:00Z"

    def test_il_definitivo_sostituisce_il_preliminare(self, data_dir):
        fx.upsert_day(DAY, [entry(1, "preliminary", "Over 1.5")], generated_at=NOW)
        fx.upsert_day(DAY, [entry(1, "definitive", "X2")], generated_at=NOW)
        assert fx.load_day(DAY)["fixtures"][0]["prediction"]["label"] == "X2"

    def test_il_preliminare_non_retrocede_il_definitivo(self, data_dir):
        """Il test che protegge la regola di prodotto: una sola revisione, e
        non se la riprende il job della notte dopo."""
        fx.upsert_day(DAY, [entry(1, "definitive", "X2")], generated_at=NOW)
        fx.upsert_day(DAY, [entry(1, "preliminary", "Over 1.5")], generated_at=NOW)
        got = fx.load_day(DAY)["fixtures"][0]
        assert got["phase"] == "definitive"
        assert got["prediction"]["label"] == "X2"

    def test_niente_scritture_dopo_il_fischio_d_inizio(self, data_dir):
        fx.upsert_day(DAY, [entry(1, "preliminary", "Over 1.5")], generated_at=NOW)
        dopo = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
        fx.upsert_day(DAY, [entry(1, "definitive", "X2")], generated_at=dopo)
        assert fx.load_day(DAY)["fixtures"][0]["prediction"]["label"] == "Over 1.5"

    def test_l_esito_e_l_unica_scrittura_ammessa_dopo(self, data_dir):
        fx.upsert_day(DAY, [entry(1, "preliminary", "Over 1.5")], generated_at=NOW)
        dopo = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
        chiuso = {**entry(1, "preliminary", "Over 1.5"), "result": {"home": 2, "away": 1}}
        fx.upsert_day(DAY, [chiuso], generated_at=dopo, allow_after_kickoff=True)
        assert fx.load_day(DAY)["fixtures"][0]["result"] == {"home": 2, "away": 1}

    def test_una_partita_gia_scritta_non_sparisce(self, data_dir):
        """`finalize` tocca solo i campionati che ha quotato: le altre partite
        del giorno devono restare nel file."""
        fx.upsert_day(
            DAY,
            [entry(1, "preliminary", "Over 1.5"), entry(2, "preliminary", "X2")],
            generated_at=NOW,
        )
        fx.upsert_day(DAY, [entry(2, "definitive", "1X")], generated_at=NOW)
        payload = fx.load_day(DAY)
        assert payload["total"] == 2
        assert {f["match_id"] for f in payload["fixtures"]} == {1, 2}

    def test_ordinate_per_orario(self, data_dir):
        fx.upsert_day(
            DAY,
            [
                entry(1, "preliminary", "A", "2026-08-22T18:45:00Z"),
                entry(2, "preliminary", "B", "2026-08-22T16:30:00Z"),
            ],
            generated_at=NOW,
        )
        assert [f["match_id"] for f in fx.load_day(DAY)["fixtures"]] == [2, 1]
