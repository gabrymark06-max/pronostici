# CENTRO

**<https://gabrymark06-max.github.io/pronostici/>**

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
riferimento       quote sgonfiate col metodo power dove il mercato determina
                  l'evento — alias inclusi — frequenza storica dove non lo
                  determina
      ↓
shrinkage         α = 1/(1 + σ²/τ²)  ·  media a posteriori verso il riferimento
      ↓
punteggio         S = p·ln(p/b) + (1−p)·ln((1−p)/(1−b)),  zero se p ≤ b
      ↓
filtri            p ≥ 0,50   ·   σ ≤ 0,12   ·   S ≥ 0,008 nats
      ↓
clustering        correlazione calcolata esatta dalla matrice congiunta;
                  si sceglie il cluster con punteggio massimo, e dentro il
                  cluster la probabilità più alta
```

Due proprietà che valgono più di quanto sembri:

**Il punteggio è direzionale.** La divergenza KL è positiva in entrambe le direzioni: usarla nuda consiglierebbe eventi che riteniamo *meno* probabili del riferimento. Kelly dice "non scommettere" quando `p ≤ q`, e il punteggio vale zero.

**Il vincolo "se è difficile che esca, non lo consigliamo" non è una soglia.** È dentro la matematica: a parità di vantaggio del 10%, il punteggio cade di 124 volte passando da p = 0,75 a p = 0,02. E i pronostici banali si escludono da soli — "Over 0.5 al 97%" contro un base rate del 96,5% vale 0,0004 nats, sotto ogni soglia.

**Lo stesso evento ha un solo riferimento.** "Asiatico casa −0.5" e "Vittoria casa" sono lo stesso identico evento, e quando ci sono le quote devono essere confrontati con la stessa probabilità di mercato. Confrontarne uno col mercato e l'altro col base rate storico farebbe scegliere all'argmax il riferimento più comodo: vantaggio fabbricato da un cambio di nome.

Tutti i mercati derivano dalla **stessa** matrice di probabilità congiunta dei gol, quindi sono coerenti fra loro per costruzione.

---

## Mercati

**114 mercati per partita**, tutti derivati dalla stessa matrice:

1X2 · doppia chance · over/under (ogni linea) · Goal/NoGoal · handicap · multigol · gol casa/ospite · risultato esatto · over/under primo tempo e HT/FT.

E cinque famiglie di **combo**: esito + Over/Under · doppia chance + Over/Under · esito + Goal/NoGoal · doppia chance + Goal/NoGoal · Goal/NoGoal + Over/Under.

Marcatori, cartellini, corner e tiri **non** sono coperti: le fonti gratuite non espongono i dati per giocatore e per evento necessari, e preferiamo non stimarli male.

### Over/Under si consiglia, ma con un avviso (12 agosto 2026)

Il backtest ha misurato che sui **gol totali** il modello non batte la
frequenza storica del campionato. Su richiesta del proprietario over/under è
tornato consigliabile — ma ogni pronostico di quella famiglia porta accanto,
in lista e sulla scheda, l'avviso che su quel mercato non abbiamo dimostrato un
vantaggio. Nella pratica non vince quasi mai: su 192 pronostici rigenerati,
zero.

### L'handicap asiatico è stato tolto (12 agosto 2026)

Non per una ragione statistica: perché il pubblico non lo legge. Un numero
corretto scritto in una forma che chi lo riceve non capisce non è un
pronostico. Le linee binarie asiatiche erano comunque **equivalenti** a mercati
che restano — «Asiatico casa -0.5» è la vittoria casa — quindi non si è perso
nulla se non una formulazione. L'handicap **europeo** resta: è la lingua delle
schedine italiane.

### Over/under si calcola, ma non si consiglia

Il backtest ha misurato che sui **gol totali** il modello non batte la semplice
frequenza storica del campionato: su Over 2.5 il log loss è 0,69922 contro
0,68855. L'indagine su sette configurazioni dichiarate ha escluso emivita,
correzione di Dixon-Coles e troncamento della matrice.

Sugli stessi dati, invece, **1X2 batte il tasso storico in tutti e sette i
bracci** con uno scarto stabile di −0,035 nats. Il modello ha risoluzione su
*chi vince*, non su *quanti gol si segnano*: è una proprietà del modello, non
un difetto di taratura.

Quindi la famiglia over/under resta calcolata, resta mostrata sulla scheda e
resta confrontata con le quote, ma **non può essere il pronostico
consigliato**. Undici mercati di cui ci fidiamo, non dodici con uno marcio.

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
│                 odds_parse.py (consenso fra bookmaker + de-vig power)
├── model/        dixon_coles · matrix · markets · devig · blend
│                 bootstrap · baserates · selection
├── jobs/         ingest · retrain · score · finalize · settle
│                 backtest · bench_fit
├── matching.py   appaia le partite di football-data con gli eventi delle quote
├── fixtures.py   i file giornalieri, con le regole di merge
├── ledger.py     registro append-only dei pronostici
└── pipeline.py

data/
├── archive/          ogni partita mai ingerita (la finestra dell'API è scorrevole:
│                     senza archivio, lo storico si accorcerebbe da solo)
├── leagues/          parametri e draw bootstrap per campionato
├── fixtures/         un file per giorno — il contratto col frontend
├── ledger/           i pronostici, append-only
├── accuracy.json     dichiarato contro realizzato, dal solo registro dal vivo
├── backtest.json     la prova storica, tenuta separata e etichettata
└── odds_budget.json  crediti quote consumati nel mese, con il tetto
```

Lo schema completo di `data/` è il contratto col frontend ed è descritto in
[docs/schema.md](docs/schema.md).

### Le due verità della stessa partita

Da T−7g a T−36h il pronostico viene dal solo modello (`w = 1,0`). A T−36h
arrivano le quote e il pronostico viene **rivisto una volta sola**, con
`w = 0,35`. Le due versioni sono **due righe permanenti** del registro, non un
aggiornamento: se il consiglio è cambiato, la scheda lo dice.

```
transition            cosa mostra la scheda
──────────────────────────────────────────────────────────────────────
confirmed             "Le quote confermano quello che dicevamo."
changed               "Fino a ieri dicevamo X. Ora diciamo Y."
prediction_to_silence "Ritiriamo il pronostico: non abbiamo un vantaggio."
silence_to_prediction "Prima non avevamo niente da dire. Ora sì."
```

Al fischio d'inizio tutto è congelato. `settle` scrive solo l'esito, e solo
sui campi che sono ancora vuoti.

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

### Accendere il sito

```bash
python scripts/sito.py
```

Poi si apre **http://localhost:3000**. CTRL+C nella stessa finestra spegne tutto.

Il sito è fatto di due pezzi: le pagine (Next.js, porta 3000) e il servizio dei
profili (FastAPI, porta 8000, il suo ambiente è in `backend/.venv`). Accenderne
uno solo **non dà errore** — le pagine si vedono lo stesso, e il guasto salta
fuori più tardi al momento di entrare. `scripts/sito.py` li accende insieme
proprio per questo; se muore uno, spegne anche l'altro.

Le due porte del sito in locale — `3000` per `npm run dev` e `4321` per
`npm run start` sull'export statico — sono le sole origini che il backend
accetta (`ORIGINI` in `backend/.env`). Su una porta diversa il browser blocca
l'accesso prima ancora di arrivare all'API.

### I job

```bash
python -m pronostici.jobs.ingest                       # scarica e archivia
python -m pronostici.jobs.retrain                      # fit + 300 bootstrap
python -m pronostici.jobs.score --days 7               # pronostici preliminari
python -m pronostici.jobs.finalize --window-hours 36   # quote → definitivi
python -m pronostici.jobs.settle                       # esiti e accuratezza
python -m pronostici.jobs.backtest                     # walk-forward
python -m pronostici.jobs.bench_fit                    # cronometra il fit
pytest                                                 # i test
```

Ogni job è idempotente: rieseguirlo non duplica righe e non cambia il passato.

`finalize` spende crediti, quindi ha due protezioni oltre al tetto: usa la
risposta su disco se è recente (`--max-age-s`), e `--dry-run` calcola tutto
senza scrivere. In sviluppo si lavora sulla cache e non si spende niente.

### In produzione

I job girano su GitHub Actions e committano il risultato: è il registro
pubblico, ed è il meccanismo che rende verificabile l'onestà del prodotto.

| Workflow | Quando (UTC) | Dove | Cosa |
|---|---|---|---|
| `daily.yml` | 03:00 | GitHub | `ingest` → `settle` → `retrain` → `score`, in sequenza |
| `odds.yml` | 10:00 e 18:00 | GitHub | `quote` alle 10:00, poi `finalize` a entrambe |
| `job-sofascore.yml` | 07:00 e 17:00 | **runner di casa** | formazioni, arbitro, quote estese |
| `tests.yml` | a ogni push | GitHub | ruff + pytest su Python 3.11 e 3.12 |
| `frontend.yml` | push su `frontend/`, `data/` | GitHub | token, tipi, lint, build, e la pubblicazione |

Ogni job è anche eseguibile a mano (`workflow_dispatch`). Le pipeline che
scrivono in `data/` **non condividono lo stesso gruppo di concorrenza**: un
workflow che ne chiama un altro tenendo il gruppo che il chiamato richiede si
aspetta da solo e non parte mai. Ognuno ha il suo, e il push riprova con
rebase.

Ogni job legge la **punta del ramo**, non il commit che ha innescato la run:
senza, in una catena ciascuno leggerebbe `data/` com'era prima che il
precedente scrivesse.

### Perché le formazioni non vengono più da Sofascore

Dal 23 agosto 2026 l'API di Sofascore vuole un token (`X-Captcha`) che si
ottiene solo dentro un browser vero, ed è **legato all'IP**. Sui runner di
GitHub non viene emesso: provato, Chrome parte davvero sotto `xvfb-run` e la
pagina non riceve nessun token entro 45 secondi. Per un giorno il job è girato
su un runner di casa — e il progetto era tornato a dipendere da un computer
acceso, la dipendenza da cui era uscito il 14 agosto.

Il 24 agosto è stato sostituito da due fonti che non hanno lucchetti:

| | Fonte | Come |
|---|---|---|
| formazioni previste | sportsgambler.com | HTML pubblico, nessuna chiave |
| arbitro | football-data.org | la chiave che già usiamo |

**Misurato da un runner di GitHub**, tutti e nove i campionati: 245 partite in
cartellone, modulo e undici titolari per ognuna. Nello stesso giro Sofascore
rispondeva 403 come controllo.

**Ci si guadagna** copertura: le previsioni arrivano fino a due settimane
prima invece delle 56 ore di mediana di Sofascore, quindi la finestra è passata
da 4 giorni a 7. La prima partita scritta è stata letta 104 ore prima del
fischio.

**Ci si perde** la panchina, le medie cartellini dell'arbitro e le quote
estese. Le quote non mancano davvero — `odds.yml` è la fonte principale e non è
mai passata di lì. Il resto si perde, e vale il cambio: un contorno più magro
che arriva sempre batte un contorno ricco che arriva solo a computer acceso.

`job-sofascore.yml` resta, senza orario, per chi vuole il contorno ricco a mano
sul runner di casa. I dati già scritti da Sofascore non si migrano: sono veri,
e contengono cose che le fonti nuove non pubblicano. Il frontend legge i due
campi tramite `lib/contorno.ts`, mai direttamente.

I segreti stanno nei GitHub Actions Secrets: `FOOTBALL_DATA_API_KEY` e
`ODDS_API_KEY`. Nient'altro — quelli dell'hosting sono facoltativi, vedi sotto.

### Pubblicare il sito

Il sito si ripubblica da solo dopo ogni pipeline dati riuscita. Dove finisce
dipende da cosa è collegato, e non c'è niente da scegliere a mano:

| Segreti presenti | Chi pubblica |
|---|---|
| nessuno | GitHub Pages, su `<utente>.github.io/pronostici/` |
| `VERCEL_*` + `SITO` | Vercel, e Pages si fa da parte da solo |

Per collegare Vercel serve un token da
[vercel.com/account/tokens](https://vercel.com/account/tokens). Il resto —
creare il progetto, leggere i due identificatori, scriverli fra i segreti — lo
fa lo script, che è innocuo da rilanciare:

```bash
py scripts/collega-vercel.py
gh workflow run frontend.yml
```

**`SITO` non è decorativo.** È l'indirizzo che finisce in `sitemap.xml` e
`robots.txt`: senza, `lib/sito.ts` ripiega sul segnaposto e il sito dichiara ai
motori di ricerca 351 URL su un dominio che non esiste. Per questo il job
fallisce rosso se i segreti di Vercel ci sono e la variabile no — mentre resta
verde quando non c'è nessun hosting, che non è un guasto. Con un dominio
proprio, `gh variable set SITO --body "https://tuo-dominio.it"`.

Il build che finisce online è **lo stesso** che ha appena passato i controlli:
si carica `frontend/out/` già costruito, e il progetto Vercel non ha nessun
preset di framework apposta, perché non ricostruisca con impostazioni sue.

---

## Prestazioni

Misurate, non stimate — vedi `data/benchmark_fit.json`.

| | |
|---|---|
| Un fit Dixon-Coles (760 partite, 47 parametri) | 0,0116 s |
| Fit + 300 bootstrap, un campionato | 3,3 – 13,2 s |
| Retrain di tutte e 10 le competizioni, due stagioni ciascuna | 72 s |
| Scoring di una giornata (25 partite, 10 campionati) | 1,0 s |
| `finalize` su un campionato, quote incluse | 1,2 s |

Il gradiente è analitico: senza, ogni passo dell'ottimizzatore costerebbe 48 valutazioni della verosimiglianza invece di una.

---

## Onestà

- Le probabilità mostrate sono sempre quelle **dopo shrinkage**, mai le stime grezze.
- L'accuratezza storica è sempre riportata **per fascia di probabilità**, mai aggregata: un dato aggregato nasconde che gli 85% sono facili e i 55% no.
- Il backtest, finché ci sarà, è etichettato come backtest e **mai** sommato ai pronostici dal vivo. Un backtest non è un track record: è la stessa persona che decide le regole e conta i punti.
- Con due stagioni di storico, P(Over 2.5) ha una banda di circa ±10 punti. Uno scarto di 5 punti dal mercato è rumore, e il prodotto non lo spaccia per segnale.
- **I risultati sfavorevoli restano pubblicati.** Che il modello non batta il tasso storico sui gol totali è scritto qui sopra, in `data/backtest.json` e nel protocollo, non nascosto in fondo a un file.
- **Il registro non si azzera per convenienza.** È stato azzerato una volta sola, l'8 agosto, quando nessuna partita si era ancora conclusa e nessuno aveva visto quelle righe. Da quando ci sono esiti reali, un cambio di parametro si **data** in [docs/registro-parametri.md](docs/registro-parametri.md) e le righe precedenti restano dove sono.

---

## Documentazione

| File | Contenuto |
|---|---|
| [docs/decisioni.md](docs/decisioni.md) | Scope, vincoli, cosa è escluso e perché |
| [docs/brief.md](docs/brief.md) | Architettura, quota, silenzio, avvio a freddo |
| [docs/schema.md](docs/schema.md) | Lo schema di `data/`: il contratto col frontend |
| [docs/protocollo-backtest.md](docs/protocollo-backtest.md) | Le regole del backtest, scritte **prima** di guardarne i risultati |
| [docs/registro-parametri.md](docs/registro-parametri.md) | Ogni cambio di parametro, con la data e le righe che lo precedono |
| [docs/research/selezione-pronostico.md](docs/research/selezione-pronostico.md) | Il metodo statistico, con le fonti |
| [docs/research/fonti-dati.md](docs/research/fonti-dati.md) | Cosa danno davvero le fonti gratuite |
| [docs/competitors.md](docs/competitors.md) | Come fanno gli altri, e cosa sbagliano |
| [docs/qa.md](docs/qa.md) | Le misure di qualità del sito, e l'unico numero che non si può chiudere prima del deploy |

---

## Gioco responsabile

Questo progetto pubblica stime statistiche, non consigli di scommessa. Nessuna previsione garantisce un risultato. Se il gioco smette di essere un passatempo: [Numero Verde Nazionale 800 558 822](https://www.iss.it/gioco-d-azzardo).
