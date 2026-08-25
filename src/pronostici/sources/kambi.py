"""Fonte — kambi: i mercati che NESSUN comparatore gratuito pubblica.

PERCHE' UNA TERZA FONTE. Le prime due coprono sei mercati fra tutte e due:
esito finale e gol totali da the-odds-api, doppia chance, gol totali su ogni
linea ed entrambe segnano da betexplorer. Il pronostico consigliato quasi mai
e' uno di quelli. Misurato il 25 agosto 2026 sulle 52 partite in cartellone
nei cinque giorni successivi:

    gol di squadra      24 consigli     0 con un prezzo
    doppia chance       11              6
    handicap europeo     7              0
    esito finale         6              6
    combo doppia chance  2              0
    entrambe segnano     2              1

Tredici su cinquantadue. Le due famiglie che mancavano — **gol di squadra** e
**handicap europeo** — pesano trentuno consigli da sole, e nessuno dei due
comparatori le espone: betexplorer serve sei mercati e basta (1X2, handicap
asiatico, doppia chance, pareggio rimborsato, entrambe segnano, gol totali),
verificato leggendo le sue stesse linguette; the-odds-api le ha ma solo
sull'endpoint per evento, che costa un credito a partita e manderebbe il
budget mensile a tre volte il tetto.

UN OPERATORE SOLO, E VA DETTO. Questa e' la piattaforma di un bookmaker, non
un comparatore: il numero e' il suo prezzo, non il consenso del mercato. E'
una quota piu' debole di una mediana e una piu' forte del niente, e il dato la
dichiara per quello che e' — `n_bookmaker` vale 1, e la pagina scrive «un
operatore europeo» invece di «N operatori». Dove una mediana esiste, vince lei:
`jobs.contorno` mette questi mercati in fondo e il primo che nomina una chiave
se la tiene.

NESSUNA CHIAVE, NESSUN LUCCHETTO. E' l'API che alimenta il loro stesso sito:
JSON pubblico su CDN, nessuna autenticazione, nessun limite dichiarato. Un giro
intero sono nove richieste di elenco piu' una quarantina di richieste di quote
a due partite per volta — circa un minuto, contro i venticinque di betexplorer.

COSA SI LEGGE QUI. Sette mercati su seicento che Kambi pubblica per partita.
Due sono la ragione per cui questa fonte esiste — gol di squadra e handicap
europeo, che nessun comparatore gratuito espone. Gli altri cinque viaggiano
nella stessa risposta e quindi costano zero richieste in piu': si leggono
perche' su una partita che le mediane non hanno agganciato sono l'unico prezzo
che ci sia. Tutto il resto — cartellini, angoli, marcatori, primo tempo — non
si tocca.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

from ..matching import canonical, contenimento
from ..model.devig import DevigError, devig_power

log = logging.getLogger(__name__)

BASE = "https://eu-offering-api.kambicdn.com/offering/v2018/ub"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)

# I NOSTRI codici competizione verso i loro percorsi, letti da `group.json` e
# non indovinati. Un percorso sbagliato qui risponde 404, che e' rumoroso — al
# contrario di betexplorer, dove diventava una lega muta per undici giorni.
LEGHE: dict[str, str] = {
    "PL": "football/england/premier_league",
    "ELC": "football/england/the_championship",
    "SA": "football/italy/serie_a",
    "PD": "football/spain/la_liga",
    "BL1": "football/germany/bundesliga",
    "FL1": "football/france/ligue_1",
    "DED": "football/netherlands/eredivisie",
    "PPL": "football/portugal/primeira_liga",
    "BSA": "football/brazil/brasileirao_serie_a",
}

# I NOMI NOSTRI DEI MERCATI. Stanno in costanti e non in letterali sparsi
# perche' li leggono in tre: il parsing qui, la traduzione in chiave nostra in
# `jobs.contorno`, e la tavola dei nomi del frontend — che ha una regola dura,
# «quello che non so tradurre non si mostra», e senza queste righe scarterebbe
# tutto in silenzio.
#
# I QUATTRO CHE HANNO GIA' UN NOME LO TENGONO, carattere per carattere: sono
# gli stessi mercati che pubblica betexplorer, e due nomi diversi per la stessa
# scommessa vorrebbero dire due righe nella tavola con due prezzi vicini —
# esattamente il doppione che il progetto ha appena finito di togliere.
MERCATO_HANDICAP = "Handicap europeo"
MERCATO_GOL_CASA = "Gol di squadra casa"
MERCATO_GOL_OSPITE = "Gol di squadra ospite"
MERCATO_ESITO = "Esito finale"
MERCATO_DOPPIA = "Doppia chance"
MERCATO_ENTRAMBE = "Entrambe segnano"
MERCATO_GOL_TOTALI = "Gol totali"

# Che linea porta ogni mercato: nessuna, intera, o a mezzo gol.
SENZA_LINEA = "senza"
LINEA_INTERA = "intera"
LINEA_DECIMALE = "decimale"

# I tipi di esito sono stabili e in inglese anche quando l'etichetta e'
# tradotta nella lingua del mercato: si legge questo, mai `label`.
TIPI_TRE_VIE = {"OT_ONE": "1", "OT_CROSS": "X", "OT_TWO": "2"}
TIPI_DUE_VIE = {"OT_OVER": "Over", "OT_UNDER": "Under"}
TIPI_DOPPIA = {"OT_ONE_OR_CROSS": "1X", "OT_ONE_OR_TWO": "12", "OT_CROSS_OR_TWO": "X2"}
TIPI_ENTRAMBE = {"OT_YES": "Sì", "OT_NO": "No"}

# L'ULTIMO NUMERO E' QUANTI ESITI SI AVVERANO, come in betexplorer, e non e' un
# dettaglio: sgonfiare vuol dire dividere per la somma delle inverse, e quella
# somma tende a 1 solo se gli esiti sono una PARTIZIONE. La doppia chance non
# lo e' — «1X», «12» e «X2» coprono ogni risultato due volte — e trattandola
# come le altre uscirebbe un margine del 113%.
MERCATI: dict[str, tuple[str, tuple[str, ...], int]] = {
    MERCATO_HANDICAP: (MERCATO_HANDICAP, ("1", "X", "2"), 1),
    MERCATO_GOL_CASA: (MERCATO_GOL_CASA, ("Over", "Under"), 1),
    MERCATO_GOL_OSPITE: (MERCATO_GOL_OSPITE, ("Over", "Under"), 1),
    MERCATO_ESITO: (MERCATO_ESITO, ("1", "X", "2"), 1),
    MERCATO_DOPPIA: (MERCATO_DOPPIA, ("1X", "12", "X2"), 2),
    MERCATO_ENTRAMBE: (MERCATO_ENTRAMBE, ("Sì", "No"), 1),
    MERCATO_GOL_TOTALI: (MERCATO_GOL_TOTALI, ("Over", "Under"), 1),
}

# Come li chiama Kambi, verso il nostro nome, i tipi di esito e la forma della
# linea. «Total Goals by <squadra>» non e' qui perche' porta il nome della
# squadra dentro l'etichetta: lo riconosce `_famiglia` confrontando quel nome
# con le due squadre dell'evento.
ETICHETTE: dict[str, tuple[str, dict[str, str], str]] = {
    "3-Way Handicap": (MERCATO_HANDICAP, TIPI_TRE_VIE, LINEA_INTERA),
    "Full Time": (MERCATO_ESITO, TIPI_TRE_VIE, SENZA_LINEA),
    "Double Chance": (MERCATO_DOPPIA, TIPI_DOPPIA, SENZA_LINEA),
    "Both Teams To Score": (MERCATO_ENTRAMBE, TIPI_ENTRAMBE, SENZA_LINEA),
    "Total Goals": (MERCATO_GOL_TOTALI, TIPI_DUE_VIE, LINEA_DECIMALE),
}

PREFISSO_GOL_SQUADRA = "Total Goals by "

# Lo stato di un esito che il libro ha chiuso. Sta in inglese come i tipi.
SOSPESO = "SUSPENDED"

# Quote e linee arrivano in millesimi: 2800 e' 2,80 e -1500 e' -1,5.
MILLE = 1000

# DUE, E IL NUMERO NON E' PRUDENZA: E' UN TETTO MISURATO.
#
# La risposta si ferma a duemila offerte e TRONCA IN SILENZIO. Misurato il 25
# agosto 2026 sulle stesse cinque partite di LaLiga, chiedendone n per volta:
#
#     1 partita   ->  642 offerte
#     2           -> 1348
#     3           -> 1974
#     4           -> 2000, e la quarta ne riceve 63 invece di 626
#     5           -> 2000, e la quinta non compare affatto
#
# Non c'e' nessun campo che lo dica. La risposta e' 200, il JSON e' valido, e
# le partite in fondo al gruppo escono con qualche mercato o con nessuno —
# esattamente la forma di guasto che questo progetto insegue da settimane.
# Con cinque per richiesta, una partita su ventuno restava senza prezzi.
#
# Due stanno larghe sotto il tetto (1348 sul caso peggiore visto), e chi legge
# controlla comunque: `CAP_OFFERTE` fa da guardia, e una risposta che lo tocca
# viene buttata e richiesta una partita per volta.
PARTITE_PER_RICHIESTA = 2
CAP_OFFERTE = 2000

# Fra una richiesta e l'altra. Il CDN non dichiara nessun limite e non ne ha
# imposto uno nelle prove, ma un giro intero sono venti richieste contro un
# servizio che non ci ha chiesto niente e non ci fa pagare niente.
PAUSA_S = 0.5

SOGLIA_NOME = 0.72

# IN BRASILE IL NOME PORTA LO STATO: «Vasco da Gama-RJ», «Palmeiras-SP».
#
# Non e' parte del nome del club, e' la disambiguazione fra omonime di stati
# diversi — e per il confronto e' una parola in piu' che nel nostro nome non
# c'e' mai. Su venti squadre di Serie A brasiliana ne agganciava zero: ognuna
# si fermava a 0,50, cioe' meta' delle loro parole ritrovate.
#
# Venti righe di alias sarebbero venti occasioni di sbagliarne una. Meglio
# togliere il suffisso, che e' la regola vera. La forma e' stretta apposta —
# trattino e due maiuscole in fondo, niente altro — e su tutti i nomi delle
# nove leghe non colpisce nient'altro: verificato scorrendo i loro cartelloni.
_STATO_BRASILIANO = re.compile(r"-[A-Z]{2}$")

# Alias verso Kambi: chiave come lo scrivono loro DOPO `canonical`, valore come
# lo scriviamo noi. Vale la stessa regola di betexplorer — ogni riga e' stata
# VISTA mancare confrontando i due vocabolari di squadre di una lega, mai
# dedotta dalla partita non agganciata, dove il «miglior candidato» e' spesso
# un'altra partita e ne escono coppie come «Bahia -> Gremio».
#
# Attenzione: `canonical` applica gia' i suoi alias, e due di questi esistono
# per DISFARE quello che fa lui. «Athletic Bilbao» diventa «athletic club», che
# somiglia meno al nostro «Athletic Club» di quanto somigliasse prima.
ALIAS: dict[str, str] = {
    # Loro scrivono la citta', noi no (o viceversa).
    "nec nijmegen": "nec",
    "psv eindhoven": "psv",
    "excelsior rotterdam": "excelsior",
    "nacional madeira": "nacional",
    "maritimo funchal": "maritimo",
    "vitoria guimaraes": "vitoria",
    "sporting cp": "sporting portugal",
    # Le iniziali puntate diventano tre parole, e due non si ritrovano.
    "s c braga": "braga",
    # Nomi in un'altra lingua.
    "bayern munich": "bayern munchen",
    # Rimesso com'era prima dell'alias di `canonical`.
    "athletic club": "athletic",
    # Brasile: tolto lo stato restano due omonime che si distinguono per il
    # nome della societa', e nessuna delle due forme si ritrova nell'altra.
    "atletico mineiro": "mineiro",
    "athletico paranaense": "paranaense",
}


class KambiNonRaggiungibile(RuntimeError):
    """Il servizio non ha risposto. La partita resta senza questi mercati."""


class LegaVuota(RuntimeError):
    """La lega risponde ma non ha nessun evento con le quote aperte.

    Non e' un guasto di per se': fuori stagione, o in pausa nazionali, e'
    esattamente cio' che deve succedere. Chi chiama lo riporta invece di
    trattarlo come un errore.
    """


@dataclass
class EventoKB:
    """Un evento del loro cartellone: l'id serve a chiedere le quote."""

    id: int
    casa: str
    ospiti: str
    inizio: datetime | None = None


def _chiave(nome: str) -> str:
    base = canonical(_STATO_BRASILIANO.sub("", nome.strip()))
    return ALIAS.get(base, base)


def somiglianza(nostro: str, loro: str) -> float:
    return contenimento(_chiave(nostro), _chiave(loro))


def _scarica(percorso: str) -> dict:
    url = f"{BASE}/{percorso}?lang=en_GB&market=GB"
    testate = {"User-Agent": UA, "Accept": "application/json"}
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=testate), timeout=30
        ) as risposta:
            corpo = risposta.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        raise KambiNonRaggiungibile(f"{percorso}: {e}") from e
    time.sleep(PAUSA_S)
    try:
        return json.loads(corpo)
    except ValueError as e:
        raise KambiNonRaggiungibile(f"{percorso}: risposta non JSON ({e})") from e


def _quando(grezzo: object) -> datetime | None:
    if not isinstance(grezzo, str) or not grezzo:
        return None
    try:
        return datetime.fromisoformat(grezzo.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def elenco(codice: str, *, dati: dict | None = None) -> list[EventoKB]:
    """Gli eventi di una competizione con le quote aperte.

    L'elenco NON e' la stagione intera come su betexplorer: sono le partite su
    cui il libro e' aperto, tipicamente due giornate. E' abbastanza per la
    finestra del contorno, e vuol dire che una lega vuota qui non e' il segnale
    di guasto che e' la'.
    """
    percorso = LEGHE.get(codice)
    if percorso is None:
        return []
    if dati is None:
        dati = _scarica(f"listView/{percorso}.json")

    eventi: list[EventoKB] = []
    for voce in dati.get("events") or []:
        e = voce.get("event") or {}
        casa, ospiti = e.get("homeName"), e.get("awayName")
        if not isinstance(e.get("id"), int) or not casa or not ospiti:
            continue
        eventi.append(
            EventoKB(id=e["id"], casa=casa, ospiti=ospiti, inizio=_quando(e.get("start")))
        )
    if not eventi:
        raise LegaVuota(f"{codice} ({percorso}): nessun evento con le quote aperte")
    return eventi


def aggancia(
    eventi: list[EventoKB], casa: str, ospiti: str, quando: datetime | None = None
) -> EventoKB | None:
    """Il loro evento che corrisponde alla nostra partita, o `None`.

    Come betexplorer si pretende la conferma su ENTRAMBE le squadre, che e' il
    vero argine ai falsi positivi: il confronto fra un nome ufficiale lungo e
    uno da stadio e' asimmetrico apposta, e da solo dice che «Paris
    Saint-Germain FC» somiglia sia a «PSG» sia a «Paris FC» — che in Ligue 1
    sono due club diversi, e giocano tutte e due.

    QUI PERO' C'E' ANCHE L'ORA, che betexplorer non pubblica nel suo elenco, e
    a parita' di nome decide lei. Non filtra: un calendario che diverge di un
    giorno fra due fonti e' normale, e pretendere la data farebbe mancare le
    partite rinviate — che sono esattamente quelle su cui la fonte serve. Ma
    fra due eventi che il nome non sa distinguere, quello che comincia
    all'ora giusta e' quello giusto.
    """
    migliore: tuple[float, float, EventoKB] | None = None
    for e in eventi:
        s_casa = somiglianza(casa, e.casa)
        s_ospiti = somiglianza(ospiti, e.ospiti)
        if s_casa < SOGLIA_NOME or s_ospiti < SOGLIA_NOME:
            continue
        punteggio = s_casa + s_ospiti
        # Piu' piccolo e' meglio, e senza le due ore vale zero: un evento senza
        # orario non deve vincere ne' perdere per quello.
        distanza = (
            abs((e.inizio - quando).total_seconds())
            if quando is not None and e.inizio is not None
            else 0.0
        )
        candidato = (punteggio, -distanza, e)
        if migliore is None or candidato[:2] > migliore[:2]:
            migliore = candidato
    return migliore[2] if migliore else None


def _linea(grezza: object, forma: str) -> str | None:
    """La linea in millesimi verso la stringa che usiamo nelle chiavi.

    `LINEA_INTERA` per l'handicap, dove le nostre chiavi sono `eh_-2_away`: a
    tre esiti un handicap a mezzo gol non esiste, perche' il pareggio non
    potrebbe avverarsi, e se arriva la risposta non e' quella che crediamo.
    `LINEA_DECIMALE` per i gol, dove sono `hg_over_1.5` — e la formattazione
    deve coincidere con quella con cui `model.markets` costruisce la chiave, o
    il prezzo e' vero e non si ritrova mai.
    """
    if forma == SENZA_LINEA:
        return ""
    if isinstance(grezza, bool) or not isinstance(grezza, int | float):
        return None
    valore = float(grezza) / MILLE
    if forma == LINEA_INTERA:
        return str(int(valore)) if valore == int(valore) else None
    return str(valore)


def _famiglia(offerta: dict, evento: EventoKB) -> tuple[str, dict[str, str], str] | None:
    """Che mercato e' questa offerta: nome nostro, tipi di esito, forma linea.

    Torna `None` per tutto il resto — cartellini, angoli, marcatori, primo
    tempo, handicap asiatico — che e' la stragrande maggioranza delle seicento
    offerte per partita.
    """
    etichetta = ((offerta.get("criterion") or {}).get("englishLabel") or "").strip()
    noto = ETICHETTE.get(etichetta)
    if noto is not None:
        return noto
    if not etichetta.startswith(PREFISSO_GOL_SQUADRA):
        return None

    squadra = etichetta[len(PREFISSO_GOL_SQUADRA) :].strip()
    # QUALE DELLE DUE, deciso confrontando i nomi e mai l'ordine: le offerte
    # arrivano mescolate, e attribuire i gol della squadra sbagliata sarebbe un
    # prezzo vero sopra il mercato sbagliato — il guasto peggiore possibile
    # qui, perche' non ha nessun aspetto di guasto.
    verso_casa = somiglianza(evento.casa, squadra)
    verso_ospiti = somiglianza(evento.ospiti, squadra)
    if max(verso_casa, verso_ospiti) < SOGLIA_NOME or verso_casa == verso_ospiti:
        return None
    nome = MERCATO_GOL_CASA if verso_casa > verso_ospiti else MERCATO_GOL_OSPITE
    return nome, TIPI_DUE_VIE, LINEA_DECIMALE


def mercati(evento: EventoKB, offerte: list[dict]) -> list[dict]:
    """Le offerte di UN evento verso i nostri mercati.

    Il parsing sta separato dalla rete apposta: e' la parte che si rompe quando
    la fonte cambia, ed e' l'unica che ha senso provare su una risposta salvata.
    """
    per_mercato: dict[tuple[str, str], dict[str, float]] = {}

    for offerta in offerte:
        letto = _famiglia(offerta, evento)
        if letto is None:
            continue
        nome, tipi, forma = letto
        linea: str | None = None
        quote: dict[str, float] = {}
        for esito in offerta.get("outcomes") or []:
            colonna = tipi.get(esito.get("type") or "")
            quota = esito.get("odds")
            if colonna is None or isinstance(quota, bool):
                continue
            if esito.get("status") == SOSPESO or not isinstance(quota, int | float):
                # UN ESITO SOSPESO NON HA PREZZO, e lo dice in due modi: il
                # campo `odds` sparisce e `status` diventa `SUSPENDED`. Si
                # guardano tutti e due — il primo perche' e' quello che capita
                # davvero, il secondo perche' se un giorno mandassero un prezzo
                # vecchio accanto alla sospensione lo pubblicheremmo come
                # fresco. Capita sulle linee estreme: «Under 7,5» su
                # Real Madrid-Real Sociedad, visto il 25 agosto 2026.
                continue
            valore = float(quota) / MILLE
            if valore <= 1.0:
                continue
            if linea is None:
                linea = _linea(esito.get("line"), forma)
            quote[colonna] = valore

        _, colonne, _ = MERCATI[nome]
        if linea is None or len(quote) != len(colonne):
            # Un mercato a meta' non e' meta' mercato: senza tutti gli esiti il
            # margine non si puo' togliere, e senza margine tolto la
            # probabilita' non e' confrontabile con la nostra.
            continue
        if (nome, linea) in per_mercato:
            # Kambi ripete la stessa linea marcandola `MAIN_LINE`. La prima
            # basta: sono gli stessi prezzi.
            continue
        per_mercato[(nome, linea)] = quote

    fuori: list[dict] = []
    for (nome, linea), quote in sorted(per_mercato.items()):
        _, colonne, vincenti = MERCATI[nome]
        mercato = _mercato(nome, linea, colonne, [quote[c] for c in colonne], vincenti)
        if mercato is not None:
            fuori.append(mercato)
    return fuori


def _mercato(
    nome: str,
    linea: str,
    colonne: tuple[str, ...],
    quote: list[float],
    vincenti: int,
) -> dict | None:
    """Un mercato con le probabilita' gia' sgonfiate del margine.

    Stesso `devig_power` delle altre due fonti: cambiare metodo per fonte
    renderebbe i numeri non confrontabili proprio nella colonna che esiste per
    confrontarli.
    """
    try:
        esito = devig_power(quote, n_winners=vincenti)
    except DevigError as exc:
        log.warning("%s linea %s: quote scartate (%s)", nome, linea, exc)
        return None

    return {
        "fonte": "kambi",
        "mercato": nome,
        # `None` e non stringa vuota per i mercati senza linea: e' la forma che
        # usa betexplorer, e la tavola dei mercati unisce le due fonti sulla
        # coppia nome-linea. Due modi di scrivere «nessuna linea» sono due
        # righe dove ce n'e' una.
        "linea": linea or None,
        # UNO, e scritto. Non e' una mediana e il dato non deve poter essere
        # scambiato per una: la pagina legge questo numero per decidere se
        # dire «un operatore» o «N operatori».
        "n_bookmaker": 1,
        "bookmaker": ["unibet"],
        "esiti": [
            {
                "esito": colonna,
                "decimale": round(quota, 2),
                "probabilita_implicita": round(float(p), 4),
            }
            for colonna, quota, p in zip(colonne, quote, esito.probabilities, strict=True)
        ],
        "somma_probabilita": round(esito.overround, 4),
        "margine_percento": round((esito.overround / vincenti - 1.0) * 100, 2),
    }


def _offerte(gruppo: list[EventoKB]) -> dict[int, list[dict]] | None:
    """Le offerte grezze di un gruppo, o `None` se la risposta e' troncata.

    `None` non e' «vuoto»: e' «non ci si puo' fidare di questa risposta». Chi
    chiama riprova una partita per volta invece di pubblicare una scheda a
    meta' senza che niente lo dica.
    """
    ids = ",".join(str(e.id) for e in gruppo)
    try:
        dati = _scarica(f"betoffer/event/{ids}.json")
    except KambiNonRaggiungibile as exc:
        # Un gruppo che non risponde non ferma gli altri: quelle partite
        # restano senza questi mercati, che e' com'erano prima.
        log.warning("quote di %s non lette: %s", ids, exc)
        return {}

    tutte = dati.get("betOffers") or []
    if len(tutte) >= CAP_OFFERTE and len(gruppo) > 1:
        log.warning(
            "risposta troncata a %d offerte su %s: rifaccio una per una", len(tutte), ids
        )
        return None

    per_evento: dict[int, list[dict]] = {e.id: [] for e in gruppo}
    for offerta in tutte:
        id_evento = offerta.get("eventId")
        if id_evento in per_evento:
            per_evento[id_evento].append(offerta)
    return per_evento


def quote_di_gruppo(eventi: list[EventoKB]) -> dict[int, list[dict]]:
    """I mercati di piu' partite per richiesta, per id evento.

    Kambi accetta gli id separati da virgola sullo stesso percorso, ed e' la
    ragione per cui questa fonte gira in un minuto dove betexplorer ne prende
    venticinque. Quanti per volta lo decide `PARTITE_PER_RICHIESTA`, che sta
    sotto un tetto misurato e non scelto: vedi il commento la'.
    """
    fuori: dict[int, list[dict]] = {}
    per_id = {e.id: e for e in eventi}

    for i in range(0, len(eventi), PARTITE_PER_RICHIESTA):
        gruppo = eventi[i : i + PARTITE_PER_RICHIESTA]
        per_evento = _offerte(gruppo)
        if per_evento is None:
            per_evento = {}
            for solo in gruppo:
                per_evento.update(_offerte([solo]) or {})

        for id_evento, offerte in per_evento.items():
            evento = per_id.get(id_evento)
            if evento is not None and offerte:
                fuori[id_evento] = mercati(evento, offerte)
    return fuori
