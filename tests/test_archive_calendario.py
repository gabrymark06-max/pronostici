"""Il calendario cambia, e per anni l'archivio non se n'e' accorto.

`information_score` conta solo il risultato: gol finali, primo tempo, stato
concluso. Una partita futura vale zero prima e zero dopo che la fonte ne
pubblichi l'orario, quindi `nuovo > vecchio` era falso e il record restava
com'era la prima volta che l'avevamo visto.

Misurato il 25 agosto 2026: 1938 partite future su 2936 avevano in archivio un
orario che football-data aveva gia' corretto.
"""

from __future__ import annotations

from dataclasses import replace

from pronostici.archive import Match, _perche_aggiornare


def _partita(**cambi) -> Match:
    base = Match(
        match_id=1,
        competition="BSA",
        season=2026,
        utc_date="2026-08-29T00:00:00Z",
        status="SCHEDULED",
        matchday=22,
        stage="REGULAR_SEASON",
        home_id=10,
        home_name="CA Mineiro",
        home_tla="CAM",
        home_crest=None,
        away_id=11,
        away_name="EC Vitória",
        away_tla="VIT",
        away_crest=None,
        ft_home=None,
        ft_away=None,
        ht_home=None,
        ht_away=None,
        venue=None,
        referee=None,
        first_seen="2026-05-01T00:00:00Z",
    )
    return replace(base, **cambi)


class TestOrarioPubblicatoDopo:
    """Il caso che ha rotto le quote del Brasileirao.

    L'abbinamento con la fonte delle quote tollera sei ore, e fra mezzanotte e
    un calcio d'inizio alle 23:00 ce ne sono ventitre: nessuna partita si
    agganciava, e nessuna aveva un prezzo.
    """

    def test_da_mezzanotte_a_un_orario_vero_e_una_notizia(self) -> None:
        vecchio = _partita()
        nuovo = _partita(utc_date="2026-08-29T21:30:00Z", status="TIMED")
        assert _perche_aggiornare(nuovo, vecchio) == "calendario"

    def test_il_solo_cambio_di_stato_basta(self) -> None:
        vecchio = _partita()
        nuovo = _partita(status="TIMED")
        assert _perche_aggiornare(nuovo, vecchio) == "calendario"

    def test_un_rinvio_si_registra(self) -> None:
        vecchio = _partita(utc_date="2026-08-29T21:30:00Z", status="TIMED")
        nuovo = _partita(utc_date="2026-09-10T21:30:00Z", status="POSTPONED")
        assert _perche_aggiornare(nuovo, vecchio) == "calendario"

    def test_se_non_cambia_niente_non_si_riscrive(self) -> None:
        """Riscrivere per nulla renderebbe illeggibile il registro pubblico."""
        assert _perche_aggiornare(_partita(), _partita()) is None


class TestIlPassatoNonSiRiprogramma:
    """Su una partita conclusa il calendario non si tocca.

    La fonte non riprogramma il passato: una data che cambia li' e' un errore
    di lettura, non una notizia. E soprattutto il record con il risultato non
    deve poter essere sostituito da uno senza.
    """

    def _conclusa(self, **cambi) -> Match:
        return _partita(
            status="FINISHED", ft_home=2, ft_away=1, ht_home=1, ht_away=0, **cambi
        )

    def test_una_data_diversa_su_una_conclusa_si_ignora(self) -> None:
        vecchio = self._conclusa()
        nuovo = self._conclusa(utc_date="2026-08-30T00:00:00Z")
        assert _perche_aggiornare(nuovo, vecchio) is None

    def test_un_record_senza_risultato_non_cancella_quello_con(self) -> None:
        vecchio = self._conclusa()
        nuovo = _partita(status="TIMED", utc_date="2026-08-29T21:30:00Z")
        assert _perche_aggiornare(nuovo, vecchio) is None


class TestIlRisultatoVinceComePrima:
    def test_i_gol_finali_aggiornano(self) -> None:
        vecchio = _partita(status="IN_PLAY")
        nuovo = _partita(status="FINISHED", ft_home=2, ft_away=1)
        assert _perche_aggiornare(nuovo, vecchio) == "risultato"
