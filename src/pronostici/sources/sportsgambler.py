"""Formazioni previste da sportsgambler.com, per HTTP semplice.

PERCHE' ESISTE. Dal 23 agosto 2026 Sofascore emette il token che autorizza la
sua API solo dentro un browser vero e solo per IP residenziali: sui runner di
GitHub la pagina non ne riceve nessuno, misurato. Il job delle formazioni era
finito su un runner di casa, e il progetto aveva ricominciato a dipendere da un
computer acceso — la cosa da cui era scappato in agosto.

Questa fonte non ha nessun lucchetto: HTML servito a chiunque, nessuna chiave,
nessun browser. Misurato dai runner di GitHub il 24 agosto 2026, tutti e nove i
campionati: 245 partite in elenco e un frammento con modulo e undici titolari
per ognuna.

COSA DA' IN PIU' DI SOFASCORE. Le previsioni arrivano fino a due settimane
prima, contro le 56 ore di mediana di Sofascore.

COSA DA' IN MENO. Niente panchina, niente arbitro, niente quote estese. La
panchina si perde e basta; l'arbitro arriva da football-data.org, che lo
manda gia' oggi nel campo `referees` della stessa chiamata che facciamo per il
calendario.

COME E' FATTO IL SITO. Due passi, e il secondo non e' facoltativo:

    /lineups/football/<lega>/          l'elenco, con id e nomi squadra
    /lineups/lineups-load2.php?id=N    il frammento con i giocatori

La pagina di elenco NON contiene i giocatori: li carica dopo in AJAX. Chi si
fermasse al primo passo troverebbe 200 e zero formazioni.
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher

from ..matching import canonical

log = logging.getLogger(__name__)

BASE = "https://www.sportsgambler.com"

# Un `User-Agent` di un browser vero. Non e' un travestimento: e' il valore che
# un sito si aspetta, e il default di `urllib` («Python-urllib/3.12») e' quello
# che fa scattare i filtri piu' grossolani senza che nessuno abbia deciso
# niente su di noi.
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)

# I NOSTRI codici competizione verso le loro pagine. Le chiavi sono quelle di
# football-data.org, che e' la fonte del calendario: se una competizione non e'
# qui, semplicemente non prende le formazioni — non e' un errore.
LEGHE: dict[str, str] = {
    "PL": "england-premier-league",
    "ELC": "england-championship",
    "SA": "italy-serie-a",
    "PD": "spain-la-liga",
    "BL1": "germany-bundesliga",
    "FL1": "france-ligue-1",
    "DED": "netherlands-eredivisie",
    "PPL": "portugal-primeira-liga",
    "BSA": "brazil-serie-a",
}

# Soglia di somiglianza fra i nostri nomi e i loro. La stessa che usa il
# modulo di Sofascore, per la stessa ragione: sotto questo valore due club
# diversi si somigliano abbastanza da passare.
SOGLIA = 0.72

# Alias validi SOLO verso sportsgambler, che accorcia i nomi in modo che
# nessuna somiglianza puo' colmare. Regola come in `matching.py`: un alias
# accorcia o sostituisce, non allunga. Chiavi e valori gia' normalizzati.
# Alias validi SOLO verso sportsgambler. Chiave: come lo scrivono loro, gia'
# normalizzato. Valore: come lo scriviamo noi, idem.
#
# Qui stanno i casi che il contenimento non puo' risolvere per costruzione,
# e sono di due tipi soli:
#
#   · abbreviazioni che non sono prefissi — "utd" non comincia "united",
#     "qpr" non e' contenuto in "queens park rangers";
#   · nomi LORO piu' lunghi dei nostri — "NEC Nijmegen" contro il nostro
#     "NEC": il verso si inverte e il contenimento fallisce dalla parte
#     sbagliata.
#
# Ogni riga qui e' un abbinamento che e' stato visto mancare su dati veri, non
# un'ipotesi: la lista si allunga misurando, non immaginando.
ALIAS: dict[str, str] = {
    "nott m forest": "nottingham forest",
    "go ahead e": "go ahead eagles",
    "sp rotterdam": "sparta rotterdam",
    "nec nijmegen": "nec",
    "bayern munich": "bayern munchen",
    "sheffield utd": "sheffield united",
    "b m gladbach": "borussia monchengladbach",
    "athletico pr": "paranaense",
    "qpr": "queens park rangers",
}

MESI = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


class SportsgamblerNonRaggiungibile(RuntimeError):
    """Il sito non ha risposto. Le partite restano senza formazione."""


@dataclass
class PartitaSG:
    """Una riga dell'elenco: quanto basta per agganciarla a una nostra partita."""

    id: int
    giorno: date
    casa: str
    ospiti: str
    confermate: bool


@dataclass
class Lato:
    modulo: str | None = None
    titolari: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Formazione:
    casa: Lato
    ospiti: Lato
    confermate: bool


def _chiave(nome: str) -> str:
    base = canonical(nome)
    return ALIAS.get(base, base)


# Quanto due parole devono somigliarsi per contare come la stessa. Alta
# apposta: sotto, "united" e "unidos" passerebbero.
RATIO_PAROLA = 0.85
# Sotto le tre lettere un prefisso non dice niente: "in" sta in "inter" e in
# "internacional", che sono due club di due continenti diversi.
PREFISSO_MINIMO = 3


def _parola_simile(nostra: str, loro: str) -> bool:
    if nostra == loro:
        return True
    corta, lunga = sorted((nostra, loro), key=len)
    if len(corta) >= PREFISSO_MINIMO and lunga.startswith(corta):
        return True
    return SequenceMatcher(None, nostra, loro).ratio() >= RATIO_PAROLA


def somiglianza(nostro: str, loro: str) -> float:
    """Quanta parte del LORO nome si ritrova nel nostro. Asimmetrica apposta.

    I due siti scrivono gli stessi club a lunghezze diverse, e sempre nello
    stesso verso: noi prendiamo il nome ufficiale da football-data.org
    ("Borussia Dortmund", "Olympique Lyonnais", "Stade Brestois 29"), loro
    scrivono come si dice allo stadio ("Dortmund", "Lyon", "Brest").

    Con una somiglianza simmetrica — quella di `matching.py`, che confronta
    due nomi alla pari — le parole che loro non scrivono contano come
    differenze, e un abbinamento giusto scende sotto soglia. Misurato sul
    cartellone del 24 agosto 2026: 49 partite agganciate su 174, e i
    candidati scartati erano quasi tutti quelli giusti.

    Qui si chiede solo che ogni parola del loro nome si ritrovi nel nostro.
    "Dortmund" dentro "Borussia Dortmund" vale 1; "Man City" contro
    "Manchester United" vale 0,5, perche' "city" non c'e' da nessuna parte —
    ed e' quello che tiene separati i due club della stessa citta'.

    Il vero argine ai falsi positivi non e' comunque questa soglia: e'
    `aggancia`, che pretende la conferma su ENTRAMBE le squadre e sulla data.
    """
    a, b = _chiave(nostro), _chiave(loro)
    if a == b:
        return 1.0
    nostre = a.split()
    loro_parole = b.split()
    if not nostre or not loro_parole:
        return 0.0
    trovate = sum(1 for w in loro_parole if any(_parola_simile(n, w) for n in nostre))
    return trovate / len(loro_parole)


def _scarica(percorso: str, referer: str = "") -> str:
    testate = {"User-Agent": UA, "Accept": "*/*"}
    if referer:
        # Il frammento e' pensato per essere chiesto dalla sua pagina: queste
        # due testate sono quelle che manderebbe il browser, e ometterle
        # significa chiedere a un sito di comportarsi in un modo che non ha
        # mai previsto.
        testate["Referer"] = referer
        testate["X-Requested-With"] = "XMLHttpRequest"
    richiesta = urllib.request.Request(f"{BASE}{percorso}", headers=testate)
    try:
        with urllib.request.urlopen(richiesta, timeout=30) as risposta:
            return risposta.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        raise SportsgamblerNonRaggiungibile(f"{percorso}: {e}") from e


def _senza_tag(frammento: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", frammento)).strip()


def _giocatori(frammento: str) -> list[dict[str, str]]:
    """Numero di maglia e nome, nell'ordine in cui il sito li dispone in campo.

    L'ordine e' informazione: la prima riga e' il portiere, l'ultima gli
    attaccanti. Non si riordina.
    """
    trovati: list[dict[str, str]] = []
    for maglia, nome in re.findall(
        r'class="player-profile"[^>]*>([^<]*)<.*?class="player-name"[^>]*>([^<]*)<',
        frammento,
        re.S,
    ):
        pulito = _senza_tag(nome)
        if pulito:
            trovati.append({"nome": pulito, "maglia": maglia.strip()})
    return trovati


def _anno_probabile(giorno: int, mese: int, oggi: date) -> int:
    """L'anno che il sito non scrive.

    Le intestazioni dicono «Monday 24 August» e basta. Per quasi tutto l'anno
    dedurlo e' ovvio, ma a cavallo di capodanno «03 January» in una pagina
    aperta il 28 dicembre e' l'anno dopo, e prenderlo per quello in corso
    sposterebbe la partita indietro di dodici mesi: l'aggancio fallirebbe in
    silenzio, e proprio nella settimana in cui si gioca di piu'.

    Si sceglie l'anno che mette la data piu' vicina a oggi.
    """
    candidati = []
    for anno in (oggi.year - 1, oggi.year, oggi.year + 1):
        try:
            candidati.append(date(anno, mese, giorno))
        except ValueError:
            # 29 febbraio in un anno non bisestile.
            continue
    return min(candidati, key=lambda d: abs((d - oggi).days)).year


def elenco(
    codice: str, *, oggi: date | None = None, html: str | None = None
) -> list[PartitaSG]:
    """Le partite in cartellone per una competizione, con il loro id.

    `html` esiste per i test: il parsing e' la parte che si rompe quando il
    sito cambia, ed e' l'unica che ha senso provare su una pagina salvata.
    """
    lega = LEGHE.get(codice)
    if lega is None:
        return []
    if html is None:
        html = _scarica(f"/lineups/football/{lega}/")
    return _leggi_elenco(html, oggi or date.today())


def _leggi_elenco(html: str, oggi: date) -> list[PartitaSG]:
    partite: list[PartitaSG] = []
    giorno_corrente: date | None = None

    # Un'unica scansione in ordine di documento: le intestazioni di data e le
    # righe partita sono fratelli, e una riga appartiene all'ultima
    # intestazione vista sopra di se'. Cercarle separatamente perderebbe
    # proprio questo legame.
    schema = re.compile(
        r'class="date-headline"[^>]*>(?P<data>[^<]+)<'
        r'|class="fxs-team home"[^>]*>(?P<casa>[^<]*)<'
        r'|class="fxs-team"[^>]*>(?P<ospiti>[^<]*)<'
        r'|onClick="reply_click\((?P<id>\d+)\)"'
        r"|>(?P<stato>Confirmed|Predicted) Lineups<"
    )
    casa = ospiti = None
    identificativo = None

    for m in schema.finditer(html):
        if m.group("data"):
            testo = m.group("data").strip()
            trovato = re.search(r"(\d{1,2})\s+([A-Za-z]+)", testo)
            if trovato:
                g = int(trovato.group(1))
                mese = MESI.get(trovato.group(2).lower())
                if mese:
                    giorno_corrente = date(_anno_probabile(g, mese, oggi), mese, g)
        elif m.group("casa") is not None:
            casa = m.group("casa").strip()
        elif m.group("ospiti") is not None:
            ospiti = m.group("ospiti").strip()
        elif m.group("id"):
            identificativo = int(m.group("id"))
        elif m.group("stato"):
            if giorno_corrente and casa and ospiti and identificativo:
                partite.append(
                    PartitaSG(
                        id=identificativo,
                        giorno=giorno_corrente,
                        casa=casa,
                        ospiti=ospiti,
                        confermate=m.group("stato") == "Confirmed",
                    )
                )
            casa = ospiti = None
            identificativo = None
    return partite


def aggancia(
    partite: list[PartitaSG],
    casa: str,
    ospiti: str,
    quando: datetime,
    *,
    tolleranza_giorni: int = 3,
) -> PartitaSG | None:
    """La loro partita che corrisponde alla nostra, o `None`.

    SERVE LA CONFERMA SU ENTRAMBE LE SQUADRE, come per Sofascore: un aggancio
    su una sola sceglie fra due partite delle stesse due squadre a sei mesi di
    distanza, o peggio, appaia il derby sbagliato.

    LA TOLLERANZA SULLA DATA E' DI TRE GIORNI, e non e' generosita'. Un giorno
    servirebbe gia' solo per i fusi — una partita brasiliana delle 22:00 locali
    e' del giorno dopo in UTC — ma i due calendari a volte non concordano
    davvero: Remo-Coritiba risulta al 29 agosto da noi e al 1o settembre da
    loro. Uno dei due e' vecchio, ed e' una partita rinviata, non una partita
    diversa.

    Allargare non apre la porta ai falsi positivi perche' il vincolo vero e'
    un altro: si pretende la conferma su ENTRAMBE le squadre e nel verso
    giusto. Le stesse due squadre, casa e ospiti nello stesso ordine, a tre
    giorni di distanza, in un girone di andata e ritorno non esistono.

    A parita' di punteggio vince la data piu' vicina alla nostra.
    """
    nostro_giorno = quando.date()
    migliore: tuple[float, int, PartitaSG] | None = None

    for p in partite:
        distanza = abs((p.giorno - nostro_giorno).days)
        if distanza > tolleranza_giorni:
            continue
        s_casa = somiglianza(casa, p.casa)
        s_ospiti = somiglianza(ospiti, p.ospiti)
        if s_casa < SOGLIA or s_ospiti < SOGLIA:
            continue
        candidato = (s_casa + s_ospiti, -distanza, p)
        if migliore is None or candidato[:2] > migliore[:2]:
            migliore = candidato

    return migliore[2] if migliore else None


def formazione(match_id: int, lega: str, *, html: str | None = None) -> Formazione | None:
    """Modulo e undici titolari per lato, o `None` se il frammento e' vuoto.

    Il frammento esiste anche per partite senza formazione pubblicata: torna
    200 con la pubblicita' e nient'altro. Distinguerlo da un guasto conta —
    il primo e' normale, il secondo va detto.
    """
    if html is None:
        html = _scarica(
            f"/lineups/lineups-load2.php?id={match_id}",
            referer=f"{BASE}/lineups/football/{lega}/",
        )
    return _leggi_formazione(html)


def _leggi_formazione(html: str) -> Formazione | None:
    moduli = re.findall(r'class="lineups-toggle-formation"[^>]*>([^<]+)<', html)
    confermate = "Confirmed Lineup" in html

    # I DUE LATI SI SEPARANO CON UN TAGLIO, non con una regex che cerca la
    # fine del primo. La fine del blocco di casa non e' marcata da niente: e'
    # semplicemente dove comincia quello ospite, e i `</div>` annidati non si
    # contano con un'espressione regolare. Tagliare all'inizio del secondo e'
    # l'unica lettura che non dipende da quanti livelli ha il markup.
    inizio_casa = html.find('class="lineups-home')
    inizio_ospiti = html.find('class="lineups-away')
    if inizio_casa == -1 or inizio_ospiti <= inizio_casa:
        return None

    lati = [
        Lato(titolari=_giocatori(html[inizio_casa:inizio_ospiti])),
        Lato(titolari=_giocatori(html[inizio_ospiti:])),
    ]

    for i, lato in enumerate(lati):
        if i < len(moduli):
            lato.modulo = moduli[i].strip()

    if not lati[0].titolari or not lati[1].titolari:
        return None
    return Formazione(casa=lati[0], ospiti=lati[1], confermate=confermate)


def ore_prima(quando: datetime, adesso: datetime) -> float | None:
    """Quante ore prima del fischio stiamo leggendo.

    E' il campo che distingue una previsione a dieci giorni da una probabile
    di un'ora prima: `confermate` vale `false` in entrambi i casi, ma le due
    cose non hanno la stessa affidabilita' e la pagina lo deve poter dire.
    """
    delta: timedelta = quando - adesso
    ore = delta.total_seconds() / 3600
    return round(ore, 1) if ore > 0 else None
