# Fonti dati gratuite — verifica sul campo

**Decisione da sbloccare:** con quali fonti a costo zero si alimentano i mercati richiesti (1X2, over/under, BTTS, handicap, multigol, combo, marcatori, cartellini, corner, tiri) su campionati top di club + nazionali.

**Data della verifica: 2026-08-08.** Tutte le chiamate sotto sono state eseguite davvero da questa macchina, non ipotizzate. Dove non ho potuto verificare, è scritto esplicitamente.

---

## 1. ESPN hidden API — ❌ BLOCCATA

`https://site.api.espn.com/apis/site/v2/sports/soccer/{lega}/scoreboard`

Testati `ita.1`, `eng.1`, `esp.1`, `ger.1`, `fra.1`, `uefa.champions`, `fifa.world`, più `/leagues`.

**Risultato: HTTP 403 su tutti**, sia con User-Agent di default sia con User-Agent da browser Chrome.

Non è un problema di rete locale: nella stessa sessione `api.github.com`, `api.football-data.org` e `understat.com` hanno risposto 200. È ESPN che rifiuta.

> **Conseguenza:** l'approccio previsto ("come usavamo ESPN") non è percorribile così com'è. Servirebbero proxy o rotazione di IP — fragile, e territorio di elusione di un blocco deliberato. Non lo raccomando come fondazione di un prodotto pubblico.

---

## 2. football-data.org — ✅ LA FONDAZIONE

`https://api.football-data.org/v4/competitions` → **HTTP 200 senza API key**, 189 competizioni.

### Copertura del piano gratuito (TIER_ONE)

Coincide quasi esattamente con la richiesta:

| Tipo | Competizioni TIER_ONE |
|---|---|
| **Club** | Premier League (PL), Serie A (SA), La Liga (PD), Bundesliga (BL1), Ligue 1 (FL1), Eredivisie (DED), Primeira Liga (PPL), Championship (ELC), Brasileirão (BSA), **Champions League (CL)** |
| **Nazionali** | **FIFA World Cup (WC)**, **European Championship (EC)** |

Altre rilevanti, ma su piani superiori a pagamento: Europa League (EL, TIER_TWO), Nations League (UNL, TIER_FOUR), qualificazioni mondiali ed europee (TIER_FOUR), Coppa America (TIER_FOUR), Copa Libertadores (TIER_FOUR).

### Limite riscontrato

`https://api.football-data.org/v4/competitions/SA/matches?season=2024` → **HTTP 403 senza API key**.

Serve una **API key gratuita** (registrazione con email su football-data.org). Resta a costo zero, ma è un'azione che deve fare l'utente.

### ⚠️ Non verificato

**Non ho potuto controllare cosa contiene davvero il payload di un match** senza la key. In particolare resta da confermare se il piano gratuito includa statistiche per partita (tiri, corner, cartellini) e gli eventi per giocatore (marcatori, ammoniti), oppure solo risultato, marcatori aggregati e classifica.

Questa è la verifica che sblocca lo scope dei mercati, e va fatta appena la key esiste.

---

## 3. Understat — ⚠️ RAGGIUNGIBILE MA CAMBIATO

`https://understat.com/league/Serie_A/2024` → HTTP 200, 18.659 byte.

Sarebbe la fonte più preziosa per la qualità del modello, perché espone gli **xG** (expected goals), che predicono i risultati futuri meglio dei gol effettivi.

**Ma il metodo di accesso storico non funziona più.** Le variabili inline che tutti i tutorial usano — `datesData`, `teamsData`, `playersData` — **non sono più nella pagina**. I dati vengono ora caricati dinamicamente da `js/league.min.js`.

Estrarli richiede reverse-engineering di quel JS per trovare l'endpoint XHR, ed è una dipendenza fragile: si rompe a ogni loro modifica, senza preavviso.

---

## 4. Verdetto per mercato (preliminare — superato dalla sezione 8)

> ⚠️ Questa tabella è stata scritta **prima** di avere la API key. La verifica definitiva è nella **sezione 8**, che sostituisce le righe "condizionale".

| Mercato | Gratis? | Con cosa |
|---|---|---|
| 1X2 | ✅ Sì | Solo risultati storici → matrice dei gol |
| Over/Under (ogni linea) | ✅ Sì | Stessa matrice |
| BTTS | ✅ Sì | Stessa matrice |
| Handicap (europeo e asiatico) | ✅ Sì | Stessa matrice |
| Multigol | ✅ Sì | Stessa matrice |
| Combo (es. 1 + Over 2.5) | ✅ Sì | Stessa matrice |
| Risultato esatto | ✅ Sì | Stessa matrice |
| Gol casa / gol ospite | ✅ Sì | Stessa matrice |
| **Marcatori** | ⚠️ Difficile | Servono minuti e tiri per giocatore, per partita |
| **Cartellini** | ⚠️ Condizionale | Serve il conteggio per partita + tendenza dell'arbitro |
| **Corner** | ⚠️ Condizionale | Serve il conteggio per partita |
| **Tiri** | ⚠️ Condizionale | Serve il conteggio per partita |
| **Quote / value bet** | ❌ Non risolto | Nessuna fonte gratuita di quote verificata |

**Il punto chiave:** gli otto mercati con la spunta verde derivano **tutti dalla stessa matrice di probabilità congiunta dei gol**. Un solo modello ben calibrato li produce in modo mutuamente coerente, senza dati aggiuntivi. È molto valore da poco input.

Gli ultimi quattro sono un problema diverso: richiedono ciascuno una fonte e un modello propri.

---

## 5. Combinazione consigliata

1. **football-data.org (key gratuita)** — calendario, risultati storici, classifiche, competizioni. È l'ossatura: legale, documentata, stabile, e copre già club + Mondiali + Europei.
2. **Verifica del payload** appena la key esiste → decide se corner/cartellini/tiri entrano nello scope.
3. **Understat come arricchimento opzionale** (xG), da isolare dietro un'interfaccia in modo che se si rompe l'app continui a funzionare con dati degradati anziché spegnersi.

---

## 6. Rischi

- **Dipendenza da una singola fonte** per l'ossatura. Mitigazione: uno strato di astrazione sulle fonti fin dal primo giorno, così sostituirne una non significa riscrivere l'app.
- **Rate limit del piano gratuito** di football-data.org (nell'ordine di 10 richieste/minuto, da confermare con la key): impone una cache e un aggiornamento programmato, non chiamate a ogni visita. Con molti utenti questo diventa vincolante — ed è anche ciò che rende l'app sostenibile a costo zero.
- **Scraping fragile e ToS**: Understat e simili non offrono garanzie e possono cambiare o bloccare in qualunque momento.
- **Quote non risolte**: senza una fonte di quote gratuita, "value bet" nel senso stretto (confronto col mercato) non è alimentabile. Va deciso come affrontarlo.

---

## 7. Da fare, in ordine

1. ~~L'utente registra una API key gratuita~~ ✅ fatto
2. ~~Verificare il payload reale di un match concluso~~ ✅ fatto — vedi sezione 8
3. Decidere lo scope dei mercati sulla base di quel verdetto ← **siamo qui**

---

## 8. VERDETTO DEFINITIVO — payload reale verificato con API key

Verificato il 2026-08-08 su `GET /v4/matches/503422` (Venezia–Juventus 2-3, Serie A 2024) e sulle liste stagionali.

### Cosa il piano gratuito dà davvero

| Campo | Contenuto |
|---|---|
| `score` | **Risultato finale e primo tempo** (`fullTime`, `halfTime`, `winner`, `duration`) |
| `homeTeam` / `awayTeam` | `id`, `name`, `shortName`, `tla`, **`crest`** (URL del logo) |
| `referees` | Nome e nazionalità dell'arbitro |
| `venue` | Stadio |
| `matchday`, `stage`, `group` | Contesto della competizione |
| `utcDate`, `status` | Data e stato |

Due bonus non previsti: i **loghi delle squadre** arrivano gratis (niente da procurare per la UI) e c'è il **punteggio del primo tempo**, che apre i mercati sul primo tempo e l'HT/FT.

### Cosa NON c'è

| Assente | Conseguenza |
|---|---|
| `odds` | Risponde `"Activate Odds-Package in User-Panel"` → **componente a pagamento**. Niente confronto col mercato, quindi niente value bet in senso stretto. |
| `statistics` | Nessun tiro, corner, possesso, fallo. |
| `goals` / eventi | Nessun marcatore, nessun minuto del gol. |
| `bookings` | Nessun cartellino. Abbiamo l'identità dell'arbitro ma nessun conteggio da modellare. |
| `lineups` | Nessuna formazione. |

### Profondità storica

| Stagione | Esito |
|---|---|
| 2025 | ✅ 380 partite |
| 2024 | ✅ 380 partite |
| 2022, 2020, 2018 | ❌ 403 |

**Solo le ultime due stagioni.** Circa **760 partite per campionato**, che è sufficiente per un Dixon-Coles con decadimento temporale — quel modello pesa comunque poco le partite lontane. Non è invece sufficiente per modelli che richiedono molti anni.

### Tabella finale dei mercati

| Mercato | Alimentabile gratis? |
|---|---|
| 1X2 | ✅ Sì |
| Over/Under (ogni linea) | ✅ Sì |
| BTTS | ✅ Sì |
| Handicap europeo e asiatico | ✅ Sì |
| Multigol | ✅ Sì |
| Combo (1+Over 2.5 ecc.) | ✅ Sì |
| Risultato esatto | ✅ Sì |
| Gol casa / gol ospite | ✅ Sì |
| Doppia chance | ✅ Sì |
| **Over/Under primo tempo** | ✅ Sì (bonus) |
| **HT/FT** | ✅ Sì (bonus) |
| Marcatori | ❌ No |
| Cartellini | ❌ No |
| Corner | ❌ No |
| Tiri | ❌ No |
| Value bet vs bookmaker | ❌ No (quote a pagamento) |

**Undici mercati** da un'unica fonte gratuita, legale e stabile, tutti derivati coerentemente dalla stessa matrice dei gol. Quattro mercati richiesti restano fuori, più il confronto con le quote.

### Opzioni per recuperare ciò che manca

- **Corner / cartellini / tiri** → serve una seconda fonte via scraping (FBref, Sofascore). Sblocca i mercati ma introduce fragilità e una zona grigia rispetto ai ToS.
- **Quote** → the-odds-api ha un piano gratuito (nell'ordine di 500 richieste/mese, da verificare). Con quello il confronto col mercato torna possibile, entro un budget di chiamate stretto.

---

## API-Football, verificata il 13 agosto 2026 — non utilizzabile

Cercata per riempire l'unico buco rimasto nella colonna «il mercato» della
tavola dei pronostici: **gol di squadra** (45 righe su 101), **handicap
europeo** (19) e **combo** (3). Sofascore quelle non le quota, e derivarle dal
nostro modello sarebbe metterci il nostro numero travestito da mercato.

**Il catalogo ha esattamente quello che serve.** Su 338 tipi di scommessa
dichiarati, e su una partita reale letta per intero — 59 mercati da 13
operatori:

| id | nome | copre |
|---|---|---|
| 16 | Total - Home | `hg_over_*`, `hg_under_*` |
| 17 | Total - Away | `ag_over_*`, `ag_under_*` |
| 9 | Handicap Result | handicap europeo a tre esiti |
| 25 | Result/Total Goals | le combo esito + over/under |
| 12 | Double Chance | doppia chance |

Copertura misurata su 30 partite quotate: `Total - Home` e `Total - Away` su
27, `Handicap Result` su 29, `Result/Total Goals` su 26.

**E non ne possiamo usare niente.** Il piano gratuito ha due limiti che si
moltiplicano:

1. **Finestra di tre giorni sulle date.** Il 13 agosto la risposta e' testuale:
   `Free plans do not have access to this date, try from 2026-08-12 to
   2026-08-14`.
2. **Stagioni dal 2022 al 2024 sulle nostre competizioni.** Interrogando
   direttamente Eredivisie (88), Primeira Liga (94), Championship (40), Liga
   (140) e Brasileirao (71) per il 14 agosto, tutte e cinque rispondono
   `Free plans do not have access to this season, try from 2022 to 2024`.

Il secondo limite e' quello che chiude la porta: le quote della stagione in
corso, sul piano gratuito, esistono solo per un insieme di campionati minori.
Lette TUTTE le pagine del 14 agosto — 30 partite in 20 campionati, dalla
Division 2 svedese alla Super League uzbeka — **nessuna delle nostre**.

Quindi non e' un problema di budget di chiamate (4 su 100 usate per accertarlo)
ne' di mappatura: e' il catalogo di campionati del piano. Le due cose che
servirebbero — la stagione in corso sui campionati veri — sono entrambe a
pagamento, e sono lo stesso muro visto da due lati.

**Conseguenza:** quelle 67 righe restano senza quota di mercato finche' non
compare una fonte gratuita che quoti i gol di squadra. La tavola lo dice invece
di lasciare trattini muti.
