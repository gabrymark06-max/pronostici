# Decisioni di progetto

Progetto: web app **gratuita** di pronostici calcistici. Club (top campionati) + nazionali.
Aggiornato: 2026-08-08.

---

## Decise dall'utente

| # | Decisione | Scelta |
|---|---|---|
| 1 | Base di partenza | **Da zero**, in `progetti/pronostici/`. Il progetto in `~/football-predictor` non viene riusato. |
| 2 | Costo | **Zero, sempre.** Nessun abbonamento a dati. |
| 3 | Scope mercati | **Solo gli 11 mercati sui gol**, da un'unica fonte stabile. Niente scraping per marcatori/cartellini/corner/tiri. |
| 4 | Quote | **Sì**, via the-odds-api piano gratuito. Il confronto col mercato rientra nello scope. |
| 5 | Prodotto | Per ogni partita, **UN pronostico consigliato**, scelto con criterio e **spiegato**. |

---

## Il vincolo di prodotto che guida tutto

Parole dell'utente: *"se è presente una value bet alta ma è veramente difficile che esca, non gli consigliamo quel pronostico"*.

Il consigliato non è il massimo vantaggio atteso. È il miglior compromesso fra **vantaggio**, **probabilità reale di uscire** e **affidabilità della stima**. E va mostrato con la sua fiducia e con l'accuratezza storica, non come una certezza.

---

## Fonti dati — stato verificato

Dettaglio completo in [research/fonti-dati.md](research/fonti-dati.md).

### football-data.org — ossatura ✅

API key gratuita attiva. Verificato il 2026-08-08.

- **Competizioni (piano gratuito):** Premier League, Serie A, La Liga, Bundesliga, Ligue 1, Eredivisie, Primeira Liga, Championship, Brasileirão, **Champions League**, **Mondiali**, **Europei**.
- **Per partita:** risultato finale **e primo tempo**, squadre con **logo** (`crest`), arbitro, stadio, giornata.
- **Storico:** solo le **ultime 2 stagioni** (~760 partite per campionato). Sufficiente per Dixon-Coles con decadimento temporale.
- **Assenti:** statistiche partita, eventi gol, cartellini, formazioni.

### the-odds-api — quote ✅ (key da registrare)

- **500 crediti/mese** sul piano gratuito.
- **Costo di una chiamata = n. mercati × n. regioni.** Una chiamata restituisce tutte le partite imminenti di quel campionato.
- Copre EPL, Championship, Bundesliga, Serie A, La Liga, Ligue 1, Champions League, Europa League, Brasileirão.
- Mercati utili: `h2h` (1X2), `totals` (over/under), `spreads` (handicap).

> **Vincolo architetturale duro:** con 500 crediti/mese le quote **non possono essere richieste a ogni visita**. Vanno prese da un **job pianificato**, solo per le partite nelle prossime ~48 ore e solo per i campionati che giocano davvero, e messe in cache. Una chiamata per utente esaurirebbe la quota in un giorno.
>
> Effetto collaterale positivo: questa stessa disciplina è ciò che tiene l'app gratuita da gestire.

---

## I mercati in scope

Tutti derivati dalla **stessa matrice di probabilità congiunta dei gol**, quindi mutuamente coerenti per costruzione.

1. 1X2
2. Doppia chance
3. Over/Under (tutte le linee)
4. BTTS
5. Handicap europeo
6. Handicap asiatico
7. Multigol
8. Combo (es. 1 + Over 2.5)
9. Risultato esatto
10. Gol casa / gol ospite
11. Over/Under primo tempo e HT/FT

Il confronto con le quote è possibile su 1X2, over/under e handicap. Sugli altri la raccomandazione si basa sulla sola confidenza calibrata del modello — e va detto all'utente quando è così.

---

## Fuori scope, con motivo

| Escluso | Perché |
|---|---|
| Marcatori | Nessun evento gol nel payload gratuito |
| Cartellini | Nessun `bookings` |
| Corner, tiri | Nessun `statistics` |
| Europa League, Nations League, qualificazioni | Fuori dal piano gratuito di football-data.org |
| ESPN come fonte | **Verificato: HTTP 403** su tutti gli endpoint, anche con User-Agent da browser |

---

## Metodo di selezione — deciso ✅

Ricerca completa in [research/selezione-pronostico.md](research/selezione-pronostico.md).

**Criterio:** divergenza KL fra la probabilità del modello (dopo shrinkage) e un riferimento — quote sgonfiate col **metodo power** dove esistono, **base rate storico** dove non esistono.

`S = p̃·ln(p̃/b) + (1−p̃)·ln((1−p̃)/(1−b))`

Non è un'euristica: coincide con il tasso di crescita log-ottimale di Kelly. **Il vincolo di prodotto è già dentro la matematica** — a parità di vantaggio del 10% lo score cade di 124 volte da p=0,75 a p=0,02, e i pronostici banali (Over 0.5) vengono scartati da soli.

Conseguenze vincolanti per il build:

- **Shrinkage obbligatorio** verso il base rate: `α = 1/(1+σ²/τ²)`. Senza, l'argmax su 11 mercati sovrastima di ~1,5σ (maledizione dell'ottimizzatore, Smith & Winkler 2006).
- **Clustering per correlazione** calcolata *esatta* dalla matrice congiunta, non stimata. Si sceglie il cluster con score massimo, poi **dentro il cluster il membro con probabilità più alta** — è qui che il vincolo dell'utente morde di più.
- **Peso al modello w = 0,35** quando ci sono le quote (il mercato batte i modelli), 1,0 quando non ci sono.
- **De-vig col metodo power**, mai normalizzazione ingenua: quella fabbrica vantaggio finto sui longshot.
- **Stato "nessun pronostico"** quando nessun candidato passa i filtri. Da progettare come funzionalità, non come errore.
- **Mai mostrare** "value bet", "edge", ROI, o importi da puntare. Mai una probabilità non shrinkata.
- **Risultato esatto e HT/FT non vinceranno quasi mai** il ranking: conseguenza accettata consapevolmente.

---

## Da fare

- [x] L'utente registra una API key gratuita su the-odds-api.com
- [x] Metodo di selezione del pronostico consigliato (ricerca)
- [x] Teardown competitor — [competitors.md](competitors.md)
- [x] Scope v1 e architettura — [brief.md](brief.md) §10 e §11
- [x] Design system e direzione visiva — `design-system/`
- [x] Build — motore, sito e registro pubblico in esercizio
- [x] **Pubblicare il sito** — <https://gabrymark06-max.github.io/pronostici/>,
      su GitHub Pages. Non sostituisce Vercel (§11.2 del brief): il job Pages si
      fa da parte da solo nel momento in cui `VERCEL_TOKEN` esiste. Nel
      frattempo il registro e' raggiungibile, che era il punto.
- [ ] **Sciogliere la contraddizione sui profili** (vedi qui sotto).


---

## Aperta: i profili contraddicono il brief

**Stato: da decidere.** Registrata il 2026-08-24.

Il brief, §10, mette nella lista **Mai**:

> - Login, account, profilazione.
> - Piano a pagamento.

E §11.1 rifiuta lo stack con server proprio con questa motivazione: *«non c'e'
niente da servire dinamicamente. Nessuna scrittura utente, nessuna
autenticazione, nessuna personalizzazione.»*

Ma `backend/centro_profili` esiste ed e' finito: registrazione, accesso,
sessioni, verifica dell'indirizzo, recupero della password, 62 prove. E il sito
ha sei pagine che gli parlano.

**Non c'e' nessuna decisione scritta che ribalti quel «Mai».** Questo file, che
e' il registro delle scelte, non nomina «account» da nessun'altra parte.

Perche' conta piu' di una svista di documentazione: il prodotto chiede fiducia
mostrando il proprio registro. Un progetto che tiene un registro delle decisioni
e poi ne prende una grossa fuori dal registro si contraddice nel punto esatto in
cui la fiducia si gioca.

Le due uscite sono simmetriche, e vanno prese consapevolmente:

- **Si tengono i profili.** Allora qui va scritto perche', cosa cambia del
  vincolo #2 (zero euro, sempre — un server con Postgres non e' gratis) e cosa
  significa per la riga «Mai: piano a pagamento», visto che gli account di
  solito la precedono.
- **Si tolgono dal percorso di pubblicazione.** Il codice resta dov'e' e non si
  butta; il sito si pubblica come export statico senza profili, che e' cio' che
  §11.2 descrive. Si riaccendono il giorno in cui la prima uscita viene scelta
  e scritta.

Finche' resta aperta, il sito si costruisce con i profili spenti: e' il
comportamento predefinito, ed e' verificato da `check-profili-spenti.mjs`.
