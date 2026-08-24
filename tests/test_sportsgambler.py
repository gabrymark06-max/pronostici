"""Il parsing e l'abbinamento della fonte che ha sostituito Sofascore.

Le due parti che si rompono davvero sono queste, e si rompono in silenzio: se
il sito cambia una classe CSS il giro resta verde e scrive zero formazioni; se
l'abbinamento sbaglia, scrive la formazione di un'altra partita — che e'
peggio, perche' sembra giusta.

Niente rete: tutto gira su frammenti scritti a mano, ricalcati sul markup vero
del 24 agosto 2026.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from pronostici.sources import sportsgambler as sg

ELENCO = """
<h3 class="date-headline">Monday 24 August</h3>
<div class="fxs-table table-for-lineups">
  <div class="lineup-row">
    <span class="fxs-time">18:30</span>
    <span class="fxs-team home">Bologna</span>
    <span class="fxs-team">Lazio</span>
    <a onClick="reply_click(5749642)"><span>Confirmed Lineups</span></a>
  </div>
  <div class="lineup-row">
    <span class="fxs-time">20:45</span>
    <span class="fxs-team home">Roma</span>
    <span class="fxs-team">Fiorentina</span>
    <a onClick="reply_click(5749640)"><span>Predicted Lineups</span></a>
  </div>
</div>
<h3 class="date-headline">Friday 28 August</h3>
<div class="fxs-table table-for-lineups">
  <div class="lineup-row">
    <span class="fxs-time">20:45</span>
    <span class="fxs-team home">AC Milan</span>
    <span class="fxs-team">Venezia</span>
    <a onClick="reply_click(5749650)"><span>Predicted Lineups</span></a>
  </div>
</div>
"""


def _giocatore(maglia: str, nome: str) -> str:
    return (
        '<span class="lineups-player">'
        f'<span class="player-profile">{maglia}</span>'
        f'<span class="player-name">{nome}</span></span>'
    )


FRAMMENTO = (
    '<div class="lineups-formation">'
    "<h3><span>Bologna Predicted Lineup</span>"
    '<span class="lineups-toggle-formation">4-3-3</span></h3>'
    "<h3><span>Lazio Predicted Lineup</span>"
    '<span class="lineups-toggle-formation">3-5-2</span></h3></div>'
    '<div class="lineups-home reverse">'
    + _giocatore("1", "Lukasz Skorupski")
    + _giocatore("20", "Nadir Zortea")
    + "</div>"
    '<div class="lineups-away">'
    + _giocatore("35", "Christos Mandas")
    + _giocatore("77", "Adam Marusic")
    + "</div>"
)


class TestElenco:
    def test_legge_data_squadre_e_stato(self) -> None:
        partite = sg.elenco("SA", oggi=date(2026, 8, 24), html=ELENCO)
        assert [p.id for p in partite] == [5749642, 5749640, 5749650]
        assert partite[0].giorno == date(2026, 8, 24)
        assert (partite[0].casa, partite[0].ospiti) == ("Bologna", "Lazio")
        assert partite[0].confermate is True
        assert partite[1].confermate is False

    def test_la_riga_eredita_l_intestazione_sopra_di_se(self) -> None:
        """La data non sta nella riga: sta nell'intestazione che la precede.

        Leggere le due cose separatamente perderebbe proprio questo legame, e
        il sintomo sarebbe subdolo: tutte le partite finirebbero sul primo
        giorno della pagina, e l'abbinamento fallirebbe per data su tutte
        tranne quelle di oggi.
        """
        partite = sg.elenco("SA", oggi=date(2026, 8, 24), html=ELENCO)
        assert partite[2].giorno == date(2026, 8, 28)

    def test_competizione_che_non_copriamo(self) -> None:
        assert sg.elenco("XYZ", oggi=date(2026, 8, 24), html=ELENCO) == []


class TestAnno:
    """Il sito non scrive mai l'anno, e a capodanno la deduzione ovvia sbaglia."""

    def test_stesso_anno_nel_caso_normale(self) -> None:
        assert sg._anno_probabile(24, 8, date(2026, 8, 20)) == 2026

    def test_gennaio_letto_a_dicembre_e_l_anno_dopo(self) -> None:
        assert sg._anno_probabile(3, 1, date(2026, 12, 28)) == 2027

    def test_dicembre_letto_a_gennaio_e_l_anno_prima(self) -> None:
        assert sg._anno_probabile(29, 12, date(2027, 1, 2)) == 2026


class TestFormazione:
    def test_separa_i_due_lati(self) -> None:
        f = sg.formazione(0, "italy-serie-a", html=FRAMMENTO)
        assert f is not None
        assert f.casa.modulo == "4-3-3"
        assert f.ospiti.modulo == "3-5-2"
        assert [t["nome"] for t in f.casa.titolari] == [
            "Lukasz Skorupski",
            "Nadir Zortea",
        ]
        assert [t["nome"] for t in f.ospiti.titolari] == [
            "Christos Mandas",
            "Adam Marusic",
        ]

    def test_l_ordine_in_campo_non_si_riordina(self) -> None:
        """La prima riga e' il portiere. L'ordine e' informazione."""
        f = sg.formazione(0, "italy-serie-a", html=FRAMMENTO)
        assert f is not None
        assert f.casa.titolari[0]["maglia"] == "1"

    def test_frammento_senza_giocatori(self) -> None:
        """Esiste anche per partite senza formazione: 200 con la pubblicita'.

        Distinguerlo da un guasto conta — il primo e' il decorso normale.
        """
        vuoto = '<div class="odd-cta">Bet Now!</div>'
        assert sg.formazione(0, "italy-serie-a", html=vuoto) is None


class TestSomiglianza:
    """Il criterio e' asimmetrico apposta: loro accorciano, noi no."""

    def test_il_nome_corto_dentro_quello_lungo(self) -> None:
        assert sg.somiglianza("Borussia Dortmund", "Dortmund") == 1.0
        assert sg.somiglianza("Olympique Lyonnais", "Lyon") == 1.0

    def test_i_due_club_della_stessa_citta_restano_separati(self) -> None:
        """Il caso che rende il criterio sicuro invece che generoso."""
        assert sg.somiglianza("Manchester United FC", "Man City") < sg.SOGLIA
        assert sg.somiglianza("Manchester City FC", "Man City") >= sg.SOGLIA

    def test_alias_per_le_abbreviazioni_che_non_sono_prefissi(self) -> None:
        assert sg.somiglianza("Sheffield United FC", "Sheffield Utd") >= sg.SOGLIA
        assert sg.somiglianza("Queens Park Rangers FC", "QPR") >= sg.SOGLIA

    def test_alias_quando_il_loro_nome_e_piu_lungo_del_nostro(self) -> None:
        """Il verso si inverte e il contenimento fallirebbe dalla parte sbagliata."""
        assert sg.somiglianza("NEC", "NEC Nijmegen") >= sg.SOGLIA


class TestAggancia:
    CARTELLONE = [
        sg.PartitaSG(1, date(2026, 8, 29), "Dortmund", "Hamburger SV", False),
        sg.PartitaSG(2, date(2026, 8, 29), "Bayern Munich", "Stuttgart", False),
        sg.PartitaSG(3, date(2026, 9, 1), "Remo", "Coritiba", False),
    ]

    def _quando(self, giorno: date) -> datetime:
        return datetime(giorno.year, giorno.month, giorno.day, 18, 30, tzinfo=UTC)

    def test_aggancia_su_entrambe_le_squadre(self) -> None:
        p = sg.aggancia(
            self.CARTELLONE,
            "Borussia Dortmund",
            "Hamburger SV",
            self._quando(date(2026, 8, 29)),
        )
        assert p is not None and p.id == 1

    def test_una_squadra_sola_non_basta(self) -> None:
        """Il vincolo che tiene: con una conferma sola si sceglie il derby sbagliato."""
        assert (
            sg.aggancia(
                self.CARTELLONE,
                "Borussia Dortmund",
                "Werder Bremen",
                self._quando(date(2026, 8, 29)),
            )
            is None
        )

    def test_il_verso_conta(self) -> None:
        assert (
            sg.aggancia(
                self.CARTELLONE,
                "Hamburger SV",
                "Borussia Dortmund",
                self._quando(date(2026, 8, 29)),
            )
            is None
        )

    def test_calendari_che_non_concordano_di_tre_giorni(self) -> None:
        """Remo-Coritiba: 29 agosto da noi, 1o settembre da loro.

        E' una partita rinviata, non una partita diversa — le stesse due
        squadre nello stesso verso a tre giorni non esistono in un girone.
        """
        p = sg.aggancia(
            self.CARTELLONE,
            "Clube do Remo",
            "Coritiba FBC",
            self._quando(date(2026, 8, 29)),
        )
        assert p is not None and p.id == 3

    def test_oltre_la_tolleranza_non_si_aggancia(self) -> None:
        assert (
            sg.aggancia(
                self.CARTELLONE,
                "Clube do Remo",
                "Coritiba FBC",
                self._quando(date(2026, 8, 20)),
            )
            is None
        )

    def test_a_parita_vince_la_data_piu_vicina(self) -> None:
        doppio = [
            sg.PartitaSG(10, date(2026, 8, 30), "Dortmund", "Hamburger SV", False),
            sg.PartitaSG(11, date(2026, 8, 29), "Dortmund", "Hamburger SV", False),
        ]
        p = sg.aggancia(
            doppio, "Borussia Dortmund", "Hamburger SV", self._quando(date(2026, 8, 29))
        )
        assert p is not None and p.id == 11


class TestOrePrima:
    def test_quante_ore_mancano(self) -> None:
        fischio = datetime(2026, 8, 29, 18, 30, tzinfo=UTC)
        adesso = datetime(2026, 8, 25, 10, 30, tzinfo=UTC)
        assert sg.ore_prima(fischio, adesso) == 104.0

    def test_partita_gia_cominciata(self) -> None:
        fischio = datetime(2026, 8, 29, 18, 30, tzinfo=UTC)
        assert sg.ore_prima(fischio, fischio) is None
