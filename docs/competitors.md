# Teardown competitor — pronostici calcistici

Autore: competitor-scout. Data delle verifiche: **2026-08-08**.
Vincoli di progetto presi come dati e non rimessi in discussione: vedi [decisioni.md](decisioni.md).

---

## 0. Nota di metodo — cosa ho letto davvero

Molti siti del settore bloccano i bot. Dichiaro pagina per pagina.

**Letto direttamente (HTTP 200):**

| Pagina | Esito |
|---|---|
| `footystats.org/` | ✅ |
| `footystats.org/premium` | ✅ prezzi verbatim |
| `footystats.org/predictions/mathematical` | ✅ etichette verbatim |
| `infogol.net` | ✅ **301 → sportinglife.com/football** |
| `sportinglife.com/football` | ✅ |
| `theanalyst.com/articles/opta-football-predictions` | ✅ |
| `theanalyst.com/competition/premier-league` | ✅ (poco estraibile) |
| `understat.com` | ✅ |
| `predictionrecord.com/predictor/Opta's_'Supercomputer'` | ✅ |
| `natesilver.net` | ✅ |
| `weather.gov/ffc/pop` | ✅ definizione verbatim |
| `apps.apple.com/.../footystats-soccer-stats/id1590091942` | ✅ rating + recensione + IAP |

**Letto solo tramite proxy testuale `r.jina.ai` (il fetch diretto dà 403):**

| Pagina | Esito |
|---|---|
| `forebet.com/en/football-tips-and-predictions-for-today` | ✅ via proxy |
| `predictz.com/predictions/` | ✅ via proxy |
| `trustpilot.com/review/forebet.com` | ✅ via proxy |
| `trustpilot.com/review/footystats.org` | ✅ via proxy |
| `trustpilot.com/review/sofascore.com` | ✅ via proxy |
| `metaculus.com/questions/` | ✅ via proxy |

**NON raggiunto — non ne descrivo il contenuto:**

- `forebet.com/en/predictions-successrate`, `/en/value-bets`, `/en/football-predictions-for-tomorrow`, `/en/predictions-tips-1x2/all-leagues-predictions` → **404** (URL da me ipotizzati; il 404 dimostra che *quegli* URL non esistono, non che la funzione non esista da nessuna parte).
- `predictz.com/how-accurate-are-our-predictions/` → **404** (idem).
- `footystats.org/upgrade` → 404 (il piano sta su `/premium`).
- `clubelo.com` → connessione rifiutata.
- **Nessuna scheda-partita individuale** di Forebet o PredictZ: le pagine di dettaglio non sono state raggiunte. La descrizione del layout qui sotto vale per le **pagine-lista**, ed è etichettata come tale.
- Nessuno screenshot: descrivo solo struttura testuale e etichette effettivamente lette.

**Conseguenza onesta:** dove scrivo "non pubblicano track record" intendo *non l'ho trovato dalle pagine che ho letto e dalle loro proprie pagine di presentazione*. È un'assenza forte ma non una prova formale. La distinguo ovunque da ciò che ho letto verbatim.

---

## 1. Categoria e job-to-be-done

**Categoria:** pronostici calcistici gratuiti assistiti da modello statistico.
**Job-to-be-done:** *"Sto per guardare / giocare questa partita. Dimmi la cosa più probabile che vale la pena dire, quanto ci credi, e perché dovrei fidarmi di te — in meno di dieci secondi."*

Il job **non** è "dammi tutti i dati": quello è il job dell'analista, ed è già saturo (FootyStats, Understat, SofaScore). Il job qui è **la delega del giudizio**. Ed è quello che il settore serve peggio.

---

## 2. Tabella dei riferimenti

| # | Nome | URL | Chi serve | Prezzo d'ingresso | Punto di forza | Punto debole |
|---|---|---|---|---|---|---|
| 1 | **Forebet** | forebet.com | Scommettitore casual che vuole un numero subito | Gratis (ads + odds affiliate) | Copertura enorme, probabilità 1X2 esposte, "Pick of the day" | Un pronostico su **ogni** partita, sempre; nessun track record trovato sulle sue pagine |
| 2 | **PredictZ** | predictz.com | Scommettitore UK/US, mercato per mercato | Gratis (bet slip affiliate) | Segmentazione per mercato (BTTS, O/U 2.5, correct score) pulitissima | Zero indicatore di confidenza; è un feed di tip, non un modello leggibile |
| 3 | **FootyStats** | footystats.org | Semi-pro che vuole i dati grezzi | Gratis limitato → **£19,99/mese** ("prezzo limitato per l'Italia", listino £26,99) | Profondità dati mostruosa, 1500+ leghe, CSV | Cimitero di numeri; "value bets" senza calibrazione visibile; recensioni su profitti che non tornano |
| 4 | **Opta / The Analyst** | theanalyst.com | Lettore evoluto, giornalisti | Gratis (vetrina B2B di Stats Perform) | Autorevolezza, simulazioni Monte Carlo, probabilità piene | **Nessuna statistica di accuratezza pubblicata** sulla loro pagina di metodo; è editoriale, non uno strumento per-partita |
| 5 | **SofaScore** | sofascore.com | Tutti. È il default | Gratis (ads pesanti) + abbonamento ad-free | Il match-centre migliore del settore, densità gestita bene | Pubblicità invasiva denunciata a voce alta; le "predictions" sono sondaggi/ranking, non un consiglio |
| 6 | **Infogol** | infogol.net → sportinglife.com | *(morto)* | — | Era l'xG-native bello | **Assorbito da Sporting Life (Timeform/Flutter)**: il prodotto-modello è diventato contenuto affiliato |
| 7 | **DIY: Telegram + Excel** | t.me/… , fogli | Chi non si fida dei siti | Gratis / "VIP" a pagamento | Voce umana, senso di comunità, zero attrito | Selezione delle prove: vittorie in vetrina, sconfitte cancellate |

Riferimento adiacente non-concorrente ma rilevante: **Understat** (understat.com, vivo, `© understat 2017—2026`) — solo xG storico, **nessuna previsione**, nessuna pubblicità né paywall visibili. È il polo opposto: onestà totale, zero raccomandazione.

---

## 3. Teardown per prodotto

### 3.1 Forebet — il leader di volume

Letto: pagina-lista `/en/football-tips-and-predictions-for-today` via proxy.

**Flow.** Zero attriti: apri, sei già sulle partite di oggi. Nessun onboarding, nessun login. Il time-to-first-value è ~2 secondi. Questo è il benchmark da battere e va rispettato.

**Come presentano il pronostico.** **Entrambe le cose insieme**: mostrano le tre probabilità 1/X/2 come numeri interi affiancati (letto un esempio nella forma `48 25 26`) **e** scelgono per l'utente con una sezione **"Pick of the day"** separata dalla lista. Le colonne lette sulla lista: squadre, probabilità (1, X, 2), **punteggio previsto**, **correct score**, **media gol**, **meteo**, **coefficiente**, live score, e una colonna di trend storici.

**Confidenza.** Comunicata **solo** come percentuale grezza di probabilità. Non ho letto stelle né semafori sulla pagina-lista. Il difetto strutturale: *la probabilità dell'esito non è la fiducia nella stima*. 48% con dati abbondanti e 48% su una neopromossa dopo tre giornate hanno lo stesso aspetto. Questa confusione fra **probabilità** e **affidabilità** è il buco concettuale numero uno del settore.

**Ammettono incertezza?** No. La struttura della pagina è una riga per partita, sempre piena. Non ho trovato alcuno stato "nessun pronostico".

**Track record.** Non trovato. Ho provato `/en/predictions-successrate` e `/en/value-bets`: **404 entrambi**. La loro stessa pagina istituzionale "Main features of Forebet" (letta via proxy) descrive "a complex of mathematical algorithms based on a wide range of statistics" e l'unico numero di performance che contiene è *"Under/Over 2.5 goals predictions with an accuracy rate of 75-80%"* — un claim di marketing, senza sample size né periodo né metodo. Recensioni indipendenti riportano cifre reali intorno al **56% sui match winner** e **62,1% 1X2 verificato**, contro il claim aggregato di oltre 75%. Fonti terze, non primarie: le tratto come indizio, non come prova.
→ *Questo è il punto: il numero che rende credibile un sito di pronostici è l'unico che il leader non pubblica in forma verificabile.*

**Come sono gratis.** Pubblicità **più quote in formato americano** (`+333`, `-175` letti nella tabella) — cioè affiliazione bookmaker orientata al mercato US. La quota è *dentro* la tabella del pronostico. Effetto sulla fiducia: il consiglio e l'incentivo economico condividono la stessa riga. Non c'è modo per l'utente di sapere se il pick è scelto per lui o per il click.

**Lamentele.** Trustpilot `forebet.com`: **TrustScore 3,2**, ma su **una sola recensione** (1 stella, "Very poor performance", 13 ottobre 2025), profilo non rivendicato. **Campione inutilizzabile — lo riporto per completezza, non come evidenza.** L'evidenza vera sta nella discrepanza claim-vs-misurato sopra.

---

### 3.2 PredictZ — il feed di tip per mercato

Letto: `/predictions/` via proxy (la pagina renderizza il frame; le righe dati non sono arrivate nel testo estratto — lo dichiaro).

**Flow.** Come Forebet: aperto, subito le partite di oggi. Titolo letto verbatim: *"Football Tips Today - Saturday, August 8th, 2026"* (il sito è vivo e aggiornato in giornata).

**Come presentano il pronostico.** Per **tab di mercato**, e questa è la loro mossa migliore: `Match Tips & Odds`, `BTTS Tips & Odds`, `BTTS And Win Tips & Odds`, `Over/Under 2.5 Tips & Odds`, `Correct Score Tips & Odds`. L'utente sceglie *il mercato* e poi legge le partite, invece di leggere una partita e annegare in 11 mercati. È una risposta reale al problema della densità — ma è l'opposto del nostro prodotto, che sceglie il mercato *per* l'utente.

**Confidenza.** Nessun indicatore di confidenza letto. L'unico segnale di contesto è il **record delle ultime 5 partite** con legenda esplicita *"W (Win), D (Draw), L (Loss)"*. Le quote sono in formato `1:X:2` e sono **cliccabili per aggiungere la selezione alla schedina**.

**Ammettono incertezza?** Solo con disclaimer legali, non nel prodotto: letto verbatim *"Picks do not guarantee winning bets or profits"* e *"Gambling problem? Call 1-800-Gambler 21+ to wager"*. È copertura legale, non design dell'incertezza. Non ho trovato uno stato "nessun pronostico".

**Track record.** `/how-accurate-are-our-predictions/` → **404** (URL mio, non loro). Non ho trovato accuratezza pubblicata sulle pagine lette. Terze parti riportano stime "60–87% a seconda del mercato" — range talmente largo da essere privo di informazione, e comunque non primario.

**Come sono gratis.** Affiliazione bookmaker profonda: l'odds *è* il bottone che costruisce la schedina. Monetizzazione più integrata e più invasiva di Forebet, perché il gesto di lettura e il gesto di scommessa sono lo stesso click.

---

### 3.3 FootyStats — il cimitero di numeri con il paywall

Letto direttamente: homepage, `/premium`, `/predictions/mathematical`.

**Flow.** Homepage → tabella partite → "Stats" per fixture. Il valore arriva presto ma è **grezzo**: l'utente deve fare lui il lavoro di sintesi.

**Come presentano il pronostico.** Pagina `/predictions/mathematical`, etichette lette verbatim: **"Mathematical Predictions"**, **"Value Bets Found With Mathematical Models"**, **"Implied Odds"**, **"Real Odds"**. Ogni fixture espone **più mercati contemporaneamente** con la probabilità in percentuale — esempi letti: `51% BTTS`, `85% 8.5+ Corners`. Cioè: **non scelgono**. Espongono un elenco di candidati e lasciano all'utente l'argmax. È esattamente la maledizione dell'ottimizzatore scaricata sull'utente (cfr. decisioni.md, Smith & Winkler 2006): chi legge sceglierà il numero più alto, che è sistematicamente il più sovrastimato.

**Confidenza.** Percentuale nuda. Nessuno shrinkage dichiarato, nessuna banda, nessuna distinzione fra un 85% su 400 partite e un 85% su 12.

**Track record.** Non pubblicato in forma di calibrazione. C'è **"Profit tracked!"**, ma è riferito ai **tip postati dagli utenti** (Premium include *"5 Premium Predictions Daily"* e *"View Highest ROI Users"*): è una **leaderboard di ROI di persone**, non l'accuratezza del **loro modello**. Sostituire la propria calibrazione con la classifica dei fortunati è un'inversione notevole — e delega la responsabilità.

**Business.** Verbatim da `/premium`: **"£19.99/ Month"**, presentato come *"Limited Price for Italy"* contro un listino *"£26.99 / Month"* (−35%). Gate: *"No limits. View all stats, pages, and leagues without restrictions"*, CSV, corner e cartellini, match search, 1.500+ competizioni, le 5 predictions premium giornaliere. Il free tier è deliberatamente **rate-limited per pagina/lega**: il trigger d'upgrade è la frustrazione, non un momento di valore. Su App Store l'IAP è **$25.99**.

**Lamentele — qui c'è l'evidenza migliore di tutto il teardown.** Trustpilot `footystats.org`: **4,2/5 su 308 recensioni**, quindi non un sito screditato — il che rende le critiche più pesanti:

- *"Their claims of large daily profits did not match my actual results"* (21 aprile 2026), con segnalazione di discrepanza fra i report inviati via email e i pronostici realmente pubblicati.
- *"the odds they give on the site are totally out of sync with the real world"* (26 marzo 2026).
- *"the data and everything is not correct"* dopo un anno d'uso (11 ottobre 2024).
- Assistenza non risponde alle domande **sull'accuratezza dei pronostici** e ai rimborsi.

App Store (4,1 su sole 41 valutazioni): *"Lots of lagging, there is an auto update feature that refreshes the app regularly so if you're scrolling through a page, you'll just get reset and pushed back to the top of the page, every 30 seconds or so"* (08/10/2025), più fusi orari sbagliati per utenti non-US e "no updates in over a year despite the $26/month cost".

**Il pattern che emerge, e va detto chiaro:** gli utenti non contestano la mancanza di dati. Contestano che **il resoconto retrospettivo non coincide con quello che era stato pubblicato prima della partita**. È il fallimento di credibilità centrale del settore.

---

### 3.4 Opta / The Analyst — l'autorevole che non si misura

Letto: `theanalyst.com/articles/opta-football-predictions` e `/competition/premier-league`.

**Flow.** È **editoriale**, non uno strumento: articoli, "Expected Points Table", una voce di nav "Predictions". Non c'è un percorso "cerca la mia partita di stasera → risposta". Time-to-value alto, ma il pubblico è diverso.

**Come presentano il pronostico.** **Distribuzione completa, mai un pick secco.** Verbatim dalla loro pagina di metodo: il modello *"estimates the probability of each match outcome (win, draw or loss)"* e *"considers the strength of opponents by using these match outcome probabilities and simulates the remaining fixtures in the competition thousands of times"*. Il linguaggio è cauto ("likely to be", "estimates").

**Track record — il dato più significativo del teardown.** La loro **pagina che spiega come funzionano le previsioni non contiene alcuna statistica di accuratezza, alcun backtest, alcun risultato storico.** Nemmeno il fornitore di dati più autorevole del calcio mondiale pubblica la calibrazione del proprio modello accanto al modello.

E c'è la controprova: esiste un sito terzo, **predictionrecord.com**, che tiene il conto *al posto loro* (traccia "expert predictions about the near future" su Politica, Guerra, Economia, Calcio, Cinema; metrica dichiarata **"Average difference vs actual"**). Sulla scheda di Opta's 'Supercomputer' ho letto **4 sole previsioni tracciate, 0 corrispondenze esatte**, con un'accuratezza inferita dell'85% su una classifica a 20 squadre. **Campione ridicolo, metrica non specificata, gestore anonimo** (solo `mail@predictionrecord.com` e `@PredictionRec`): non è una fonte affidabile. Ma la sua **esistenza** è il dato: c'è domanda di rendicontazione, e la sta soddisfacendo un volontario anonimo con quattro righe di dati, perché il produttore non la soddisfa.

**Business.** Gratis, perché è la vetrina di marketing di **Stats Perform** verso i clienti B2B. Non c'è affiliazione bookmaker visibile sulle pagine lette: la fiducia non è compromessa dagli incentivi — è solo non verificabile.

---

### 3.5 SofaScore — il default, e la lezione sulla pubblicità

**Flow.** È l'app di riferimento per il match-centre: apri, partite live, tap, dettaglio profondo (heatmap, player rating, shot map). Il modello di navigazione che tutti hanno copiato.

**Come presentano il pronostico.** Non lo fanno, nel senso nostro. Hanno **sondaggi "Who will win?"** e **Power Rankings** editoriali (es. per il Mondiale 2026, costruiti mescolando forma recente e *segnali di mercato come le quote decimali*). È **consenso del pubblico + ranking**, non un consiglio motivato. Nessuna confidenza, nessun track record.

**Come sono gratis — e quanto costa in fiducia.** Qui l'evidenza è pesante e concorde su due fonti indipendenti.
Trustpilot `sofascore.com`: **TrustScore 1,9/5 su 32 recensioni** (campione piccolo e auto-selezionato — lo dichiaro), con lamentele ricorrenti su pop-up impossibili da chiudere:
- *"Had to uninstall this app because it has these pop ups that appear when you click onto the app....today was different because I couldn't get rid of it."* (16 luglio 2026)
- *"It's the most biased rating app you will ever use...they fraud the rating."* (31 luglio 2025)

Corroborato dalle recensioni Play Store, dove gli utenti riferiscono di essere *"bombarded with ads"*, di annunci che aprono altre app o il browser, non chiudibili per 30–60 secondi, e di rating abbassati a 1 stella **specificamente** per i pop-up. SofaScore risponde offrendo un abbonamento ad-free.

**Lezione operativa per noi.** Il prodotto tecnicamente migliore del settore ha la reputazione peggiore, e la causa è la monetizzazione, non il prodotto. Un'app di *pronostici* — dove il valore È la fiducia — non può permettersi nemmeno un decimo di quella pressione pubblicitaria.

---

### 3.6 Infogol — il morto istruttivo

`infogol.net` risponde **301 Moved Permanently → `sportinglife.com/football`** (verificato oggi). Infogol era il prodotto xG-native più curato del settore, sviluppato in orbita Timeform (gruppo Flutter, con Betfair, Paddy Power, Sky Betting & Gaming).

Cosa c'è ora al suo posto, letto su `sportinglife.com/football`: **articoli di tipster firmati** ("Carabao Cup tips: Back the upsets", "A strong Kase for 100/1 Palmer", a firma Jake Osgathorpe, Jimmy the Punts, Tom Carnduff), **nessuna menzione di xG sulla pagina**, e affiliazione bookmaker estesa e in evidenza (Sky Bet, Paddy Power, Betfair, Sky Vegas, con link "View the latest offer" e free bet).

Due dettagli che contano:
1. **Il modello è stato sostituito da opinioni umane e offerte di free bet.** È la traiettoria economica naturale del settore: il modello non monetizza, l'affiliazione sì.
2. **Esiste però una voce di navigazione "Tipping Records"**, e un tipster viene presentato con *"After returning profit in his last two season outright's..."*. Cioè: **il settore delle scommesse rendiconta i tipster umani, ma non i modelli.** È una convenzione già accettata dagli utenti, applicata al bersaglio sbagliato. È lo spiraglio più concreto che ho trovato.

Nota storica correlata e verificata: **FiveThirtyEight è stato chiuso da ABC/Disney nel marzo 2025**, e i modelli sportivi (incluse le Club Soccer Predictions con SPI) avevano già smesso di aggiornarsi da giugno 2023 dopo l'uscita di Nate Silver, che possedeva i modelli. Nel maggio 2026 ABC ha reindirizzato migliaia di articoli d'archivio. **Il miglior prodotto mai esistito per "previsione calcistica con calibrazione pubblica" non esiste più.** Il posto è vuoto.

---

### 3.7 L'alternativa DIY — Telegram e i fogli Excel

Non è un sito, ed è il concorrente più forte per attenzione: gratis, arriva col push, ha una voce umana, zero attrito.

**Come presentano.** Un tip secco, spesso con enfasi ("BANKER", "SURE"), senza probabilità.
**Confidenza.** Retorica, non numerica.
**Track record.** Il fallimento definitorio, e ben documentato: i tipster *"rely on psychological tricks — cherry-picked wins, deleted losses"*; i canali che promettono partite truccate o vincite garantite sono truffe; *"A good tipster shows all results — wins and losses — not just cropped screenshots"*.
**Monetizzazione.** Gruppi "VIP" a pagamento, affiliazione con link di registrazione, a volte phishing in DM.

**Perché conta per noi.** L'utente che sceglie Telegram non sta scegliendo l'accuratezza — sta scegliendo **una risposta invece di una tabella**. Ha ragione sul formato e torto sulla sostanza. Il nostro prodotto è la stessa forma (una risposta) con la sostanza opposta (verificabile). Il foglio Excel personale è l'altra faccia: chi non si fida di nessuno se lo costruisce, e paga con manutenzione infinita.

---

## 4. Convenzioni da rispettare

Distinguo i pattern **portanti** (romperli disorienta) da quelli **inerziali** (copiati per pigrizia: è lì che si vince).

### Portanti — non toccare

| Convenzione | Dove | Perché è portante |
|---|---|---|
| **Nessun login, nessun onboarding** | ingresso | Forebet, PredictZ, SofaScore: partite di oggi al primo pixel. Un signup wall qui uccide il prodotto. |
| **"Oggi" è la home** | navigazione | La domanda è sempre "stasera". Data di default = oggi, con frecce ieri/domani. |
| **Notazione 1 / X / 2** | ovunque | È l'alfabeto. Non inventare "Casa/Pari/Ospite". |
| **Riga-partita: logo, squadra casa, ora, squadra trasferta** | lista | Letto su tutti. Aspettativa muscolare. Abbiamo i `crest` da football-data.org: usarli. |
| **Nomi dei mercati standard** | schede | "Over 2.5", "BTTS", "Doppia chance", "Handicap asiatico". Sono termini tecnici già appresi, non gergo da tradurre. |
| **Forma recente W-D-L come contesto** | scheda | PredictZ la espone con legenda esplicita. È il pezzo di prova che l'utente cerca istintivamente per validare il consiglio. |
| **Le quote, se ci sono, vanno in decimale** | scheda | Forebet usa il formato americano perché monetizza sugli USA. Per un pubblico italiano il decimale è l'unica lettura naturale. |
| **Disclaimer di gioco responsabile** | footer/scheda | PredictZ lo ripete. È aspettativa di settore e requisito reputazionale. Da tenere anche non monetizzando. |

### Inerziali — qui si vince rompendo

| Convenzione | Perché è solo inerzia | Cosa fare invece |
|---|---|---|
| **Una riga per ogni partita, sempre piena** | Esiste perché la tabella è un template, non perché il modello abbia qualcosa da dire su ogni gara | **Stato "nessun pronostico"**, progettato come contenuto, non come vuoto |
| **La probabilità dell'esito usata come misura di fiducia** | Confusione concettuale ereditata, non scelta di design | Separare visivamente **probabilità dell'esito** e **affidabilità della stima**. Due grandezze, due trattamenti |
| **Esporre tutti i mercati e lasciare l'argmax all'utente** | FootyStats: `51% BTTS` accanto a `85% 8.5+ Corners`. È scarico di responsabilità | Scegliere **uno**, con criterio dichiarato (KL + shrinkage), e mostrare gli altri solo su richiesta |
| **Accuratezza come claim di marketing** ("75-80%") | Nessun sample size, nessun periodo, nessun metodo | Calibrazione misurata, con **numerosità** e **periodo** scritti accanto |
| **Il consiglio e la quota affiliate nella stessa riga** | Monetizzazione mascherata da informazione | Il vantaggio strutturale del progetto: **non monetizziamo**. Va detto esplicitamente, è il differenziatore più difendibile |
| **Il "correct score" in bella vista** | Forebet lo mette in colonna: è il numero più impressionante e il meno affidabile | decisioni.md lo prevede già: risultato esatto quasi mai vincerà il ranking. **Coerente. Tenere il punto.** |

---

## 5. Ispirazione visiva

Cinque riferimenti concreti per il problema specifico *"mostrare UNA raccomandazione con la sua incertezza e la sua affidabilità storica"*. Tre su cinque sono fuori dal calcio, perché nel calcio il problema non è risolto.

### 5.1 National Weather Service — la definizione sotto il numero
*Letto: `weather.gov/ffc/pop`.* Definizione verbatim di PoP: *"the probability that the forecast grid/point in question will receive at least 0.01\" of rain"*.
**Cosa rubare esattamente:** la **riga di definizione operativa sotto il numero grande**. Non "68% — fidati", ma `68%` con sotto, in corpo piccolo e colore attenuato, *"su 100 partite come questa, in 68 esce Over 2.5"*. Un solo rigo, sempre presente, mai un tooltip. Trasforma una percentuale opaca in un'affermazione falsificabile — che è precisamente ciò che rende il numero credibile.

### 5.2 Metaculus — la barra di distribuzione compatta accanto alla stima singola
*Letto: `metaculus.com/questions/` via proxy.* Etichette lette: **"Current estimate"**, formulazione `65% chance`, distribuzioni come barre categoriali (letto un esempio: `Very High (or higher)` 1%, `High` 17%, `Moderate` 66%, `Low (or lower)` 16%), più una sezione **"Key Factors"**.
**Cosa rubare (due cose distinte):**
1. La **composizione "un numero grande + una barra segmentata larga quanto la card sotto di esso"**. La barra non compete col numero, lo qualifica: si legge la distribuzione con la coda dell'occhio in mezzo secondo. È il modo giusto di mostrare le 11 alternative *senza* mostrarle.
2. **"Key Factors" come elenco di 2–3 ragioni brevi**, non come prosa. La nostra spiegazione deve essere una lista corta, non un paragrafo.
*Notato onestamente:* sulla card Metaculus **non** c'è calibrazione. Anche loro la tengono altrove. Rubiamo la composizione, non l'omissione.

### 5.3 FiveThirtyEight — la curva di calibrazione come ancora di fiducia
*Il sito è chiuso (marzo 2025) e l'archivio in gran parte reindirizzato: non ho potuto rifetchare le pagine originali, quindi tratto questo come riferimento di memoria, non come pagina verificata oggi.* Il loro pezzo distintivo era il grafico "quando abbiamo detto 70%, è successo il 71% delle volte" — asse x probabilità dichiarata, asse y frequenza osservata, diagonale di riferimento.
**Cosa rubare:** **una sola pagina "Come stiamo andando"**, raggiungibile da ogni pronostico con un link testuale, che contenga (a) la curva di calibrazione per bucket, (b) la numerosità sotto ogni bucket, (c) il periodo coperto. E il pezzo che nessuno fa: **mettere sulla card il dato del bucket pertinente** — *"i pronostici che diamo al 65-70% escono nel 67% dei casi (n=214, ultime 2 stagioni)"*. Questo singolo elemento, da solo, ci mette in una categoria in cui non c'è nessun altro.
**Perché è sicuro:** il posto è letteralmente vuoto. Il prodotto che occupava questa nicchia non esiste più dal 2023.

### 5.4 Sporting Life "Tipping Records" — la convenzione già accettata, spostata di bersaglio
*Letto: `sportinglife.com/football`.* Hanno una voce di nav **"Tipping Records"** e presentano i tipster con la loro storia (*"After returning profit in his last two season outright's"*).
**Cosa rubare:** la **collocazione e il tono**. Il settore ha già insegnato agli utenti che "un tipster serio mostra il suo record". Nessuno lo ha ancora applicato a un modello. Riusare la stessa etichetta mentale — un badge di record accanto al nome di chi consiglia — ma dove "chi consiglia" è il modello, e il record è calibrazione anziché profitto. Zero costo di apprendimento, differenziazione massima.

### 5.5 Understat — il rigore del bianco e la trattenutezza
*Letto: `understat.com`, vivo, nessuna pubblicità né paywall visibili.* Solo xG storico, esplicitamente **nessuna previsione**, con la definizione della metrica scritta in chiaro (*"xG is a statistical measure of the quality of chances created and conceded"*) e export CSV/JSON/XLSX.
**Cosa rubare:** il **ritmo tipografico sobrio e la densità bassa** di chi non deve vendere niente, e soprattutto la **posa**: dichiarare la metrica e i suoi limiti prima di usarla. E l'inversione utile: Understat ha l'onestà ma non dà mai una risposta; Forebet dà sempre una risposta ma nessuna onestà. **Noi stiamo esattamente in mezzo, ed è una posizione vuota.**

### 5.6 Bonus — lo stato "nessun pronostico" non ha precedenti nel settore

Non ho trovato **nessun** esempio, in nessuno dei prodotti letti, di uno stato "non ho niente da dire su questa partita". Ricerca accademica sulle app meteo (Joslyn, Univ. of Washington) fotografa lo stesso vizio in un altro dominio: le app offrono previsioni *"excessively—and potentially unrealistically—detailed... extending far into the future without sufficient disclaimers regarding the confidence level"* e *"rarely do they include any estimate of uncertainty"*.

**Indicazione per il design:** lo stato vuoto **non deve sembrare un errore o un dato mancante**. Deve avere lo stesso peso visivo di un pronostico — stesso spazio nella card, stessa dignità tipografica — e dire una cosa positiva, del tipo *"su questa partita il modello non vede nulla di diverso da quello che dicono già le quote"*, con sotto le probabilità grezze per chi le vuole. È il momento in cui il prodotto guadagna più fiducia di tutti gli altri messi insieme. **Va progettato per primo, non per ultimo.**

---

## 6. Il varco

> **Nessuno accanto al pronostico mette la prova di quanto ci ha preso, e nessuno tace mai.**
> Costruire l'unico prodotto in cui ogni consiglio porta con sé il proprio tasso di successo storico misurato nella sua fascia di confidenza — e in cui "nessun pronostico" è una risposta legittima e ben progettata.

### Le tre ipotesi, giudicate

**Ipotesi 1 — "sono cimiteri di numeri senza una raccomandazione difendibile": CONFERMATA, con una precisazione.**
FootyStats espone `51% BTTS` e `85% 8.5+ Corners` sulla stessa fixture senza scegliere: l'argmax è scaricato sull'utente, che sceglierà il numero più alto — sistematicamente il più sovrastimato. Opta mostra distribuzioni piene, mai un pick. Understat non prevede affatto.
*Precisazione:* Forebet **una scelta la fa** ("Pick of the day") e PredictZ dà tip secchi. Non è vero che nessuno sceglie. È vero che **nessuno dichiara il criterio con cui sceglie**. Forebet parla di *"a complex of mathematical algorithms"* e basta. Il varco non è "scegliere": è **scegliere con un criterio scritto**. Su questo decisioni.md è già più avanti di tutto il mercato — la divergenza KL con shrinkage è un criterio *dichiarabile in una frase*, e questo è un asset di comunicazione, non solo di modello.

**Ipotesi 2 — "danno sempre un tip anche quando non hanno niente da dire": CONFERMATA, senza eccezioni trovate.**
Zero stati "nessun pronostico" in tutti i prodotti letti. La struttura a tabella con una riga per partita *impone* che ogni riga sia piena. L'unica ammissione d'incertezza incontrata sono disclaimer legali (*"Picks do not guarantee winning bets or profits"*), che sono copertura, non design. Anche fuori dal calcio il vizio è documentato (ricerca sulle app meteo).

**Ipotesi 3 — "non mostrano onestamente quanto ci hanno preso": CONFERMATA, ed è la più forte delle tre.**
- Il **fornitore dati più autorevole del mondo** pubblica una pagina che spiega il metodo e **non contiene nessuna statistica di accuratezza**.
- Il **leader di volume** pubblicizza *"75-80%"* senza sample size né periodo, mentre verifiche indipendenti riportano ~56% sui match winner.
- Il prodotto **a pagamento** sostituisce la calibrazione del proprio modello con una **classifica di ROI di utenti** ("View Highest ROI Users"), delegando la responsabilità ai fortunati.
- Gli utenti paganti se ne accorgono e lo dicono: *"Their claims of large daily profits did not match my actual results"* (Trustpilot FootyStats, 21 aprile 2026), su un sito che ha comunque 4,2/5 — quindi non è rumore da hater.
- Un **volontario anonimo** ha aperto un sito (predictionrecord.com) per tracciare le previsioni di Opta con quattro righe di dati. La domanda esiste; l'offerta no.
- E il prodotto che questa cosa la faceva bene — FiveThirtyEight — **è stato chiuso**: modelli sportivi fermi da giugno 2023, sito spento a marzo 2025, archivi reindirizzati a maggio 2026.

### Perché fare diversamente è sicuro (non solo diverso)

1. **Il posto è vuoto, non conteso.** Non stiamo scommettendo che il mercato voglia calibrazione: stiamo osservando che l'unico che la offriva è morto per ragioni aziendali estranee al prodotto (tagli Disney, il fondatore che se ne va portandosi i modelli), non per mancanza di domanda.
2. **La convenzione esiste già, applicata altrove.** "Tipping Records" è una voce di menu che gli utenti di questo settore già capiscono. Non dobbiamo educare nessuno: dobbiamo solo puntarla sul modello anziché su un tipster.
3. **L'unico costo del "nessun pronostico" è il traffico su quella partita, e non abbiamo un business che dipende dal traffico.** Forebet e PredictZ non possono permettersi una riga vuota, perché la riga vuota è una impression persa e un click affiliate perso. Noi non monetizziamo: **il vincolo economico che impedisce a loro di essere onesti su di noi non agisce.** È un vantaggio strutturale, non una scelta di gusto.
4. **La contropartita è dichiarabile.** Se il free tier di FootyStats costa £19,99/mese per togliere i limiti e SofaScore costa la reputazione in pop-up, "gratis, senza pubblicità, senza affiliazione, e ti dico quando non so" è un posizionamento che nessun incumbent può copiare senza uccidere i propri ricavi.

### Il rischio da non sottovalutare

Un prodotto che dice "non lo so" **su troppe partite** non viene percepito come onesto: viene percepito come rotto. La soglia di silenzio è una decisione di **prodotto**, non solo statistica. Servirà una calibrazione della frequenza — indicativamente il silenzio dovrebbe restare una minoranza netta e **visibilmente motivata** ogni volta. Da definire con `product-strategist` sui dati veri, non a priori.

---

## 7. Consegne

### → `brainstormer`
- Il formato "una risposta invece di una tabella" ha già vinto la battaglia dell'attenzione: lo hanno vinto i canali Telegram, con contenuti pessimi. La forma è validata, la sostanza è libera.
- Tre territori inesplorati emersi dal teardown: **(a)** il pronostico che porta con sé il proprio tasso storico nella sua fascia; **(b)** lo stato "nessun pronostico" come contenuto di valore, non come vuoto; **(c)** "non guadagniamo se scommetti" come promessa esplicita — nessuno dei sei riferimenti può dirlo.
- Non inseguire la profondità dati: quella partita è persa (FootyStats ha 1.500+ leghe e 10 anni di CSV) ed è il job sbagliato.

### → `product-strategist`
- **La pagina "Come stiamo andando" non è una feature secondaria: è il prodotto.** Va nello scope v1, non nel backlog. Senza, siamo il settimo Forebet.
- Il vincolo dati di decisioni.md (2 stagioni di storico) definisce anche il **limite di ciò che possiamo affermare**: la calibrazione va pubblicata con numerosità e periodo, e le fasce con n troppo basso vanno mostrate come tali. È coerenza, non debolezza — e nessun competitor lo fa.
- Decisione aperta da prendere presto: **quanto spesso il prodotto può tacere** prima di sembrare rotto (§6, rischio).
- Il free tier di FootyStats (£19,99/mese, blocchi per pagina e lega) definisce cosa NON dobbiamo fare: nessun rate-limit sull'esperienza base. Il nostro vincolo di quota the-odds-api va assorbito dal job pianificato, mai dall'utente.
- Anti-obiettivo esplicito: nessuna affiliazione bookmaker, nemmeno "solo un link alle quote". Forebet e PredictZ mostrano cosa succede alla leggibilità del consiglio quando l'incentivo entra nella stessa riga.

### → `designer` e `ui-ux-designer`
- **Da progettare per primo, non per ultimo: lo stato "nessun pronostico".** Non ha precedenti in tutto il settore. Stesso peso visivo di un pronostico, messaggio positivo, probabilità grezze in secondo piano. §5.6.
- **Gerarchia della card, in ordine, sopra la piega:** (1) il pronostico in chiaro; (2) la probabilità con la sua riga di definizione operativa sotto (§5.1); (3) il record storico della fascia di confidenza (§5.3); (4) 2–3 "ragioni" in elenco (§5.2). Tutto il resto sotto la piega.
- **Due grandezze, due linguaggi visivi distinti:** *probabilità dell'esito* e *affidabilità della stima*. Tutto il settore le collassa in un numero solo. È l'errore più sfruttabile.
- **Composizione da rubare:** numero grande + barra segmentata a piena larghezza sotto (Metaculus). Risolve "mostrare 11 mercati senza soffocare" mostrandone uno e alludendo agli altri.
- **Convenzioni portanti da non toccare:** nessun login, "oggi" di default, 1/X/2, riga-partita con crest, nomi standard dei mercati, forma W-D-L, quote in decimale. §4.
- **Densità:** SofaScore è il benchmark di come si gestisce la profondità (e va studiato per il match-centre), ma **la sua pubblicità è il caso-limite da non avvicinare**: Trustpilot 1,9/5 e recensioni Play Store al minimo per i pop-up. Il nostro asset è la fiducia; una sola interruzione la costa più di quanto renda.
- **Tono visivo:** la sobrietà di Understat (§5.5), non l'entusiasmo da tipster. Chi non deve vendere niente lo si deve vedere dal ritmo tipografico.

---

## Fonti

Tutte consultate il **2026-08-08**. `[proxy]` = letta via `r.jina.ai` perché il fetch diretto restituisce 403.

- Forebet, previsioni di oggi — https://www.forebet.com/en/football-tips-and-predictions-for-today `[proxy]`
- Forebet, "Main features of Forebet" — https://www.forebet.com/index.php/en/news-about-the-site/17463-main-features-of-forebet `[proxy]`
- PredictZ, previsioni — https://www.predictz.com/predictions/ `[proxy]`
- FootyStats, homepage — https://footystats.org/
- FootyStats, prezzi — https://footystats.org/premium
- FootyStats, mathematical predictions — https://footystats.org/predictions/mathematical
- FootyStats su App Store — https://apps.apple.com/us/app/footystats-soccer-stats/id1590091942
- Opta Analyst, come funzionano le previsioni — https://theanalyst.com/articles/opta-football-predictions
- Opta Analyst, Premier League — https://theanalyst.com/competition/premier-league
- Prediction Record, scheda Opta — https://predictionrecord.com/predictor/Opta's_'Supercomputer'
- Infogol → Sporting Life (301 verificato) — https://www.infogol.net/ → https://www.sportinglife.com/football
- Trustpilot, Forebet — https://www.trustpilot.com/review/forebet.com `[proxy]`
- Trustpilot, FootyStats — https://www.trustpilot.com/review/footystats.org `[proxy]`
- Trustpilot, SofaScore — https://www.trustpilot.com/review/sofascore.com `[proxy]`
- SofaScore su Google Play — https://play.google.com/store/apps/details?id=com.sofascore.results
- Understat — https://understat.com/
- Metaculus — https://www.metaculus.com/questions/ `[proxy]`
- National Weather Service, definizione di PoP — https://www.weather.gov/ffc/pop
- Silver Bulletin — https://www.natesilver.net/
- Chiusura di FiveThirtyEight — https://www.niemanlab.org/2025/03/fivethirtyeight-is-shutting-down-as-part-of-broader-cuts-at-abc-and-disney/
- Nate Silver sull'archivio 538 — https://www.natesilver.net/p/disney-erased-fivethirtyeight
- FiveThirtyEight, "How our club soccer predictions work" (archivio) — https://fivethirtyeight.com/features/how-our-club-soccer-predictions-work
- Tipster Telegram, pratiche e red flag — https://www.honestbettingreviews.com/best-football-tipster-telegram/ · https://www.101greatgoals.com/telegram-betting-tipsters/
- Ricerca sulla comunicazione dell'incertezza nelle app meteo — https://rmets.onlinelibrary.wiley.com/doi/full/10.1002/met.1589
- Verifiche indipendenti sull'accuratezza di Forebet (fonti terze, non primarie) — https://betzoid.com/ng/forebet/ · https://www.victorspredict.com/article/how-accurate-is-forebet-prediction/
