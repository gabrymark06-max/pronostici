# Pronostici

Pronostici calcistici gratuiti sui principali campionati europei. Per ogni partita **un solo pronostico consigliato**, scelto con un criterio dichiarato, spiegato, e accompagnato da quanto spesso pronostici simili si sono avverati.

Quando il modello non ha niente di non ovvio da dire, **lo dice**.

---

## Perché esiste

I siti di pronostici hanno tutti lo stesso problema: danno un consiglio su ogni partita, non dichiarano mai con che criterio l'hanno scelto, e non mostrano quanto ci hanno preso davvero.

Qui:

- **Il criterio è scritto.** Il punteggio di un pronostico è la divergenza KL fra la nostra probabilità e un riferimento — che coincide esattamente con il tasso di crescita log-ottimale di Kelly. Non è un'euristica scelta a mano.
- **Il registro è pubblico e append-only.** Ogni pronostico è un commit datato in questo repository. Non possiamo riscrivere il passato: la cronologia di Git lo impedisce.
- **A volte tace.** Se nessun mercato supera i filtri, la risposta è "questa partita non ci dice niente più della media". Un consiglio su ogni partita sarebbe più facile da monetizzare e meno onesto.
- **Non guadagniamo se scommetti.** Nessuna pubblicità, nessun link affiliato a bookmaker, nessun piano a pagamento, nessun account.

---

## Come sceglie il pronostico

```
matrice dei gol   Dixon-Coles con decadimento esponenziale (emivita 365 giorni)
      ↓
incertezza        300 draw bootstrap dei parametri, per campionato
      ↓
riferimento       quote sgonfiate col metodo power dove esistono,
                  frequenza storica del campionato dove non esistono
      ↓
shrinkage         α = 1/(1 + σ²/τ²)  ·  media a posteriori verso il riferimento
      ↓
punteggio         S = p·ln(p/b) + (1−p)·ln((1−p)/(1−b)),  zero se p ≤ b
      ↓
filtri            p ≥ 0,50   ·   σ ≤ 0,12   ·   S ≥ 0,005 nats
      ↓
clustering        correlazione calcolata esatta dalla matrice congiunta;
                  si sceglie il cluster con punteggio massimo, e dentro il
                  cluster la probabilità più alta
```

Due proprietà che valgono più di quanto sembri:

**Il punteggio è direzionale.** La divergenza KL è positiva in entrambe le direzioni: usarla nuda consiglierebbe eventi che riteniamo *meno* probabili del riferimento. Kelly dice "non scommettere" quando `p ≤ q`, e il punteggio vale zero.

**Il vincolo "se è difficile che esca, non lo consigliamo" non è una soglia.** È dentro la matematica: a parità di vantaggio del 10%, il punteggio cade di 124 volte passando da p = 0,75 a p = 0,02. E i pronostici banali si escludono da soli — "Over 0.5 al 97%" contro un base rate del 96,5% vale 0,0004 nats, sotto ogni soglia.

Tutti i mercati derivano dalla **stessa** matrice di probabilità congiunta dei gol, quindi sono coerenti fra loro per costruzione.

---

## Mercati

1X2 · doppia chance · over/under (ogni linea) · BTTS · handicap europeo e asiatico · multigol · combo · risultato esatto · gol casa/ospite · over/under primo tempo e HT/FT.

Marcatori, cartellini, corner e tiri **non** sono coperti: le fonti gratuite non espongono i dati per giocatore e per evento necessari, e preferiamo non stimarli male.

---

## Architettura

Non c'è un server. Il calcolo gira in job pianificati che scrivono file versionati in questo repository; il sito li legge come file statici.

Tre conseguenze, tutte volute:

- **Impossibile esaurire la quota delle quote per colpa del traffico** — il sito non ha un runtime da cui chiamare l'API.
- **Impossibile riscrivere il passato in silenzio** — il registro è append-only e ogni riga ha il suo commit datato.
- **Impossibile che il traffico costi.**

```
src/pronostici/
├── sources/      football_data.py · odds_api.py (con governo della quota)
├── model/        dixon_coles · matrix · markets · devig · blend
│                 bootstrap · baserates · selection
├── jobs/         ingest · retrain · score · bench_fit
├── ledger.py     registro append-only dei pronostici
└── pipeline.py

data/
├── archive/      ogni partita mai ingerita (la finestra dell'API è scorrevole:
│                 senza archivio, lo storico si accorcerebbe da solo)
├── leagues/      parametri e draw bootstrap per campionato
├── fixtures/     un file per giorno — il contratto col frontend
└── ledger/       i pronostici, append-only
```

---

## Avvio locale

Serve Python 3.11+.

```bash
git clone https://github.com/GabrieleMarchesini2006/pronostici.git
cd pronostici
pip install -e ".[dev]"

cp .env.example .env      # poi riempi le due chiavi
```

Le chiavi sono **gratuite**:

| Variabile | Dove si ottiene |
|---|---|
| `FOOTBALL_DATA_API_KEY` | [football-data.org/client/register](https://www.football-data.org/client/register) |
| `ODDS_API_KEY` | [the-odds-api.com](https://the-odds-api.com/#get-access) — 500 crediti/mese |

Senza `ODDS_API_KEY` il sistema funziona lo stesso: degrada a "solo modello" e ogni scheda lo dichiara.

### I job

```bash
python -m pronostici.jobs.ingest                       # scarica e archivia
python -m pronostici.jobs.retrain --competitions SA    # fit + 300 bootstrap
python -m pronostici.jobs.score --days 7               # pronostici preliminari
python -m pronostici.jobs.bench_fit                    # cronometra il fit
pytest                                                 # i test
```

Ogni job è idempotente: rieseguirlo non duplica righe e non cambia il passato.

---

## Prestazioni

Misurate, non stimate — vedi `data/benchmark_fit.json`.

| | |
|---|---|
| Un fit Dixon-Coles (760 partite, 47 parametri) | 0,0116 s |
| Fit + 300 bootstrap, un campionato | 3,8 s |
| Tutte e 10 le competizioni | 38 s |

Il gradiente è analitico: senza, ogni passo dell'ottimizzatore costerebbe 48 valutazioni della verosimiglianza invece di una.

---

## Onestà

- Le probabilità mostrate sono sempre quelle **dopo shrinkage**, mai le stime grezze.
- L'accuratezza storica è sempre riportata **per fascia di probabilità**, mai aggregata: un dato aggregato nasconde che gli 85% sono facili e i 55% no.
- Il backtest, finché ci sarà, è etichettato come backtest e **mai** sommato ai pronostici dal vivo. Un backtest non è un track record: è la stessa persona che decide le regole e conta i punti.
- Con due stagioni di storico, P(Over 2.5) ha una banda di circa ±10 punti. Uno scarto di 5 punti dal mercato è rumore, e il prodotto non lo spaccia per segnale.

---

## Documentazione

| File | Contenuto |
|---|---|
| [docs/decisioni.md](docs/decisioni.md) | Scope, vincoli, cosa è escluso e perché |
| [docs/brief.md](docs/brief.md) | Architettura, quota, silenzio, avvio a freddo |
| [docs/research/selezione-pronostico.md](docs/research/selezione-pronostico.md) | Il metodo statistico, con le fonti |
| [docs/research/fonti-dati.md](docs/research/fonti-dati.md) | Cosa danno davvero le fonti gratuite |
| [docs/competitors.md](docs/competitors.md) | Come fanno gli altri, e cosa sbagliano |

---

## Gioco responsabile

Questo progetto pubblica stime statistiche, non consigli di scommessa. Nessuna previsione garantisce un risultato. Se il gioco smette di essere un passatempo: [Numero Verde Nazionale 800 558 822](https://www.iss.it/gioco-d-azzardo).
