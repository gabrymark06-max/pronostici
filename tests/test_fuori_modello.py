"""Una squadra che il modello non conosce non fa sparire la partita.

Il caso vero: 10 settembre 2026, sei partite di Champions in calendario e due
nel file del giorno. Roma, Como, Lens e Fenerbahce non hanno storico in
Champions nella finestra del modello, `score_fixture` sollevava KeyError e
`score` saltava la fixture. La partita si giocava lo stesso; il sito diceva
di no.

Adesso la squadra sconosciuta vale «una squadra media della competizione», i
numeri si calcolano come sempre, e la scheda esce in silenzio con il suo
motivo. Il silenzio e' la parte che conta: un prior non e' una previsione, e
su un prior non si consiglia niente.
"""

from __future__ import annotations

import numpy as np
import pytest

from pronostici.archive import Match
from pronostici.model.bootstrap import BootstrapResult
from pronostici.model.dixon_coles import DCParams
from pronostici.pipeline import _silence_sentence, score_fixture

SQUADRE = ("Alfa", "Beta", "Gamma", "Delta")


@pytest.fixture
def boot() -> BootstrapResult:
    """Un bootstrap piccolo ma vero: quattro squadre, venti draw."""
    rng = np.random.default_rng(7)
    n, draws = len(SQUADRE), 20
    attack = rng.normal(0.0, 0.25, size=(draws, n))
    defence = rng.normal(0.0, 0.25, size=(draws, n))
    home_adv = np.full(draws, 0.25)
    rho = np.full(draws, -0.05)
    point = DCParams(
        attack=attack.mean(axis=0),
        defence=defence.mean(axis=0),
        home_adv=0.25,
        rho=-0.05,
        teams=SQUADRE,
    )
    return BootstrapResult(
        point=point,
        attack=attack,
        defence=defence,
        home_adv=home_adv,
        rho=rho,
        teams=SQUADRE,
        converged=draws,
        seed=7,
    )


def _partita(casa: str, ospite: str) -> Match:
    return Match(
        match_id=1,
        competition="CL",
        season=2026,
        utc_date="2026-09-10T19:00:00Z",
        status="TIMED",
        matchday=1,
        home_id=1,
        home_name=casa,
        home_tla=None,
        home_crest=None,
        away_id=2,
        away_name=ospite,
        away_tla=None,
        away_crest=None,
        ft_home=None,
        ft_away=None,
        ht_home=None,
        ht_away=None,
        venue=None,
        referee=None,
        first_seen="2026-09-01T00:00:00Z",
    )


BASE = {"1x2_home": 0.45, "1x2_draw": 0.27, "1x2_away": 0.28}


def test_la_squadra_media_ha_i_parametri_medi(boot):
    """Il prior e' la media delle colonne, draw per draw."""
    att, dif = boot._params("Squadra Mai Vista")
    assert att.shape == (boot.draws,)
    assert np.allclose(att, boot.attack.mean(axis=1))
    assert np.allclose(dif, boot.defence.mean(axis=1))


def test_una_squadra_nota_non_cambia(boot):
    att, dif = boot._params("Beta")
    assert np.allclose(att, boot.attack[:, 1])
    assert np.allclose(dif, boot.defence[:, 1])


def test_la_partita_non_sparisce_piu(boot):
    """Prima: KeyError, e `score` la saltava. Adesso: una FixtureScore."""
    scored = score_fixture(_partita("AS Roma", "Alfa"), boot, BASE)
    assert scored.match.home_name == "AS Roma"
    assert scored.lam_home > 0 and scored.lam_away > 0


def test_ma_esce_in_silenzio_col_suo_motivo(boot):
    """Un prior non e' una previsione: non si consiglia niente."""
    scored = score_fixture(_partita("AS Roma", "Alfa"), boot, BASE)
    assert scored.selection.is_silent
    assert scored.selection.silence_reason == "fuori_modello"
    assert scored.selection.runners_up == []


def test_la_frase_fa_il_nome(boot):
    """«Una squadra» non spiega niente; «AS Roma» spiega tutto."""
    scored = score_fixture(_partita("AS Roma", "Alfa"), boot, BASE)
    frase = _silence_sentence(scored.match, scored.selection, boot, with_odds=False)
    assert frase.startswith("AS Roma non ha ancora giocato")
    assert "squadra media" in frase


def test_con_due_sconosciute_le_nomina_tutte_e_due(boot):
    scored = score_fixture(_partita("Fenerbahçe SK", "AS Roma"), boot, BASE)
    frase = _silence_sentence(scored.match, scored.selection, boot, with_odds=False)
    assert frase.startswith("Fenerbahçe SK e AS Roma non hanno")


def test_due_squadre_note_si_comportano_come_prima(boot):
    """La strada normale non deve accorgersi di niente."""
    scored = score_fixture(_partita("Alfa", "Beta"), boot, BASE)
    assert scored.selection.silence_reason != "fuori_modello"


def test_conosciuta_contro_sconosciuta_usa_i_parametri_veri_della_nota(boot):
    """Como-Lipsia: il Lipsia resta il Lipsia, e' il Como che diventa medio.

    Se anche la squadra nota venisse appiattita sulla media, due partite con
    una sconosciuta avrebbero sempre gli stessi gol attesi — ed e' proprio il
    sintomo che si e' visto sui dati veri fra Fenerbahce-Roma e
    Manchester United-Sabah, dove le sconosciute erano tutte e quattro.
    """
    contro_forte = score_fixture(_partita("Nuova", "Alfa"), boot, BASE)
    contro_altra = score_fixture(_partita("Nuova", "Gamma"), boot, BASE)
    assert contro_forte.lam_away != pytest.approx(contro_altra.lam_away)
