"""La fonte che quota i mercati che nessun comparatore pubblica.

Due famiglie sono la ragione per cui esiste — gol di squadra e handicap
europeo — e sono quelle su cui cadeva la meta' dei pronostici consigliati, con
la scheda partita che scriveva «nessuna delle fonti che leggiamo quota questa
scommessa». Le altre cinque viaggiano nella stessa risposta e servono da
ripiego dove le mediane non arrivano.

Il rischio proprio di questa fonte non e' che non risponda: e' che risponda
BENE e sul mercato sbagliato. «Total Goals by Valencia» e «Total Goals by Real
Betis» sono due mercati diversi con la stessa forma, arrivano mescolati fra
seicento offerte, e scambiarli produrrebbe un prezzo vero sopra la squadra
sbagliata — un guasto che non ha nessun aspetto di guasto.
"""

from __future__ import annotations

import pytest

from pronostici.sources import kambi as kb


def _evento(casa: str = "Valencia", ospiti: str = "Real Betis") -> kb.EventoKB:
    return kb.EventoKB(id=1, casa=casa, ospiti=ospiti)


def _offerta(etichetta: str, esiti: list[dict]) -> dict:
    return {"criterion": {"englishLabel": etichetta}, "outcomes": esiti}


def _ou(linea: int, over: int | None, under: int | None) -> list[dict]:
    return [
        {"type": "OT_OVER", "line": linea, "odds": over},
        {"type": "OT_UNDER", "line": linea, "odds": under},
    ]


def _tre_vie(linea: int, uno: int, x: int, due: int) -> list[dict]:
    return [
        {"type": "OT_ONE", "line": linea, "odds": uno},
        {"type": "OT_CROSS", "line": linea, "odds": x},
        {"type": "OT_TWO", "line": linea, "odds": due},
    ]


class TestElenco:
    def test_legge_gli_eventi(self) -> None:
        dati = {
            "events": [
                {
                    "event": {
                        "id": 42,
                        "homeName": "Valencia",
                        "awayName": "Real Betis",
                        "start": "2026-08-25T19:00:00Z",
                    }
                }
            ]
        }
        (evento,) = kb.elenco("PD", dati=dati)
        assert (evento.id, evento.casa, evento.ospiti) == (42, "Valencia", "Real Betis")
        assert evento.inizio is not None
        assert evento.inizio.hour == 19

    def test_una_lega_che_non_conosciamo_non_e_un_errore(self) -> None:
        """Un codice fuori tabella torna vuoto senza chiamare la rete."""
        assert kb.elenco("XXX") == []

    def test_una_lega_senza_quote_aperte_lo_dice(self) -> None:
        """Vuoto QUI non e' il guasto che sarebbe su betexplorer.

        La' l'elenco e' la stagione intera, quindi zero righe significa
        percorso cambiato. Qui sono le partite col libro aperto: in pausa
        nazionali sono zero, ed e' giusto cosi'. Chi chiama lo distingue.
        """
        with pytest.raises(kb.LegaVuota):
            kb.elenco("PD", dati={"events": []})

    def test_una_voce_senza_nomi_si_salta(self) -> None:
        dati = {
            "events": [
                {"event": {"id": 1, "homeName": "Valencia"}},
                {"event": {"id": 2, "homeName": "Roma", "awayName": "Lazio"}},
            ]
        }
        assert [e.id for e in kb.elenco("SA", dati=dati)] == [2]

    def test_una_data_illeggibile_non_butta_via_l_evento(self) -> None:
        dati = {
            "events": [
                {
                    "event": {
                        "id": 7,
                        "homeName": "Roma",
                        "awayName": "Lazio",
                        "start": "ieri",
                    }
                }
            ]
        }
        (evento,) = kb.elenco("SA", dati=dati)
        assert evento.inizio is None


class TestAggancio:
    def test_i_nomi_corti_si_ritrovano_in_quelli_ufficiali(self) -> None:
        """Noi scriviamo «Real Betis Balompié», loro «Real Betis»."""
        eventi = [_evento("Valencia", "Real Betis")]
        trovato = kb.aggancia(eventi, "Valencia CF", "Real Betis Balompié")
        assert trovato is not None
        assert trovato.id == 1

    def test_serve_la_conferma_su_ENTRAMBE_le_squadre(self) -> None:
        eventi = [_evento("Valencia", "Real Betis")]
        assert kb.aggancia(eventi, "Valencia CF", "Sevilla FC") is None

    def test_le_due_di_manchester_non_si_confondono(self) -> None:
        eventi = [_evento("Manchester City", "Arsenal")]
        assert kb.aggancia(eventi, "Manchester United FC", "Arsenal FC") is None

    def test_senza_candidati_torna_niente(self) -> None:
        assert kb.aggancia([], "Roma", "Lazio") is None

    def test_a_parita_di_nome_decide_l_ora(self) -> None:
        """«Paris Saint-Germain FC» somiglia a «PSG» e a «Paris FC» allo stesso
        modo, e in Ligue 1 sono due club diversi che giocano tutti e due.

        Il nome non li distingue: il calcio d'inizio si'.
        """
        from datetime import UTC, datetime

        sbagliato = kb.EventoKB(
            id=1,
            casa="Paris FC",
            ospiti="Lille",
            inizio=datetime(2026, 8, 30, 15, tzinfo=UTC),
        )
        giusto = kb.EventoKB(
            id=2,
            casa="PSG",
            ospiti="Lille",
            inizio=datetime(2026, 8, 28, 19, tzinfo=UTC),
        )
        trovato = kb.aggancia(
            [sbagliato, giusto],
            "Paris Saint-Germain FC",
            "Lille OSC",
            datetime(2026, 8, 28, 19, tzinfo=UTC),
        )
        assert trovato is not None
        assert trovato.id == 2

    def test_senza_ora_si_decide_come_prima(self) -> None:
        """Un evento senza orario non deve ne' vincere ne' perdere per quello."""
        eventi = [kb.EventoKB(id=3, casa="Valencia", ospiti="Real Betis")]
        trovato = kb.aggancia(eventi, "Valencia CF", "Real Betis Balompié")
        assert trovato is not None
        assert trovato.id == 3


class TestINomiComeLiScrivono:
    """Ogni riga di `ALIAS` e' un aggancio che senza di lei non avviene."""

    def test_lo_stato_brasiliano_non_e_parte_del_nome(self) -> None:
        """Venti squadre su venti si fermavano a 0,50 per un suffisso."""
        for loro, nostro in (
            ("Vasco da Gama-RJ", "CR Vasco da Gama"),
            ("Palmeiras-SP", "SE Palmeiras"),
            ("Grêmio-RS", "Grêmio FBPA"),
            ("Corinthians-SP", "SC Corinthians Paulista"),
        ):
            assert kb.somiglianza(nostro, loro) >= kb.SOGLIA_NOME, loro

    def test_le_omonime_brasiliane_restano_distinte(self) -> None:
        """Tolto lo stato, «Atlético Mineiro» e «Athletico Paranaense» si
        distinguono per il nome della societa', non per la sigla."""
        assert kb.somiglianza("CA Mineiro", "Atlético Mineiro-MG") >= kb.SOGLIA_NOME
        assert kb.somiglianza("CA Mineiro", "Athletico Paranaense-PR") < kb.SOGLIA_NOME

    def test_gli_alias_agganciano_quello_che_devono(self) -> None:
        for loro, nostro in (
            ("Bayern Munich", "FC Bayern München"),
            ("NEC Nijmegen", "NEC"),
            ("PSV Eindhoven", "PSV"),
            ("Excelsior Rotterdam", "SBV Excelsior"),
            ("Athletic Bilbao", "Athletic Club"),
            ("Sporting Lisbon", "Sporting Clube de Portugal"),
            ("S.C. Braga", "Sporting Clube de Braga"),
            ("Nacional Madeira", "CD Nacional"),
            ("Vitoria Guimarães", "Vitória SC"),
        ):
            assert kb.somiglianza(nostro, loro) >= kb.SOGLIA_NOME, loro

    def test_le_due_di_sporting_non_si_scambiano(self) -> None:
        """Braga e Portugal si chiamano tutte e due «Sporting Clube de»."""
        assert (
            kb.somiglianza("Sporting Clube de Braga", "Sporting Lisbon") < kb.SOGLIA_NOME
        )
        assert kb.somiglianza("Sporting Clube de Portugal", "S.C. Braga") < kb.SOGLIA_NOME


class TestQualeSquadra:
    """Il guasto silenzioso di questa fonte, e l'unica cosa che lo previene."""

    def test_i_gol_di_casa_vanno_alla_squadra_di_casa(self) -> None:
        evento = _evento("Valencia", "Real Betis")
        letto = kb._famiglia(_offerta("Total Goals by Valencia", []), evento)
        assert letto is not None
        assert letto[0] == kb.MERCATO_GOL_CASA

    def test_i_gol_dell_ospite_vanno_all_ospite(self) -> None:
        evento = _evento("Valencia", "Real Betis")
        letto = kb._famiglia(_offerta("Total Goals by Real Betis", []), evento)
        assert letto is not None
        assert letto[0] == kb.MERCATO_GOL_OSPITE

    def test_l_ordine_delle_offerte_non_decide_niente(self) -> None:
        """Le offerte arrivano mescolate: se decidesse l'ordine, meta' delle
        partite avrebbe i gol attribuiti alla squadra sbagliata."""
        evento = _evento("Valencia", "Real Betis")
        offerte = [
            _offerta("Total Goals by Real Betis", _ou(1500, 2430, 1500)),
            _offerta("Total Goals by Valencia", _ou(1500, 2550, 1460)),
        ]
        letti = {
            m["mercato"]: m["esiti"][0]["decimale"] for m in kb.mercati(evento, offerte)
        }
        assert letti[kb.MERCATO_GOL_OSPITE] == 2.43
        assert letti[kb.MERCATO_GOL_CASA] == 2.55

    def test_un_nome_che_non_e_ne_l_una_ne_l_altra_si_scarta(self) -> None:
        evento = _evento("Valencia", "Real Betis")
        assert kb._famiglia(_offerta("Total Goals by Sevilla", []), evento) is None

    def test_un_derby_fra_omonime_non_si_indovina(self) -> None:
        """Con due nomi che pesano uguale non si sceglie: si tace.

        Attribuire a caso vorrebbe dire sbagliare una volta su due senza che
        niente lo dica.
        """
        evento = _evento("Milan", "Milan")
        assert kb._famiglia(_offerta("Total Goals by Milan", []), evento) is None

    def test_tutto_il_resto_non_e_roba_nostra(self) -> None:
        evento = _evento()
        for etichetta in ("Total Corners by Valencia", "Asian Handicap", "To Score"):
            assert kb._famiglia(_offerta(etichetta, []), evento) is None


class TestLinee:
    def test_le_quote_arrivano_in_millesimi(self) -> None:
        evento = _evento()
        (m,) = kb.mercati(
            evento, [_offerta("Total Goals by Valencia", _ou(2500, 6000, 1100))]
        )
        assert m["linea"] == "2.5"
        assert [e["decimale"] for e in m["esiti"]] == [6.0, 1.1]

    def test_la_linea_dei_gol_si_scrive_come_la_scrive_il_modello(self) -> None:
        """`hg_over_1.5`, non `1,5` e non `1.50`.

        La chiave si compone concatenando questa stringa: una formattazione
        diversa e' un prezzo vero che non si ritrova mai.
        """
        evento = _evento()
        (m,) = kb.mercati(
            evento, [_offerta("Total Goals by Valencia", _ou(500, 1320, 3100))]
        )
        assert m["linea"] == "0.5"

    def test_l_handicap_si_scrive_intero_col_segno(self) -> None:
        evento = _evento()
        (m,) = kb.mercati(
            evento, [_offerta("3-Way Handicap", _tre_vie(-2000, 12500, 7500, 1110))]
        )
        assert m["linea"] == "-2"
        assert [e["esito"] for e in m["esiti"]] == ["1", "X", "2"]

    def test_un_handicap_a_mezzo_gol_si_rifiuta(self) -> None:
        """A tre esiti non puo' esistere: il pareggio non potrebbe avverarsi.

        Se arriva, la risposta non e' quella che crediamo e il mercato si
        scarta invece di inventargli una chiave.
        """
        evento = _evento()
        assert (
            kb.mercati(
                evento, [_offerta("3-Way Handicap", _tre_vie(-1500, 200, 300, 400))]
            )
            == []
        )


class TestQuoteIncomplete:
    def test_un_esito_sospeso_porta_via_tutto_il_mercato(self) -> None:
        """`odds: null` capita sulle linee estreme, e senza quell'esito il
        mercato non e' piu' una partizione: il margine non si puo' togliere."""
        evento = _evento()
        assert (
            kb.mercati(
                evento, [_offerta("Total Goals by Valencia", _ou(3500, 16000, None))]
            )
            == []
        )

    def test_un_esito_dichiarato_sospeso_non_si_pubblica(self) -> None:
        """Lo dicono in due modi — `odds` sparisce e `status` diventa
        `SUSPENDED` — e si guardano tutti e due: se un giorno mandassero un
        prezzo vecchio accanto alla sospensione, lo pubblicheremmo per fresco."""
        evento = _evento()
        offerta = _offerta(
            "Total Goals by Valencia",
            [
                {"type": "OT_OVER", "line": 1500, "odds": 2550},
                {"type": "OT_UNDER", "line": 1500, "odds": 1460, "status": kb.SOSPESO},
            ],
        )
        assert kb.mercati(evento, [offerta]) == []

    def test_una_quota_sotto_uno_e_una_cella_letta_male(self) -> None:
        evento = _evento()
        assert (
            kb.mercati(
                evento, [_offerta("Total Goals by Valencia", _ou(1500, 900, 1460))]
            )
            == []
        )

    def test_la_linea_ripetuta_si_legge_una_volta_sola(self) -> None:
        """Kambi ripete la linea principale marcandola `MAIN_LINE`."""
        evento = _evento()
        offerte = [
            _offerta("Total Goals by Valencia", _ou(1500, 2550, 1460)),
            _offerta("Total Goals by Valencia", _ou(1500, 2550, 1460)),
        ]
        assert len(kb.mercati(evento, offerte)) == 1


class TestIlMargine:
    def test_il_margine_e_l_eccesso_sulle_inverse(self) -> None:
        evento = _evento()
        (m,) = kb.mercati(
            evento, [_offerta("Total Goals by Valencia", _ou(1500, 2550, 1460))]
        )
        atteso = (1 / 2.55 + 1 / 1.46 - 1) * 100
        assert m["margine_percento"] == pytest.approx(atteso, abs=0.02)

    def test_le_probabilita_sgonfiate_sommano_a_uno(self) -> None:
        evento = _evento()
        (m,) = kb.mercati(
            evento, [_offerta("3-Way Handicap", _tre_vie(1000, 1480, 4000, 5000))]
        )
        somma = sum(e["probabilita_implicita"] for e in m["esiti"])
        assert somma == pytest.approx(1.0, abs=0.001)

    def test_la_sgonfiata_sta_sotto_la_grezza(self) -> None:
        """Il de-vig toglie il margine: ogni probabilita' scende."""
        evento = _evento()
        (m,) = kb.mercati(
            evento, [_offerta("Total Goals by Valencia", _ou(1500, 2550, 1460))]
        )
        for esito in m["esiti"]:
            assert esito["probabilita_implicita"] < 1 / esito["decimale"]


class TestIlDatoDichiaraCosaE:
    def test_dice_che_e_un_operatore_solo(self) -> None:
        """Non e' una mediana, e il dato non deve poter essere scambiato per
        una: e' questo numero che decide se la pagina scrive «un operatore» o
        «N operatori»."""
        evento = _evento()
        (m,) = kb.mercati(
            evento, [_offerta("Total Goals by Valencia", _ou(1500, 2550, 1460))]
        )
        assert m["n_bookmaker"] == 1
        assert m["fonte"] == "kambi"
        assert m["bookmaker"] == ["unibet"]

    def test_ogni_mercato_dichiarato_sa_dire_i_suoi_esiti(self) -> None:
        """`MERCATI` e' il contratto verso il job e verso la pagina.

        Le colonne dichiarate la' devono essere ESATTAMENTE quelle che il
        parsing produce, nello stesso ordine: `_mercato` le accoppia alle quote
        con `zip(..., strict=True)`, e un ordine diverso attribuirebbe in
        silenzio il prezzo di un esito a un altro.
        """
        for _, (nome, tipi, _) in kb.ETICHETTE.items():
            assert kb.MERCATI[nome][1] == tuple(tipi.values())
        for nome in (kb.MERCATO_GOL_CASA, kb.MERCATO_GOL_OSPITE):
            assert kb.MERCATI[nome][1] == tuple(kb.TIPI_DUE_VIE.values())

    def test_i_mercati_che_hanno_gia_un_nome_lo_tengono(self) -> None:
        """Gli stessi quattro che pubblica betexplorer, scritti uguale.

        Due nomi diversi per la stessa scommessa sono due righe nella tavola
        con due prezzi vicini: e' il doppione che il progetto ha appena finito
        di togliere, rimesso da un'altra porta.
        """
        from pronostici.sources import betexplorer as bx

        loro = {nome for nome, _, _ in bx.MERCATI.values()} | {"Esito finale"}
        nostri = {nome for nome, _, _ in kb.MERCATI.values()}
        condivisi = {
            kb.MERCATO_ESITO,
            kb.MERCATO_DOPPIA,
            kb.MERCATO_ENTRAMBE,
            kb.MERCATO_GOL_TOTALI,
        }
        assert condivisi <= loro
        assert condivisi <= nostri

    def test_la_doppia_chance_copre_due_volte(self) -> None:
        """Tre esiti che contengono ognuno due dei tre risultati.

        Sgonfiarla come una partizione dava un margine del 113%: il banco che
        si prende piu' di quanto incassa.
        """
        assert kb.MERCATI[kb.MERCATO_DOPPIA][2] == 2

    def test_un_mercato_senza_linea_la_scrive_assente_e_non_vuota(self) -> None:
        """`None`, come betexplorer: la tavola unisce le fonti sulla coppia
        nome-linea, e due modi di dire «nessuna» sono due righe."""
        evento = _evento()
        offerta = _offerta(
            "Double Chance",
            [
                {"type": "OT_ONE_OR_CROSS", "line": None, "odds": 1490},
                {"type": "OT_ONE_OR_TWO", "line": None, "odds": 1340},
                {"type": "OT_CROSS_OR_TWO", "line": None, "odds": 1430},
            ],
        )
        (m,) = kb.mercati(evento, [offerta])
        assert m["linea"] is None
        assert m["mercato"] == kb.MERCATO_DOPPIA
        # 1/1,49 + 1/1,34 + 1/1,43 vale circa 2,11: il margine e' sull'eccesso
        # rispetto a DUE, non a uno.
        assert m["margine_percento"] == pytest.approx(5.6, abs=0.5)


class TestRichiesteAGruppi:
    def test_le_offerte_finiscono_sull_evento_giusto(self, monkeypatch) -> None:
        eventi = [
            kb.EventoKB(id=1, casa="Valencia", ospiti="Real Betis"),
            kb.EventoKB(id=2, casa="Roma", ospiti="Lazio"),
        ]
        risposta = {
            "betOffers": [
                {
                    "eventId": 1,
                    **_offerta("Total Goals by Valencia", _ou(1500, 2550, 1460)),
                },
                {"eventId": 2, **_offerta("Total Goals by Roma", _ou(1500, 2000, 1800))},
            ]
        }
        chiesti: list[str] = []

        def finto(percorso: str) -> dict:
            chiesti.append(percorso)
            return risposta

        monkeypatch.setattr(kb, "_scarica", finto)
        fuori = kb.quote_di_gruppo(eventi)

        assert chiesti == ["betoffer/event/1,2.json"]
        assert fuori[1][0]["mercato"] == kb.MERCATO_GOL_CASA
        assert fuori[1][0]["esiti"][0]["decimale"] == 2.55
        assert fuori[2][0]["esiti"][0]["decimale"] == 2.0

    def test_si_chiede_a_gruppi(self, monkeypatch) -> None:
        eventi = [kb.EventoKB(id=i, casa="A", ospiti="B") for i in range(1, 6)]
        chiesti: list[str] = []
        monkeypatch.setattr(
            kb, "_scarica", lambda p: chiesti.append(p) or {"betOffers": []}
        )
        kb.quote_di_gruppo(eventi)
        assert chiesti == [
            "betoffer/event/1,2.json",
            "betoffer/event/3,4.json",
            "betoffer/event/5.json",
        ]

    def test_un_gruppo_che_non_risponde_non_ferma_gli_altri(self, monkeypatch) -> None:
        eventi = [
            kb.EventoKB(id=i, casa="Valencia", ospiti="Real Betis") for i in range(1, 7)
        ]

        def finto(percorso: str) -> dict:
            if percorso.startswith("betoffer/event/1,"):
                raise kb.KambiNonRaggiungibile("timeout")
            return {
                "betOffers": [
                    {
                        "eventId": 6,
                        **_offerta("Total Goals by Valencia", _ou(1500, 2550, 1460)),
                    }
                ]
            }

        monkeypatch.setattr(kb, "_scarica", finto)
        fuori = kb.quote_di_gruppo(eventi)
        assert set(fuori) == {6}


class TestLaRispostaTroncata:
    """Il guasto piu' subdolo di questa fonte, e l'unico che non si vede.

    Il servizio si ferma a duemila offerte e taglia SENZA DIRLO: risposta 200,
    JSON valido, e le partite in fondo al gruppo escono con qualche mercato o
    con nessuno. Chiedendone cinque per volta, una partita su ventuno restava
    senza prezzi e il giro non aveva niente da segnalare.
    """

    @staticmethod
    def _offerte(quante: int, id_evento: int) -> list[dict]:
        return [
            {
                "eventId": id_evento,
                "criterion": {"englishLabel": "Corners"},
                "outcomes": [],
            }
            for _ in range(quante)
        ]

    def test_una_risposta_al_tetto_si_butta_e_si_richiede_una_per_volta(
        self, monkeypatch
    ) -> None:
        buona = _offerta("Total Goals by Valencia", _ou(1500, 2550, 1460))
        chiesti: list[str] = []

        def finto(percorso: str) -> dict:
            chiesti.append(percorso)
            if "," in percorso:
                # Il gruppo risponde al tetto: e' troncato, non ci si fida.
                return {"betOffers": self._offerte(kb.CAP_OFFERTE, 1)}
            id_evento = int(percorso.split("/")[-1].split(".")[0])
            return {"betOffers": [{"eventId": id_evento, **buona}]}

        monkeypatch.setattr(kb, "_scarica", finto)
        eventi = [kb.EventoKB(id=i, casa="Valencia", ospiti="Real Betis") for i in (1, 2)]
        fuori = kb.quote_di_gruppo(eventi)

        assert chiesti == [
            "betoffer/event/1,2.json",
            "betoffer/event/1.json",
            "betoffer/event/2.json",
        ]
        assert set(fuori) == {1, 2}

    def test_una_richiesta_singola_al_tetto_si_tiene(self, monkeypatch) -> None:
        """Con una partita sola il tetto non e' un troncamento del gruppo.

        Rifiutarla vorrebbe dire buttare via l'unica risposta possibile, e
        rifarla all'infinito.
        """
        offerte = self._offerte(kb.CAP_OFFERTE - 1, 1)
        offerte.append(
            {"eventId": 1, **_offerta("Total Goals by Valencia", _ou(1500, 2550, 1460))}
        )
        monkeypatch.setattr(kb, "_scarica", lambda p: {"betOffers": offerte})
        fuori = kb.quote_di_gruppo(
            [kb.EventoKB(id=1, casa="Valencia", ospiti="Real Betis")]
        )
        assert fuori[1][0]["mercato"] == kb.MERCATO_GOL_CASA

    def test_sotto_il_tetto_non_si_rifa_niente(self, monkeypatch) -> None:
        chiesti: list[str] = []
        monkeypatch.setattr(
            kb,
            "_scarica",
            lambda p: chiesti.append(p) or {"betOffers": self._offerte(10, 1)},
        )
        kb.quote_di_gruppo([kb.EventoKB(id=i, casa="A", ospiti="B") for i in (1, 2)])
        assert chiesti == ["betoffer/event/1,2.json"]
