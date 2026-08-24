"""Il parsing di betexplorer, e le due trappole che ha gia' teso.

Niente rete: le tabelle qui sotto sono ridotte all'osso ma hanno la stessa
forma di quelle vere — un `<tr>` per bookmaker, le quote in `data-odd`
nell'ordine delle colonne, la linea dentro `data-hcp`.
"""

from __future__ import annotations

from pronostici.sources import betexplorer as bx


def _riga(quote: list[str], hcp: str = "E-1-2-0-0-0") -> str:
    celle = "".join(f'<td data-hcp="{hcp}" data-odd="{q}"></td>' for q in quote)
    return f"<tr>{celle}</tr>"


class TestLinea:
    def test_la_linea_e_il_quinto_pezzo(self) -> None:
        assert bx._linea("E-2-2-0-2.5-0") == "2.5"

    def test_uno_zero_non_e_una_linea(self) -> None:
        """`1X2` non ha linea, e il campo la scrive `0`: non e' «linea zero»."""
        assert bx._linea("E-1-2-0-0-0") is None

    def test_un_campo_corto_non_fa_esplodere_niente(self) -> None:
        assert bx._linea("E-1") is None


class TestMediana:
    def test_serve_un_minimo_di_bookmaker(self) -> None:
        """Una mediana su due prezzi non e' una mediana."""
        html = _riga(["2.00", "3.00", "4.00"]) + _riga(["2.10", "3.10", "4.10"])
        assert bx._leggi_mercato(html, "Esito finale", ("1", "X", "2")) == []

    def test_con_tre_bookmaker_si_pubblica(self) -> None:
        html = "".join(
            _riga([a, b, c])
            for a, b, c in (
                ("2.00", "3.00", "4.00"),
                ("2.10", "3.10", "4.10"),
                ("2.20", "3.20", "4.20"),
            )
        )
        fuori = bx._leggi_mercato(html, "Esito finale", ("1", "X", "2"))
        assert len(fuori) == 1
        assert [e["decimale"] for e in fuori[0]["esiti"]] == [2.10, 3.10, 4.10]
        assert fuori[0]["n_bookmaker"] == 3

    def test_una_quota_sotto_uno_e_una_cella_letta_male(self) -> None:
        """Una quota decimale non puo' valere meno di 1: quella riga si butta.

        Ne basterebbe una a spostare la mediana, e il prezzo che ne esce
        sarebbe pubblicato come se fosse il mercato.
        """
        buone = "".join(
            _riga([a, b, c])
            for a, b, c in (
                ("2.00", "3.00", "4.00"),
                ("2.10", "3.10", "4.10"),
                ("2.20", "3.20", "4.20"),
            )
        )
        html = buone + _riga(["0.01", "0.01", "0.01"])
        fuori = bx._leggi_mercato(html, "Esito finale", ("1", "X", "2"))
        assert fuori[0]["n_bookmaker"] == 3


class TestQuantiEsitiSiAvverano:
    """La doppia chance non e' una partizione, e trattarla come tale mente.

    "1X", "12" e "X2" coprono ogni risultato due volte: la somma delle inverse
    tende a 2, non a 1. Sgonfiandola come un 1X2 usciva un margine del 113%,
    cioe' un banco che si prende piu' di quanto incassa.
    """

    def _tre_righe(self, quote: tuple[str, str, str], hcp: str) -> str:
        return "".join(_riga(list(quote), hcp) for _ in range(3))

    def test_il_margine_della_doppia_chance_e_credibile(self) -> None:
        html = self._tre_righe(("1.36", "1.36", "1.50"), "E-4-2-0-0-0")
        fuori = bx._leggi_mercato(html, "Doppia chance", ("1X", "12", "X2"), 2)
        assert len(fuori) == 1
        assert 0 < fuori[0]["margine_percento"] < 20

    def test_le_sue_probabilita_sommano_a_due(self) -> None:
        html = self._tre_righe(("1.36", "1.36", "1.50"), "E-4-2-0-0-0")
        fuori = bx._leggi_mercato(html, "Doppia chance", ("1X", "12", "X2"), 2)
        somma = sum(e["probabilita_implicita"] for e in fuori[0]["esiti"])
        assert abs(somma - 2.0) < 0.01

    def test_una_partizione_somma_a_uno(self) -> None:
        html = self._tre_righe(("2.50", "3.00", "3.05"), "E-1-2-0-0-0")
        fuori = bx._leggi_mercato(html, "Esito finale", ("1", "X", "2"), 1)
        somma = sum(e["probabilita_implicita"] for e in fuori[0]["esiti"])
        assert abs(somma - 1.0) < 0.01


class TestLineeSeparate:
    def test_ogni_linea_e_un_mercato_a_se(self) -> None:
        """«Over» non vuol dire niente se non si sa sopra cosa."""
        html = "".join(
            _riga(["1.41", "2.75"], "E-2-2-0-1.5-0") for _ in range(3)
        ) + "".join(_riga(["2.30", "1.57"], "E-2-2-0-2.5-0") for _ in range(3))
        fuori = bx._leggi_mercato(html, "Gol totali", ("Over", "Under"))
        assert sorted(m["linea"] for m in fuori) == ["1.5", "2.5"]

    def test_la_riga_senza_linea_e_intestazione_non_mercato(self) -> None:
        html = "".join(_riga(["1.41", "2.75"], "E-2-2-0-0-0") for _ in range(3))
        assert bx._leggi_mercato(html, "Gol totali", ("Over", "Under")) == []


class TestPrefissoDiLingua:
    """Da un IP italiano gli URL hanno `/it/`, da un datacenter no.

    E' il primo modo in cui questa integrazione si e' rotta: la regex
    pretendeva il prefisso e trovava zero partite su una pagina piena, ma solo
    quando girava su GitHub.
    """

    def _pagina(self, href: str) -> str:
        return (
            f'<tr><td class="table-main__datetime">Oggi 17:30</td>'
            f'<td><a href="{href}" class="in-match">'
            f"<span>Bologna</span> - <span>Lazio</span></a></td>"
            f'<td data-odd="2.51"></td><td data-odd="2.95"></td>'
            f'<td data-odd="3.10"></td></tr>'
        )

    def test_con_prefisso(self) -> None:
        p = bx._leggi_elenco(self._pagina("/it/football/italy/serie-a/x/vm6sImkC/"))
        assert [(x.id, x.casa, x.ospiti) for x in p] == [("vm6sImkC", "Bologna", "Lazio")]

    def test_senza_prefisso(self) -> None:
        p = bx._leggi_elenco(self._pagina("/football/italy/serie-a/x/vm6sImkC/"))
        assert [(x.id, x.casa, x.ospiti) for x in p] == [("vm6sImkC", "Bologna", "Lazio")]

    def test_le_quote_dell_elenco_si_prendono_al_volo(self) -> None:
        p = bx._leggi_elenco(self._pagina("/football/italy/serie-a/x/vm6sImkC/"))
        assert p[0].esito_finale == [2.51, 2.95, 3.10]


class TestAggancio:
    def _p(self, casa: str, ospiti: str) -> bx.PartitaBX:
        return bx.PartitaBX(id="x", casa=casa, ospiti=ospiti)

    def test_il_nome_corto_si_ritrova_nel_nostro(self) -> None:
        elenco = [self._p("Bologna", "Lazio")]
        assert bx.aggancia(elenco, "Bologna FC 1909", "SS Lazio") is not None

    def test_serve_la_conferma_su_entrambe(self) -> None:
        elenco = [self._p("Bologna", "Lazio")]
        assert bx.aggancia(elenco, "Bologna FC 1909", "AS Roma") is None

    def test_i_due_club_della_stessa_citta_restano_separati(self) -> None:
        elenco = [self._p("Man City", "Arsenal")]
        assert bx.aggancia(elenco, "Manchester United FC", "Arsenal FC") is None
