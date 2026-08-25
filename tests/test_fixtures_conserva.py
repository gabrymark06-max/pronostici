"""Chi riscrive una partita deve conservare cio' che non e' suo.

IL GUASTO CHE QUESTI TEST DESCRIVONO E' GIA' SUCCESSO. Il 24 agosto 2026 il
blocco del contorno e' stato rinominato da `sofascore` a `contorno` nel job che
lo scrive, e `CAMPI_DI_ALTRI` e' rimasta indietro. La notte dopo `score` ha
riscritto i file dal solo modello e ha portato via formazioni, mercati estesi e
stime sui giocatori da 41 partite su 43.

Niente e' diventato rosso: i file erano validi, semplicemente piu' poveri. Ce ne
saremmo accorti aprendo una scheda partita — e le formazioni di quei giorni
sarebbero state perse, perche' esistono solo prima del fischio d'inizio.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pronostici import fixtures as fx


def _partita(**extra) -> dict:
    base = {
        "match_id": 1,
        "competition": "SA",
        "utc_date": "2026-12-01T20:45:00Z",
        "home": {"name": "Bologna FC 1909", "tla": "BOL", "crest": None},
        "away": {"name": "SS Lazio", "tla": "LAZ", "crest": None},
        "prediction": {"p": 0.5},
        "silence": None,
    }
    return {**base, **extra}


class TestIlNomeStaInUnPostoSolo:
    def test_il_job_e_l_archivio_usano_la_stessa_costante(self) -> None:
        """Se il nome vivesse in due posti, potrebbero divergere. E' successo."""
        from pronostici.jobs import contorno as job

        assert job.CAMPO_CONTORNO is fx.CAMPO_CONTORNO

    def test_il_campo_del_contorno_e_fra_quelli_da_conservare(self) -> None:
        assert fx.CAMPO_CONTORNO in fx.CAMPI_DI_ALTRI

    def test_il_vecchio_nome_resta_protetto(self) -> None:
        """I file scritti fino al 23 agosto 2026 contengono `sofascore`.

        Toglierlo dalla lista li ripulirebbe alla prima riscrittura: sono dati
        veri, letti davvero da Sofascore, e contengono cose che le fonti nuove
        non pubblicano.
        """
        assert "sofascore" in fx.CAMPI_DI_ALTRI


class TestUnaRiscritturaNonPortaViaNiente:
    def test_il_contorno_sopravvive_al_giro_notturno(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(fx, "FIXTURES_DIR", tmp_path)
        giorno = "2026-12-01"
        contorno = {"letto": "2026-11-30T07:00:00Z", "formazioni": {"confermate": False}}

        fx.upsert_day(giorno, [_partita(**{fx.CAMPO_CONTORNO: contorno})])
        # `score` ricostruisce dal solo modello: non sa niente del contorno.
        fx.upsert_day(giorno, [_partita()])

        scritto = fx.load_day(giorno)["fixtures"][0]
        assert scritto.get(fx.CAMPO_CONTORNO) == contorno

    def test_e_lo_stesso_vale_per_le_quote(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(fx, "FIXTURES_DIR", tmp_path)
        giorno = "2026-12-01"
        odds = {"market_p": {"1x2_home": 0.5}}

        fx.upsert_day(giorno, [_partita(odds=odds)])
        fx.upsert_day(giorno, [_partita()])

        assert fx.load_day(giorno)["fixtures"][0].get("odds") == odds

    def test_ma_un_contorno_nuovo_sostituisce_quello_vecchio(
        self, tmp_path, monkeypatch
    ) -> None:
        """Conservare non vuol dire congelare: chi possiede il campo lo aggiorna."""
        monkeypatch.setattr(fx, "FIXTURES_DIR", tmp_path)
        giorno = "2026-12-01"
        fx.upsert_day(giorno, [_partita(**{fx.CAMPO_CONTORNO: {"letto": "vecchio"}})])
        fx.upsert_day(
            giorno,
            [_partita(**{fx.CAMPO_CONTORNO: {"letto": "nuovo"}})],
            generated_at=datetime(2026, 11, 30, tzinfo=UTC),
        )
        atteso = {"letto": "nuovo"}
        assert fx.load_day(giorno)["fixtures"][0][fx.CAMPO_CONTORNO] == atteso


class TestPartiteRiprogrammate:
    """Una partita rinviata non deve restare anche nel giorno da cui e' partita.

    `upsert_day` fonde per `match_id` dentro UN giorno solo: quando la data
    cambia, la voce vecchia resta dov'era e la stessa partita compare due volte,
    in due giorni diversi e con due orari diversi. Misurato il 25 agosto 2026:
    nove partite doppie.
    """

    def test_la_voce_nel_giorno_vecchio_sparisce(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(fx, "FIXTURES_DIR", tmp_path)
        fx.upsert_day("2026-12-01", [_partita()])
        fx.upsert_day("2026-12-02", [_partita(utc_date="2026-12-02T20:45:00Z")])
        assert len(fx.load_day("2026-12-01")["fixtures"]) == 1

        ripuliti = fx.rimuovi_fantasmi({1: "2026-12-02"})

        assert ripuliti == ["2026-12-01"]
        assert fx.load_day("2026-12-01")["fixtures"] == []
        assert len(fx.load_day("2026-12-02")["fixtures"]) == 1

    def test_i_conteggi_in_testa_seguono(self, tmp_path, monkeypatch) -> None:
        """`total` e `silence_count` sono dichiarati in cima al file.

        Lasciarli fermi dopo una pulizia significherebbe un file che dice di
        contenere piu' partite di quante ne ha.
        """
        monkeypatch.setattr(fx, "FIXTURES_DIR", tmp_path)
        fx.upsert_day("2026-12-01", [_partita(), _partita(match_id=2)])
        fx.rimuovi_fantasmi({2: "2026-12-05"})
        letto = fx.load_day("2026-12-01")
        assert letto["total"] == 1 == len(letto["fixtures"])

    def test_una_partita_che_il_giro_non_conosce_non_si_tocca(
        self, tmp_path, monkeypatch
    ) -> None:
        """Sconosciuta vuol dire «non ricostruita adesso», non «da buttare».

        Un giro su una sola competizione non deve poter svuotare i giorni delle
        altre.
        """
        monkeypatch.setattr(fx, "FIXTURES_DIR", tmp_path)
        fx.upsert_day("2026-12-01", [_partita()])
        assert fx.rimuovi_fantasmi({}) == []
        assert len(fx.load_day("2026-12-01")["fixtures"]) == 1
