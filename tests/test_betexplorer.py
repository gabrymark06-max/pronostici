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


class TestPassoAdattivo:
    """Il passo si regola da se', invece di essere indovinato una volta.

    La soglia di betexplorer non e' un numero fisso che si possa scoprire e
    cablare: misurato dai runner di GitHub, a tre secondi un 429 su quaranta
    richieste, a due secondi quattordici su centocinquantacinque. Quello buono
    cambia durante il giro stesso.
    """

    def setup_method(self) -> None:
        bx.azzera_passo()

    def teardown_method(self) -> None:
        bx.azzera_passo()

    def test_si_parte_dal_lato_veloce(self) -> None:
        """Correre troppo costa un rinvio ogni errore; andare piano costa su
        tutte le richieste. I due errori non pesano uguale."""
        assert bx.passo() == bx.PAUSA_INIZIALE_S

    def test_un_429_rallenta(self) -> None:
        bx._rallenta()
        assert bx.passo() == bx.PAUSA_INIZIALE_S + bx.INCREMENTO_S

    def test_non_si_torna_mai_indietro(self) -> None:
        """Un giro che ha appena preso un 429 non ha motivo di credere che il
        prossimo andra' meglio."""
        bx._rallenta()
        dopo = bx.passo()
        assert bx.passo() == dopo

    def test_c_e_un_tetto(self) -> None:
        for _ in range(50):
            bx._rallenta()
        assert bx.passo() == bx.PAUSA_MASSIMA_S


class TestLegaVuota:
    """Una pagina che risponde 200 e non ha partite non e' «niente in calendario».

    L'elenco copre l'intera stagione, quindi zero righe significa percorso
    cambiato o markup diverso. E betexplorer non risponde 404 su un percorso
    sbagliato: rimanda alla pagina generica del calcio, che e' 200 e pesa
    settecento kilobyte. Il Brasileirao e' rimasto senza mercati senza che
    niente lo dicesse, perche' il suo percorso porta il nome dello sponsor —
    `serie-a-betano`, non `serie-a`.
    """

    def test_zero_partite_e_un_errore_non_un_silenzio(self) -> None:
        import pytest

        with pytest.raises(bx.LegaVuota):
            bx.elenco("SA", html="<html><body>niente qui</body></html>")

    def test_una_lega_che_non_seguiamo_torna_vuota_senza_gridare(self) -> None:
        """Non e' un guasto: e' una competizione che non copriamo."""
        assert bx.elenco("XX", html="<html></html>") == []


class TestAliasVersoBetexplorer:
    """Gli alias mappano societa' vere, non il primo nome che somiglia.

    Le pagine elencano anche squadre che non seguiamo — Bolton e Lincoln su
    quella di Championship, Schalke su quella di Bundesliga. Dedurre gli alias
    dalle partite non agganciate produceva coppie come «Bahia -> Gremio»: il
    «miglior candidato» era un'altra partita.
    """

    def test_le_omonime_brasiliane_si_distinguono(self) -> None:
        """Loro usano la sigla dello stato, noi quella della societa'."""
        assert bx.somiglianza("CA Paranaense", "Athletico-PR") >= bx.SOGLIA_NOME
        assert bx.somiglianza("CA Mineiro", "Atletico-MG") >= bx.SOGLIA_NOME

    def test_e_non_si_confondono_fra_loro(self) -> None:
        assert bx.somiglianza("CA Mineiro", "Athletico-PR") < bx.SOGLIA_NOME
        assert bx.somiglianza("Botafogo FR", "Flamengo RJ") < bx.SOGLIA_NOME

    def test_le_abbreviazioni_inglesi(self) -> None:
        assert bx.somiglianza("Manchester United FC", "Manchester Utd") >= bx.SOGLIA_NOME
        assert bx.somiglianza("Queens Park Rangers FC", "QPR") >= bx.SOGLIA_NOME

    def test_i_due_di_manchester_restano_separati(self) -> None:
        assert bx.somiglianza("Manchester City FC", "Manchester Utd") < bx.SOGLIA_NOME
