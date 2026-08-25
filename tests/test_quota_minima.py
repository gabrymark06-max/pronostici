"""Il pronostico deve pagare almeno 1,30, o non e' un pronostico.

Deciso dal proprietario il 25 agosto 2026, guardando il sito. `P_MIN` ha sempre
avuto un solo verso — non consigliamo cio' che e' meno probabile che no — ma un
esito quasi certo e' un cattivo consiglio per la ragione opposta: non paga
abbastanza perche' valga la pena rischiarci qualcosa. Quel giorno, sui 59
consigli in cartellone, 29 pagavano meno di 1,30 e nove meno di 1,10.

LA PROVA CAMBIA, LA REGOLA NO. Dove il prezzo esiste decide lui. Dove non
esiste si decide solo cio' che si puo' DIMOSTRARE: nessun operatore paga piu'
del prezzo equo, quindi `1/p < 1,30` esclude senza bisogno di vedere niente.
Sul resto non si puo' provare niente in nessuno dei due versi, e passa.
"""

from __future__ import annotations

import numpy as np
import pytest

from pronostici.model.selection import (
    QUOTA_MINIMA,
    Selection,
    build_candidates,
    select,
)

# La probabilita' sopra la quale la quota EQUA non arriva alla soglia. Non e'
# una costante del modulo apposta: e' una conseguenza di `QUOTA_MINIMA`, e
# scriverla come tale qui la lega al numero vero invece che a una copia.
P_EQUA = 1.0 / QUOTA_MINIMA


def _draws(p: float, n: int = 200) -> np.ndarray:
    """Estrazioni bootstrap tutte uguali: sigma zero, nessuno shrinkage."""
    return np.full(n, p)


def _candidato(key: str, p: float, riferimento: float, prezzi=None):
    (c,) = build_candidates({key: _draws(p)}, {key: riferimento}, prezzi=prezzi)
    return c


class TestIlPrezzoVeroDecide:
    def test_una_quota_sotto_la_soglia_esclude(self) -> None:
        c = _candidato("dc_1x", 0.88, 0.80, prezzi={"dc_1x": 1.10})
        assert c.passes_quota_min is False
        assert c.survives is False

    def test_una_quota_sopra_la_soglia_passa(self) -> None:
        c = _candidato("dc_1x", 0.88, 0.80, prezzi={"dc_1x": 1.45})
        assert c.passes_quota_min is True

    def test_esattamente_la_soglia_passa(self) -> None:
        """«Almeno 1,30» include 1,30."""
        c = _candidato("dc_1x", 0.88, 0.80, prezzi={"dc_1x": QUOTA_MINIMA})
        assert c.passes_quota_min is True

    def test_il_prezzo_vero_batte_la_probabilita_anche_quando_la_smentisce(
        self,
    ) -> None:
        """IL CASO CHE UN TETTO SULLA PROBABILITA' ROVINEREBBE.

        Diamo questa scommessa all'88 su 100 — quota equa 1,14 — e un operatore
        la paga 1,45. Se filtrassimo sulla probabilita' la butteremmo via, e
        butteremmo via proprio il caso in cui il mercato ci sta pagando piu' di
        quanto pensiamo che valga.
        """
        c = _candidato("dc_1x", 0.88, 0.80, prezzi={"dc_1x": 1.45})
        assert 1 / c.p_tilde < QUOTA_MINIMA
        assert c.passes_quota_min is True

    def test_e_lo_stesso_al_contrario(self) -> None:
        """Quota equa 1,33 e prezzo vero 1,19: e' il margine, ed e' reale.

        Cinque dei ventinove consigli sotto soglia stavano esattamente qui, e un
        tetto sulla sola probabilita' non li avrebbe visti.
        """
        p = 0.751
        c = _candidato("ag_under_1.5", p, 0.70, prezzi={"ag_under_1.5": 1.19})
        assert 1 / p > QUOTA_MINIMA
        assert c.passes_quota_min is False


class TestSenzaPrezzoSiDeduceQuelloCheSiPuo:
    def test_una_quota_equa_sotto_soglia_esclude_lo_stesso(self) -> None:
        """Nessun operatore paga piu' del prezzo equo: se l'equo non arriva a
        1,30, il vero non ci arriva di sicuro. E' una deduzione, non una quota
        inventata."""
        c = _candidato("hg_under_2.5", 0.911, 0.85)
        assert c.prezzo is None
        assert c.passes_quota_min is False

    def test_una_quota_equa_sopra_soglia_passa(self) -> None:
        """Qui non si puo' provare niente in nessuno dei due versi.

        Il prezzo vero potrebbe stare sotto per via del margine — ma potrebbe
        anche non esserci affatto, ed e' il caso delle combo. La scheda dice
        gia' che nessuno le quota: escluderle in piu' vorrebbe dire tacere due
        volte sulla stessa assenza.
        """
        c = _candidato("combodc_12_over_1.5", 0.705, 0.62)
        assert c.prezzo is None
        assert c.passes_quota_min is True

    def test_il_confine_sta_dove_lo_mette_la_soglia(self) -> None:
        assert _candidato("btts_yes", P_EQUA - 0.001, 0.4).passes_quota_min is True
        assert _candidato("btts_yes", P_EQUA + 0.001, 0.4).passes_quota_min is False


class TestIlFiltroSceglieDavvero:
    """Non basta che il candidato sia marcato: deve cambiare il consigliato."""

    @staticmethod
    def _matrice() -> np.ndarray:
        """Una congiunta piatta 3x3: due mercati qualunque non si accorpano."""
        return np.full((13, 13), 1.0 / 169.0)

    def test_il_consigliato_diventa_quello_che_paga(self) -> None:
        """E IL PREZZO E' L'UNICA COSA CHE CAMBIA FRA I DUE GIRI.

        `dc_1x` ha quota equa 1,33: sopra la soglia, quindi senza prezzi passa
        e vince, perche' e' quello che si discosta di piu'. Con i prezzi si
        scopre che un operatore lo paga 1,19 — il margine — e il consiglio
        passa al secondo, che paga 1,55.
        """
        draws = {"dc_1x": _draws(0.75), "1x2_home": _draws(0.62)}
        rif = {"dc_1x": 0.60, "1x2_home": 0.55}

        senza = select(build_candidates(draws, rif), self._matrice())
        assert senza.pick is not None
        assert senza.pick.key == "dc_1x"

        con = select(
            build_candidates(draws, rif, prezzi={"dc_1x": 1.19, "1x2_home": 1.55}),
            self._matrice(),
        )
        assert con.pick is not None
        assert con.pick.key == "1x2_home"

    def test_se_non_paga_niente_si_tace(self) -> None:
        draws = {"dc_1x": _draws(0.88), "dc_x2": _draws(0.86)}
        rif = {"dc_1x": 0.80, "dc_x2": 0.78}
        fuori = select(
            build_candidates(draws, rif, prezzi={"dc_1x": 1.10, "dc_x2": 1.12}),
            self._matrice(),
        )
        assert fuori.is_silent

    def test_il_silenzio_dice_che_e_stata_la_quota(self) -> None:
        """DUE SILENZI DIVERSI, e il lettore ha diritto di distinguerli.

        «Non abbiamo niente da aggiungere» e «avevamo qualcosa da dire ma non
        conviene giocarla» sono cose opposte. Senza questo motivo la scheda
        scriverebbe la prima anche quando e' vera la seconda.
        """
        draws = {"dc_1x": _draws(0.88)}
        rif = {"dc_1x": 0.80}
        fuori = select(
            build_candidates(draws, rif, prezzi={"dc_1x": 1.10}), self._matrice()
        )
        assert fuori.silence_reason == "quota_min"

    def test_un_silenzio_per_mancanza_di_informazione_resta_quello_di_prima(
        self,
    ) -> None:
        """Se il mercato non aveva niente da dire, la quota non c'entra."""
        draws = {"dc_1x": _draws(0.80)}
        rif = {"dc_1x": 0.80}
        fuori = select(
            build_candidates(draws, rif, prezzi={"dc_1x": 1.10}), self._matrice()
        )
        assert fuori.silence_reason == "S_min"

    def test_quanti_ne_ha_esclusi_sta_scritto(self) -> None:
        draws = {"dc_1x": _draws(0.88), "dc_x2": _draws(0.86)}
        rif = {"dc_1x": 0.80, "dc_x2": 0.78}
        fuori = select(
            build_candidates(draws, rif, prezzi={"dc_1x": 1.10, "dc_x2": 1.12}),
            self._matrice(),
        )
        assert fuori.filter_bites["quota_min"] == 2


class TestIlDatoPortaIlPrezzo:
    def test_il_prezzo_finisce_nel_payload(self) -> None:
        """Il backtest deve poter misurare quanto costa la soglia, e senza il
        prezzo accanto al punteggio non potrebbe."""
        c = _candidato("dc_1x", 0.88, 0.80, prezzi={"dc_1x": 1.45})
        assert c.to_dict()["prezzo"] == 1.45

    def test_dove_non_c_e_non_si_scrive(self) -> None:
        """Uno zero o un `null` in un campo che si chiama «prezzo» si legge
        come «vale zero». Il campo semplicemente non c'e'."""
        c = _candidato("combodc_12_over_1.5", 0.70, 0.62)
        assert "prezzo" not in c.to_dict()


class TestLaSogliaSiPuoSpostare:
    def test_e_un_parametro_non_una_costante_cablata(self) -> None:
        """Il proprietario ha scelto 1,30 e potrebbe scegliere altro: il
        backtest deve poter misurare il costo di ogni soglia."""
        alta = build_candidates(
            {"btts_yes": _draws(0.60)},
            {"btts_yes": 0.50},
            prezzi={"btts_yes": 1.60},
            quota_minima=2.0,
        )
        assert alta[0].passes_quota_min is False

    def test_a_zero_non_esclude_niente(self) -> None:
        bassa = build_candidates(
            {"btts_yes": _draws(0.99)},
            {"btts_yes": 0.90},
            prezzi={"btts_yes": 1.01},
            quota_minima=1.0,
        )
        assert bassa[0].passes_quota_min is True


def test_la_soglia_e_quella_decisa() -> None:
    assert pytest.approx(1.30) == QUOTA_MINIMA


class TestIlSilenzioSaDireCosaHaScartato:
    """«Non conviene» in astratto e' un'opinione. Col nome e col prezzo e' un
    fatto che il lettore puo' andare a controllare da solo."""

    @staticmethod
    def _matrice() -> np.ndarray:
        return np.full((13, 13), 1.0 / 169.0)

    def test_tiene_il_mercato_respinto(self) -> None:
        fuori = select(
            build_candidates(
                {"dc_1x": _draws(0.75)}, {"dc_1x": 0.60}, prezzi={"dc_1x": 1.19}
            ),
            self._matrice(),
        )
        assert fuori.respinto_per_quota is not None
        assert fuori.respinto_per_quota.key == "dc_1x"
        assert fuori.respinto_per_quota.prezzo == 1.19

    def test_fra_piu_respinti_tiene_il_migliore(self) -> None:
        fuori = select(
            build_candidates(
                {"dc_1x": _draws(0.75), "dc_x2": _draws(0.72)},
                {"dc_1x": 0.60, "dc_x2": 0.70},
                prezzi={"dc_1x": 1.19, "dc_x2": 1.20},
            ),
            self._matrice(),
        )
        assert fuori.respinto_per_quota is not None
        assert fuori.respinto_per_quota.key == "dc_1x"

    def test_un_silenzio_di_altro_tipo_non_ne_ha_uno(self) -> None:
        """Chi cade su `S_min` non e' stato «respinto per la quota»."""
        fuori = select(
            build_candidates({"dc_1x": _draws(0.60)}, {"dc_1x": 0.60}), self._matrice()
        )
        assert fuori.respinto_per_quota is None

    def test_la_frase_porta_nome_e_prezzo(self) -> None:
        from pronostici.model.selection import Candidate
        from pronostici.pipeline import _silence_sentence

        respinto = Candidate(
            key="dc_1x",
            family="double_chance",
            label="1X (casa o pareggio)",
            p_hat=0.75,
            sigma=0.0,
            p5=0.75,
            p95=0.75,
            p_tilde=0.75,
            alpha=1.0,
            reference=0.60,
            score=0.05,
            passes_p_min=True,
            passes_sigma_max=True,
            passes_s_min=True,
            prezzo=1.19,
            passes_quota_min=False,
        )
        frase = _silence_sentence(
            None,
            Selection(
                pick=None,
                silence_reason="quota_min",
                n_candidates=1,
                n_clusters=0,
                respinto_per_quota=respinto,
            ),
            None,
            True,
        )
        assert "1X (casa o pareggio)" in frase
        assert "1,19" in frase
        assert "1,30" in frase

    def test_senza_prezzo_la_frase_dice_la_quota_equa(self) -> None:
        """Il numero che si puo' dire e' quello che si e' dedotto, e va detto
        per quello che e': il massimo che potrebbe pagare, non un prezzo."""
        from pronostici.model.selection import Candidate
        from pronostici.pipeline import _silence_sentence

        respinto = Candidate(
            key="hg_under_2.5",
            family="team_goals",
            label="Casa Under 2.5",
            p_hat=0.91,
            sigma=0.0,
            p5=0.91,
            p95=0.91,
            p_tilde=0.91,
            alpha=1.0,
            reference=0.85,
            score=0.05,
            passes_p_min=True,
            passes_sigma_max=True,
            passes_s_min=True,
            prezzo=None,
            passes_quota_min=False,
        )
        frase = _silence_sentence(
            None,
            Selection(
                pick=None,
                silence_reason="quota_min",
                n_candidates=1,
                n_clusters=0,
                respinto_per_quota=respinto,
            ),
            None,
            False,
        )
        assert "nessuno lo quota" in frase
        assert "1,10" in frase
