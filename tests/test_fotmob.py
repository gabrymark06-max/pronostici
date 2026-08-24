"""I tassi di fotmob, e l'errore di unita' che ha gia' prodotto numeri assurdi.

Niente rete: i payload qui sotto hanno la stessa forma di quelli veri, ridotti
alle chiavi che leggiamo.
"""

from __future__ import annotations

from pronostici.sources import fotmob as fm


def _lista(titolo: str, righe: list[dict]) -> dict:
    return {"TopLists": [{"Title": titolo, "StatList": righe}]}


def _riga(nome: str, valore: float, minuti: int = 1800, partite: int = 20) -> dict:
    return {
        "ParticipantName": nome,
        "ParticiantId": 1,
        "TeamName": "Flamengo",
        "StatValue": valore,
        "MinutesPlayed": minuti,
        "MatchesPlayed": partite,
        "Positions": ["Forward"],
    }


class TestUnita:
    """Le statistiche non hanno tutte la stessa unita', e niente lo segnala.

    `goals` e `yellow_card` sono conteggi di stagione; `fouls` e
    `ontarget_scoring_att` sono gia' medie per 90. Dividendo tutto per i minuti
    come fosse un conteggio, il miglior attaccante del Brasileirao usciva a
    0,04 falli ogni novanta minuti: plausibile come forma, assurdo nei fatti,
    e nessun controllo lo avrebbe fermato.
    """

    def test_un_conteggio_si_divide_per_i_minuti(self) -> None:
        per_nome: dict[str, fm.Giocatore] = {}
        fm._accumula(per_nome, _lista("Top scorer", [_riga("Pedro", 15.0)]), "gol", False)
        # 15 gol in 1800 minuti = 0,75 a partita.
        assert per_nome["pedro"].tassi["gol_per_90"] == 0.75

    def test_una_media_si_prende_com_e(self) -> None:
        per_nome: dict[str, fm.Giocatore] = {}
        fm._accumula(
            per_nome,
            _lista("Fouls committed per 90", [_riga("Pedro", 0.8)]),
            "falli",
            True,
        )
        assert per_nome["pedro"].tassi["falli_per_90"] == 0.8

    def test_se_il_titolo_contraddice_la_dichiarazione_si_salta(self) -> None:
        """L'unico posto in cui fotmob dice l'unita' e' il titolo umano.

        Non e' un contratto — e' testo per le persone — ma un disaccordo
        significa che una delle due cose e' cambiata, e continuare vorrebbe
        dire pubblicare tassi sbagliati di un fattore venti.
        """
        per_nome: dict[str, fm.Giocatore] = {}
        fm._accumula(
            per_nome,
            _lista("Fouls committed per 90", [_riga("Pedro", 15.0)]),
            "falli",
            False,  # dichiarato come conteggio, ma il titolo dice per 90
        )
        assert per_nome == {}

    def test_il_contrario_vale_uguale(self) -> None:
        per_nome: dict[str, fm.Giocatore] = {}
        fm._accumula(per_nome, _lista("Top scorer", [_riga("Pedro", 15.0)]), "gol", True)
        assert per_nome == {}


class TestAccumulo:
    def test_le_statistiche_si_sommano_sullo_stesso_giocatore(self) -> None:
        per_nome: dict[str, fm.Giocatore] = {}
        fm._accumula(per_nome, _lista("Top scorer", [_riga("Pedro", 15.0)]), "gol", False)
        fm._accumula(per_nome, _lista("Assists", [_riga("Pedro", 4.0)]), "assist", False)
        assert sorted(per_nome["pedro"].tassi) == ["assist_per_90", "gol_per_90"]

    def test_i_minuti_sono_il_massimo_visto(self) -> None:
        """Un file che non elenca un giocatore non dice che ha giocato zero.

        Dice che non ha segnato. Prendere il minimo azzererebbe il
        denominatore di chi compare in una sola statistica.
        """
        per_nome: dict[str, fm.Giocatore] = {}
        fm._accumula(
            per_nome,
            _lista("Top scorer", [_riga("Pedro", 15.0, minuti=1800)]),
            "gol",
            False,
        )
        fm._accumula(
            per_nome,
            _lista("Yellow cards", [_riga("Pedro", 2.0, minuti=0)]),
            "gialli",
            False,
        )
        assert per_nome["pedro"].minuti == 1800


class TestSoglia:
    def test_un_campione_troppo_corto_non_diventa_un_tasso(self) -> None:
        """Un giallo in ventun minuti darebbe 4,3 gialli per 90.

        Cioe' piu' di quattro espulsioni a partita: e' un episodio
        moltiplicato, non una tendenza.
        """
        indice = _lista("Yellow cards", [_riga("Tale", 1.0, minuti=21, partite=1)])
        assert fm.tassi_lega("SA", frammenti={"yellow_card": indice}) == {}

    def test_con_abbastanza_minuti_si_pubblica(self) -> None:
        indice = _lista("Yellow cards", [_riga("Tale", 4.0, minuti=1800)])
        fuori = fm.tassi_lega("SA", frammenti={"yellow_card": indice})
        assert list(fuori) == ["tale"]


class TestCerca:
    def test_solo_corrispondenza_esatta(self) -> None:
        """Due compagni possono chiamarsi Silva e Silva Junior.

        Attribuire i cartellini dell'uno all'altro sarebbe un errore
        invisibile: il numero esce plausibile e riguarda la persona sbagliata.
        """
        tassi = {"joao silva": fm.Giocatore(nome="Joao Silva", squadra="X")}
        assert fm.cerca(tassi, "Joao Silva") is not None
        assert fm.cerca(tassi, "Joao Silva Junior") is None

    def test_gli_accenti_non_contano(self) -> None:
        tassi = {fm.canonical("Carlos Vinícius"): fm.Giocatore(nome="x", squadra="y")}
        assert fm.cerca(tassi, "Carlos Vinicius") is not None


class TestRuolo:
    def test_il_codice_numerico_non_diventa_un_ruolo(self) -> None:
        """`Positions` e' una lista di codici e la legenda non e' pubblica.

        Prendendone il primo, la scheda partita ha pubblicato «ruolo: 72»
        accanto a un giocatore vero: un numero senza significato, messo dove
        il lettore si aspetta «attaccante».
        """
        per_nome: dict[str, fm.Giocatore] = {}
        riga = _riga("Pedro", 15.0)
        riga["Positions"] = [115]
        fm._accumula(per_nome, _lista("Top scorer", [riga]), "gol", False)
        assert per_nome["pedro"].ruolo is None
