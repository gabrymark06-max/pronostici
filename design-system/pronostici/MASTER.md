# Design System Master — Pronostici

> **LOGICA:** quando costruisci una pagina, guarda prima `pages/<nome>.md`.
> Se esiste, le sue regole **sovrascrivono** questo file. Altrimenti vale solo questo.
> I token vivono in [`tokens.css`](./tokens.css) — è quello che il frontend importa.

**Progetto:** Pronostici — web app gratuita di pronostici calcistici
**Generato:** 2026-08-08 · rigenerato a mano sopra l'output di `ui-ux-pro-max --design-system`
**Stack:** Next.js App Router in **export statico** (`output: 'export'`), nessun runtime.
**Lingua:** italiano, una sola.

---

## 0. Da dove viene questo sistema, e cosa ho scavalcato

Il database `ui-ux-pro-max` ha prodotto la base. Tre risultati li ho tenuti, quattro li ho scavalcati
con motivo — perché scavalcarli in silenzio significherebbe che il prossimo agente li rimette.

| Voce | Output del database | Decisione | Motivo |
|---|---|---|---|
| Stile | **Editorial Grid / Magazine** (WCAG AAA, performance eccellente) | **TENUTO** | È esattamente la posa di Understat che il brief chiede: griglia editoriale, tipografia da stampa, densità bassa. |
| Font display | **Newsreader** | **TENUTO** | Variabile, pensato per la lettura lunga, cifre lining di buon disegno. |
| Palette base | Editorial black `#18181B` su `#FAFAFA` | **TENUTO come impianto**, ricalibrato su carta calda | Il neutro freddo di Zinc legge come dashboard SaaS. Serve carta. |
| Font testo | **Roboto** | **SCAVALCATO → Public Sans** | Roboto è il grottesco di default che `CLAUDE.md` vieta per spirito (voce "Inter a tre dimensioni"). Public Sans è nello stesso database (coppia *Magazine Style*), registro istituzionale, e regge il tono "atto pubblico" che il prodotto rivendica. |
| Accento | `#EC4899` rosa | **SCAVALCATO → carminio `#8E1F3D`** | Il rosa del database fallisce il contrasto (3.4:1 su `#FAFAFA`). Il carminio da stampa tiene 7.71:1, resta lontanissimo dal verde-scommessa, ed è credibile in un bollettino italiano. |
| Pattern di pagina | **Real-Time / Operations Landing** (hero + metriche + CTA "Start trial") | **SCARTATO** | È un pattern di landing per prodotti in vendita. Qui non c'è niente da vendere, niente trial, nessuna CTA. La home è una lista di partite. |
| Movimento | GSAP **Scroll Reveal** | **SCARTATO** | Il database stesso avverte: *"Don't reveal below-the-fold content needed for SEO/crawlers as invisible-by-default"*. Qui **tutto** il contenuto è quello. Nessun GSAP, nessuna libreria di motion. |
| Componenti | card con `border-radius: 12px`, `box-shadow`, `translateY(-2px)` in hover | **SCARTATO** | Raggio uniforme e ombre sono le due voci che `CLAUDE.md` vieta per default. Qui l'elevazione è un filetto. |

Ricerche di supporto eseguite: `--domain ux` (accessibilità, feedback/stati vuoti),
`--domain color`, `--domain typography`, `--domain google-fonts`, `--domain chart`
(banda di confidenza), `--domain product`, `--stack nextjs`.

---

## 1. Il prodotto in una riga, e la direzione

**Tipo e pubblico.** Bollettino statistico a lettura pubblica: tifoso italiano adulto che alle 19
di sera vuole sapere *cosa si può ragionevolmente dire* sulla partita di stasera — e che è già stato
deluso dai siti di pronostici. Non è un prodotto da scommessa; non c'è login, non c'è denaro, non c'è fretta.

> **Direzione dichiarata: "referto meteorologico composto come un quotidiano di analisi".**
> La severità di un bollettino ufficiale — numeri con la loro definizione operativa accanto, il
> silenzio dichiarato e contato — nel ritmo tipografico di una pagina stampata: filetti, non ombre;
> carta calda, non grigio da dashboard; serif con autorità, non grottesco neutro.

**Chiaro o scuro.** Il tema **chiaro (carta calda) è il default**, per decisione di progetto: il
buio con accenti fluorescenti è l'estetica dei siti di scommesse, e la distanza da quella estetica è
un argomento di prodotto, non di gusto. Il tema scuro esiste completo (uso serale reale) ed è
verificato separatamente, mai dedotto dal chiaro.

**Elemento firma — la riga di definizione operativa.** Sotto **ogni** numero del prodotto, senza
eccezioni, in mono piccolo con un filetto verticale a sinistra: *"Su 100 partite come questa, in 72
esce «X2»."* Non è un tooltip, non è un asterisco, non è opzionale. È l'elemento che ricorre su ogni
schermata e trasforma una percentuale opaca in un'affermazione falsificabile. Classe `.definizione`.

---

## 2. Il problema centrale: due grandezze, due linguaggi visivi

Questo è il capitolo che nessun concorrente ha risolto e la ragione per cui questo file esiste.
**Probabilità** e **affidabilità** non condividono nessuna proprietà grafica. Non due tinte della
stessa scala: **due linguaggi**, distinti per *forma* e *peso*, non per colore — perché il colore da
solo non può mai portare significato.

| | **A — PROBABILITÀ** (quanto è probabile l'esito) | **B — AFFIDABILITÀ** (quanto ci fidiamo della stima) |
|---|---|---|
| Marca grafica | **pieno** — barra continua riempita | **tratto** — parentesi, tacche, contorno. Mai un pieno. |
| Forma | rettangolo orizzontale a piena larghezza | parentesi `├───┤` con serif alle estremità |
| Numero | cifra grande in Newsreader 600 | **nessuna cifra grande**: la banda è in parole nella riga di definizione |
| Colore | `--prob-fill` (inchiostro) su `--prob-track` | `--rel-stroke` (ardesia), solo come tratto |
| Tipo | display serif | mono, e glifi matematici (`≈` `±` `<`) |
| Bordo | raggio 0, spigoli vivi | il chip di provenienza è **l'unico elemento arrotondato del prodotto** |
| Ridondanza testuale | "72 su 100" | "fra 67 e 86" + "stima stabile / incerta" + badge di provenienza a parole |

**Conseguenza operativa:** se disattivi tutti i colori della pagina, i due sistemi restano
distinguibili — pieno contro tratto, cifra contro parentesi, spigolo contro pillola. È il test da
eseguire su ogni componente nuovo.

**Le tre componenti di affidabilità, tutte e tre visibili:**

1. **La banda p5–p95** — parentesi in tratto ardesia, disegnata **sullo stesso asse** della barra di
   probabilità (così sono confrontabili) ma con una marca che non si confonde mai col riempimento.
   Larghezza della banda `w = band_p95 − band_p5`, qualificata anche a parole:
   `w ≤ 0.08` → "stima stretta" · `0.08 < w ≤ 0.16` → "stima media" · `w > 0.16` → "stima larga".
2. **Il badge di provenienza** — chip a pillola, l'unico raggio del sistema, in due stati che devono
   essere distinguibili **a colpo d'occhio e senza colore**:

   | `source` | Resa | Testo |
   |---|---|---|
   | `blended_with_odds` | chip **pieno**: fondo `--rel-stroke`, testo `--paper`, bordo continuo | **"confrontato con le quote"** |
   | `model_only` | chip **vuoto**: fondo trasparente, bordo **tratteggiato** 1.5px `--rel-stroke`, testo `--rel-stroke` | **"solo modello statistico"** |

   Pieno contro tratteggiato: la differenza sopravvive a monocromia, a daltonismo e a stampa.
   Il testo è sempre presente — mai un pallino, mai solo un'icona.
3. **La qualifica in parole** nella riga di definizione, che è l'unico posto dove la banda diventa
   leggibile a chi non guarda grafica: *"Fra 67 e 86 su 100 nelle nostre simulazioni."*

**Mai:** `sigma` grezza, `shrink_alpha`, `score`, `p_raw`, `reference` mostrati come numeri
all'utente. Sono diagnostica. `p_raw` in particolare è **vietato** dal brief.

---

## 3. Token

I valori canonici stanno in [`tokens.css`](./tokens.css). Qui il perché.

### 3.1 Colore — tre ruoli che non si sovrappongono mai

| Token | Chiaro | Scuro | Ruolo — e dove è **vietato** |
|---|---|---|---|
| `--paper` | `#F4F1EA` | `#14130F` | fondo pagina |
| `--paper-alt` | `#EAE6DC` | `#1B1915` | tinta "documento diverso": sezione backtest, blocco revisione |
| `--ink` | `#171614` | `#EFEBE2` | testo primario |
| `--ink-2` | `#4C473D` | `#C0BAAC` | testo secondario, etichette |
| `--ink-muted` | `#6B6558` | `#9A9386` | riga di definizione, `n=`, date |
| `--rule-hair` / `--rule-heavy` / `--rule-accent` | `#6B6558` / `#171614` / `#8E1F3D` | `#9A9386` / `#EFEBE2` / `#F08CA4` | filetti: 1px / 2px / 2px |
| `--prob-fill` / `--prob-track` | `#171614` / `#CFC7B4` | `#EFEBE2` / `#46413A` | **linguaggio A.** Vietato usarlo per affidabilità. |
| `--rel-stroke` | `#35566F` | `#9DC0E0` | **linguaggio B.** Vietato usarlo come riempimento di barra. |
| `--accent` | `#8E1F3D` | `#F08CA4` | nav attiva, link, filetto di testata, il numero dei silenzi del giorno. **Vietato su qualunque dato.** |
| `--outcome-yes` / `--outcome-no` | `#2C5E3F` / `#8A2C2C` | `#7FBF95` / `#E58E8E` | esito a partita conclusa, **sempre** accompagnato da parola + glifo |
| `--warn` | `#6B4E00` | `#D6B25E` | esclusivamente lo stato "dati non leggibili" |

Il carminio è l'accento editoriale: navigazione, link, filetti. **Non tocca mai un numero di
modello.** L'unica cifra che il carminio ha il permesso di toccare è il conteggio dei silenzi del
giorno — perché quello non è una stima, è una rivendicazione.

Niente verde acido. Niente gradienti. Niente `backdrop-filter`. Niente viola→blu.

### 3.2 Tipografia — tre famiglie con ruoli disgiunti

Importate con `next/font/google` (self-hosted, zero layout shift, compatibile con export statico).
Mai `<link>` a fonts.googleapis.com.

```ts
// app/layout.tsx
import { Newsreader, Public_Sans, Red_Hat_Mono } from 'next/font/google';

const newsreader  = Newsreader({ subsets: ['latin'], display: 'swap',
                                 weight: ['400','500','600'], style: ['normal','italic'],
                                 variable: '--font-newsreader' });
const publicSans  = Public_Sans({ subsets: ['latin'], display: 'swap',
                                 weight: ['400','500','600'], variable: '--font-public-sans' });
const redHatMono  = Red_Hat_Mono({ subsets: ['latin'], display: 'swap',
                                 weight: ['400','500'], variable: '--font-red-hat-mono' });
```

| Famiglia | Ruolo esclusivo |
|---|---|
| **Newsreader** (serif) | titoli di pagina, il nome del pronostico, **la cifra grande**, il messaggio di silenzio, il testo delle transizioni (in corsivo). |
| **Public Sans** (sans) | corpo, UI, righe di lista, tabelle testuali. |
| **Red Hat Mono** (mono) | etichette maiuscolette, riga di definizione, `n=`, date, chiavi di mercato, cifre delle tabelle, glifi matematici. |

**Scala — contrasto vero, non tre dimensioni della stessa cosa.** Rapporto display-xl / body = 3.3×.

| Token | px | Famiglia / peso | Uso |
|---|---|---|---|
| `--fs-display-xl` | 44→56 | Newsreader 600, `--lh-tight` | la probabilità: `72` |
| `--fs-display-l` | 28→34 | Newsreader 600, `--lh-title` | titolo di pagina, nome del mercato consigliato |
| `--fs-h2` | 24 | Newsreader 500 | il messaggio di silenzio, titoli di sezione |
| `--fs-h3` | 19 | Public Sans 600 · Newsreader 400 *italic* nelle transizioni | sottotitoli |
| `--fs-body` | 17 | Public Sans 400, `--lh-body` | corpo |
| `--fs-body-s` | 15 | Public Sans 400 | righe di lista, note |
| `--fs-label` | 13 | Red Hat Mono 500, `+0.06em`, maiuscolo | etichette, riga di definizione |
| `--fs-micro` | 12 | Red Hat Mono 400 | `n=`, timestamp. **Pavimento assoluto: mai sotto 12px.** |

Su `/come-funziona` il corpo passa a **Newsreader 19/1.7**: quella pagina è un articolo, le altre
sono un bollettino. È densità deliberata, non incoerenza.

Tutte le cifre: `font-variant-numeric: tabular-nums lining-nums`. Le colonne di numeri non ballano.

### 3.3 Spazio, raggi, ombre, movimento

- **Spazio**: 4/8/12/16/24/32/48/64/96. Densità deliberata: la riga-partita stringe (`--s-3`
  verticale, 48px minimi), l'eroe della scheda respira (`--s-7`/`--s-8`). Padding uniforme = incompiuto.
- **Raggi**: `0` ovunque. **Unica eccezione dell'intero prodotto**: `--radius-chip: 999px` sul badge
  di provenienza. Essendo l'unica cosa arrotondata della pagina, il chip si stacca da solo — ed è
  proprio l'elemento che deve appartenere a un sistema visivo diverso (§2).
- **Ombre: nessuna.** `--shadow: none`. L'elevazione è un filetto: 1px `--rule-hair` per i divisori
  interni, 2px `--rule-heavy` per i confini di sezione, 2px `--rule-accent` per la testata di card.
  Un bollettino non ha ombre.
- **Movimento**: `--dur-1: 120ms` (focus, sottolineatura nav), `--dur-2: 180ms` (tinta di hover,
  chip), `--dur-3: 260ms` (apertura di "altre famiglie di mercato"). Solo `transform` e `opacity`.
  Nessuna animazione di ingresso, nessun reveal allo scroll, nessuno skeleton, nessuna libreria di
  motion. `prefers-reduced-motion` porta tutto a 1ms.

### 3.4 Contrasti verificati

Calcolati, non stimati. Su `--paper` chiaro: ink 16.03 · ink-2 8.18 · ink-muted 5.13 · accent 7.71 ·
rel-stroke 6.86 · outcome-yes 6.70 · outcome-no 7.51 · warn 6.86.
Su `--paper` scuro: ink 15.62 · ink-2 9.61 · ink-muted 6.10 · accent 7.96 · rel-stroke 9.78 ·
outcome-yes 8.66 · outcome-no 7.60 · warn 9.20. **Tutti ≥ 4.5:1 in entrambi i temi.**
Riempimento contro traccia della barra: 10.75:1 chiaro, 8.50:1 scuro.
L'estensione della barra è definita da una linea di base 1px `--prob-baseline` (5.13:1), perché la
traccia da sola non raggiungerebbe 3:1 contro la carta.

---

## 4. Layout e navigazione

**Larghezze.** `--w-page: 1120px` massimo. **Colonna singola, sempre. Nessuna colonna laterale, mai
— nemmeno vuota.** Una colonna da 300px è la forma di uno slot pubblicitario: il layout non deve
avere il posto dove metterla, così nessuno potrà mai tentare. Prosa `68ch`, scheda partita `720px`,
lista `880px`.

**Breakpoint**: 375 / 768 / 1024 / 1440. Mobile-first. Nessuno scroll orizzontale di pagina; le
tabelle larghe scorrono dentro il proprio contenitore `overflow-x: auto`.

**Navigazione — tre destinazioni, sempre visibili, nessun hamburger.**

```
─────────────────────────────────────────────────────────  ← 2px --rule-accent
PRONOSTICI                                       [tema ☾]
OGGI    COME STIAMO ANDANDO    COME FUNZIONA
─────────────────────────────────────────────────────────  ← 1px --rule-hair
```

Voci in Red Hat Mono 13 maiuscolo `+0.06em`: a 375px le tre entrano in 343px senza abbreviare.
Nessun menu a scomparsa a nessuna larghezza — tre voci non si nascondono. Voce attiva:
sottolineatura 2px `--accent` + `aria-current="page"` (mai solo colore). Bersagli 44×44.

**Rotte** (tutte pre-renderizzate, deep-linking obbligatorio):

| Rotta | Contenuto | Sorgente |
|---|---|---|
| `/` | redirect statico al giorno più recente disponibile | — |
| `/giorno/[data]` | lista partite di quel giorno | `data/fixtures/{data}.json` |
| `/partita/[match_id]` | scheda partita | la `fixture` dentro il file del giorno |
| `/come-stiamo-andando` | registro dal vivo + backtest | `accuracy.json` + `backtest.json` |
| `/come-funziona` | criterio, parametri, protocollo | `backtest.json.parameters`, `odds_budget.json` |

Le frecce ieri/domani sono `<a href>` verso `/giorno/{data±1}`: funzionano senza JavaScript,
sono condivisibili, e il back del browser fa la cosa giusta senza codice.

---

## 5. Lo stato di silenzio — progettato per primo

Il 26% delle partite non ha un pronostico. Quel silenzio è la funzionalità. Deve leggersi come
**severità**, non come guasto — e la differenza sta tutta in tre regole strutturali.

### 5.1 Le tre regole non negoziabili

1. **Stesso contenitore.** Il blocco di silenzio ha lo **stesso filetto di testata (2px
   `--rule-accent`), la stessa larghezza, lo stesso padding, lo stesso colore di testo** del blocco
   di pronostico. Mai più chiaro, mai tratteggiato, mai grigio, mai centrato con un'illustrazione.
2. **Il messaggio occupa lo slot della cifra.** Dove ci sarebbe `72` a 56px, c'è la frase a
   `--fs-h2` (24px) in Newsreader 500. **La massa visiva è conservata.** È la regola che, da sola,
   impedisce al silenzio di sembrare un vuoto.
3. **Si mostra il lavoro fatto.** *"Abbiamo esaminato {diagnostics.n_candidates} mercati su questa
   partita. Nessuno passa il nostro criterio."* — il dato c'è (`n_candidates: 98`). È la frase che
   converte un'assenza in uno sforzo, ed è la ragione per cui il silenzio non legge come "rotto".

**Vietato nello stato di silenzio:** icona di avviso o triangolo, bordo tratteggiato del
contenitore, testo in `--ink-muted`, sfondo grigio, skeleton o shimmer, la parola "errore",
"nessun dato", "non disponibile", "N/D", e qualunque illustrazione da empty state.

### 5.2 Anatomia

```
──────────────────────────────────────────────────  2px --rule-accent
NESSUN PRONOSTICO                              ≈    ← .label  |  glifo mono 20px --rel-stroke
                                    NON DISTINGUIBILE          ← .label --rel-stroke
                                                    (~s-7 di respiro)
Il nostro modello dice quasi esattamente
quello che dicono già le quote.                     ← Newsreader 500, --fs-h2, --ink
                                                       occupa lo slot della cifra
Abbiamo esaminato 98 mercati su questa partita.     ← Public Sans, --fs-body-s, --ink-2
Nessuno passa il nostro criterio.

[ chip: confrontato con le quote ]                  ← stesso chip del pronostico
──────────────────────────────────────────────────  1px --rule-hair
LE PROBABILITÀ, SENZA CONSIGLIO                     ← .label
1  22      X  25      2  52      Over 2.5  46       ← Red Hat Mono, tabellare, --ink
──────────────────────────────────────────────────  1px --rule-hair
Perché a volte non diciamo niente →                 ← link --accent a /come-funziona#silenzio
```

Le probabilità grezze si mostrano **come numeri nudi, senza barra**. La barra è il linguaggio del
"questo lo consigliamo": darla a numeri che non consigliamo inviterebbe l'occhio a scegliere la più
alta, cioè a ricostruire l'argmax che abbiamo tolto di mezzo apposta.

### 5.3 Le tre varianti — cambia solo il testo, mai la cornice

Il glifo matematico distingue i tre motivi **senza colore e senza icona**: è un segno tipografico,
e un segno matematico dice "misurato", non "guasto".

| `silence.reason` | Glifo | Etichetta mono | Titolo (fallback se `reasons[0]` manca) | Sottotitolo |
|---|---|---|---|---|
| `S_min`, `model_weight = 1.0` | `≈` | NON DISTINGUIBILE | "Il nostro modello dice quasi esattamente quello che dice già la media del campionato." | "Abbiamo esaminato {n} mercati su questa partita. Nessuno si discosta abbastanza." |
| `S_min`, `model_weight = 0.35` | `≈` | NON DISTINGUIBILE | "Il nostro modello dice quasi esattamente quello che dicono già le quote." | idem, + "Il confronto è stato fatto con le quote." |
| `sigma_max` | `±` | STIMA INSTABILE | "Abbiamo troppe poche partite affidabili su {squadra} per dare un numero in cui crediamo." | "La stessa stima oscilla troppo da una simulazione all'altra." |
| `p_min` | `<` | TROPPO IMPROBABILE | "Quello che vediamo di diverso è troppo improbabile perché ve lo consigliamo." | "Il mercato che si discosta di più ha meno di 50 probabilità su 100 di uscire." |
| `no_candidates` | `≈` | — | tratta come `S_min` (regola di `schema.md`) | |

**Regola per il frontend:** `reasons[0]` è già italiano pronto e va usato come titolo quando c'è.
La tabella sopra è il fallback, e resta l'unica fonte per glifo ed etichetta.
*Nota per `backend-python`:* il testo `sigma_max` richiede il nome della squadra interpolato lato
backend dentro `reasons[0]` — il frontend non ha modo di sapere quale delle due squadre ha morso.

### 5.4 La riga di silenzio nella lista

Stessa altezza, stesso peso di una riga con pronostico. La differenza è **di forma, non di tinta**:

```
[crest] 20:45  Bologna — Lazio        nessun pronostico  ≈   ← Newsreader 17 CORSIVO, --ink
[crest] 18:00  Inter — Monza          12 (nessun pareggio)  90  ├──┤  [chip]
```

Corsivo serif contro tondo + cifra: distinguibile a colpo d'occhio, in monocromia, e in stampa.
Il testo resta `--ink` pieno: attenuarlo sarebbe dire che quella riga vale meno.

### 5.5 Il conteggio del giorno, in testa alla lista

```
SABATO 22 AGOSTO                          ← --fs-display-l, Newsreader 600
Oggi taciamo su 3 partite su 14.          ← --fs-body, --ink (NON attenuato)
                                             le cifre in Newsreader 600, colore --accent
| Tacere è una risposta: la diamo quando nessun mercato   ← .definizione
| supera il nostro criterio. Perché →
```

La riga c'è **sempre**, anche a zero: *"Oggi abbiamo un pronostico per tutte e 14 le partite."*
È il rituale del prodotto — un sito che conta i propri silenzi in prima pagina sembra severo.

**Valvola del 40%** (brief §8.2): se `silence_count / total > 0.40`, compare sotto una nota con
filetto sinistro 3px `--rule-accent` su `--paper-alt`, **non** un banner d'allarme:
> *"Oggi è una giornata insolita: taciamo su più di quattro partite su dieci. Non abbassiamo la
> soglia per riempire la pagina — spieghiamo perché."* → link.

---

## 6. Le due verità: la revisione delle 36 ore

Le quattro transizioni sono, per il brief §7.3, **le schermate che guadagnano più fiducia
dell'intero prodotto**. Trattamento: il **blocco di rettifica**, che riprende una convenzione che
i lettori già conoscono — l'errata corrige di un giornale, che è storicamente un dispositivo di
fiducia, non di imbarazzo.

**Resa:** fondo `--paper-alt`, filetto sinistro 3px `--rule-accent`, testo in **Newsreader 19
corsivo**, etichetta mono sopra. Nessuna animazione all'apertura.

**Posizione — questa è la regola che impedisce di nasconderle:**

| `transition` | Dove | Etichetta mono |
|---|---|---|
| `changed` | **sopra la piega**, subito sotto il pronostico | REVISIONE DELLE 36 ORE — CAMBIATO |
| `prediction_to_silence` | **sopra la piega**, subito sotto il blocco di silenzio | REVISIONE DELLE 36 ORE — RITIRATO |
| `silence_to_prediction` | **sopra la piega**, subito sotto il pronostico | REVISIONE DELLE 36 ORE — NUOVO |
| `confirmed` | sotto la riga di fascia storica | REVISIONE DELLE 36 ORE — CONFERMATO |
| `still_silent` | sotto le probabilità grezze | REVISIONE DELLE 36 ORE — ANCORA NIENTE |
| `first` | nessun blocco | — |

**Testi:**

- `confirmed` — *"Le quote sono arrivate e confermano quello che dicevamo. Il pronostico non cambia."*
- `changed` — *"Fino al {previous.written_at} dicevamo **{previous.market_label}** ({previous.p} su
  100). Con l'arrivo delle quote la nostra stima è cambiata: ora diciamo **{label}** ({p} su 100)."*
- `prediction_to_silence` — *"Fino al {previous.written_at} dicevamo **{previous.market_label}**. Le
  quote dicono più o meno quello che dicevamo noi: **ritiriamo il pronostico**. Su questa partita
  non abbiamo un vantaggio da raccontare."*
- `silence_to_prediction` — *"Fino al {previous.written_at} non avevamo niente da dire su questa
  partita. Con l'arrivo delle quote è emerso qualcosa: **{label}**, {p} su 100."*
- `still_silent` — *"Anche con le quote non abbiamo niente da aggiungere su questa partita."*

**Il confronto prima/ora — mai barrato.** Il barrato dice "sbagliato"; qui non c'è niente di
sbagliato, ci sono due stime datate. Due righe impilate, allineate sulla stessa colonna:

```
PRIMA   (solo modello, 21 ago)   Over 2.5      68 su 100     ← corsivo, --ink-2, chip tratteggiato
  ↓                                                             (glifo mono, non un'icona)
ORA     (con le quote, 22 ago)   Over 1.5      74 su 100     ← tondo, --ink pieno, chip pieno
```

**Nella lista del giorno**, le tre transizioni che cambiano stato portano un tag mono accanto al
mercato: `RIVISTO` · `RITIRATO` · `NUOVO`. E, quando ce n'è almeno una, l'intestazione del giorno
aggiunge una riga calcolata dal file stesso: *"Oggi abbiamo rivisto 3 pronostici e ne abbiamo
ritirato 1."*

---

## 7. Componenti di sistema

### 7.1 `<BarraProbabilita p bandP5 bandP95 label />` — la composizione Metaculus

```
 72  su 100                                        ← Newsreader 600 56px + Public Sans 19 --ink-2
┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐
│██████████████░░│░░│░░│░░│░░│                     ← riempimento continuo; 9 tacche 1px ai decili
└──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘                       tacca del 50 più marcata (è il nostro p_min)
──────────────────────────────                     ← linea di base 1px --prob-baseline
        ├───────────┤                              ← banda p5–p95, TRATTO 1.5px --rel-stroke
              │                                       tacca centrale su p
| Su 100 partite come questa, in 72 esce «X2».     ← .definizione — SEMPRE
| Fra 67 e 86 su 100 nelle nostre simulazioni.
```

- Barra: larghezza piena della card, alta 12px (10px < 768px), raggio 0.
- Il riempimento è **continuo**, le tacche ai decili gli passano sopra: nessun arrotondamento
  a segmenti, quindi nessuna bugia di quantizzazione. Le tacche fanno da righello.
- La tacca del 50 è più marcata: mostrare dov'è il pavimento `p_min` è già un argomento.
- Banda: solo tratto, con serif alle estremità. **Mai riempita, mai colorata di una tinta della
  scala di probabilità.**
- Accessibilità: il gruppo barra+banda è `role="img"` con
  `aria-label="72 su 100. Banda di incertezza fra 67 e 86 su 100."` La riga di definizione è testo
  reale nel DOM, quindi l'informazione esiste anche senza il grafico.

### 7.2 `<ChipProvenienza source />`

Pillola, 32px di altezza, `--fs-label`, testo sempre presente. Pieno = `blended_with_odds`,
tratteggiato = `model_only` (§2). Non è interattivo: nessun hover, nessun cursore a mano.
Se è cliccabile verso `/come-funziona#quote`, allora rispetta i 44px di bersaglio.

### 7.3 `<RigaFascia p />` — il record storico

L'unica affermazione di accuratezza che il prodotto pronuncia sulla scheda. **La fonte è dentro la
frase**, mai un asterisco (brief §9.5):

- Fascia storica: *"Su 100 pronostici in questa fascia (65–80), **nel nostro test storico** ne sono
  usciti 76."* + `n=540 · stagioni 2024-25` in mono micro.
- Appena quella fascia raggiunge `n ≥ 50` dal vivo, **automaticamente**: *"Su 100 pronostici in
  questa fascia (65–80), **fra quelli che abbiamo pubblicato** ne sono usciti 76."* + `n=214 · da set. 2026`.

Fasce: `0.50–0.65` · `0.65–0.80` · `0.80–1.00`, lette da `backtest.json.buckets` o
`accuracy.json.live.buckets`. Il passaggio è per fascia, non globale.

### 7.4 `<RigaPartita />`

```
[crest 24] 20:45  Udinese — Como        X2 (pareggio o ospite)   72  ├─┤  [chip]  ›
```

`<a>` che avvolge l'intera riga, `min-height: 48px`, divisore 1px `--rule-hair` fra le righe.
Hover: tinta di fondo `--paper-alt` in 180ms — mai `transform`, mai ombra, nessuno spostamento di
layout. Focus: outline 2px `--focus` con `outline-offset: -2px`.
A 375px la riga va su due livelli: crest+ora+squadre sopra, mercato+cifra+chip sotto. Mai troncare
il nome del mercato: è il contenuto.
Crest: `<img width height loading="lazy" alt="">` con fondo `--prob-track` come segnaposto — lo
spazio è riservato, CLS zero. **Se il crest non carica**, ripiego sul `tla` in un quadrato 24px mono
1px `--rule-hair`. Mai un'icona di immagine rotta, mai uno spazio che collassa.

### 7.5 Icone

Lucide, tratto 1.5, dimensioni `16 / 20 / 24` da token. Usate con parsimonia: chevron per le frecce
del giorno, freccia esterna per i link a GitHub, spunta per `confirmed`. **Nessuna emoji, mai,
in nessun contesto.** I glifi matematici (`≈ ± < → ▪ ▫`) sono **tipografia in Red Hat Mono**, non
icone: non vanno sostituiti con SVG. Nessuna icona nello stato di silenzio.

---

## 8. Stati: caricamento, vuoto, errore

Il sito è statico: non c'è un fetch che possa essere lento. Questo cambia i tre stati.

- **Caricamento: nessuno skeleton, in nessun punto del prodotto.** Uno skeleton grigio a forma di
  card è visivamente indistinguibile da uno stato di silenzio mal fatto, e quella confusione è
  fatale per l'unico differenziatore che abbiamo. L'HTML arriva già pieno. Le uniche risorse
  differite sono i crest, che hanno lo spazio riservato.
- **Vuoto (nessuna partita quel giorno).** Non è un silenzio e non deve somigliargli: niente
  cornice, niente filetto carminio. Testo centrato, Public Sans 17: *"Il 12 agosto non si gioca in
  nessuno dei campionati che seguiamo."* Le frecce ieri/domani restano attive e puntano al primo
  giorno con partite.
- **Errore — `schema_version` diversa da quella attesa.** Il frontend **deve fallire forte**
  (`schema.md`), non degradare. Pagina intera, `role="alert"`, filetto sinistro 3px `--warn`,
  titolo mono `DATI NON LEGGIBILI`, corpo che dice la versione attesa e quella trovata, e un link al
  repo. Nessun colore da solo: c'è il titolo, c'è il filetto, c'è il testo.
- **Errore di rete su una risorsa statica**: non esiste come stato progettato — se il CDN non
  risponde non c'è pagina. Non progettare fallback fantasma.

**Non ci sono form nel prodotto** (niente login, niente ricerca lato server). Gli unici controlli
sono i filtri del registro in `/come-stiamo-andando`: sono `<button>` con `aria-pressed`, filtrano
righe già presenti nel DOM, e funzionano su una tabella completa anche senza JavaScript.

---

## 9. Stati commerciali

**Non esistono, per decisione permanente** (`decisioni.md` #2, brief §10 "Mai"): nessun piano,
nessun limite, nessun paywall, nessun upgrade, nessun pagamento, nessun login, nessuna pubblicità,
nessun link a bookmaker in nessuna forma.

Il design ha comunque due obblighi che discendono da questa decisione:

1. **Il layout non deve avere il posto per un annuncio.** Colonna singola, nessun rail laterale,
   nessuna fascia orizzontale libera fra le sezioni, nessun contenitore di larghezza 300/336/728px.
   Se un giorno qualcuno volesse infilarci un banner, dovrebbe rifare il layout — ed è voluto.
2. **La gratuità è contenuto, non una nota legale.** In fondo a ogni pagina, in `--fs-body-s`:
   *"Gratis, senza pubblicità, senza affiliazioni. Non guadagniamo se scommetti."* + gioco
   responsabile con il link istituzionale + il link al repo pubblico. È il differenziatore più
   difendibile del prodotto (competitors §6): va detto, non nascosto in un footer di 11px.

---

## 10. Anti-pattern — cosa questo progetto non fa mai

Dall'`AVOID` del database, dallo studio, e dai vincoli del brief.

**Dal database `ui-ux-pro-max`:**
- ❌ Emoji come icone → SVG Lucide (o tipografia mono per i glifi matematici)
- ❌ `cursor: pointer` mancante sugli elementi cliccabili
- ❌ Hover che spostano il layout (`scale`, `translateY`) → solo tinta e opacità
- ❌ Testo sotto 4.5:1
- ❌ Cambi di stato istantanei (0ms) → 150–300ms
- ❌ Focus invisibile
- ❌ Contenuto nascosto dietro barre fisse; scroll orizzontale su mobile
- ❌ Significato affidato al solo colore
- ❌ Bersagli sotto 44×44px, spaziatura sotto 8px fra bersagli adiacenti
- ❌ Layout shift (CLS): ogni immagine ha `width`/`height`

**Dallo studio (`CLAUDE.md`), qui particolarmente esposti:**
- ❌ Gradiente viola→blu, glassmorphism, `backdrop-filter`
- ❌ `border-radius` uniforme su tutto (qui: 0 ovunque, tranne il chip)
- ❌ Tre feature-card equidistanti con icone generiche
- ❌ Un solo grottesco neutro a tre dimensioni

**Specifici di questo prodotto — se ne violi uno, hai rotto il prodotto, non lo stile:**
- ❌ Le parole **"value bet", "edge", ROI, rendimento, "quota consigliata", "puntata", "stake"**
- ❌ Qualunque importo da puntare, in qualunque unità
- ❌ `p_raw` (probabilità non shrinkata), `sigma`, `score`, `shrink_alpha`, `reference` mostrati
- ❌ Un'accuratezza aggregata senza la fascia di appartenenza accanto
- ❌ Numeri di `accuracy.json` e di `backtest.json` nello stesso grafico, nella stessa tabella o
  nella stessa media. Componenti separati, file separati, nessuna prop condivisa.
- ❌ Il silenzio reso come vuoto, errore, skeleton, grigio o illustrazione
- ❌ Il barrato sul pronostico precedente in una transizione
- ❌ Verde acido, urgenza, countdown, "ultimi minuti", quote in evidenza
- ❌ Punteggi in diretta o qualunque cosa che suggerisca un aggiornamento live: il sito non ha
  runtime, e fingere il contrario è una promessa che non possiamo mantenere
- ❌ Barre sulle probabilità grezze mostrate sotto un silenzio
- ❌ Tooltip come unico portatore di un'informazione necessaria (la riga di definizione è testo)

---

## 11. Lista di controllo prima della consegna

Verbatim dall'output di `ui-ux-pro-max`, più le voci che questo prodotto aggiunge.

**Dal database:**
- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile

**Aggiunte di questo progetto:**
- [ ] Tema scuro verificato **separatamente**, non dedotto dal chiaro
- [ ] Test in scala di grigi: probabilità e affidabilità restano distinguibili (pieno vs tratto)
- [ ] Lo stato di silenzio ha la stessa massa visiva di un pronostico, nelle tre varianti
- [ ] I tre motivi di silenzio si distinguono senza colore (glifo + etichetta + testo)
- [ ] Le quattro transizioni sono renderizzate, e le tre che cambiano stato stanno sopra la piega
- [ ] Ogni cifra del prodotto ha la sua riga di definizione operativa sotto
- [ ] Ogni affermazione di accuratezza porta `n` e periodo **dentro la frase**
- [ ] `accuracy.json` e `backtest.json` non si toccano in nessun componente
- [ ] Nessuna delle parole vietate compare nel bundle (`grep -ri "value bet\|edge\|ROI"`)
- [ ] `lang="it"`, skip link a `#contenuto`, tabelle con `<caption>` e `<th scope>`
- [ ] Il layout non contiene nessun contenitore di larghezza compatibile con un banner
- [ ] Il frontend fallisce forte se `schema_version ≠ 1`
- [ ] LCP < 2.5s · CLS < 0.1 · INP < 200ms su `/giorno/[data]` e `/partita/[id]`
