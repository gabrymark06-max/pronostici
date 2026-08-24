"""Job — `formazioni`: attacca formazioni previste e arbitro, senza browser.

PERCHE' SOSTITUISCE `jobs.sofascore`. Dal 23 agosto 2026 Sofascore autorizza la
sua API con un token che nasce solo dentro un browser vero e solo per IP
residenziali. Sui runner di GitHub la pagina non ne riceve nessuno — provato — e
il job era finito su un runner in casa: il progetto era tornato a dipendere da
un computer acceso, che e' esattamente la dipendenza da cui era uscito in
agosto.

Qui non c'e' nessun lucchetto da aggirare. Due fonti, entrambe raggiungibili da
qualunque macchina:

    formazioni previste   sportsgambler.com, HTML pubblico, nessuna chiave
    arbitro               football-data.org, la chiave che gia' abbiamo

COSA CAMBIA IN MEGLIO. Le previsioni arrivano fino a due settimane prima invece
delle 56 ore di mediana di Sofascore, quindi la finestra predefinita e' piu'
larga.

COSA SI PERDE, e va detto invece che scoperto: la panchina, le statistiche
dell'arbitro (medie cartellini) e le quote estese. Il nome dell'arbitro resta,
le sue medie no. Le quote non mancano davvero — arrivano gia' da `jobs.quote`,
che e' la fonte principale e non e' mai passata di qui.

NON SCRIVE MAI SU UNA PARTITA GIA' COMINCIATA: dopo il fischio d'inizio queste
non sono piu' informazioni pre-partita.

DOVE SCRIVE. Nel campo `contorno`, non in `sofascore`. Il vecchio campo resta
dov'e' sui file gia' scritti — sono dati veri, letti davvero da Sofascore — ma
non si riempie piu': mettere dati di sportsgambler in un campo chiamato
`sofascore` sarebbe una bugia che nessun controllo puo' pescare.
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
        "non_agganciate": [],
        "leghe_non_lette": [],
        "arbitri_non_letti": [],
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

    per_giorno: dict[str, list[dict]] = defaultdict(list)
    frammenti: dict[int, sg.Formazione | None] = {}

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
        description="Formazioni previste (sportsgambler) e arbitro (football-data)"
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
