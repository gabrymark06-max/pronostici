"""Job — `contorno`: formazioni, arbitro, mercati estesi e stime sui singoli.

PERCHE' SOSTITUISCE `jobs.sofascore`. Dal 23 agosto 2026 Sofascore autorizza la
sua API con un token che nasce solo dentro un browser vero e solo per IP
residenziali. Sui runner di GitHub la pagina non ne riceve nessuno — provato — e
il job era finito su un runner in casa: il progetto era tornato a dipendere da
un computer acceso, che e' esattamente la dipendenza da cui era uscito in
agosto.

Qui non c'e' nessun lucchetto da aggirare. Quattro fonti, tutte raggiungibili
da qualunque macchina e tutte provate DAI RUNNER DI GITHUB, non da un
portatile:

    formazioni previste   sportsgambler.com, HTML pubblico, nessuna chiave
    arbitro               football-data.org, la chiave che gia' abbiamo
    mercati estesi        betexplorer.com, con i bookmaker italiani
    tassi dei giocatori   fotmob, un file JSON per statistica

COSA CAMBIA IN MEGLIO. Le previsioni arrivano fino a due settimane prima invece
delle 56 ore di mediana di Sofascore, quindi la finestra predefinita e' piu'
larga.

COSA SI PERDE, e va detto invece che scoperto:

  · LA PANCHINA. Sportsgambler pubblica gli undici e basta.
  · LE MEDIE CARTELLINI DELL'ARBITRO. Il nome arriva, le sue statistiche no,
    e senza quelle `moltiplicatore_arbitro` vale 1: le stime sui cartellini
    non sono piu' corrette per chi dirige. E' un'informazione in meno, non un
    numero sbagliato — ma il campo resta nel blocco, a 1, perche' si veda.
  · IL PRIMO TEMPO. Betexplorer non lo espone fra i mercati che leggiamo.

NON SCRIVE MAI SU UNA PARTITA GIA' COMINCIATA: dopo il fischio d'inizio queste
non sono piu' informazioni pre-partita.

DOVE SCRIVE. Nel campo `contorno`, non in `sofascore`. Il vecchio campo resta
dov'e' sui file gia' scritti — sono dati veri, letti davvero da Sofascore — ma
non si riempie piu': mettere dati di altre fonti in un campo chiamato
`sofascore` sarebbe una bugia che nessun controllo puo' pescare. Per la stessa
ragione ogni sezione porta la sua `fonte`: le quattro vengono da quattro posti
diversi, e la pagina deve poterlo dire.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from .. import fixtures as fx
from ..fixtures import CAMPO_CONTORNO
from ..model.giocatori import moltiplicatore_arbitro, stime_giocatore
from ..sources import betexplorer as bx
from ..sources import fotmob as fm
from ..sources import kambi as kb
from ..sources import sportsgambler as sg
from ..sources.football_data import FootballDataClient, FootballDataError

log = logging.getLogger(__name__)

# Sette giorni, non quattro. Sofascore obbligava a stare stretti perche' oltre
# le ~56 ore non c'era niente da leggere; qui le previsioni ci sono, e una
# partita che compare in pagina con una settimana d'anticipo non ha ragione di
# essere ignorata.
FINESTRA_DEFAULT = 7

# Fra una richiesta e l'altra. Un giro completo sono una decina di pagine di
# elenco e una settantina di frammenti: senza pausa sarebbero un centinaio di
# richieste in pochi secondi contro un sito che non ci ha chiesto niente e non
# ci fa pagare niente.
PAUSA_S = 0.7

# Sotto questo numero di partite agganciate, «zero formazioni» puo' essere
# vero: una finestra corta in pausa nazionali non ha niente da leggere.
# Sopra, non puo'.
SOGLIA_ALLARME = 10

# I MERCATI SI CHIEDONO SOLO PER LE PARTITE VICINE, e non per avarizia: sono
# cinque richieste per partita, e betexplorer risponde 429 se si corre.
#
# CINQUE GIORNI, misurati e non scelti a occhio. Con tre, il giro del 24 agosto
# ne copriva sei su cinquantaquattro agganciate: quasi tutte le partite in
# cartellone cadevano fuori, perche' le giornate piene erano il 28, 29 e 30.
# Con cinque ci si arriva.
#
# Non di piu', e non e' solo il tempo: le quote si muovono, e leggerle una
# volta a sette giorni per poi non tornarci sarebbe pubblicare un prezzo
# vecchio. Con due giri al giorno e questa finestra, ogni partita ha i suoi
# mercati riletti dieci volte prima del fischio d'inizio.
FINESTRA_MERCATI = 5

# Quanti minuti si attribuiscono a un titolare. Non 90: chi comincia esce, e
# il termine dei minuti attesi domina tutte le stime. Lo stesso numero che
# usava il job di prima.
MINUTI_TITOLARE = 76

# OLTRE QUESTO TEMPO NON SI CHIEDONO PIU' MERCATI, e si scrive quello che c'e'.
#
# I mercati sono la parte lenta e crescente: betexplorer limita il numero di
# richieste, quindi il giro rallenta da solo quando ce ne sono tante, e le
# partite crescono con le giornate piene. Misurato: 23,7 minuti con 43 partite,
# contro un tetto del workflow di 45.
#
# Il punto non e' la stima, e' cosa succede quando sbaglia. Il commit sta in
# fondo: un giro ucciso dal tetto non scrive NIENTE — nemmeno le formazioni,
# che erano gia' in mano da venti minuti e che dopo il fischio d'inizio non si
# recuperano piu'. Meglio qualche partita senza mercati che un giorno intero
# senza contorno.
SCADENZA_MERCATI_S = 1800


def _giorni(finestra: int, oggi: str) -> list[str]:
    inizio = datetime.strptime(oggi, "%Y-%m-%d").replace(tzinfo=UTC)
    return [
        (inizio + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(finestra + 1)
    ]


def _cartellone(report: dict) -> list[sg.PartitaSG]:
    """L'elenco unito di tutte le competizioni.

    LE PAGINE MESCOLANO LE COMPETIZIONI: sulla pagina della Premier League
    compaiono anche partite di Championship. Filtrare per lega scarterebbe
    proprio quelle righe, e non serve a niente: due nomi di squadra piu' la
    data identificano una partita meglio di quanto faccia l'etichetta del
    campionato.
    """
    cartellone: list[sg.PartitaSG] = []
    for codice in sg.LEGHE:
        try:
            righe = sg.elenco(codice)
        except sg.SportsgamblerNonRaggiungibile as exc:
            # Una lega che non risponde non ferma le altre: le sue partite
            # restano senza formazione, che e' com'erano prima.
            log.warning("elenco %s non letto: %s", codice, exc)
            report["leghe_non_lette"].append(codice)
            continue
        cartellone.extend(righe)
        time.sleep(PAUSA_S)
    return cartellone


def _arbitri(competizioni: set[str], da: str, a: str, report: dict) -> dict[int, dict]:
    """Nome dell'arbitro per id partita, da football-data.org.

    Le designazioni escono tardi — misurato il 24 agosto 2026: una su dodici
    per le partite oltre la settimana — quindi la maggior parte dei giri ne
    trova poche. Non e' un guasto: e' quando esistono.
    """
    trovati: dict[int, dict] = {}
    cliente = FootballDataClient()
    for codice in sorted(competizioni):
        try:
            dati = cliente.get(
                f"/competitions/{codice}/matches", {"dateFrom": da, "dateTo": a}
            )
        except FootballDataError as exc:
            log.warning("arbitri %s non letti: %s", codice, exc)
            report["arbitri_non_letti"].append(codice)
            continue
        for partita in dati.get("matches", []):
            for ufficiale in partita.get("referees") or []:
                if ufficiale.get("type") == "REFEREE" and ufficiale.get("name"):
                    trovati[partita["id"]] = {
                        "fonte": "football-data",
                        "nome": ufficiale["name"],
                        "paese": ufficiale.get("nationality"),
                    }
                    break
    return trovati


def _cartelloni_mercati(report: dict) -> dict[str, list[bx.PartitaBX]]:
    """L'elenco di betexplorer per ogni competizione, tenuto separato per lega.

    Separato e non unito come quello di sportsgambler: li' l'aggancio usa
    anche la data e un elenco unico va bene, qui si abbina sui soli nomi e
    l'elenco copre l'intera stagione. Mescolare nove campionati vorrebbe dire
    cercare "Bologna - Lazio" fra millecinquecento righe di paesi diversi.
    """
    per_lega: dict[str, list[bx.PartitaBX]] = {}
    for codice in bx.LEGHE:
        try:
            per_lega[codice] = bx.elenco(codice)
        except bx.LegaVuota as exc:
            # NON e' «non risponde»: risponde e non ha niente dentro, che
            # significa percorso o markup cambiati. Va distinto, perche' il
            # primo si risolve da solo e il secondo no.
            log.error("%s", exc)
            report["leghe_vuote"].append(codice)
        except bx.BetexplorerNonRaggiungibile as exc:
            log.warning("elenco mercati %s non letto: %s", codice, exc)
            report["mercati_non_letti"].append(codice)
    return per_lega


def _mercati_kambi(
    da_fare: list[tuple[str, dict, datetime]], report: dict
) -> dict[int, list[dict]]:
    """I gol di squadra e l'handicap europeo, per `match_id` nostro.

    TUTTO IN UN COLPO, PRIMA DEL GIRO, e non partita per partita dentro: kambi
    accetta cinque id per richiesta, quindi cinquanta partite costano dieci
    richieste invece di cinquanta. Un giro intero sta sotto il minuto, e questo
    ha una conseguenza che vale piu' della velocita' — questi mercati NON
    dipendono da `SCADENZA_MERCATI_S`. Quando betexplorer viene interrotto dal
    tempo, le partite rimaste perdono la doppia chance e i gol totali; il
    prezzo del pronostico consigliato, che quasi sempre e' una di queste due
    famiglie, resta.

    NESSUNA FINESTRA, al contrario di betexplorer: il loro elenco contiene solo
    le partite col libro aperto — tipicamente due giornate — quindi la finestra
    la impone gia' la fonte, e ristringerla ancora toglierebbe soltanto.
    """
    per_lega: dict[str, list[kb.EventoKB]] = {}
    for codice in kb.LEGHE:
        try:
            per_lega[codice] = kb.elenco(codice)
        except kb.LegaVuota as exc:
            # Qui vuoto NON e' un guasto: e' una lega ferma o fuori stagione.
            # Su betexplorer significherebbe percorso cambiato, perche' li'
            # l'elenco e' la stagione intera; qui sono le partite quotate.
            log.info("%s", exc)
            report["kambi_leghe_ferme"].append(codice)
        except kb.KambiNonRaggiungibile as exc:
            log.warning("elenco kambi %s non letto: %s", codice, exc)
            report["kambi_non_letta"].append(codice)

    abbinati: dict[int, int] = {}
    eventi: dict[int, kb.EventoKB] = {}
    for _giorno, entry, calcio in da_fare:
        loro = kb.aggancia(
            per_lega.get(entry.get("competition", ""), []),
            entry["home"]["name"],
            entry["away"]["name"],
            calcio,
        )
        if loro is None:
            continue
        abbinati[entry["match_id"]] = loro.id
        eventi[loro.id] = loro

    report["kambi_agganciate"] = len(abbinati)
    if not eventi:
        return {}

    quote = kb.quote_di_gruppo(list(eventi.values()))
    return {
        match_id: quote[id_evento]
        for match_id, id_evento in abbinati.items()
        if quote.get(id_evento)
    }


# I mercati estesi verso le NOSTRE chiavi. La tabella e' la stessa che il
# progetto usa per le quote principali, cosi' i due insiemi si possono
# confrontare invece di vivere in universi separati.
_CHIAVI: dict[str, dict[str, str]] = {
    "Esito finale": {"1": "1x2_home", "X": "1x2_draw", "2": "1x2_away"},
    "Doppia chance": {"1X": "dc_1x", "12": "dc_12", "X2": "dc_x2"},
    "Entrambe segnano": {"Sì": "btts_yes", "No": "btts_no"},
}

# I mercati con una linea: il nome del mercato verso il prefisso della chiave.
# Il verso (`over`/`under`, oppure `home`/`draw`/`away`) lo mette l'esito.
_PREFISSO_LINEA: dict[str, str] = {
    "Gol totali": "",
    kb.MERCATO_GOL_CASA: "hg_",
    kb.MERCATO_GOL_OSPITE: "ag_",
}

_LATI_HANDICAP = {"1": "home", "X": "draw", "2": "away"}


def _chiave_nostra(mercato: dict, esito: dict) -> str | None:
    """La chiave con cui il resto del progetto chiama questo esito.

    LE CHIAVI DEVONO COINCIDERE CON QUELLE DI `model.markets`, carattere per
    carattere: e' su quelle che la scheda partita cerca il prezzo del
    pronostico consigliato. `hg_under_2.5` con la linea scritta `2,5` o `2.50`
    sarebbe un prezzo vero che non si ritrova mai.
    """
    nome = mercato.get("mercato") or ""
    linea = mercato.get("linea")

    if nome == kb.MERCATO_HANDICAP and linea:
        lato = _LATI_HANDICAP.get(esito.get("esito", ""))
        return f"eh_{linea}_{lato}" if lato else None

    prefisso = _PREFISSO_LINEA.get(nome)
    if prefisso is not None and linea:
        verso = esito.get("esito")
        if verso not in ("Over", "Under"):
            return None
        return f"{prefisso}{verso.lower()}_{linea}"

    return _CHIAVI.get(nome, {}).get(esito.get("esito", ""))


def _unisci(mediane: list[dict], singolo: list[dict]) -> list[dict]:
    """Le due liste in una, senza doppioni, con le mediane davanti.

    LE FONTI SI SOVRAPPONGONO. Da quando kambi legge anche esito finale, doppia
    chance, entrambe segnano e gol totali — che gli costano zero richieste in
    piu', perche' stanno nella stessa risposta — quei quattro mercati arrivano
    da tutte e due. Concatenare vorrebbe dire due righe «Gol totali 2,5» una
    sotto l'altra con due prezzi diversi: entrambi veri, e insieme illeggibili.

    A parita' di mercato e linea vince la MEDIANA: e' calcolata su una ventina
    di operatori contro l'unico di kambi. Lui resta per tutto il resto — i gol
    di squadra e l'handicap europeo, che nessun comparatore pubblica — e per le
    partite su cui l'altra fonte non ha agganciato niente.
    """
    chiave = lambda m: (m.get("mercato"), m.get("linea"))  # noqa: E731
    visti = {chiave(m) for m in mediane}
    return [*mediane, *(m for m in singolo if chiave(m) not in visti)]


def _prezzi(mercati: list[dict]) -> dict[str, dict]:
    """I PREZZI VERI, nelle nostre chiavi. Non le probabilita': le quote.

    La differenza conta piu' di quanto sembri. `market_p` qui sotto sono
    probabilita' sgonfiate del margine — utili per confrontare, ma nessuno le
    paga. Questi sono i numeri che un operatore espone davvero, e sono gli
    unici che la pagina ha il diritto di chiamare «quota».

    Servono perche' the-odds-api quota cinque mercati e il pronostico
    consigliato quasi mai e' uno di quelli: misurato il 25 agosto 2026, quattro
    consigli su trentatre avevano un prezzo. Con la doppia chance, i gol totali
    su ogni linea e l'entrambe segnano di betexplorer diventano undici, e con i
    gol di squadra e l'handicap europeo di kambi quasi tutti.

    IL PRIMO CHE NOMINA UNA CHIAVE SE LA TIENE, e l'ordine della lista non e'
    un caso: betexplorer sta davanti perche' i suoi prezzi sono una mediana di
    operatori, kambi dietro perche' e' il prezzo di uno solo. Dove esistono
    entrambi vince la mediana; dove esiste solo lui, un prezzo di un operatore
    e' meglio di nessun prezzo — purche' il dato dica quale dei due e', ed e'
    per questo che `operatori` viaggia insieme al numero.
    """
    fuori: dict[str, dict] = {}
    for mercato in mercati:
        for esito in mercato.get("esiti") or []:
            quota = esito.get("decimale")
            chiave = _chiave_nostra(mercato, esito)
            if chiave in fuori:
                continue
            if chiave and isinstance(quota, int | float) and quota > 1:
                # Il numero di operatori viaggia CON il prezzo. La pagina dice
                # «mediana di N operatori» e quel N cambia da un mercato
                # all'altro: tenerne uno solo per partita vorrebbe dire
                # attribuire a una linea il consenso di un'altra.
                fuori[chiave] = {
                    "decimale": float(quota),
                    "operatori": mercato.get("n_bookmaker") or 0,
                    # DA DOVE VIENE QUESTO NUMERO. Non e' ridondante con
                    # `operatori`: la pagina scrive «operatori statunitensi»
                    # per la mediana di betexplorer, che dai nostri runner
                    # mostra libri americani, e «un operatore europeo» per
                    # kambi. Senza questo campo la mappa dei prezzi non
                    # ricorda piu' quale delle due ha scritto la riga, e la
                    # frase sarebbe giusta per una e falsa per l'altra.
                    "fonte": mercato.get("fonte"),
                }
    return fuori


def _market_p(mercati: list[dict]) -> dict[str, float]:
    """Le probabilita' sgonfiate, nelle nostre chiavi.

    Riempie la colonna «il mercato» sulle partite che la fonte principale non
    copre. Sta in un campo suo e non dentro `odds` apposta: le due fonti non
    si mescolano nello stesso posto, cosi' la pagina puo' sempre dire da dove
    viene il numero che mostra.
    """
    fuori: dict[str, float] = {}
    for mercato in mercati:
        for esito in mercato.get("esiti") or []:
            p = esito.get("probabilita_implicita")
            chiave = _chiave_nostra(mercato, esito)
            # Stessa precedenza dei prezzi, e per la stessa ragione: la
            # probabilita' e' quella di QUELLE quote, e prenderla da una fonte
            # mentre il prezzo viene dall'altra vorrebbe dire mostrare in due
            # celle vicine due numeri che non parlano dello stesso mercato.
            if chiave and p is not None and chiave not in fuori:
                fuori[chiave] = p
    return fuori


def _tassi_per_lega(competizioni: set[str], report: dict) -> dict[str, dict]:
    """I tassi per 90 dei giocatori, una lega per volta.

    Cinque file per campionato e nient'altro: fotmob li pubblica gia'
    aggregati, quindi non serve nessuna cache — il giro intero costa meno di
    un minuto, contro le circa milleduecento chiamate per giocatore che
    costava la stessa cosa su Sofascore.
    """
    fuori: dict[str, dict] = {}
    for codice in sorted(competizioni & set(fm.LEGHE)):
        try:
            tassi = fm.tassi_lega(codice)
        except fm.FotmobNonRaggiungibile as exc:
            log.warning("tassi %s non letti: %s", codice, exc)
            report["tassi_non_letti"].append(codice)
            continue
        if tassi:
            fuori[codice] = tassi
        else:
            # A stagione appena cominciata nessuno ha ancora i minuti minimi.
            # Non e' un guasto, ed e' meglio dirlo che lasciare un buco muto.
            report["leghe_senza_tassi"].append(codice)
    return fuori


def _stime_lato(
    titolari: list[dict], tassi: dict, molt: float, conta: dict
) -> list[dict]:
    """Le stime per gli undici di una squadra.

    SOLO I TITOLARI, come prima: per un subentrato i minuti attesi sarebbero
    inventati, e i minuti attesi sono il termine che domina ogni stima.
    """
    elenco: list[dict] = []
    for giocatore in titolari:
        trovato = fm.cerca(tassi, giocatore.get("nome", ""))
        if trovato is None:
            conta["nome_non_trovato"] += 1
            continue
        stime = stime_giocatore(
            trovato.per_il_modello(),
            minuti_attesi=MINUTI_TITOLARE,
            molt_cartellini=molt,
        )
        if not stime:
            # IL MODELLO RIFIUTA I CAMPIONI CORTI, ed e' una sua regola:
            # «meglio nessuna stima che una stima su tre partite». A stagione
            # appena cominciata rifiuta quasi tutti, e senza questo contatore
            # il report direbbe «ho i tassi di cinque campionati» accanto a
            # zero stime, senza dire perche'.
            conta["campione_corto"] += 1
            continue
        elenco.append(
            {
                "id": trovato.id_fotmob,
                "nome": trovato.nome,
                "ruolo": trovato.ruolo,
                "presenze": trovato.presenze,
                "minuti": trovato.minuti,
                "stime": [
                    {
                        "mercato": s.mercato,
                        "etichetta": s.etichetta,
                        "p": s.p,
                        "base": s.base,
                    }
                    for s in stime
                ],
            }
        )
    return elenco


def _giocatori(
    formazione: sg.Formazione, tassi: dict, arbitro: dict | None, conta: dict
) -> dict | None:
    """Le stime sui singoli, o `None` se non c'e' nessuno da stimare."""
    # SENZA LE MEDIE DELL'ARBITRO IL MOLTIPLICATORE VALE 1, e si vede.
    #
    # Sofascore mandava quanti gialli estrae un arbitro a partita, e le stime
    # sui cartellini venivano corrette di conseguenza. football-data.org manda
    # il nome e basta. Il campo resta nel blocco, a 1: toglierlo farebbe
    # sparire l'informazione che quella correzione non c'e' piu'.
    arb = arbitro or {}
    molt = moltiplicatore_arbitro(arb.get("gialli_per_partita"), arb.get("partite"))

    casa = _stime_lato(formazione.casa.titolari, tassi, molt, conta)
    ospiti = _stime_lato(formazione.ospiti.titolari, tassi, molt, conta)
    if not casa and not ospiti:
        return None

    return {
        "fonte": "fotmob",
        "misurato": False,
        "nota": (
            "Stime non misurate: non esiste una quota di mercato su questi "
            "esiti ne' uno storico per verificarle. Non entrano nel registro."
        ),
        "moltiplicatore_arbitro": round(molt, 3),
        "minuti_attesi_titolare": MINUTI_TITOLARE,
        "casa": casa,
        "ospiti": ospiti,
    }


def _lato(lato: sg.Lato) -> dict:
    return {
        "modulo": lato.modulo,
        "titolari": lato.titolari,
        # Sportsgambler non pubblica la panchina. Il campo resta, vuoto: il
        # contratto con il frontend non cambia, e una lista vuota dice «non
        # ce l'ho» meglio di un campo assente.
        "panchina": [],
    }


def _blocco(
    formazione: sg.Formazione,
    *,
    confermate_in_elenco: bool,
    ore_prima: float | None,
    letto: str,
    arbitro: dict | None,
) -> dict:
    # SI DICHIARA «CONFERMATA» SOLO SE LO DICONO ENTRAMBI.
    #
    # L'elenco e il frammento non sempre concordano: Bologna-Lazio aveva il
    # pulsante «Confirmed Lineups» e dentro «Predicted Lineup». Uno dei due e'
    # vecchio, e non sappiamo quale. Nel dubbio si dice la cosa piu' debole —
    # sbagliare dicendo «probabile» costa un'imprecisione, sbagliare dicendo
    # «confermata» significa affermare che quello e' l'undici che scende in
    # campo quando non lo sappiamo.
    blocco: dict = {
        "letto": letto,
        "formazioni": {
            "fonte": "sportsgambler",
            "confermate": bool(formazione.confermate and confermate_in_elenco),
            "ore_prima": ore_prima,
            "casa": _lato(formazione.casa),
            "ospiti": _lato(formazione.ospiti),
        },
    }
    if arbitro:
        blocco["arbitro"] = arbitro
    return blocco


def _senza_ora(blocco: dict) -> dict:
    """Il blocco senza `letto`, per capire se e' cambiato qualcosa di sostanza.

    `letto` cambia a ogni giro per costruzione. Se entrasse nel confronto ogni
    esecuzione riscriverebbe tutti i file, e il registro pubblico delle
    modifiche — che e' meta' del prodotto — diventerebbe illeggibile.
    """
    return {k: v for k, v in blocco.items() if k != "letto"}


def _allarme_parsing(report: dict) -> str | None:
    """Il messaggio da dare se il markup e' cambiato, o `None` se regge.

    Sta fuori da `run` perche' sia provabile senza rete: e' una condizione su
    due numeri, e un test che ne ricopiasse la formula dentro l'asserzione non
    proverebbe niente.
    """
    if report["agganciate"] >= SOGLIA_ALLARME and report["con_formazioni"] == 0:
        return (
            f"{report['agganciate']} partite agganciate e nessuna formazione letta: "
            "il markup di sportsgambler e' probabilmente cambiato. "
            "Controlla `_leggi_formazione` in sources/sportsgambler.py."
        )
    return None


def run(
    *,
    finestra: int = FINESTRA_DEFAULT,
    dry_run: bool = False,
    oggi: str | None = None,
) -> dict:
    partenza = time.monotonic()
    adesso = datetime.now(UTC)
    oggi = oggi or adesso.strftime("%Y-%m-%d")
    letto = adesso.strftime("%Y-%m-%dT%H:%M:%SZ")

    report: dict = {
        "generated_at": letto,
        "finestra_giorni": finestra,
        "esaminate": 0,
        "agganciate": 0,
        "con_formazioni": 0,
        "con_arbitro": 0,
        "con_mercati": 0,
        "con_giocatori": 0,
        "giocatori_nome_non_trovato": 0,
        "giocatori_campione_corto": 0,
        "non_agganciate": [],
        "leghe_non_lette": [],
        "arbitri_non_letti": [],
        "mercati_non_letti": [],
        "leghe_vuote": [],
        "mercati_interrotti_per_tempo": False,
        "kambi_agganciate": 0,
        "con_mercati_kambi": 0,
        "kambi_leghe_ferme": [],
        "kambi_non_letta": [],
        "tassi_non_letti": [],
        "leghe_senza_tassi": [],
        "days_written": [],
        "dry_run": dry_run,
    }

    giorni = _giorni(finestra, oggi)
    cartellone = _cartellone(report)
    report["righe_in_cartellone"] = len(cartellone)
    if not cartellone:
        report["errore"] = "nessun elenco letto: il sito non ha risposto su nessuna lega"
        report["seconds"] = round(time.monotonic() - partenza, 1)
        return report

    # Prima si guarda quali partite ci sono davvero: gli arbitri si chiedono
    # solo per le competizioni in cartellone, non per tutte.
    competizioni: set[str] = set()
    da_fare: list[tuple[str, dict, datetime]] = []
    for giorno in giorni:
        esistente = fx.load_day(giorno)
        if not esistente:
            continue
        for entry in esistente.get("fixtures", []):
            try:
                calcio = datetime.fromisoformat(entry["utc_date"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if calcio <= adesso:
                continue
            report["esaminate"] += 1
            competizioni.add(entry.get("competition", ""))
            da_fare.append((giorno, entry, calcio))

    arbitri = _arbitri(competizioni & set(sg.LEGHE), giorni[0], giorni[-1], report)
    report["arbitri_disponibili"] = len(arbitri)

    mercati_lega = _cartelloni_mercati(report)
    mercati_kambi = _mercati_kambi(da_fare, report)
    report["con_mercati_kambi"] = len(mercati_kambi)
    tassi_lega = _tassi_per_lega(competizioni, report)
    report["leghe_con_tassi"] = sorted(tassi_lega)

    # OLTRE QUESTO ISTANTE non si chiedono piu' mercati: sono cinque richieste
    # lente per partita, e su una finestra di sette giorni supererebbero da
    # sole il tempo massimo del job.
    limite_mercati = adesso + timedelta(days=FINESTRA_MERCATI)

    per_giorno: dict[str, list[dict]] = defaultdict(list)
    frammenti: dict[int, sg.Formazione | None] = {}
    mercati_scaduti = False

    for giorno, entry, calcio in da_fare:
        loro = sg.aggancia(
            cartellone, entry["home"]["name"], entry["away"]["name"], calcio
        )
        if loro is None:
            report["non_agganciate"].append(
                {
                    "match_id": entry["match_id"],
                    "partita": f"{entry['home']['name']} - {entry['away']['name']}",
                    "motivo": "nessuna riga corrispondente nel cartellone",
                }
            )
            continue

        report["agganciate"] += 1
        # Una stessa riga puo' servire due nostre partite quando i calendari
        # divergono: il frammento si scarica una volta.
        if loro.id not in frammenti:
            try:
                frammenti[loro.id] = sg.formazione(
                    loro.id, sg.LEGHE.get(entry.get("competition", ""), "")
                )
            except sg.SportsgamblerNonRaggiungibile as exc:
                log.warning("frammento %s non letto: %s", loro.id, exc)
                frammenti[loro.id] = None
            time.sleep(PAUSA_S)

        formazione = frammenti[loro.id]
        arbitro = arbitri.get(entry["match_id"])
        if formazione is None:
            # Nessuna formazione pubblicata: se pero' l'arbitro c'e', vale da
            # solo e va scritto lo stesso.
            if not arbitro:
                continue
            blocco = {"letto": letto, "arbitro": arbitro}
        else:
            report["con_formazioni"] += 1
            blocco = _blocco(
                formazione,
                confermate_in_elenco=loro.confermate,
                ore_prima=sg.ore_prima(calcio, adesso),
                letto=letto,
                arbitro=arbitro,
            )
        if arbitro:
            report["con_arbitro"] += 1

        codice = entry.get("competition", "")

        # ------------------------------------------------ i mercati estesi
        if not mercati_scaduti and time.monotonic() - partenza > SCADENZA_MERCATI_S:
            mercati_scaduti = True
            report["mercati_interrotti_per_tempo"] = True
            log.warning(
                "oltre %ds: smetto di chiedere mercati e scrivo quello che ho",
                SCADENZA_MERCATI_S,
            )

        quote: list[dict] = []
        if calcio <= limite_mercati and not mercati_scaduti:
            loro_bx = bx.aggancia(
                mercati_lega.get(codice, []),
                entry["home"]["name"],
                entry["away"]["name"],
            )
            if loro_bx is not None:
                try:
                    quote = bx.mercati(loro_bx, codice)
                except bx.BetexplorerNonRaggiungibile as exc:
                    log.warning("mercati di %s non letti: %s", entry["match_id"], exc)
                    quote = []
                if quote:
                    report["con_mercati"] += 1

        # LE MEDIANE DAVANTI, IL SINGOLO OPERATORE DIETRO. L'ordine di questa
        # lista decide chi vince quando due fonti quotano lo stesso mercato:
        # `_prezzi` e `_market_p` tengono il primo che nomina una chiave.
        quote = _unisci(quote, mercati_kambi.get(entry["match_id"], []))

        if quote:
            blocco["quote"] = {"n_mercati": len(quote), "mercati": quote}
            probabilita = _market_p(quote)
            if probabilita:
                blocco["market_p"] = probabilita
            prezzi = _prezzi(quote)
            if prezzi:
                blocco["prezzi"] = prezzi

        # ------------------------------------------- le stime sui singoli
        if formazione is not None and codice in tassi_lega:
            conta = {"nome_non_trovato": 0, "campione_corto": 0}
            stime = _giocatori(formazione, tassi_lega[codice], arbitro, conta)
            report["giocatori_nome_non_trovato"] += conta["nome_non_trovato"]
            report["giocatori_campione_corto"] += conta["campione_corto"]
            if stime:
                report["con_giocatori"] += 1
                blocco["giocatori"] = stime

        if _senza_ora(blocco) == _senza_ora(entry.get(CAMPO_CONTORNO) or {}):
            continue
        per_giorno[giorno].append({**entry, CAMPO_CONTORNO: blocco})

    if not dry_run:
        for giorno, aggiornate in per_giorno.items():
            if aggiornate and fx.upsert_day(giorno, aggiornate, generated_at=adesso):
                report["days_written"].append(giorno)

    # SE IL SITO CAMBIA UNA CLASSE CSS, IL GIRO DEVE DIVENTARE ROSSO.
    #
    # E' il guasto tipico di una fonte che si legge dall'HTML, ed e' silenzioso:
    # l'elenco continua a rispondere 200, le partite si agganciano tutte, i
    # frammenti arrivano — e non se ne cava piu' un giocatore. Il job uscirebbe
    # verde avendo scritto niente, e nessuno se ne accorgerebbe fino a guardare
    # una scheda partita e trovarla spoglia. Nel frattempo le formazioni di
    # quei giorni sono perse: esistono solo prima del fischio d'inizio.
    #
    # La soglia serve a non gridare al lupo su un giro piccolo. Con almeno
    # dieci partite agganciate e zero formazioni lette, la spiegazione «nessuno
    # ha ancora pubblicato niente» non regge: vorrebbe dire nessuna formazione
    # su dieci partite in sette giorni e nove campionati. E' rotto il parsing.
    allarme = _allarme_parsing(report)
    if allarme:
        report["errore"] = allarme
        log.error("%s", allarme)

    report["seconds"] = round(time.monotonic() - partenza, 1)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Il contorno delle partite: formazioni, arbitro, mercati, giocatori"
    )
    parser.add_argument("--window-days", type=int, default=FINESTRA_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--today", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    report = run(finestra=args.window_days, dry_run=args.dry_run, oggi=args.today)
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 1 if report.get("errore") else 0


if __name__ == "__main__":
    raise SystemExit(main())
