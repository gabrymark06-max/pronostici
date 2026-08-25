"""Le due decisioni del job che non si vedono guardando l'output.

Il resto — scaricare, agganciare, scrivere — e' provato altrove o si vede da
solo quando manca. Queste due no: sbagliano producendo un risultato plausibile.
"""

from __future__ import annotations

from pronostici.jobs import contorno as job
from pronostici.sources import sportsgambler as sg


def _formazione(confermate: bool) -> sg.Formazione:
    return sg.Formazione(
        casa=sg.Lato(modulo="4-3-3", titolari=[{"nome": "Skorupski", "maglia": "1"}]),
        ospiti=sg.Lato(modulo="3-5-2", titolari=[{"nome": "Mandas", "maglia": "35"}]),
        confermate=confermate,
    )


class TestConfermate:
    """Nel dubbio si dice la cosa piu' debole.

    L'elenco e il frammento non sempre concordano — Bologna-Lazio aveva il
    pulsante «Confirmed» e dentro «Predicted» — e non sappiamo quale dei due
    sia vecchio. Dire «probabile» su una formazione confermata costa
    un'imprecisione; dire «confermata» su una probabile significa affermare
    che quello e' l'undici che scende in campo, e non lo sappiamo.
    """

    def _blocco(self, frammento: bool, elenco: bool) -> dict:
        return job._blocco(
            _formazione(frammento),
            confermate_in_elenco=elenco,
            ore_prima=12.0,
            letto="2026-08-24T15:00:00Z",
            arbitro=None,
        )

    def test_confermata_solo_se_lo_dicono_entrambi(self) -> None:
        assert self._blocco(True, True)["formazioni"]["confermate"] is True

    def test_elenco_confermato_ma_frammento_no(self) -> None:
        assert self._blocco(False, True)["formazioni"]["confermate"] is False

    def test_frammento_confermato_ma_elenco_no(self) -> None:
        assert self._blocco(True, False)["formazioni"]["confermate"] is False

    def test_la_fonte_e_dichiarata(self) -> None:
        """Senza questo campo il dato e' indistinguibile da quello di Sofascore."""
        assert self._blocco(True, True)["formazioni"]["fonte"] == "sportsgambler"

    def test_panchina_vuota_e_non_assente(self) -> None:
        """Sportsgambler non la pubblica. Una lista vuota dice «non ce l'ho»."""
        blocco = self._blocco(False, False)
        assert blocco["formazioni"]["casa"]["panchina"] == []


class TestSenzaOra:
    """`letto` cambia a ogni giro e non e' una novita'.

    Se entrasse nel confronto, ogni esecuzione riscriverebbe tutti i file e il
    registro pubblico delle modifiche — che e' meta' del prodotto — diventerebbe
    illeggibile.
    """

    def test_due_giri_identici_non_sono_una_modifica(self) -> None:
        a = {"letto": "2026-08-24T07:00:00Z", "arbitro": {"nome": "Maresca"}}
        b = {"letto": "2026-08-24T17:00:00Z", "arbitro": {"nome": "Maresca"}}
        assert job._senza_ora(a) == job._senza_ora(b)

    def test_un_arbitro_nuovo_invece_lo_e(self) -> None:
        a = {"letto": "2026-08-24T07:00:00Z", "arbitro": {"nome": "Maresca"}}
        b = {"letto": "2026-08-24T07:00:00Z", "arbitro": {"nome": "Orsato"}}
        assert job._senza_ora(a) != job._senza_ora(b)


class TestGuardiaSulParsing:
    """Il guasto tipico di una fonte letta dall'HTML e' silenzioso.

    Se cambia una classe CSS l'elenco risponde ancora 200, le partite si
    agganciano tutte e i frammenti arrivano — solo che non se ne cava piu' un
    giocatore. Senza questa guardia il job uscirebbe verde avendo scritto
    niente, e le formazioni di quei giorni sarebbero perse: esistono solo
    prima del fischio d'inizio.
    """

    def _report(
        self,
        agganciate: int,
        con_formazioni: int,
        kambi_agganciate: int = 0,
        con_mercati_kambi: int = 1,
    ) -> dict:
        return {
            "agganciate": agganciate,
            "con_formazioni": con_formazioni,
            "kambi_agganciate": kambi_agganciate,
            "con_mercati_kambi": con_mercati_kambi,
        }

    def test_molte_agganciate_e_zero_formazioni_e_un_guasto(self) -> None:
        r = self._report(job.SOGLIA_ALLARME, 0)
        assert job._allarme_parsing(r) is not None

    def test_poche_partite_puo_essere_vero(self) -> None:
        """Una finestra corta in pausa nazionali non ha niente da leggere."""
        r = self._report(job.SOGLIA_ALLARME - 1, 0)
        assert job._allarme_parsing(r) is None

    def test_una_formazione_sola_basta_a_dire_che_il_parsing_regge(self) -> None:
        r = self._report(80, 1)
        assert job._allarme_parsing(r) is None

    def test_molte_agganciate_su_kambi_e_zero_mercati_e_un_guasto(self) -> None:
        """Kambi e' JSON: non si rompe con una classe CSS, si rompe con
        un'etichetta rinominata. Il giro uscirebbe verde avendo scritto zero
        prezzi proprio sulle famiglie che nessun altro quota."""
        r = self._report(80, 5, kambi_agganciate=job.SOGLIA_ALLARME, con_mercati_kambi=0)
        allarme = job._allarme_parsing(r)
        assert allarme is not None
        assert "kambi" in allarme

    def test_su_kambi_poche_partite_puo_essere_vero(self) -> None:
        """Il loro elenco copre solo le partite col libro aperto."""
        r = self._report(
            80, 5, kambi_agganciate=job.SOGLIA_ALLARME - 1, con_mercati_kambi=0
        )
        assert job._allarme_parsing(r) is None

    def test_un_mercato_solo_basta_a_dire_che_le_etichette_reggono(self) -> None:
        r = self._report(80, 5, kambi_agganciate=80, con_mercati_kambi=1)
        assert job._allarme_parsing(r) is None


class TestMercatiVersoLeNostreChiavi:
    """I mercati estesi devono parlare la lingua del resto del progetto.

    `market_p` riempie la colonna «il mercato» sulle partite che la fonte
    principale non copre: se le chiavi non combaciassero con quelle di `odds`,
    le due fonti vivrebbero in universi separati e nessuna pagina potrebbe
    confrontarle.
    """

    def _mercato(self, nome: str, esiti: list[tuple[str, float]], linea=None) -> dict:
        return {
            "mercato": nome,
            "linea": linea,
            "esiti": [{"esito": e, "probabilita_implicita": p} for e, p in esiti],
        }

    def test_esito_finale(self) -> None:
        m = [self._mercato("Esito finale", [("1", 0.38), ("X", 0.31), ("2", 0.31)])]
        assert job._market_p(m) == {
            "1x2_home": 0.38,
            "1x2_draw": 0.31,
            "1x2_away": 0.31,
        }

    def test_i_gol_totali_portano_la_linea_nella_chiave(self) -> None:
        """Senza, le dodici soglie diventerebbero dodici volte la stessa voce."""
        m = [
            self._mercato("Gol totali", [("Over", 0.68), ("Under", 0.32)], linea="1.5"),
            self._mercato("Gol totali", [("Over", 0.40), ("Under", 0.60)], linea="2.5"),
        ]
        assert job._market_p(m) == {
            "over_1.5": 0.68,
            "under_1.5": 0.32,
            "over_2.5": 0.40,
            "under_2.5": 0.60,
        }

    def test_un_mercato_che_non_sappiamo_tradurre_si_ignora(self) -> None:
        """Meglio non dirlo che dirlo con una chiave inventata."""
        m = [self._mercato("Handicap asiatico", [("1", 0.5), ("2", 0.5)])]
        assert job._market_p(m) == {}

    def test_entrambe_segnano(self) -> None:
        m = [self._mercato("Entrambe segnano", [("Sì", 0.48), ("No", 0.52)])]
        assert job._market_p(m) == {"btts_yes": 0.48, "btts_no": 0.52}


class TestPrezziVeri:
    """Solo le quote che qualcuno espone davvero possono chiamarsi «quota».

    `market_p` sono probabilita' sgonfiate del margine: utili a confrontare,
    ma nessuno le paga. `prezzi` sono i numeri che un operatore mostra, e sono
    gli unici che la pagina ha il diritto di stampare come quota.
    """

    def _mercato(self, nome, esiti, linea=None):
        return {
            "mercato": nome,
            "linea": linea,
            "esiti": [
                {"esito": e, "decimale": q, "probabilita_implicita": round(1 / q, 4)}
                for e, q in esiti
            ],
        }

    def test_la_doppia_chance_finisce_nelle_nostre_chiavi(self) -> None:
        m = [self._mercato("Doppia chance", [("1X", 1.36), ("12", 1.4), ("X2", 1.5)])]
        assert {k: v["decimale"] for k, v in job._prezzi(m).items()} == {
            "dc_1x": 1.36,
            "dc_12": 1.4,
            "dc_x2": 1.5,
        }

    def test_i_gol_totali_portano_la_linea(self) -> None:
        m = [self._mercato("Gol totali", [("Over", 2.3), ("Under", 1.57)], linea="2.5")]
        assert {k: v["decimale"] for k, v in job._prezzi(m).items()} == {
            "over_2.5": 2.3,
            "under_2.5": 1.57,
        }

    def test_una_quota_impossibile_non_entra(self) -> None:
        """Una decimale sotto 1 e' una cella letta male, non un prezzo."""
        m = [self._mercato("Entrambe segnano", [("Sì", 0.5), ("No", 1.8)])]
        assert list(job._prezzi(m)) == ["btts_no"]

    def test_un_mercato_che_non_sappiamo_tradurre_si_ignora(self) -> None:
        m = [self._mercato("Handicap asiatico", [("1", 1.9), ("2", 1.9)])]
        assert job._prezzi(m) == {}

    def test_prezzi_e_probabilita_usano_la_stessa_mappatura(self) -> None:
        """Se divergessero, la pagina mostrerebbe il prezzo di un mercato
        accanto alla probabilita' di un altro."""
        m = [
            self._mercato("Doppia chance", [("1X", 1.36), ("12", 1.4), ("X2", 1.5)]),
            self._mercato("Gol totali", [("Over", 2.3), ("Under", 1.57)], linea="2.5"),
        ]
        assert sorted(job._prezzi(m)) == sorted(job._market_p(m))


class TestDueFontiUnaTavola:
    """betexplorer e kambi quotano gli stessi quattro mercati.

    Da quando kambi legge anche esito finale, doppia chance, entrambe segnano e
    gol totali — che gli costano zero richieste in piu', perche' viaggiano
    nella stessa risposta dei gol di squadra — le due fonti si sovrappongono.
    Concatenarle metteva due righe «Gol totali 2,5» una sotto l'altra con due
    prezzi diversi: entrambi veri, e insieme illeggibili.
    """

    @staticmethod
    def _m(fonte: str, nome: str, quota: float, linea: str | None = None) -> dict:
        return {
            "fonte": fonte,
            "mercato": nome,
            "linea": linea,
            "n_bookmaker": 20 if fonte == "betexplorer" else 1,
            "esiti": [
                {"esito": "Over", "decimale": quota, "probabilita_implicita": 0.5},
                {"esito": "Under", "decimale": quota, "probabilita_implicita": 0.5},
            ],
        }

    def test_a_parita_di_mercato_vince_la_mediana(self) -> None:
        mediane = [self._m("betexplorer", "Gol totali", 1.91, "2.5")]
        singolo = [self._m("kambi", "Gol totali", 1.76, "2.5")]
        (rimasto,) = job._unisci(mediane, singolo)
        assert rimasto["fonte"] == "betexplorer"

    def test_le_linee_diverse_convivono(self) -> None:
        """Stesso mercato, linea diversa: sono due scommesse, non un doppione."""
        mediane = [self._m("betexplorer", "Gol totali", 1.91, "2.5")]
        singolo = [self._m("kambi", "Gol totali", 2.4, "3.5")]
        assert len(job._unisci(mediane, singolo)) == 2

    def test_i_mercati_senza_linea_si_riconoscono_fra_loro(self) -> None:
        mediane = [self._m("betexplorer", "Doppia chance", 1.36)]
        singolo = [self._m("kambi", "Doppia chance", 1.4)]
        assert len(job._unisci(mediane, singolo)) == 1

    def test_quello_che_solo_lui_quota_resta(self) -> None:
        mediane = [self._m("betexplorer", "Gol totali", 1.91, "2.5")]
        singolo = [self._m("kambi", "Gol di squadra casa", 1.46, "1.5")]
        assert [m["mercato"] for m in job._unisci(mediane, singolo)] == [
            "Gol totali",
            "Gol di squadra casa",
        ]

    def test_senza_mediane_resta_tutto_il_singolo(self) -> None:
        """La fonte delle mediane copre cinque giorni, questa arriva dove
        arriva il libro: fuori da quella finestra c'e' solo lei."""
        singolo = [self._m("kambi", "Doppia chance", 1.4)]
        assert job._unisci([], singolo) == singolo

    def test_il_prezzo_pubblicato_e_quello_della_mediana(self) -> None:
        """La precedenza deve arrivare fino alla chiave, non fermarsi alla
        lista: e' la chiave che la scheda partita cerca."""
        uniti = job._unisci(
            [self._m("betexplorer", "Gol totali", 1.91, "2.5")],
            [self._m("kambi", "Gol totali", 1.76, "2.5")],
        )
        assert job._prezzi(uniti)["over_2.5"]["decimale"] == 1.91


class TestLeChiaviDeiMercatiNuovi:
    """I gol di squadra e l'handicap europeo verso le chiavi del modello.

    Devono coincidere carattere per carattere con quelle di `model.markets`:
    e' su quelle che la scheda partita cerca il prezzo del pronostico
    consigliato, e `hg_under_2,5` sarebbe un prezzo vero che non si trova mai.
    """

    def test_le_chiavi_esistono_davvero_nel_catalogo(self) -> None:
        from pronostici.model.markets import catalog

        note = {d.key for d in catalog(12)}
        casi = [
            ({"mercato": "Gol di squadra casa", "linea": "2.5"}, {"esito": "Under"}),
            ({"mercato": "Gol di squadra ospite", "linea": "0.5"}, {"esito": "Over"}),
            ({"mercato": "Handicap europeo", "linea": "-2"}, {"esito": "2"}),
            ({"mercato": "Handicap europeo", "linea": "1"}, {"esito": "1"}),
            ({"mercato": "Handicap europeo", "linea": "-1"}, {"esito": "X"}),
        ]
        for mercato, esito in casi:
            chiave = job._chiave_nostra(mercato, esito)
            assert chiave in note, f"{mercato} {esito} -> {chiave}"

    def test_una_linea_che_il_modello_non_ha_non_inventa_niente(self) -> None:
        """Kambi quota anche l'handicap -4, noi arriviamo a -2.

        La chiave si costruisce lo stesso — e' una stringa — ma non corrisponde
        a nessun mercato nostro, quindi non la cerchera' mai nessuno. Quello
        che conta e' che non finisca sopra la chiave di un altro.
        """
        from pronostici.model.markets import catalog

        note = {d.key for d in catalog(12)}
        chiave = job._chiave_nostra(
            {"mercato": "Handicap europeo", "linea": "-4"}, {"esito": "2"}
        )
        assert chiave == "eh_-4_away"
        assert chiave not in note

    def test_un_esito_che_non_e_over_ne_under_non_diventa_una_chiave(self) -> None:
        assert (
            job._chiave_nostra(
                {"mercato": "Gol di squadra casa", "linea": "1.5"}, {"esito": "1"}
            )
            is None
        )
