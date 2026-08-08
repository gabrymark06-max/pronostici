# Brief di decisione — v1

Autore: brainstormer (reasoning partner). Data: **2026-08-08**.
Input letti: [decisioni.md](decisioni.md), [competitors.md](competitors.md), [research/selezione-pronostico.md](research/selezione-pronostico.md), [research/fonti-dati.md](research/fonti-dati.md).

Scope mercati e fonti sono **decisi** e non rimessi in discussione. Qui si decide **come si costruisce** e **cosa entra in v1**.

Notazione: **[V]** = verificato nei documenti letti o calcolato da me da numeri verificati. **[A]** = assunzione mia, dichiarata. **[R]** = va verificato da `ricercatore` prima di dipenderci.

---

## 1. Obiettivo

Un utente apre il sito, vede le partite di oggi, e in dieci secondi capisce **cosa gli consigliamo su una partita, perché, e quanto spesso consigli come questo si sono avverati** — senza registrarsi, senza pubblicità, senza che nessuno guadagni se lui scommette.

Il prodotto non è "pronostici". Il prodotto è **un giudizio con la sua ricevuta**. Il pronostico è il pretesto; la ricevuta è il differenziatore.

---

## 2. Utenti e flusso centrale

**Chi.** Uno solo, in v1: l'appassionato italiano che sta per guardare o giocare una partita e vuole un parere motivato in pochi secondi. Non l'analista (job saturo: FootyStats, Understat), non il professionista (non gli bastiamo e non dobbiamo provarci).

**Flusso, in ordine, senza deviazioni:**

1. Apre la home → **le partite di oggi**, già lì, nessun login, nessun onboarding (convenzione portante, competitors §4).
2. Scorre le righe-partita: logo, casa, ora, trasferta, e **una riga di anteprima del consiglio** o l'indicazione che su quella partita taciamo.
3. Tocca la partita che gli interessa → **la scheda**: un pronostico, la probabilità con la sua definizione operativa, la banda di incertezza, il record storico della sua fascia, 2–3 ragioni.
4. *(momento di valore raggiunto qui)*
5. Se vuole verificare: link testuale "Come stiamo andando" → curva/hit rate con numerosità e periodo, e il confronto fra quanto dicevamo di sapere e quanto sapevamo davvero.
6. Se torna il giorno dopo: vede se il pronostico di ieri è uscito, e — quando è cambiato — che cosa dicevamo prima e perché abbiamo cambiato idea.

Il passo 5 non è opzionale nel design: è il passo che converte "l'ennesimo sito di tip" in "questi si misurano". Ma **è al passo 5, non al passo 1**: la fiducia si offre, non si impone.

---

## 3. Opzioni

Quattro approcci realmente diversi per architettura e per scopo. Il costo è sempre quello vero: tempo di build e fragilità operativa, dato che il costo in euro deve restare zero per costruzione.

### Opzione A — Il sito compilato da un job ("static build")

Un job pianificato (GitHub Actions) fa **tutto** il calcolo: ingest, fit, bootstrap, quote, scoring, selezione, settlement. Scrive il risultato come **file JSON versionati nel repo**. Il sito è un **Next.js in export statico** che legge quei file a build time. Nessun database, nessun server applicativo, nessuna chiamata a runtime.

- **Costa:** ~1 settimana di setup dei job, poi manutenzione quasi nulla. Zero euro strutturali, non "zero euro finché il free tier regge".
- **Cosa la rompe:** se un giorno serve una risposta che non è conoscibile al momento del build (account, live in-play, ricerca su tutto lo storico). Nessuna di queste è in scope. Secondariamente: il peso del repo se si versionano male i file (mitigabile: sovrascrittura, non append, tranne il ledger).
- **A 10× traffico:** invariata. Sono file statici su CDN. È l'unica opzione in cui il traffico non ha proprio un costo.
- **Quando la scegli:** quando il contenuto è identico per tutti gli utenti ed è noto ore prima. Che è esattamente il nostro caso.
- **Effetto collaterale che vale più dell'architettura:** i commit del job sono **datati e immutabili**. Il ledger dei pronostici in un repo pubblico è la prova, verificabile da chiunque, che quello che abbiamo detto prima della partita è quello che riportiamo dopo. Il fallimento di credibilità centrale del settore (competitors §3.3: *"i report non coincidono con quello che era stato pubblicato prima"*) qui è **impossibile per costruzione**, non per buona volontà.

### Opzione B — Job + database gestito

Stesso job, ma scrive su un Postgres gestito su free tier (Neon/Supabase [R]). Il sito Next.js legge dal DB con ISR/cache.

- **Costa:** un po' più di setup, più uno strato di ORM/migrazioni. Query storiche comode.
- **Cosa la rompe:** i free tier dei DB gestiti sono la parte meno stabile del piano — sospensione per inattività, cambi di policy, tetti di storage [R]. Introduciamo una dipendenza gestita che può cambiare condizioni, per ottenere query che con 3.500 righe/stagione non ci servono.
- **A 10×:** il DB free tier è il primo collo di bottiglia (connessioni, non calcolo).
- **Quando la scegli:** quando lo storico supera il milione di righe o quando servono query ad-hoc dall'app. Non ora. **Trigger per adottarla:** se un giorno il ledger supera ~500k righe o serve filtrare per utente.

### Opzione C — Lo stack di default dello studio (FastAPI + Postgres + Next.js su Vercel/Railway)

Backend FastAPI con endpoint, worker separato per i job, Postgres, frontend Next.js.

- **Costa:** il setup più lungo dei quattro, e — questo è il punto — **costa denaro ricorrente appena finisce il credito di prova del PaaS** [R: Railway non ha più un free tier permanente, da verificare]. Un servizio always-on per servire risposte precalcolate identiche per tutti.
- **Cosa la rompe:** il vincolo #2 di decisioni.md ("zero, sempre"). Basta un mese di fatturazione e il progetto è morto per una ragione non-prodotto.
- **Cosa non compra:** nessuno degli endpoint sarebbe dinamico. Non c'è scrittura utente, non c'è autenticazione, non c'è personalizzazione. FastAPI qui è un proxy verso righe che il job ha già scritto.
- **Quando la scegli:** il giorno in cui esiste un utente registrato. **Trigger esplicito:** account, notifiche push server-side, o un'API pubblica.

### Opzione D — "Fai meno": una lega, niente quote, sito statico

Solo Serie A. Niente the-odds-api in v1 (w = 1,0 ovunque). Backtest interpretabile su una sola distribuzione, silenzio calibrato su un solo campionato, storia semplice da raccontare.

- **Costa:** pochissimo. È la v1 più onesta concepibile e si costruisce in giorni.
- **Cosa la rompe, ed è decisivo:** **il volume di pronostici è il carburante della pagina "Come stiamo andando"**. Una sola lega produce ~380 partite/stagione, cioè ~10 partite a settimana, cioè ~7 pronostici pubblicati a settimana dopo il silenzio. Per arrivare a 500 pronostici dal vivo servirebbero **più di un anno**. Con dieci competizioni ne servono **otto settimane** (calcolo in §7.5). In un prodotto il cui differenziatore è il track record, **la copertura non è una leva di reach: è una leva di credibilità**, ed è la leva che si muove più lentamente.
- **Quando la scegli:** se il backtest dicesse che il modello ha risoluzione dimostrabile su una sola lega. È l'unico caso, ed è un caso di ripiego, non di progetto.

---

## 4. Raccomandazione

> **Opzione A, su tutte e dieci le competizioni, con lancio in ombra dei job quattro settimane prima del sito.**

**La ragione unica:** in questo prodotto la credibilità si compra solo col volume di pronostici pubblicati e datati, e l'Opzione A è l'unica in cui pubblicare e datare i pronostici **è** l'architettura, non una funzionalità aggiuntiva. Tutto il resto (costo zero, resistenza al traffico, semplicità) viene dietro, gratis.

Il corollario operativo, che vale quanto la scelta: **si costruisce il backend per primo e lo si fa girare in pubblico mentre si costruisce il frontend.** Non è una raccomandazione di processo, è la soluzione al problema più difficile del progetto (§7.5).

---

## 5. Architettura di calcolo (domanda 1)

### 5.1 L'osservazione che cambia il dimensionamento

I 300 bootstrap **non si fanno per partita: si fanno per campionato**.

La pipeline di §8.1 della ricerca sembra per-partita, ma il costo è tutto nel rifit del Dixon-Coles, e il rifit dipende solo dai risultati del campionato. Quindi:

- **Passo costoso, O(campionati):** stima DC + 300 rifit bootstrap → si conservano i **300 draw di parametri** `(α_i, β_i, γ, ρ)`. Peso: ~300 × 42 float ≈ **100 KB per campionato**, JSON compresso molto meno. [V, aritmetica]
- **Passo economico, O(partite):** per ogni fixture, 300 matrici 11×11 costruite dai draw già in memoria + i ~9 mercati marginalizzati. Sono prodotti esterni di Poisson: **millisecondi per partita**. [V, natura del calcolo]

Conseguenza: il retrain e lo scoring sono **due job separati con due frequenze diverse**. Fonderli è l'errore che rende il sistema lento e fragile.

### 5.2 I sei job, con la loro cadenza

| # | Job | Quando (UTC) | Cosa fa | Costo |
|---|---|---|---|---|
| 1 | `ingest` | 03:00 ogni giorno | football-data.org: calendario prossimi 10 giorni + risultati partite concluse. **Archivia tutto in repo** (vedi rischio R7). | ~30 chiamate |
| 2 | `retrain` | 03:30, **solo per i campionati con nuovi risultati** | DC pesato + 300 bootstrap → `params.json` per campionato | il pesante |
| 3 | `score` | 04:00 ogni giorno | Per ogni fixture nei prossimi 7 giorni: matrici, p̂/σ, base rate, shrinkage, KL, filtri, clustering → **pronostico preliminare** (w=1,0) | secondi |
| 4 | `odds` | 2 finestre/giorno (10:00 e 18:00) | Solo campionati che giocano entro ~36h e non ancora quotati. Vedi §6. | crediti |
| 5 | `finalize` | subito dopo `odds` | Ricalcola con w=0,35 → **pronostico definitivo**. Una sola volta per partita. | secondi |
| 6 | `settle` | 03:15 ogni giorno | Chiude i pronostici delle partite finite, ricalcola accuratezza, silence rate, skill dichiarato vs realizzato | secondi |

Ogni job termina con un commit su `data/` se qualcosa è cambiato; il commit fa scattare il build del sito. **~3–4 deploy al giorno** [V, aritmetica], dentro qualsiasi free tier plausibile [A].

Nota sulla frequenza rispetto ai calendari reali: `retrain` non gira "ogni notte per tutte le leghe", gira **quando arrivano risultati**. In pratica lunedì/martedì e giovedì/venerdì per le leghe europee, con 3–6 campionati alla volta invece di 10. Questo da solo dimezza abbondantemente il carico medio.

### 5.3 Il tempo di calcolo: misurare prima di progettare

Non ho un dato verificato su quanto duri un fit DC su 760 partite con `scipy.optimize`. Il documento di ricerca dice "decimi di secondo" (§5.2) — se è vero, 10 campionati × 300 rifit = **~25 minuti**, banale. Se il fit costasse 3 secondi, sarebbero 2,5 ore, ancora dentro il limite di 6 ore per job di GitHub Actions [A], ma scomodo.

**Primo task di `backend-python`, prima di qualsiasi altra cosa: cronometrare un fit DC su Serie A reale e scrivere il numero nel repo.** Da quel numero dipende quale gradino della scala serve:

1. Rifit solo dei campionati con nuovi risultati (sempre attivo).
2. **Warm start**: ogni rifit bootstrap parte dai parametri del fit puntuale. I bootstrap sono per definizione vicini al punto stimato; questo è il singolo intervento con il rapporto guadagno/sforzo più alto.
3. **Matrice di job** di GitHub Actions: un runner per campionato, in parallelo [A: ~20 runner concorrenti sul piano gratuito, R].
4. Ridurre B da 300 a 200 (errore relativo sulla sd da 4% a 5% — irrilevante per lo shrinkage) [V, formula 1/√(2B)].
5. Solo come ultimo gradino: rifit settimanale invece che per giornata.

Non si scende sotto il gradino 4 senza dati. E non si parte dal gradino 3 per paura: la parallelizzazione complica il commit dei risultati.

### 5.4 Perché non i job pianificati dell'hosting

I cron di Vercel sul piano Hobby hanno limiti di numero e di granularità, e soprattutto **le funzioni hanno un tetto di durata nell'ordine dei secondi/minuto** [A, R]: un job che rifitta 3.000 modelli non ci sta e non ci starà mai. Non è un dettaglio da aggirare — è la ragione per cui il calcolo pesante non deve stare nel provider che serve le pagine. GitHub Actions è l'unico posto gratuito con **ore** di CPU e cron veri [A: minuti illimitati su repo pubblico, 2.000/mese su privato — R].

Questa separazione (calcolo su Actions, servizio su CDN) è anche ciò che rende **strutturalmente impossibile** chiamare the-odds-api da una richiesta utente: il client delle quote vive in un package che il sito non importa e non potrebbe eseguire. Il vincolo duro di decisioni.md diventa una proprietà del build, non una regola da ricordare.

---

## 6. Politica dei 500 crediti/mese (domanda 2)

### 6.1 I conti

Fatti di partenza [V, decisioni.md]: 500 crediti/mese; **costo di una chiamata = n. mercati × n. regioni**; una chiamata restituisce **tutte** le partite imminenti di quel campionato; copertura EPL, Championship, Bundesliga, Serie A, La Liga, Ligue 1, Champions League, Europa League, Brasileirão.

**Decisione 1 — mercati:** `h2h` + `totals`. Niente `spreads`.
`h2h` dà 3 vincoli, `totals` ne dà 2 per linea (e tipicamente restituisce più linee): sono più che sufficienti per risolvere ai minimi quadrati la coppia (λ_h*, λ_a*) che riproduce il mercato. `spreads` aggiungerebbe il **50% del costo** per vincoli quasi collineari a quelli che abbiamo già. Taglio netto.

**Decisione 2 — regioni:** `eu`, una sola. **Costo per chiamata = 2 crediti.**

**Decisione 3 — chi si quota:**

| Fascia | Competizioni | Politica |
|---|---|---|
| Con quote | EPL, Serie A, La Liga, Bundesliga, Ligue 1, Champions League, Championship, Brasileirão | 1 chiamata per lega per turno, nella finestra **T−36h → T−24h** |
| Solo modello, per sempre | Eredivisie, Primeira Liga | fuori copertura the-odds-api [V, decisioni.md] |
| Solo modello, per ora | Mondiali, Europei | **nessuna partita fino al 2028**, vedi §8.4 |

**Il conto mensile:**

| Voce | Chiamate/mese | Crediti |
|---|---|---|
| EPL, SA, PD, BL1, FL1 — 1 turno/settimana | 5 × 4,3 = 21,5 | 43 |
| Championship — 2 turni/settimana | 8,6 | 17 |
| Brasileirão — 1 turno/settimana | 4,3 | 9 |
| Champions League — ~2 settimane di gare/mese | 4 | 8 |
| **Audit CLV** — 1 sola lega (Serie A), 1 chiamata a T−2h, settimanale | 4,3 | 9 |
| **Totale regime** | ~43 | **~86** |

**~86 crediti su 500: il 17% della quota.** [V, aritmetica sui fatti sopra]

### 6.2 Perché lasciare l'83% inutilizzato è la scelta giusta

Non è timidezza. La riserva serve a quattro cose, tutte reali:

1. **Il mese di sviluppo**, in cui si bruciano chiamate per capire il formato delle risposte.
2. **I job falliti e ripetuti.** Un `odds` che va in errore a metà e riparte spende due volte.
3. **Le settimane congestionate** (turni infrasettimanali sovrapposti alla Champions, recuperi).
4. **La possibilità futura**, se mai la vorremo, di un secondo snapshot. Oggi non la vogliamo (§7).

Un sistema che deve girare da solo per anni senza che nessuno lo guardi non va dimensionato all'80% della quota. Va dimensionato al 20%.

### 6.3 Il governo della quota, in codice

- **Contatore persistito** in `data/odds_budget.json`: mese, crediti usati, dettaglio per chiamata. Il job **rifiuta** di chiamare se `usati + costo > tetto_mensile`. Tetto **hard-coded a 250**, metà della quota: se lo tocchiamo, c'è un bug, non un picco di traffico.
- **Riconciliazione con gli header di risposta** dell'API (`x-requests-remaining` / `x-requests-used` [R: nomi da verificare]). Se il nostro contatore e il loro divergono, vince il loro e il job si mette in pausa fino a intervento.
- **Mai chiamare per leghe che non giocano.** L'ordine è: leggi i fixture da football-data → calcola quali leghe hanno partite entro 36h → chiama solo quelle.
- **Mai chiamare due volte la stessa partita.** Un `odds_snapshot_id` per partita; se esiste, si salta. Questo è anche ciò che implementa la decisione di §7.
- **In sviluppo e nei test: mai la rete.** Ogni risposta grezza viene salvata come fixture su disco al primo contatto; i test girano solo su quelle. Regola non negoziabile per `backend-python`.

### 6.4 La scala di degradazione quando la quota finisce

Non esiste uno stato "quota finita = prodotto rotto", perché **ogni partita ha sempre un pronostico da solo modello**. Le quote sono un miglioramento, non una dipendenza. Ordine di rinuncia:

1. Salta l'audit CLV (−9/mese).
2. Salta Brasileirão e Championship (−26/mese).
3. Passa a `h2h` soltanto (dimezza tutto il resto).
4. Solo modello ovunque, e la scheda lo dichiara col badge che già esiste.

Al gradino 4 il prodotto continua a funzionare, mostra `w = 1,0` su tutto, e la pagina "Come stiamo andando" registra il periodo come tale. Nessuna schermata di errore, nessun buco.

---

## 7. Le due verità dello stesso match (domanda 3)

### 7.1 Le tre risposte possibili, e perché due sono sbagliate

**Congelare al primo calcolo.** Il pronostico preliminare (w=1,0) è quello definitivo. Coerenza massima. Ma: abbiamo speso crediti per delle quote che non usiamo per l'utente, e — peggio — **sappiamo di stare mostrando la stima peggiore**. La ricerca è netta: il mercato batte i modelli (§2.2), tanto che diamo al nostro DC solo il 35% del peso quando c'è un'alternativa. Congelare significa pubblicare consapevolmente la versione a cui noi stessi crediamo meno. È coerenza pagata in accuratezza, e in un prodotto che pubblica la propria accuratezza è un autogol misurabile.

**Aggiornare liberamente, in silenzio.** Massima accuratezza istantanea, e la distruzione esatta del nostro unico asset. L'evidenza è nel teardown: la lamentela più grave e più documentata del settore — utenti paganti, sito con 4,2/5 — è *"i loro claim non coincidevano con i miei risultati reali"*, con segnalazione di discrepanza fra ciò che era pubblicato prima e ciò che veniva riportato dopo (competitors §3.3). Un tip che cambia senza dirlo **fabbrica** quella discrepanza. Scartata senza appello.

**La terza:** il pronostico ha un **ciclo di vita a due fasi dichiarate**, entrambe pubblicate, entrambe permanenti, entrambe misurate separatamente.

### 7.2 La scelta

> **Al massimo una revisione, in un momento programmato e annunciato in anticipo, sempre visibile, e valutata separatamente nel track record.**

Non "congelato" e non "aggiornabile": **revisione unica e dichiarata**.

| Fase | Finestra | Peso | Badge | Nel ledger |
|---|---|---|---|---|
| **Preliminare** | da T−7g a T−36h | w = 1,0 | "solo modello statistico" | riga propria, con timestamp |
| **Definitivo** | da T−36h al fischio d'inizio | w = 0,35 (se le quote sono arrivate) | "confrontato con le quote" | riga propria, con timestamp |

Regole dure:
- **Una sola finalizzazione per partita.** Se `finalize` è già girato, non rigira, nemmeno se il job viene rieseguito. Questo limita la variazione possibile a **esattamente una**, per costruzione.
- **Al fischio d'inizio tutto è congelato.** Nessuna scrittura dopo il kickoff, mai, per nessun motivo. Il `settle` scrive solo l'esito.
- **Il preliminare non viene mai cancellato.** Se il consiglio è cambiato, la scheda lo mostra come contenuto, non come nota a piè di pagina:
  > *"Fino a ieri dicevamo **Over 2.5**. Con l'arrivo delle quote la nostra stima si è abbassata: ora diciamo **Over 1.5**."*
- **Le due fasi si misurano separatamente.** La pagina "Come stiamo andando" ha due colonne: *preliminare (solo modello)* e *definitivo (con quote)*. Dopo una stagione potremo dire, con dati nostri, **se e quanto il confronto col mercato ci abbia migliorati**. Nessuno nel settore può dire una frase del genere.

### 7.3 I due casi scomodi, che sono i più preziosi

**Da pronostico a silenzio.** Il preliminare diceva Over 2.5; con le quote nessun candidato supera i filtri.
> *"Le quote sono arrivate e dicono più o meno quello che dicevamo noi. Ritiriamo il pronostico: su questa partita non abbiamo un vantaggio da raccontare."*

**Da silenzio a pronostico.** Il contrario, ed è la stessa schermata al rovescio.

Queste due sono, secondo me, **le schermate che guadagnano più fiducia dell'intero prodotto**. Un sistema che ritira pubblicamente un proprio consiglio non lo ha mai fatto nessuno dei sette riferimenti analizzati. Vanno progettate insieme allo stato di silenzio, non dopo.

### 7.4 Perché T−36h e non T−3h

Le quote più vicine al kickoff sono più informative (si muovono sulle formazioni). Ma:
1. **Non abbiamo le formazioni** [V, fonti-dati §8]: quel movimento contiene informazione che il nostro modello non può assorbire, solo copiare.
2. Un consiglio che cambia tre ore prima è **inutile a chi ha letto ieri sera** e ha già deciso come passare la serata. Il valore d'uso di un pronostico decade prima della sua accuratezza.
3. La chiamata a T−2h resta, ma **solo per l'audit CLV su una lega** (§6.1) e **non tocca mai un pronostico pubblicato**. Separazione pulita fra ciò che serve a noi per misurarci e ciò che diciamo all'utente.

---

## 8. La soglia di silenzio (domanda 4)

### 8.1 Non si sceglie la soglia: si sceglie il tasso e si legge la soglia

`S_min = 0,005 nats` è un valore iniziale motivato (ricerca §8.3), non un valore calibrato. Il procedimento corretto è l'inverso:

1. Il backtest walk-forward (che serve comunque, §9) produce, per ogni partita storica, la distribuzione di `max_cluster S` con i parametri congelati.
2. Da lì si legge la funzione **tasso di silenzio in funzione di S_min**.
3. Si sceglie il **tasso obiettivo** con giudizio di prodotto, e si ricava `S_min`.
4. Si **congela** e si scrive nel repo, con la data e con il conteggio delle configurazioni provate (ricerca §7.2 — questa disciplina è obbligatoria, non consigliata).

### 8.2 Il tasso obiettivo

> **25%, con banda accettabile 15–30%, e un limite duro: mai più del 40% delle partite di una singola giornata.** [A: è un giudizio percettivo, dichiarato come tale]

Il ragionamento, con numeri concreti. Una domenica di Serie A ha 10 partite. Al 25% tacciamo su 2–3 e parliamo su 7–8: si legge come **selettività**. Al 60% tacciamo su 6: si legge come **guasto**. Sotto il 15% il silenzio smette di portare informazione — se non tace quasi mai, tacere non significa niente, e perdiamo il differenziatore senza guadagnare copertura.

Il limite giornaliero al 40% è una **valvola di prodotto**, non statistica: se una giornata sfora, non si abbassa la soglia — si mostra il numero e si spiega (turno infrasettimanale, inizio stagione con squadre nuove). Vedi §8.4.

### 8.3 I tre filtri non sono la stessa cosa, e vanno governati diversamente

Questa è la parte che rende il silenzio calibrabile senza diventare arbitrario:

| Filtro | Ruolo | Governo |
|---|---|---|
| `p_min = 0,50` | **Sicurezza.** È il vincolo di prodotto dell'utente tradotto in codice. | **Mai toccato.** Se morde spesso, il problema è a monte nel modello (ricerca §10.2) |
| `σ_max = 0,12` | **Sicurezza.** Stima troppo instabile per dire qualcosa. | **Mai toccato.** |
| `S_min` | **Editoriale.** Quanto poco è "troppo poco da dire". | **L'unica manopola**, calibrata una volta sul tasso obiettivo, poi congelata fino a revisione annuale |

Una sola manopola, girata una volta: è tutto ciò che il budget statistico di due stagioni permette (ricerca §7.2: con 5 anni si può provare al massimo ~45 configurazioni; noi ne abbiamo 2).

### 8.4 Cosa si mostra quando si tace

Il silenzio **non è uno stato vuoto**: è una card con lo stesso peso visivo di un pronostico, che contiene tre cose.

**1. Il motivo, e il motivo dipende da quale filtro ha morso.** Questo è il requisito tecnico che rende il silenzio informativo — il backend deve persistere **quale filtro ha scartato l'ultimo candidato**, non un booleano:

| Filtro che ha morso | Testo |
|---|---|
| `S_min` | *"Il nostro modello dice quasi esattamente quello che dice già la media del campionato."* (o *"...quello che dicono già le quote"*, se w=0,35) |
| `σ_max` | *"Abbiamo troppe poche partite affidabili su [squadra] per dare un numero in cui crediamo."* |
| `p_min` | *"Quello che vediamo di diverso è troppo improbabile perché ve lo consigliamo."* |

**2. Le probabilità grezze, in secondo piano**, sotto l'etichetta *"le probabilità, senza consiglio"*: 1X2 e Over 2.5, in trattamento neutro. Chi vuole i numeri li ha; chi voleva un consiglio ha una risposta.

**3. Il numero del giorno, dichiarato.** In cima alla lista di oggi: *"Oggi taciamo su 3 partite su 14."* Rivendicare il conteggio è ciò che trasforma l'assenza in scelta. Un sito che nasconde di aver taciuto sembra rotto; un sito che conta i propri silenzi in prima pagina sembra severo.

E, sulla pagina "Come stiamo andando", il **tasso di silenzio nel tempo** come grafico. È una metrica del prodotto esposta all'utente, e nessuno la ha.

### 8.5 Il ripiego, se il backtest dà un tasso molto alto

Se al valore iniziale `S_min = 0,005` il silenzio superasse il 50%, la lettura corretta **non è abbassare la soglia**. È che `τ̂² ≈ 0` su gran parte delle famiglie di mercato: il modello non ha risoluzione dimostrabile oltre il rumore (ricerca §5.3). La risposta onesta è **restringere lo scope, non il criterio**: pubblicare solo le leghe e le famiglie dove `τ̂² > 0`. Meglio cinque campionati che parlano che dieci che borbottano.

---

## 9. L'avvio a freddo di "Come stiamo andando" (domanda 5)

La questione più delicata, e la tratto come tale.

### 9.1 Il problema, detto senza sconti

Il giorno del lancio abbiamo **zero** pronostici pubblicati e una pagina che è il prodotto. Le tre scorciatoie disponibili sono tutte forme dello stesso imbroglio:

- Mostrare i numeri del backtest **come se fossero** un track record → è letteralmente Forebet ("75-80%", nessun campione, nessun periodo, nessun metodo). Fatale, perché è precisamente la cosa che siamo nati per non fare.
- **Nascondere la pagina** finché non ci sono dati → il differenziatore manca esattamente nelle settimane in cui chiediamo fiducia. Siamo il settimo Forebet per due mesi, e la prima impressione è l'unica che si dà.
- **Retrodatare** pronostici generati oggi su partite passate → fabbricazione di prove. Fuori discussione, e in un repo pubblico anche facilmente smascherabile.

### 9.2 La risposta: sì, un backtest walk-forward dichiarato è accettabile — a tre condizioni

Un backtest non è un track record. Diventa **prova ammissibile** se e solo se:

**Condizione 1 — Separazione architetturale, mai aggregazione.**
Due dataset, due nomi, mai una media fra i due, mai lo stesso grafico:
- **"Registro dal vivo"** — i pronostici pubblicati prima della partita, con il loro commit datato.
- **"Prova storica (backtest)"** — le previsioni walk-forward sulle due stagioni disponibili.

La pagina mostra **prima** il registro dal vivo, anche quando è quasi vuoto (*"22 pronostici dal 1 settembre: troppo pochi per una curva. Ecco i numeri grezzi."*), e **poi**, sotto un titolo proprio, il backtest. L'ordine è il messaggio: la cosa vera viene prima anche quando è più piccola.

**Condizione 2 — Il backtest è pre-registrato, non raccontato.**
Ciò che rende credibile un backtest non sono i suoi numeri: è che il protocollo sia stato fissato **prima** e non sia modificabile dopo. Quindi, prima del primo pronostico dal vivo, si pubblica nel repo un documento congelato con:

- la tabella dei parametri (ricerca §8.3) con i valori usati;
- la regola di walk-forward esatta e lo split a tre finestre;
- **il numero di configurazioni provate** — obbligatorio, ricerca §7.2: *se il numero non è scritto, il backtest non è interpretabile*;
- l'hash del commit del codice che ha prodotto i numeri.

In un repo pubblico, con la data del commit. **Questo è il secondo dividendo dell'Opzione A**: il pre-registro non è una promessa, è un fatto verificabile da chiunque.

**Condizione 3 — La sostituzione è promessa, datata e contata.**
La pagina dichiara in alto la propria scadenza:
> *"Da quando avremo 500 pronostici dal vivo, questa pagina mostrerà quelli. Il backtest resterà sotto, per confronto."*
> `147 / 500` — con la barra.

Una barra di avanzamento verso la propria resa dei conti è essa stessa un dispositivo di fiducia, e nessuno ne ha una.

### 9.3 Le due mosse che accorciano drasticamente il freddo

**Mossa 1 — Il lancio in ombra.**
I job entrano in produzione **quattro settimane prima del sito**, e cominciano a scrivere il ledger nel repo pubblico. Costo: zero, perché i job vanno costruiti e stabilizzati prima del frontend comunque. Guadagno: **si lancia con 200–300 pronostici dal vivo già datati e verificabili il giorno uno**.

È la mossa migliore di tutto il brief, e non è una mossa di design: è una mossa di **ordine di build**. Il problema dell'avvio a freddo non si risolve con la copy, si risolve con la sequenza.

**Mossa 2 — Il volume, che è più alto di quanto sembri.**

Partite per stagione delle dieci competizioni [V, aritmetica sui formati noti]:

| Competizione | Squadre | Partite/stagione |
|---|---|---|
| Premier League, Serie A, La Liga, Brasileirão | 20 | 380 × 4 = 1.520 |
| Bundesliga, Ligue 1, Eredivisie, Primeira Liga | 18 | 306 × 4 = 1.224 |
| Championship | 24 | 552 |
| Champions League | 36 | ~190 |
| **Totale** | | **~3.490** |

Su ~9 mesi: **~90 partite a settimana** nel cuore della stagione. Al 25% di silenzio: **~65–70 pronostici pubblicati a settimana**.

> **500 pronostici dal vivo ≈ 8 settimane.** Con il lancio in ombra: **~4 settimane dopo il lancio pubblico.**

Questo è il numero che rende la promessa di §9.2 condizione 3 credibile, ed è il numero che uccide l'Opzione D.

### 9.4 La metrica che funziona dal primo giorno

Il reliability diagram per bucket ha bisogno di centinaia di punti *per bucket*. Ma **lo skill dichiarato contro lo skill realizzato** (ricerca §10.1) è una media su tutti i pronostici insieme, e converge molto prima. Nella simulazione della ricerca, la sovraconfidenza produce 0,079 dichiarato contro 0,014 realizzato: **un fattore 5,7**. Un divario così non ha bisogno di 500 punti per essere visibile — ne bastano ~100 [A, ma il rapporto segnale/rumore è enorme].

> **Questo è il numero in testa alla pagina, dal primo giorno**, in italiano semplice:
> *"Dicevamo di saperne tanto così. Ne sapevamo davvero tanto così."* — due barre affiancate, e la differenza commentata in una riga.

È veloce a convergere, è impossibile da selezionare a posteriori (è una media su tutto), è la diagnosi diretta del nostro unico difetto atteso (shrinkage troppo debole), e **letteralmente nessuno nel settore la pubblica**. Se dovessi tenere una sola cosa di tutta la pagina, terrei questa.

Gerarchia di ciò che appare, in funzione di quanti dati ci sono:

| Da | Cosa appare |
|---|---|
| n ≥ 1 | Il registro: elenco dei pronostici pubblicati con esito, filtrabile. Nudo, senza sintesi. |
| n ≥ ~100 | Skill dichiarato vs realizzato, con la banda di incertezza. |
| n ≥ ~150 | Hit rate su **3 bucket grossolani** (50–65 / 65–80 / 80+), con `n` sotto ciascuno. Bucket con n < 30: mostrati in grigio con "troppo pochi", **non nascosti**. |
| n ≥ 500, con n ≥ 50 per bucket | Reliability diagram a 5 punti, decomposizione Ferro-Fricker. Il backtest scende definitivamente in seconda posizione. |

### 9.5 Cosa scrive la scheda-partita durante il freddo

La riga di record storico della card (competitors §5.3) non può mentire il primo giorno. Regola di formulazione, **una sola riga, fonte sempre nominata**:

- Prima: *"Su 100 pronostici come questo, **nel nostro test storico** ne sono usciti 67 (n=214, stagioni 2024-25)."*
- Dopo, **per bucket, automaticamente**, appena quel bucket raggiunge n ≥ 50 dal vivo: *"Su 100 pronostici come questo, **fra quelli che abbiamo pubblicato** ne sono usciti 67 (n=214, da set. 2026)."*

Il passaggio è per bucket, non globale, ed è automatico. La parola "test storico" non è un asterisco: è dentro la frase, dove non si può saltare.

### 9.6 L'obiezione a me stesso

Il nostro stesso documento di ricerca (§7.2) dice che con due stagioni siamo già oltre il budget di configurazioni: **un backtest su questi dati può essere sovra-adattato e noi non lo sapremmo**. Vero. Ed è esattamente il motivo per cui il pre-registro della condizione 2 non è una raffinatezza ma l'elemento portante — e per cui il limite va **stampato accanto al numero**, non in una FAQ:

> *"Un backtest non è un track record: è la stessa persona che decide le regole e conta i punti. Per questo lo teniamo separato, e per questo abbiamo scritto le regole prima. Il numero che conta è quello sopra."*

Trasformare il caveat in copy è la posa di Understat (competitors §5.5: dichiarare la metrica e i suoi limiti prima di usarla), ed è la sola posa coerente con il resto del prodotto.

---

## 10. Scope v1 (domanda 6)

Il momento di valore è: **apre → legge un consiglio → capisce perché → vede quanto spesso consigli così si avverano.** Tutto ciò che non serve a quei quattro passi esce.

### Dentro

**Prodotto**
- Home "oggi", con frecce ieri/domani; riga-partita con crest, ora, squadre, e anteprima del consiglio o dello stato di silenzio.
- Contatore dei silenzi del giorno in testa alla lista.
- Scheda partita: **un** pronostico; `p̃` come "85 su 100"; la riga di definizione operativa sotto il numero; la banda bootstrap p5–p95; il badge di provenienza (solo modello / confrontato con le quote); 2–3 ragioni in elenco; la riga di accuratezza della fascia.
- **Stato di silenzio**, con il motivo specifico del filtro che ha morso e le probabilità grezze sotto.
- **Storia a due fasi** sulla scheda: preliminare → definitivo, con la riga di spiegazione quando è cambiato, incluse le transizioni pronostico↔silenzio.
- Sotto la piega: le altre famiglie di mercato, forma W-D-L recente, esito a partita conclusa.
- **"Come stiamo andando"**: registro dal vivo, skill dichiarato vs realizzato, hit rate per bucket con n, tasso di silenzio nel tempo, barra 147/500, sezione backtest separata e etichettata.
- **"Come funziona"**: il criterio in un paragrafo comprensibile, la tabella dei parametri, il link al protocollo pre-registrato, *"non guadagniamo se scommetti"*, gioco responsabile.
- Italiano, una lingua sola.

**Tecnica**
- I sei job di §5.2, idempotenti, ciascuno eseguibile a mano.
- **Archiviazione locale di tutte le partite ingerite dal giorno uno** (vedi rischio 7 — non rimandabile).
- Ledger append-only in repo pubblico, con `schema_version`.
- Contatore e tetto dei crediti quote, con la scala di degradazione.
- Backtest walk-forward + protocollo pre-registrato, **prima** di qualunque lavoro di frontend.
- Fixture di risposta su disco per test senza rete.

### Rimandato, con il grilletto per riprenderlo

| Cosa | Grilletto |
|---|---|
| **Calibratore beta in produzione** (ricerca §4.3) | Quando ci sono >1.000 pronostici dal vivo per famiglia. In v1 la calibrazione si **misura**, non si corregge: impilare un calibratore stimato sopra lo shrinkage senza dati di conferma è la seconda correzione senza prova. |
| **Mercati primo tempo e HT/FT nel set dei candidati** | Quando `λ_HT/λ_FT` è stimato dai punteggi HT reali (è un task da un giorno). Fino ad allora si calcolano e si mostrano, ma non concorrono alla selezione: il rapporto 0,45 non è verificato (ricerca §11). |
| **CLV come metrica continua** | Mai, con 500 crediti. Resta audit settimanale su una lega. |
| **Database** | Ledger > ~500k righe, o query ad-hoc dall'app. |
| **Grafici di calibrazione fini a 5 punti** | n ≥ 50 per bucket. |
| **Analytics** | Se e quando serve una decisione che dipende dal comportamento. |
| **Competizioni per nazionali** | Mondiali ed Europei sono nel piano dati ma **non hanno partite fino al 2028**: il Mondiale 2026 si è appena concluso. Il codice li supporti; la UI non ci spenda un pixel. |

### Mai

- Affiliazione bookmaker, in qualunque forma, nemmeno "solo un link alle quote".
- Importi da puntare, ROI, "value bet", "edge", percentuali di rendimento.
- Pubblicità.
- Login, account, profilazione.
- Piano a pagamento.
- Scraping di FBref/Sofascore per corner/cartellini/tiri, e scraping di Understat per gli xG (fragile e fuori decisione).
- Probabilità non shrinkate mostrate all'utente.
- Accuratezza aggregata senza il bucket di appartenenza.

---

## 11. Stack e architettura (domanda 7)

### 11.1 Il verdetto sul default dello studio

FastAPI + Postgres + Next.js su Vercel/Railway **non regge**, per due ragioni distinte:

1. **Sul costo:** un servizio always-on più un DB gestito è, oggi, una spesa ricorrente o un free tier che può cambiare condizioni [R]. Il vincolo #2 di decisioni.md è "zero, sempre" — non "zero finché regge".
2. **Sulla necessità, che è la ragione più forte:** non c'è **niente** da servire dinamicamente. Nessuna scrittura utente, nessuna autenticazione, nessuna personalizzazione. Ogni risposta è identica per tutti ed è nota da ore. Un backend qui sarebbe un proxy davanti a righe già scritte da un job.

Il default dello studio va usato quando c'è uno stato del server. Qui lo stato del server è un file.

### 11.2 Lo stack raccomandato

| Strato | Scelta | Perché |
|---|---|---|
| **Calcolo** | Python 3.12, `numpy` + `scipy` + `pandas`. Job come CLI: `python -m pronostici.jobs.<nome>` | Nessuna dipendenza esotica. La ricerca conferma che non serve `cvxpy` né uno stack MCMC (§11, §5.2) |
| **Scheduler** | **GitHub Actions**, cron, repo **pubblico** | L'unico posto gratuito con ore di CPU e cron veri [A/R]. Repo pubblico = minuti illimitati **e** ledger verificabile |
| **Persistenza** | **Il repo stesso.** Niente database | 3.500 righe/stagione. Un DB qui è complessità senza contropartita. E i commit datati sono la prova di pubblicazione |
| **Sito** | **Next.js in export statico** (`output: 'export'`) | È il default della squadra, e in export statico non porta con sé nessun costo runtime |
| **Hosting** | **Vercel Hobby** [A: uso non commerciale consentito — noi lo siamo per decisione #2, permanentemente]. Uscita pronta: **Cloudflare Pages** | Zero euro, deploy da git. Se un giorno comparisse monetizzazione, si trasloca in un pomeriggio |

**Nessun FastAPI in v1.** Grilletto per introdurlo: il primo requisito che non sia conoscibile a build time. Non ce n'è in scope.

### 11.3 Il disegno

```
   football-data.org            the-odds-api (500/mese)
        │  (key in GH secrets)        │  (key in GH secrets)
        ▼                             ▼
┌──────────────────────────────────────────────────────┐
│              GITHUB ACTIONS  (cron)                  │
│                                                      │
│  ingest ──▶ retrain ──▶ score ──▶ odds ──▶ finalize  │
│    03:00     03:30      04:00    10/18h    subito    │
│                                                      │
│  settle 03:15 ──▶ accuratezza, silence rate, skill   │
└──────────────────────────────────────────────────────┘
        │  git commit  (datato, immutabile, pubblico)
        ▼
┌──────────────────────────────────────────────────────┐
│                     data/   — IL CONTRATTO           │
│  archive/{lega}/{stagione}.json   storico nostro     │
│  leagues/{lega}/params.json       300 draw bootstrap │
│  fixtures/{data}.json             partite + tip      │
│  ledger/{stagione}.jsonl          append-only        │
│  accuracy.json  ·  odds_budget.json  ·  schema.json  │
└──────────────────────────────────────────────────────┘
        │  webhook di build
        ▼
┌──────────────────────────────────────────────────────┐
│   NEXT.JS static export  ──▶  CDN                    │
│   Nessuna chiamata a runtime. Nessun segreto.        │
└──────────────────────────────────────────────────────┘
```

**Il confine, ed è l'unico che conta:** lo schema dei file in `data/` è **il contratto** fra `backend-python` e `frontend-engineer`. Va versionato (`schema_version`), fissato nella prima settimana, e cambiato solo con un bump esplicito. Il frontend non sa niente di Dixon-Coles; il backend non sa niente di React. Con questo confine i due possono lavorare in parallelo dal giorno tre.

**Tre proprietà che vengono gratis da questo disegno**, e che vanno rivendicate perché sono argomenti di prodotto, non di infrastruttura:

1. **Impossibile chiamare the-odds-api da una richiesta utente.** Non è una regola: è che il sito non ha runtime.
2. **Impossibile riscrivere il passato in silenzio.** Il ledger è append-only in un repo pubblico con commit datati.
3. **Impossibile che il traffico costi qualcosa.** File statici su CDN.

### 11.4 Una nota, non una riapertura

In `~/football-predictor/backend` esistono già `models/dixon_coles.py` (DC con decadimento EWMA) e `models/markets.py` (motore multi-mercato dalla matrice congiunta, con linee O/U, handicap asiatici ed europei, multigol già enumerati). La decisione #1 dice che quel progetto **non viene riusato**, e non la rimetto in discussione. La segnalo solo perché quei due file sono **funzioni pure senza dipendenze dal resto**, e leggerli come riferimento (non importarli) può risparmiare qualche giorno a `backend-python` sull'enumerazione dei mercati. Resta una scelta dell'utente.

### 11.5 Il sito non è live, ed è voluto

Nessun punteggio in diretta. I risultati compaiono col `settle` della notte. Non è una limitazione da mascherare: SofaScore possiede il match-centre e non glielo togliamo. Noi possediamo il giudizio e la sua ricevuta. Ogni pixel speso a inseguire il live è pixel tolto al differenziatore — e riporterebbe le chiamate a runtime, cioè demolirebbe l'architettura.

---

## 12. Rischi, in ordine

| # | Rischio | Perché fa paura | Mitigazione / grilletto |
|---|---|---|---|
| 1 | **`τ̂² ≤ 0`: il modello non ha risoluzione dimostrabile** | Se la dispersione delle nostre previsioni attorno al base rate è tutta rumore di stima, non abbiamo niente da dire, e nessuna UI lo risolve | **Il backtest walk-forward è il primo task del progetto, prima di ogni riga di frontend.** Se `τ̂² ≤ 0` su una famiglia, quella famiglia esce. Se esce quasi tutto, la decisione torna all'utente: il prodotto onesto diventa una pagina di probabilità senza consigli |
| 2 | **Tasso di silenzio fuori banda** | Sopra il 40% sembriamo rotti (competitors §6) | Calibrare `S_min` sul tasso (§8.1), limite duro giornaliero, motivo per filtro, contatore dichiarato. Se sfora strutturalmente → restringere lo scope, non la soglia |
| 3 | **Avvio a freddo della credibilità** | È il prodotto, e all'inizio è vuoto | Lancio in ombra di 4 settimane + skill dichiarato/realizzato dal giorno uno + protocollo pre-registrato (§9) |
| 4 | **Tempo di calcolo del bootstrap su Actions** | Se un fit DC è lento, il job non chiude | **Misurare al primo giorno.** Scala a 5 gradini di §5.3 |
| 5 | **ToS di the-odds-api sulla ripubblicazione delle quote** [R] | Potremmo non poter mostrare i prezzi | Mostrare solo la **probabilità implicita sgonfiata**, mai un prezzo di un bookmaker nominato. Coerente col divieto di affiliazione, e probabilmente anche prodotto migliore. `ricercatore` verifica prima del build della scheda |
| 6 | **Chiavi API in un repo pubblico** | Errore banale, danno immediato | Solo GitHub Secrets; mai chiavi in `data/`; hook pre-commit che rifiuta pattern di chiave; nessuna risposta grezza contenente credenziali versionata |
| 7 | **football-data.org dà solo le ultime 2 stagioni, e la finestra scorre** | Quando inizia la 2026-27, la 2024-25 può sparire e il nostro storico **si accorcia da solo** | **Archiviare in repo ogni partita ingerita dal primo giorno.** Costo ~nullo, e fra due anni abbiamo 4 stagioni invece di 2. Non è un'ottimizzazione: è l'unica cosa in v1 che migliora il modello col tempo senza lavoro |
| 8 | **Rate limit di football-data (~10 req/min)** [R] | Job che fallisce a metà | Backoff, job idempotenti, ingest incrementale |
| 9 | **Clausola non-commerciale di Vercel Hobby** [A/R] | Non ci tocca (decisione #2), ma è una dipendenza da una policy | Trasloco su Cloudflare Pages come uscita già provata una volta |
| 10 | **Budget statistico bruciato dal fiddling** | Con 2 stagioni bastano poche prove per rendere il backtest privo di significato (ricerca §7.2) | Contatore delle configurazioni scritto nel repo e controllato in review. Si toccano **al massimo due** parametri, e uno è `S_min` |

---

## 13. Domande aperte

Ognuna ha la mia assunzione di default: **il lavoro può partire comunque**.

| # | Domanda | Default con cui procedere | Chi la chiude |
|---|---|---|---|
| 1 | **Repo pubblico o privato?** | **Pubblico.** Sblocca i minuti Actions illimitati [R] *e* il ledger verificabile, che è il dispositivo di fiducia più forte del progetto. Se privato: 2.000 min/mese (fattibile con rifit selettivo) e ledger con catena di hash pubblicata — più debole, ma non fatale | utente |
| 2 | **Tasso di silenzio obiettivo** | **25%**, banda 15–30%, limite giornaliero 40% | `product-strategist`, sui dati del backtest |
| 3 | **Lancio in ombra di 4 settimane** | **Sì.** Costo zero, e risolve il problema più difficile | utente |
| 4 | **Momento del pronostico definitivo** | **T−36h → T−24h**, così il definitivo è online la sera prima. Da verificare contro il comportamento della finestra "upcoming" di the-odds-api | `ricercatore` + `backend-python` |
| 5 | **Dominio proprio** | Sottodominio gratuito in v1. Un dominio è l'unica spesa plausibile (~10 €/anno) e non è bloccante | utente |
| 6 | **Lingua** | **Solo italiano.** Il prodotto è quasi tutto copy di fiducia; tradurlo male costa più di quanto renda | `product-strategist` |
| 7 | **Le quote si mostrano come prezzo o come probabilità?** | **Probabilità implicita sgonfiata**, mai il prezzo. Dipende dal rischio 5 | `ricercatore` |

---

## 14. Consegne

### → `product-strategist`

1. **Fissa il tasso di silenzio obiettivo** (default 25%, banda 15–30%) sui dati del backtest, non a priori — e scrivi nel repo la data e il numero di configurazioni provate per arrivarci. Da lì `backend-python` ricava `S_min` e lo congela.
2. **Possiedi la pagina "Come stiamo andando" come oggetto di prodotto**, non come dashboard: definisci la gerarchia di §9.4 (cosa appare a n≥1, ~100, ~150, 500) e le formulazioni esatte delle due frasi di §9.5 — sono le uniche affermazioni di accuratezza che il prodotto pronuncia.
3. **Scrivi il protocollo pre-registrato** (§9.2 condizione 2) e fallo committare **prima** del primo pronostico dal vivo. È la cosa che rende ammissibile il backtest.
4. **Decidi il lancio in ombra** e la data di apertura del sito, in funzione di quando i job sono stabili.
5. Presidia gli anti-obiettivi di §10 "Mai" — sono decisioni già prese, il tuo compito è che nessuna deroga entri dalla finestra durante il build.

### → `ui-ux-designer`

1. **Progetta per primo lo stato di silenzio**, con **tre varianti di motivo** (`S_min`, `σ_max`, `p_min` — §8.4): stesso peso visivo di un pronostico, probabilità grezze in secondo piano, messaggio positivo. Non ha precedenti nel settore: non c'è niente da copiare.
2. **Progetta per secondo le due transizioni** pronostico→silenzio e silenzio→pronostico (§7.3). Sono le schermate che guadagnano più fiducia dell'intero prodotto e sono anche le più facili da fare male.
3. **Gerarchia della scheda**, sopra la piega, in quest'ordine: pronostico → probabilità con la riga di definizione operativa sotto → record storico della fascia → 2–3 ragioni. Tutto il resto sotto.
4. **Due grandezze, due linguaggi visivi**: probabilità dell'esito ≠ affidabilità della stima. È l'errore più sfruttabile del settore; non collassarle in un numero.
5. **Progetta la doppia fase** come contenuto della scheda (preliminare / definitivo), non come metadato nascosto, e la riga "fino a ieri dicevamo X".
6. **La pagina "Come stiamo andando" ha come titolo il confronto dichiarato/realizzato**, non la curva di calibrazione. La curva viene dopo, e all'inizio non c'è.
7. Convenzioni portanti intoccabili: nessun login, "oggi" di default, 1/X/2, riga-partita con crest, nomi standard dei mercati, forma W-D-L, quote in decimale, disclaimer di gioco responsabile.

### → `designer`

1. **Tono: la sobrietà di Understat**, non l'entusiasmo del tipster. Chi non deve vendere niente lo si deve capire dal ritmo tipografico prima che dalle parole.
2. **Un trattamento visivo per il silenzio** che non assomigli a un errore, a un vuoto o a uno skeleton di caricamento. È il pezzo di design più difficile e più identitario del progetto.
3. **La composizione da Metaculus**: numero grande + barra segmentata a piena larghezza sotto. Risolve "mostrare undici mercati senza soffocare" mostrandone uno e alludendo agli altri.
4. **Due palette semantiche distinte** per probabilità e per affidabilità. Non due tonalità della stessa: due linguaggi.
5. **La riga di definizione operativa** (stile National Weather Service) è un elemento di sistema, sempre presente, mai un tooltip: corpo piccolo, colore attenuato, sotto il numero grande.
6. Zero pubblicità, zero interruzioni, zero pattern da conversione. Il caso SofaScore (Trustpilot 1,9) è il limite da non avvicinare.

### → `backend-python`

1. **Task zero, prima di tutto: cronometra un fit Dixon-Coles su Serie A reale** e scrivi il numero nel repo. Determina l'architettura del retrain (§5.3).
2. **Task uno: il backtest walk-forward** con i parametri congelati di §8.3 della ricerca, che produce `τ̂²` per famiglia, la curva silenzio↔`S_min`, e i numeri della "Prova storica". **Prima di qualsiasi frontend.** Se `τ̂² ≤ 0` quasi ovunque, si ferma tutto e si riapre lo scope.
3. **Separa `retrain` (per campionato, pesante) da `score` (per partita, leggero)**, persistendo i 300 draw di parametri. È la decisione architetturale che rende il sistema gestibile.
4. **Sei job idempotenti** (§5.2), ciascuno eseguibile a mano, ciascuno che committa su `data/` solo se qualcosa è cambiato.
5. **Archivia ogni partita ingerita dal giorno uno.** La finestra di football-data scorre; il nostro storico deve crescere, non traslare (rischio 7).
6. **Governo della quota quote**: contatore persistito, tetto hard a 250, riconciliazione con gli header di risposta, scala di degradazione a 4 gradini, e **nessuna chiamata di rete nei test** (fixture su disco).
7. **Una sola finalizzazione per partita**, congelamento assoluto al fischio d'inizio, e **persistenza di quale filtro ha scartato l'ultimo candidato** — il frontend ne ha bisogno per scrivere il motivo del silenzio.
8. **Definisci e versiona lo schema di `data/`** nella prima settimana: è il contratto con il frontend.
9. De-vig **solo col metodo power**. Il de-vig ingenuo fabbrica vantaggio finto sui longshot ed è l'errore più costoso della lista dei gotcha.
10. Non fare grid search. Due parametri toccabili al massimo, e il conteggio delle configurazioni va scritto nel repo.

### → `frontend-engineer`

1. **Next.js in export statico. Nessuna chiamata a runtime, nessuna variabile d'ambiente segreta, nessun `fetch` verso terzi.** Se ti serve un dato che non è in `data/`, è un bug del contratto, non un caso da risolvere lato client.
2. **Consuma `data/` come contratto versionato.** Se `schema_version` non corrisponde, il build fallisce forte invece di degradare in silenzio.
3. **Lo stato di silenzio è un tipo di card di prima classe**, con le sue tre varianti di motivo — non un ramo `else` del rendering del pronostico. Modellalo nei tipi.
4. **Costruisci la pagina "Come stiamo andando" per essere corretta a n piccolo**: bucket sotto n=30 in grigio con "troppo pochi", mai nascosti; `n` e periodo sempre stampati accanto a ogni numero; sezione backtest visivamente e semanticamente separata, mai aggregata con il registro dal vivo.
5. **Time-to-first-value sotto i 2 secondi**, che è il benchmark di Forebet. Con l'export statico è un obiettivo facile: non sprecarlo con font pesanti o JS non necessario.
6. Un deploy per commit di dati, ~4 al giorno. Il build deve essere veloce e deterministico: nessuna dipendenza dalla data di sistema in fase di render.
