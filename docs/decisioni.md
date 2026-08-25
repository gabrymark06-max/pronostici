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

## Deciso: Eredivisie e Primeira Liga hanno le quote di mercato (2026-08-25)

Erano marcate `odds_key = None` in `competitions.py`, con il commento «solo
modello per sempre». La decisione risaliva a quando the-odds-api non le
copriva; il suo catalogo oggi le dà entrambe attive — verificato chiamando
`/v4/sports`, che non consuma crediti.

Entrano fra le **secondarie** insieme a Brasileirão e Championship: sono le
prime a cedere quando la quota stringe, perché una copertura arrivata per
ultima non deve togliere il prezzo a chi ce l'aveva già.

Il tetto crediti sale da 250 a 400 su 500. Due campionati in più sono circa un
quarto di richieste in più, e a 250 sarebbero entrati a spese di qualcun altro.
Il tetto sta ora in `config.py` e in nessun workflow: `quote` e `finalize`
contano sullo stesso file e ne dichiaravano due diversi — 450 e 250 — così che
appena il primo superava 250 il secondo si spegneva da solo credendo la quota
finita.

**Misurato dopo:** Eredivisie 6 partite su 9, Primeira Liga 7 su 7. Prima
nessuna delle due aveva un solo prezzo di mercato.


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

---

## Le formazioni cambiano fonte (24 agosto 2026)

**Decisione: sportsgambler.com al posto di Sofascore, e il job torna su
`ubuntu-latest`.**

Il 23 agosto Sofascore ha messo davanti alla sua API un token (`X-Captcha`) che
nasce solo dentro un browser vero e vale solo per l'IP che l'ha ottenuto. Sui
runner di GitHub non viene emesso — provato: Chrome parte davvero sotto
`xvfb-run` e la pagina non riceve niente in 45 secondi.

Per un giorno la risposta è stata un runner self-hosted in casa. Funzionava, ma
riportava il progetto dentro la dipendenza da cui era uscito il 14 agosto: un
computer acceso a un'ora precisa, e formazioni perse per sempre quando non lo
era. Non è un compromesso accettabile per un dato che esiste solo prima del
fischio d'inizio.

**Le alternative considerate, e perché sono state scartate:**

| Strada | Perché no |
|---|---|
| Proxy residenziale davanti a Chrome | Funzionerebbe, ma costa ~2–5 $/mese e viola il vincolo #2 (zero euro) |
| VPS come runner | ~5 €/mese, e resta un IP da datacenter: probabilmente bloccato uguale |
| API-Football, piano gratuito | Le formazioni escono 20–40 minuti prima del fischio: troppo tardi perché il sito le mostri a chi lo apre la mattina |
| Sportmonks, piano gratuito | Ha le formazioni previste, ma solo Danimarca e Scozia. Il piano che copre i nostri campionati costa 29 €/mese |

**La strada scelta non costa niente e copre di più.** Sportsgambler pubblica le
formazioni previste fino a due settimane prima, contro le 56 ore di mediana di
Sofascore: la finestra del job è passata da 4 a 7 giorni. L'arbitro arriva da
football-data.org, che lo manda già nel campo `referees` della chiamata che
facciamo per il calendario — nessuna chiave nuova.

**Cosa si perde, scritto qui perché non lo si scopra da un buco:** la panchina,
le medie cartellini dell'arbitro e i mercati estesi. Questi ultimi solo in
apparenza: `odds.yml` è la fonte principale delle quote e non è mai passata di
lì.

**Il campo `sofascore` non si riempie più**, ma i file già scritti non si
migrano. Quei dati li ha letti Sofascore davvero e contengono cose che le fonti
nuove non pubblicano: riscriverli sotto un'altra insegna sarebbe l'unico modo
di perderli. Il nuovo va in `contorno`, con la fonte dichiarata dentro ogni
sezione, e il frontend legge le due epoche da `lib/contorno.ts`.

`job-sofascore.yml` resta senza cron, per chi vuole il contorno ricco a mano
sul runner di casa.

---

## Deciso: un prezzo di un operatore solo, dove non c'è una mediana (25 agosto 2026)

**Il problema.** Il sito prometteva «un pronostico per partita, con il prezzo
dove l'abbiamo trovato», e su 62 partite in cartellone il prezzo c'era 14 volte.
Non per un guasto: il modello sceglie il mercato in cui si discosta di più dal
mercato, e quello quasi mai è uno dei sei che le due fonti coprivano. 24 volte
era un *gol di squadra*, 7 un *handicap europeo* — due famiglie che **nessun
comparatore gratuito espone**. Betexplorer serve sei mercati e basta (verificato
sulle sue linguette: 1X2, handicap asiatico, doppia chance, draw no bet,
entrambe segnano, gol totali); The Odds API le ha solo sull'endpoint per evento,
che costa un credito a partita e porterebbe il consumo a tre volte il tetto
mensile.

**Le due strade.** O si restringe il consigliato ai mercati che sappiamo
quotare — cioè si cambia il modello per far tornare i conti alla pagina — o si
trova chi quota quelli che il modello sceglie. La prima cambierebbe il 75% dei
consigli e ciò su cui il progetto si è fatto misurare, per un motivo che non è
statistico. Scartata.

**La scelta.** Kambi — la piattaforma dietro Unibet — pubblica quelle due
famiglie in JSON, senza chiave, su tutti e nove i campionati. I consigli con un
prezzo passano da 14 a 52 su 62.

**Il prezzo di questa scelta, ed è reale.** Non è un comparatore: è **un
operatore solo**. Il numero è il suo, non il consenso del mercato, ed è una
quota più debole di una mediana. Il progetto lo accetta a due condizioni, che
sono nel codice e non nelle intenzioni:

1. **Dove esiste una mediana, vince la mediana.** `jobs.contorno._unisci` mette
   questi mercati in fondo alla lista, e il primo che nomina una chiave se la
   tiene. Kambi non sostituisce mai un prezzo che qualcun altro ha calcolato su
   venti libri.
2. **La pagina lo dice.** `prezzi` porta la `fonte` accanto al numero, e la
   scheda scrive «un operatore europeo» invece di «N operatori». La tavola dei
   mercati aggiunge una riga quando almeno un prezzo poggia su uno solo.

**Resta scoperto** ciò che nessuno espone: le *combo*. Lì la pagina continua a
mostrare la probabilità e a tacere sulla quota, che è il vero stato delle cose.
