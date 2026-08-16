"""Cosa consideriamo «finita», e cosa facciamo quando la fonte parla strano.

Questo file nasce da un guasto vero. Il 16 agosto 2026 football-data ha
risposto con un ORARIO al posto dello stato — `"status": "2026-08-16 18:30:00Z"`
— su 147 partite di Brasileirao e Primeira Liga, tutte col punteggio finale
gia' presente. Cinque di quelle erano partite su cui avevamo pubblicato un
pronostico, e il registro non le chiudeva.

Il codice si comportava bene: non chiudeva niente su uno stato che non
riconosce. Ma lo faceva in silenzio, dentro lo stesso contatore delle partite
che semplicemente non si sono ancora giocate. Questi test bloccano entrambe le
meta' del comportamento — la prudenza E la visibilita' — perche' l'una senza
l'altra e' meta' del lavoro.
"""

from __future__ import annotations

from pronostici.archive import Match


def _match(*, status: str, ft_home: int | None, ft_away: int | None) -> Match:
    return Match(
        match_id=1,
        competition="BSA",
        season=2026,
        utc_date="2026-08-15T19:30:00Z",
        status=status,
        matchday=23,
        home_id=1765,
        home_name="Fluminense FC",
        home_tla="FLU",
        home_crest=None,
        away_id=1769,
        away_name="SE Palmeiras",
        away_tla="PAL",
        away_crest=None,
        ft_home=ft_home,
        ft_away=ft_away,
        ht_home=None,
        ht_away=None,
        venue=None,
        referee=None,
        first_seen="2026-08-15",
    )


def test_stato_illeggibile_non_rende_chiudibile_la_partita():
    """Le due asserzioni insieme sono il punto.

    La prima protegge il registro pubblico: un punteggio che c'e' NON basta a
    chiudere, perche' la fonte popola `fullTime` — e perfino `winner` — anche a
    partita in corso, e chiudere li' significherebbe pubblicare come definitivo
    l'esito di una partita al 60'.

    La seconda protegge da noi stessi: senza il flag, quella partita resta
    indistinguibile da una che non si e' ancora giocata, e del guasto non se ne
    accorge nessuno.
    """
    partita = _match(status="2026-08-16 18:30:00Z", ft_home=3, ft_away=2)
    assert partita.is_finished is False
    assert partita.stato_incomprensibile is True


def test_uno_stato_ignoto_senza_punteggio_non_e_un_allarme():
    """Senza punteggio non c'e' nessun esito che stiamo perdendo, e segnalarlo
    riempirebbe il rapporto di rumore su cui poi nessuno guarda piu'."""
    partita = _match(status="BOH", ft_home=None, ft_away=None)
    assert partita.stato_incomprensibile is False


def test_gli_stati_normali_non_finiscono_fra_gli_illeggibili():
    for stato in ("SCHEDULED", "TIMED", "IN_PLAY", "LIVE", "POSTPONED", "FINISHED"):
        partita = _match(status=stato, ft_home=1, ft_away=0)
        assert partita.stato_incomprensibile is False, stato


def test_in_corso_col_punteggio_provvisorio_non_e_finita():
    """Il caso che vieta la scorciatoia «c'e' il punteggio, quindi e' finita»:
    a partita in corso football-data manda gia' `fullTime` col parziale."""
    assert _match(status="IN_PLAY", ft_home=3, ft_away=1).is_finished is False
    assert _match(status="LIVE", ft_home=2, ft_away=2).is_finished is False


def test_finita_col_punteggio_si_chiude():
    assert _match(status="FINISHED", ft_home=2, ft_away=1).is_finished is True
    assert _match(status="AWARDED", ft_home=3, ft_away=0).is_finished is True


def test_finita_senza_punteggio_non_si_chiude():
    """Uno `status` giusto non basta: senza i due numeri non c'e' niente da
    registrare, e `outcome_of` riceverebbe `None`."""
    assert _match(status="FINISHED", ft_home=None, ft_away=None).is_finished is False
