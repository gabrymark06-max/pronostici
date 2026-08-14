"""Stime sui singoli giocatori — gol, assist, cartellini, falli, tiri in porta.

QUESTO MODULO PRODUCE NUMERI NON MISURATI, E VA DETTO PRIMA DI TUTTO IL RESTO.

Il resto del progetto pubblica solo cio' che e' passato da un backtest: 5.018
partite, una calibrazione dichiarata, un registro dal vivo. Queste stime no, e
per due ragioni che non dipendono dalla qualita' del codice:

  1. **Non esiste una quota di mercato** contro cui confrontarle. Sofascore
     pubblica diciassette mercati e nessuno riguarda il singolo giocatore. Il
     criterio con cui il sito sceglie un pronostico — lo scarto dal mercato —
     qui non e' calcolabile, perche' manca il mercato.
  2. **Non esiste uno storico** per il backtest. Servirebbero le statistiche
     partita per partita di ogni giocatore su una stagione intera; la fonte le
     espone una partita alla volta.

Finche' quelle due cose mancano, questi numeri vanno tenuti in una sezione a
se', dichiarata, fuori dal registro. Il modulo non lo impone — non e' compito
suo — ma chi lo usa deve saperlo.

IL MODELLO, IN UNA RIGA. Tasso per novanta minuti dalla stagione in corso,
riscalato sui minuti attesi, e una Poisson per la probabilita' di almeno uno.

    lambda = tasso_per_90 * (minuti_attesi / 90)
    P(almeno uno) = 1 - exp(-lambda)

E' la stessa famiglia di modello che il progetto usa gia' per i gol di squadra.
Non e' sofisticato ed e' apposta: con un campione di venti partite per giocatore
un modello piu' ricco stimerebbe rumore.

COSA NON FA:

* **non stima i giocatori in panchina.** Un subentrato puo' giocare novanta
  minuti o zero, e la probabilita' che entri non e' nei dati. Stimarlo
  significherebbe inventare i minuti attesi, che e' il termine che domina il
  risultato. Restano fuori.
* **non somma competizioni diverse.** Il tasso viene dalla competizione
  principale del giocatore. Sommare campionato e coppe darebbe un campione piu'
  grande e un tasso peggiore, perche' l'avversario medio e' diverso.
* **non tratta gol e assist come indipendenti quando li somma.** Vedi
  `gol_o_assist`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Minuti attesi per un titolare. Non 90: i titolari vengono sostituiti, e nei
# cinque campionati principali la media di chi parte titolare sta poco sotto i
# quattro quinti della partita. Usare 90 gonfierebbe ogni stima del 18%.
MINUTI_TITOLARE = 76.0

# Presenze sotto le quali il tasso e' rumore travestito da misura. Con meno di
# cinque partite un solo gol porta il tasso a 0,2 per 90, che e' il livello di
# un attaccante di prima fascia.
PRESENZE_MINIME = 5

# Media di cartellini gialli per squadra a partita, usata come riferimento per
# l'effetto arbitro. E' un ordine di grandezza dichiarato, non una misura fatta
# su questo archivio: serve solo a dire se un arbitro sta sopra o sotto la
# media, non a produrre un valore assoluto.
GIALLI_RIFERIMENTO = 2.0

# Quanto pesa l'arbitro. Il moltiplicatore grezzo viene contratto verso 1 in
# funzione di quante partite ha diretto: con dieci partite un arbitro puo'
# sembrare severissimo per caso. A n partite il peso e' n/(n+K).
K_ARBITRO = 20.0

# Tetto al moltiplicatore, in entrambe le direzioni. Nessun arbitro raddoppia
# davvero i cartellini: oltre questi limiti si sta modellando il campione, non
# l'arbitro.
MOLT_MIN, MOLT_MAX = 0.70, 1.40


@dataclass(frozen=True)
class Stima:
    """Una stima su un mercato di un giocatore."""

    mercato: str
    etichetta: str
    p: float
    lambda_: float
    base: str  # da quale tasso viene, in chiaro


def _p_almeno_uno(lam: float) -> float:
    if lam <= 0:
        return 0.0
    return 1.0 - math.exp(-lam)


def moltiplicatore_arbitro(
    gialli_per_partita: float | None, partite: int | None
) -> float:
    """Quanto l'arbitro alza o abbassa la probabilita' di cartellino.

    Contratto verso 1 con il campione, e con un tetto. Un arbitro a 2,7 gialli
    a partita su 10 partite non vale 1,35 volte la media: vale molto meno,
    perche' dieci partite non bastano a distinguerlo dal caso.
    """
    if not gialli_per_partita or not partite or partite <= 0:
        return 1.0
    grezzo = gialli_per_partita / GIALLI_RIFERIMENTO
    peso = partite / (partite + K_ARBITRO)
    contratto = 1.0 + (grezzo - 1.0) * peso
    return max(MOLT_MIN, min(MOLT_MAX, contratto))


def stime_giocatore(
    tassi: dict,
    *,
    minuti_attesi: float = MINUTI_TITOLARE,
    molt_cartellini: float = 1.0,
) -> list[Stima]:
    """Le stime per un giocatore, dai suoi tassi per 90 minuti.

    `tassi` e' la risposta del comando `statistiche` del CLI Sofascore.
    Restituisce una lista vuota quando il campione e' troppo sottile: meglio
    nessuna stima che una stima su tre partite.
    """
    presenze = int(tassi.get("presenze") or 0)
    if presenze < PRESENZE_MINIME:
        return []

    quota = minuti_attesi / 90.0
    fuori: list[Stima] = []

    def aggiungi(
        chiave: str, mercato: str, etichetta: str, molt: float = 1.0
    ) -> float | None:
        tasso = tassi.get(chiave)
        if tasso is None:
            return None
        lam = float(tasso) * quota * molt
        fuori.append(
            Stima(
                mercato=mercato,
                etichetta=etichetta,
                p=round(_p_almeno_uno(lam), 4),
                lambda_=round(lam, 4),
                base=(
                    f"{tasso} {chiave.replace('_per_90', '')} per 90', "
                    f"{presenze} presenze"
                ),
            )
        )
        return lam

    lam_gol = aggiungi("gol_per_90", "gol", "Segna almeno un gol")
    lam_ass = aggiungi("assist_per_90", "assist", "Almeno un assist")
    aggiungi("gialli_per_90", "cartellino", "Prende un cartellino", molt=molt_cartellini)
    aggiungi("falli_per_90", "fallo", "Commette almeno un fallo")
    aggiungi("tiri_in_porta_per_90", "tiro_in_porta", "Almeno un tiro in porta")

    # GOL O ASSIST. Le due Poisson si sommano — la somma di due Poisson e' una
    # Poisson di parametro somma — ma questo vale per eventi INDIPENDENTI, e
    # gol e assist dello stesso giocatore non lo sono del tutto: chi tira di
    # piu' assiste di meno, e un giocatore non assiste il proprio gol.
    # La somma sovrastima leggermente. La si tiene perche' l'errore e' piccolo
    # rispetto all'incertezza del tasso, e la si dichiara qui invece di
    # nasconderla.
    if lam_gol is not None and lam_ass is not None:
        lam = lam_gol + lam_ass
        fuori.append(
            Stima(
                mercato="gol_o_assist",
                etichetta="Gol o assist",
                p=round(_p_almeno_uno(lam), 4),
                lambda_=round(lam, 4),
                base="somma dei due tassi, trattati come indipendenti",
            )
        )

    return fuori
