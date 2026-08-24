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
from ..model.giocatori import moltiplicatore_arbitro, stime_giocatore
from ..sources import betexplorer as bx
from ..sources import fotmob as fm
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


# I mercati estesi verso le NOSTRE chiavi. La tabella e' la stessa che il
# progetto usa per le quote principali, cosi' i due insiemi si possono
# confrontare invece di vivere in universi separati.
_CHIAVI: dict[str, dict[str, str]] = {
    "Esito finale": {"1": "1x2_home", "X": "1x2_draw", "2": "1x2_away"},
    "Doppia chance": {"1X": "dc_1x", "12": "dc_12", "X2": "dc_x2"},
    "Entrambe segnano": {"Sì": "btts_yes", "No": "btts_no"},
}


def _market_p(mercati: list[dict]) -> dict[str, float]:
    """Le probabilita' sgonfiate, nelle nostre chiavi.

    Riempie la colonna «il mercato» sulle partite che la fonte principale non
    copre. Sta in un campo suo e non dentro `odds` apposta: le due fonti non
    si mescolano nello stesso posto, cosi' la pagina puo' sempre dire da dove
    viene il numero che mostra.
    """
    fuori: dict[str, float] = {}
    for mercato in mercati:
        nome = mercato.get("mercato")
        for esito in mercato.get("esiti") or []:
            p = esito.get("probabilita_implicita")
            if p is None:
                continue
            if nome == "Gol totali" and mercato.get("linea"):
                verso = "over" if esito["esito"] == "Over" else "under"
                fuori[f"{verso}_{mercato['linea']}"] = p
            else:
                chiave = _CHIAVI.get(nome or "", {}).get(esito.get("esito", ""))
                if chiave:
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
                    blocco["quote"] = {"n_mercati": len(quote), "mercati": quote}
                    probabilita = _market_p(quote)
                    if probabilita:
                        blocco["market_p"] = probabilita

        # ------------------------------------------- le stime sui singoli
        if formazione is not None and codice in tassi_lega:
            conta = {"nome_non_trovato": 0, "campione_corto": 0}
            stime = _giocatori(formazione, tassi_lega[codice], arbitro, conta)
            report["giocatori_nome_non_trovato"] += conta["nome_non_trovato"]
            report["giocatori_campione_corto"] += conta["campione_corto"]
            if stime:
                report["con_giocatori"] += 1
                blocco["giocatori"] = stime

        if _senza_ora(blocco) == _senza_ora(entry.get("contorno") or {}):
            continue
        per_giorno[giorno].append({**entry, "contorno": blocco})

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
