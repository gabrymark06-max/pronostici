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


# -- il prestito da un altro campionato -----------------------------------


def _boot(squadre, seed, forte=None, quanto=1.5):
    """Un campionato finto. `forte` e' una squadra spinta sopra la media."""
    rng = np.random.default_rng(seed)
    n, draws = len(squadre), 20
    attack = rng.normal(0.0, 0.25, size=(draws, n))
    defence = rng.normal(0.0, 0.25, size=(draws, n))
    if forte is not None:
        i = squadre.index(forte)
        attack[:, i] += quanto
        defence[:, i] -= quanto
    return BootstrapResult(
        point=DCParams(attack.mean(0), defence.mean(0), 0.25, -0.05, tuple(squadre)),
        attack=attack,
        defence=defence,
        home_adv=np.full(draws, 0.25),
        rho=np.full(draws, -0.05),
        teams=tuple(squadre),
        converged=draws,
        seed=seed,
    )


def test_il_prestito_aggiunge_la_squadra_e_ricorda_da_dove(boot):
    serie_a = _boot(["AS Roma", "Como", "Lecce", "Pisa"], seed=3, forte="AS Roma")
    con = boot.con_prestiti({"SA": serie_a}, ["AS Roma"])
    assert con.knows("AS Roma")
    assert con.prestiti == {"AS Roma": "SA"}
    assert con.attack.shape == (boot.draws, len(SQUADRE) + 1)


def test_chi_domina_il_suo_campionato_arriva_forte_ma_non_dominante(boot):
    """La posizione viaggia, il numero no — e con un freno.

    La Roma finta e' a +1,5 di attacco sopra la Serie A finta: un mostro. In
    Champions deve arrivare sopra la media (la forza si vede), ma NON a +1,5
    (non si copia il numero) e meno di quanto lo direbbe la sola posizione
    (c'e' lo shrink): chi domina un campionato non domina la Champions.
    """
    from pronostici.model.bootstrap import PRESTITO_SHRINK

    serie_a = _boot(["AS Roma", "Como", "Lecce", "Pisa"], seed=3, forte="AS Roma")
    con = boot.con_prestiti({"SA": serie_a}, ["AS Roma"])
    att_roma = con.attack[:, con.teams.index("AS Roma")].mean()
    media_cl = boot.attack.mean()
    sd_cl = boot.attack.std(axis=1).mean()
    assert att_roma > media_cl
    assert att_roma < media_cl + 1.5
    z_in_sa = (
        (serie_a.attack[:, 0] - serie_a.attack.mean(axis=1)) / serie_a.attack.std(axis=1)
    ).mean()
    atteso = media_cl + PRESTITO_SHRINK * z_in_sa * sd_cl
    assert att_roma == pytest.approx(atteso, rel=0.05)


def test_una_squadra_in_prestito_non_e_piu_fuori_modello(boot):
    """Con il prestito c'e' un numero vero: si puo' consigliare."""
    serie_a = _boot(["AS Roma", "Como", "Lecce", "Pisa"], seed=3, forte="AS Roma")
    con = boot.con_prestiti({"SA": serie_a}, ["AS Roma"])
    scored = score_fixture(_partita("AS Roma", "Alfa"), con, BASE)
    assert scored.selection.silence_reason != "fuori_modello"


def test_la_scheda_dice_da_dove_viene_la_forza(boot):
    from pronostici.pipeline import _reasons

    serie_a = _boot(["AS Roma", "Como", "Lecce", "Pisa"], seed=3, forte="AS Roma")
    con = boot.con_prestiti({"SA": serie_a}, ["AS Roma"])
    scored = score_fixture(_partita("AS Roma", "Alfa"), con, BASE)
    frasi = _reasons(
        scored.match, scored.lam_home, scored.lam_away, scored.selection, {}, con
    )
    assert any("La forza di AS Roma viene dalla Serie A" in f for f in frasi)


def test_chi_non_ha_nessun_campionato_resta_fuori_modello(boot):
    """Fenerbahce e Sabah: nessun modello li conosce, e vale la squadra media."""
    serie_a = _boot(["AS Roma", "Como", "Lecce", "Pisa"], seed=3)
    con = boot.con_prestiti({"SA": serie_a}, ["Fenerbahçe SK", "Sabah FK"])
    assert con is boot
    scored = score_fixture(_partita("Fenerbahçe SK", "Sabah FK"), con, BASE)
    assert scored.selection.silence_reason == "fuori_modello"


def test_un_modello_con_draw_diversi_non_si_mescola(boot):
    """Allineare draw per draw ha senso solo se i draw sono gli stessi."""
    rng = np.random.default_rng(1)
    strano = BootstrapResult(
        point=boot.point,
        attack=rng.normal(size=(7, 2)),
        defence=rng.normal(size=(7, 2)),
        home_adv=np.full(7, 0.2),
        rho=np.full(7, 0.0),
        teams=("AS Roma", "Como"),
        converged=7,
        seed=1,
    )
    assert boot.con_prestiti({"SA": strano}, ["AS Roma"]) is boot


def test_il_prestito_non_cambia_le_squadre_di_casa(boot):
    serie_a = _boot(["AS Roma", "Como", "Lecce", "Pisa"], seed=3, forte="AS Roma")
    con = boot.con_prestiti({"SA": serie_a}, ["AS Roma"])
    for i, team in enumerate(SQUADRE):
        assert np.allclose(con.attack[:, i], boot.attack[:, i])
        assert con.teams[i] == team
