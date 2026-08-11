# Design System Master — Pronostici

> **LOGICA:** quando costruisci una pagina, guarda prima `pages/<nome>.md`.
> Se esiste, le sue regole **sovrascrivono** questo file. Altrimenti vale solo questo.
> I token vivono in [`tokens.css`](./tokens.css) — è quello che il frontend importa.

**Progetto:** Pronostici — web app gratuita di pronostici calcistici
**Generato:** 2026-08-08 · **rifatto nel carattere** 2026-08-08 (v2)
**Stack:** Next.js App Router in **export statico** (`output: 'export'`), nessun runtime.
**Lingua:** italiano, una sola.

---

## 0. Cosa è cambiato in v2, e cosa no

La v1 era corretta e anonima: un bollettino stampato. Il proprietario l'ha guardata e ha detto
quattro cose insieme — *spoglia e piatta*, *la tipografia non convince*, *i colori non funzionano*,
*sembra un documento, non un'app*. Aveva ragione su tutte e quattro, e le quattro erano **lo stesso
difetto**: la v1 costruiva tutta la sua struttura con **filetti da 1px su una carta uniforme**. Una
pagina fatta di sole linee sottili non ha piani, quindi non ha profondità; e un oggetto senza piani
non si comporta come un'interfaccia, si comporta come un foglio.

**La struttura è validata e si conserva integra.** Non cambia niente di:

- la gerarchia dell'informazione e l'ordine dei blocchi sopra la piega;
- i due linguaggi visivi (§2), il trattamento del silenzio (§5), i blocchi di rettifica (§6);
- cosa si mostra e cosa non si mostra mai (§10, `docs/research/selezione-pronostico.md` §9);
- l'assenza di pubblicità, login, bookmaker, paywall (§9).

**Cambia il carattere:** tipografia, colore, densità, profondità.

| Voce | v1 | v2 | Perché |
|---|---|---|---|
| Impianto | filetti 1px su carta chiara uniforme | **superfici piene su quattro piani** + spigoli duri | I filetti non fanno profondità. I piani sì, e senza una sola ombra. |
| Fondo | chiaro sempre, scuro a preferenza di sistema | **scuro di default**, chiaro solo dall'interruttore | Il chiaro caldo era la fonte principale del "sembra un documento". |
| Display | Newsreader (serif) | **Archivo variabile, asse `wdth` a 62** | Il serif *è* la voce della carta stampata. Il condensato è la voce del tabellone. |
| Testo | Public Sans | **IBM Plex Sans** | Scheletro davvero diverso dal display, corsivo vero (serve al silenzio in lista), registro tecnico-istituzionale. |
| Mono | Red Hat Mono | **IBM Plex Mono** | Sorella del testo: il livello delle etichette sembra progettato, non assemblato. |
| Accento | carminio `#8E1F3D`, usato come inchiostro | **ocra segnale, usata come superficie** | Un accento che colora testo resta un dettaglio. Un accento che riempie blocchi costruisce la pagina. |
| Elemento firma | riga di definizione (`.definizione`) | **la fascia** — il filetto da 2px diventato blocco da 6px | La definizione operativa **resta**, ma non può essere la firma: è troppo piccola per farsi vedere. Ora sono due, una forte e una fine. |
| Cifra in lista | 19px | **26→32px condensata, incolonnata** | "I numeri dominano" si misura in millimetri, non in intenzioni. |
| Elevazione | filetto | **piano + spigolo + fascia** | Nessuna ombra, nessun blur, nessun gradiente: restano vietati. |

**Rifiutato deliberatamente in v2** (le alternative facili, e perché no):

- ❌ **Il fondo scuro con accento fluorescente** (verde acido, vermiglio, ciano). È insieme
  l'estetica delle scommesse e il preset che ogni generatore produce. L'ocra è un colore da
  segnaletica e da carta sportiva, non da vincita.
- ❌ **Glassmorphism, `backdrop-filter`, ombre sfumate.** Sono l'altra faccia esatta del difetto
  della v1: profondità finta al posto di profondità nulla. Qui la profondità è **valore + spigolo**.
- ❌ **Oswald / Bebas Neue** come condensata. Oswald è la condensata di default del web; Bebas non
  ha minuscole né una vera famiglia di cifre. Archivo ha l'asse di larghezza: la condensazione
  diventa una *decisione continua*, non un font diverso.
- ❌ **Barlow Condensed + Barlow**, che è quello che il database `ui-ux-pro-max` propone alla voce
  "Sports/Fitness". È il preset da template sportivo: due tagli della stessa faccia, nessun
  contrasto di scheletro.
- ❌ **Il verde campo come colore di sistema.** Impossibile da separare dal verde dei bookmaker.
  Il verde resta solo su `--outcome-yes`, sempre con parola e glifo accanto.
- ❌ **Le card con ombra e raggio 8px.** Raggio 0 ovunque, unica eccezione il chip (§2).

---

## 1. Il prodotto in una riga, e la direzione

**Tipo e pubblico.** Bollettino statistico a lettura pubblica: tifoso italiano adulto che alle 19
di sera vuole sapere *cosa si può ragionevolmente dire* sulla partita di stasera — e che è già stato
deluso dai siti di pronostici. Non è un prodotto da scommessa; non c'è login, non c'è denaro, non c'è
fretta.

> ## Direzione dichiarata: **"tabellone da stadio composto in tipografia".**
>
> La forza di un tabellone — fondo scuro, fasce piene, condensata grande, cifre che pesano come
> oggetti — con la disciplina di una composizione tipografica: griglia rigida, spigoli vivi,
> colonne che si incolonnano, nessuna ombra e nessun ornamento. Sport nella voce, tipografia nella
> mano.

**Scuro o chiaro.** Il **tema scuro è il default del prodotto**, e non segue la preferenza di
sistema: `:root` è scuro, il chiaro si ottiene solo con l'interruttore in testata. È una decisione
di marca, non di gusto — il fondo chiaro uniforme era ciò che faceva leggere il prodotto come un
foglio A4. Mitigazione dovuta: l'interruttore è **sempre visibile in testata**, 44×44, la scelta è
persistita e applicata prima del primo paint, ed **entrambi i temi sono verificati separatamente**
(§3.4). Il chiaro non è "lo scuro invertito": lì il fondo è una greige e le lastre sono **più
chiare** del fondo, perché è l'inversione che dà profondità anche in chiaro.

**Elemento firma — la fascia.** Un blocco pieno di ocra, alto **6px**, largo quanto il suo
contenitore, con subito sotto un'etichetta mono maiuscola. Sta in cima a **ogni blocco in cui il
prodotto si espone**: il pronostico, il silenzio, la rettifica delle 36 ore, ogni testata di
sezione, il confine del backtest (lì a 12px), la pagina di errore (lì in `--warn`), la voce di
navigazione attiva e il giorno attivo (lì a 3px). È il filetto da 2px della v1 diventato superficie:
lo stesso gesto, ma visibile. Classe `.fascia`.

**Secondo elemento ricorrente — la riga di definizione operativa.** Sotto **ogni** numero del
prodotto, senza eccezioni: *"Su 100 partite come questa, in 72 esce «X2»."* Non è un tooltip, non è
un asterisco, non è opzionale. In v2 non è più appesa a un filetto: è **incassata** su `--surface-2`
con un bordo sinistro da 3px. Classe `.definizione`.

La fascia si vede da tre metri, la definizione si legge da trenta centimetri. Servono entrambe.

---

## 2. Il problema centrale: due grandezze, due linguaggi visivi

*(Invariato dalla v1. È la ragione per cui questo file esiste, e nessuna scelta estetica lo tocca.)*

**Probabilità** e **affidabilità** non condividono nessuna proprietà grafica. Non due tinte della
stessa scala: **due linguaggi**, distinti per *forma* e *peso*, non per colore — perché il colore da
solo non può mai portare significato.

| | **A — PROBABILITÀ** (quanto è probabile l'esito) | **B — AFFIDABILITÀ** (quanto ci fidiamo della stima) |
|---|---|---|
| Marca grafica | **pieno** — barra continua riempita | **tratto** — parentesi, tacche, contorno. Mai un pieno. |
| Forma | rettangolo orizzontale a piena larghezza | parentesi `├───┤` con serif alle estremità |
| Numero | cifra grande in Archivo condensata 800 | **nessuna cifra grande**: la banda è in parole nella riga di definizione |
| Colore | `--prob-fill` (inchiostro) su `--prob-track` | `--rel-stroke` (acciaio), solo come tratto |
| Tipo | display condensato | mono, e glifi matematici (`≈` `±` `<`) |
| Bordo | raggio 0, spigoli vivi | il chip di provenienza è **l'unico elemento arrotondato del prodotto** |
| Ridondanza testuale | "72 su 100" | "fra 67 e 86" + "stima stabile / incerta" + badge di provenienza a parole |

**Conseguenza operativa:** se disattivi tutti i colori della pagina, i due sistemi restano
distinguibili — pieno contro tratto, cifra contro parentesi, spigolo contro pillola. È il test da
eseguire su ogni componente nuovo.

**Le tre componenti di affidabilità, tutte e tre visibili:**

1. **La banda p5–p95** — parentesi in tratto acciaio, disegnata **sullo stesso asse** della barra di
   probabilità (così sono confrontabili) ma con una marca che non si confonde mai col riempimento.
   Larghezza della banda `w = band_p95 − band_p5`, qualificata anche a parole:
   `w ≤ 0.08` → "stima stretta" · `0.08 < w ≤ 0.16` → "stima media" · `w > 0.16` → "stima larga".
2. **Il badge di provenienza** — chip a pillola, l'unico raggio del sistema, in due stati che devono
   essere distinguibili **a colpo d'occhio e senza colore**:

   | `source` | Resa | Testo |
   |---|---|---|
   | `blended_with_odds` | chip **pieno**: fondo `--rel-stroke`, testo `--ground`, bordo continuo | **"confrontato con le quote"** |
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

### 3.1 Colore — una rampa con vera escursione, e un accento che è una superficie

Il difetto della v1 in una riga: **tre neutri e due fondi**, cioè nessuna escursione. La v2 ha
**quattro piani** più due spigoli, ed è lì che nasce la profondità.

| Token | Scuro (default) | Chiaro | Ruolo — e dove è **vietato** |
|---|---|---|---|
| `--ground` | `#0F0E0C` | `#E6E1D6` | fondo pagina. In chiaro è una **greige**, non bianco. |
| `--surface` | `#1B1917` | `#FCFBF8` | la **lastra**: lista, scheda, testata. In chiaro è *più chiara* del fondo. |
| `--surface-2` | `#282420` | `#D9D2C3` | fascia di competizione, hover di riga, incasso della definizione |
| `--surface-3` | `#35302A` | `#C9C1AE` | pressione (`:active`), segnaposto del crest. **Mai testo sopra.** |
| `--edge` | `#332F29` | `#CBC3B2` | divisorio 1px fra righe. **Tenue di proposito** (1.3–1.7:1): la struttura la fa la superficie, non il filetto. |
| `--edge-strong` | `#6F6759` | `#847C6B` | bordo dei controlli reali (filtri, interruttore). ≥3:1. |
| `--ink` | `#F4F1EA` | `#16150F` | testo primario, cifre, riempimento barra |
| `--ink-2` | `#C7C1B6` | `#4A453C` | testo secondario, etichette |
| `--ink-3` | `#A39C8F` | `#5C564B` | `n=`, timestamp. **Vietato su `--surface-3`.** |
| `--segnale` | `#E8B027` | `#94620A` | **l'unico accento.** Riempie fasce e blocchi. |
| `--segnale-ink` | `#0F0E0C` | `#FCFBF8` | il testo che sta **sopra** il segnale |
| `--prob-fill` / `--prob-track` | `#F4F1EA` / `#403A32` | `#16150F` / `#C2B9A5` | **linguaggio A.** Vietato per affidabilità. |
| `--rel-stroke` | `#93B8D6` | `#2A5370` | **linguaggio B.** Vietato come riempimento di barra. |
| `--outcome-yes` / `--outcome-no` | `#79C08F` / `#E88C8C` | `#2A6140` / `#8C2C2C` | esito a partita conclusa, **sempre** con parola + glifo |
| `--warn` | `#D9B45C` | `#6B4E00` | esclusivamente lo stato "dati non leggibili" |

**Le tre regole del segnale — sono la ragione per cui l'accento funziona:**

1. **Il segnale è una superficie, non un inchiostro.** Riempie fasce e blocchi; il testo che gli sta
   sopra è sempre `--segnale-ink`. Non colora mai il testo corrente. (Effetto collaterale
   desiderato: è impossibile romperne il contrasto.)
2. **Il segnale non tocca mai un dato di modello.** Nessuna barra di probabilità ocra, nessuna cifra
   ocra, nessuna banda ocra. Un accento sui numeri suggerirebbe "questo è buono", che è esattamente
   la bugia del settore.
3. **Un solo blocco pieno di segnale per schermata**, e va a **la rivendicazione** — il conteggio
   dei silenzi del giorno. Se il blocco pieno ce l'ha anche qualcos'altro, il segnale ha smesso di
   valere qualcosa. Tutto il resto ha la fascia da 6px, non il pieno.

**Il link.** Inchiostro pieno + sottolineatura 2px di segnale (3px in hover). Il colore non porta
mai da solo l'affordance, e il segnale resta una superficie anche qui: una fascia alta 2px.

Niente verde acido. Niente gradienti. Niente `backdrop-filter`. Niente viola→blu. Niente ombre.

### 3.2 Tipografia — tre famiglie con ruoli disgiunti

Importate con `next/font/google` (self-hosted, zero layout shift, compatibile con export statico).
Mai `<link>` a fonts.googleapis.com.

```ts
// app/layout.tsx  — sostituisce integralmente il blocco Newsreader/Public Sans/Red Hat Mono
import { Archivo, IBM_Plex_Sans, IBM_Plex_Mono } from 'next/font/google';

/* Archivo è VARIABILE: `axes: ['wdth']` sblocca l'asse di larghezza (62–125).
   Non si passa `weight` con un font variabile: l'asse wght è già incluso. */
const archivo = Archivo({
  subsets: ['latin'],
  display: 'swap',
  axes: ['wdth'],
  variable: '--font-archivo',
});

const plexSans = IBM_Plex_Sans({
  subsets: ['latin'], display: 'swap',
  weight: ['400', '600'], style: ['normal', 'italic'],
  variable: '--font-plex-sans',
});

const plexMono = IBM_Plex_Mono({
  subsets: ['latin'], display: 'swap',
  weight: ['400', '500'],
  variable: '--font-plex-mono',
});

// <html className={`${archivo.variable} ${plexSans.variable} ${plexMono.variable}`}>
```

La condensazione si applica con **`font-stretch: 62%`** (titoli lunghi: `70%`), che è la proprietà
alto livello mappata sull'asse `wdth`. Non usare `font-variation-settings` in parallelo: si
annullano. Il ripiego è `'Arial Narrow'`, che è davvero condensato — durante lo swap la larghezza
delle righe non salta.

| Famiglia | Ruolo esclusivo |
|---|---|
| **Archivo** condensata (`wdth` 62/70) | la cifra grande, la cifra di riga, i titoli di pagina e di sezione, il nome del mercato consigliato, il messaggio di silenzio. **La voce del prodotto.** |
| **IBM Plex Sans** | corpo, UI, righe di lista, prosa. Il **corsivo** è riservato a due usi e a nessun altro: il silenzio in lista e il testo delle rettifiche. |
| **IBM Plex Mono** | etichette maiuscole, riga di definizione, `n=`, date, ore, chiavi di mercato, cifre delle tabelle, glifi matematici. |

**Scala — rapporto cifra/corpo = 7.8×.** Non tre misure della stessa cosa.

| Token | px | Famiglia / peso | Uso |
|---|---|---|---|
| `--fs-cifra` | 80→132 | Archivo `wdth 62` / 800, `lh .84`, `ls -.035em` | la probabilità nella lastra: `72` |
| `--fs-cifra-riga` | 26→32 | Archivo `wdth 62` / 700 | la cifra nella riga di lista |
| `--fs-h1` | 40→56 | Archivo `wdth 70` / 700 | titolo di pagina, data del giorno, nomi delle squadre |
| `--fs-h2` | 28→34 | Archivo `wdth 70` / 700 | titoli di sezione, nome del mercato consigliato, messaggio di silenzio |
| `--fs-h3` | 22 | Archivo `wdth 70` 700 · Plex Sans 600 | sottotitoli |
| `--fs-lead` | 20 | Plex Sans 400, `lh 1.7` | sommari, e il corpo di `/come-funziona` |
| `--fs-body` | 17 | Plex Sans 400, `lh 1.55` | corpo |
| `--fs-body-s` | 15 | Plex Sans 400 | righe di lista, note |
| `--fs-label` | 13 | Plex Mono 500, `+0.08em`, maiuscolo | etichette, riga di definizione |
| `--fs-micro` | 12 | Plex Mono 400 | `n=`, timestamp. **Pavimento assoluto: mai sotto 12px.** |

**Come si compongono i numeri — è la decisione centrale della v2.**

Il prodotto ha **due registri numerici** e non devono mai mescolarsi:

- **Cifra da tabellone** — Archivo `wdth 62`, peso 800, `tabular-nums lining-nums`,
  `letter-spacing: -0.035em`, `line-height: 0.84`. È la probabilità del pronostico e la cifra della
  riga di lista. Il numero è un **oggetto**: interlinea sotto l'unità, crenatura negativa, allineato
  sulla linea di base con l'unità `su 100` in mono a 15px `--ink-2`, distanziata di 12px. L'unità
  non è mai `%` e non è mai grande.
- **Cifra da referto** — Plex Mono 400/500, tabellare, dimensione del corpo. È tutto il resto:
  tabelle, probabilità grezze, quote, `n=`, ripartizioni. Non cresce mai oltre `--fs-body`.

La cifra da tabellone è **sempre allineata a destra dentro una colonna di larghezza fissa**
(`--col-cifra: 3.5rem`), così le unità si incolonnano lungo tutta la lista e lo scorrimento verticale
diventa un confronto. È la sola cosa che si prende da `diretta.it`, ed è la più importante.

Su `/come-funziona` il corpo passa a **Plex Sans 20/1.7** su `--surface`: quella pagina è un
articolo, le altre sono un bollettino. È densità deliberata, non incoerenza.

### 3.3 Profondità, densità, raggi, movimento

**Profondità — la ricetta, e non ce ne sono altre.** Tre strumenti, in quest'ordine:

1. **Il piano.** Il contenuto sta su `--surface`, che sta su `--ground`. La differenza è di ~5 L*:
   si vede senza gridare. `--surface-2` per gli incassi (fascia di competizione, hover, riga di
   definizione), `--surface-3` per la pressione.
2. **Lo spigolo.** Le lastre non hanno bordo su tutti i lati: hanno una **fascia in cima** e basta.
   Un contenitore incorniciato su quattro lati torna a sembrare una card, e una card con bordo è
   ancora un foglio.
3. **Il taglio a piena larghezza.** Sotto i 1024px la lastra della lista, la testata e la fascia di
   competizione **escono dalla colonna e toccano i bordi dello schermo**. Il margine bianco costante
   su entrambi i lati è la firma della pagina stampata: toglierlo è metà del lavoro.

**Vietato per fare profondità:** `box-shadow` (in qualunque forma, anche 1px), `filter: blur`,
`backdrop-filter`, gradienti, bordi a 4 lati sulle lastre, `transform: translateY` in hover.

**Densità deliberata — dove stringe e dove respira.**

| Zona | Densità | Regola |
|---|---|---|
| Riga-partita | **stretta** | 52px a riga singola (≥1024px), 72px su due livelli sotto. Padding verticale 6px. Divisore 1px `--edge`. |
| Fascia di competizione | **strettissima** | 34px pieni di `--surface-2`, mono 12 maiuscolo, conteggio partite a destra. |
| Striscia dei giorni | stretta | 52px, voci 44×44 minimo. |
| Intestazione del giorno | **respira** | 40px sopra, 24px sotto; la rivendicazione staccata di 24px. |
| Lastra del pronostico | **respira molto** | padding 24 (mobile) / 32 (desktop); 48–64px fra i blocchi ①②③④. |
| Tabelle e registro | stretta | righe 44px, `--fs-body-s`, cifre mono. |
| `/come-funziona` | **respira molto** | corpo 20/1.7, 66ch, 64px fra le sezioni. |

Il contrasto di densità è ciò che dice all'occhio dove finisce il giudizio e dove comincia il
materiale. Padding uniforme = incompiuto.

**Raggi:** `0` ovunque. **Unica eccezione dell'intero prodotto**: `--radius-chip: 999px` sul badge
di provenienza. Essendo l'unica cosa arrotondata della pagina, il chip si stacca da solo — ed è
proprio l'elemento che deve appartenere a un sistema visivo diverso (§2).

**Movimento**: `--dur-1: 120ms` (focus, sottolineature), `--dur-2: 180ms` (tinta di hover, chip),
`--dur-3: 260ms` (apertura di "altre famiglie di mercato"). Solo `background-color`, `opacity`,
`text-decoration-thickness`. **Nessun `transform` che sposti il layout**, nessuna animazione di
ingresso, nessun reveal allo scroll, nessuno skeleton, nessuna libreria di motion.
`prefers-reduced-motion` porta tutto a 1ms.

L'unica abitudine di movimento del prodotto: **hover = il piano sale di un gradino**
(`--surface` → `--surface-2`), **`:active` = sale di due** (`--surface-3`). Niente altro si muove.

### 3.4 Contrasti verificati

Calcolati, non stimati: `python design-system/pronostici/contrasti.py` li ristampa tutti (formula
WCAG 2.1). **Chi tocca un hex in `tokens.css` aggiorna lo script e lo riesegue, nello stesso commit.**
Ogni valore è testo su fondo.

**Tema scuro** — su `--ground`: ink 17.10 · ink-2 10.78 · ink-3 7.08 · rel-stroke 9.25 ·
outcome-yes 8.96 · outcome-no 7.87 · warn 9.77 · segnale (come fascia) 9.80.
Su `--surface`: ink 15.54 · ink-2 9.79 · ink-3 6.44 · rel-stroke 8.40.
Su `--surface-2`: ink 13.65 · ink-2 8.60 · ink-3 5.65.
`--segnale-ink` sopra `--segnale`: **9.80**. `--edge-strong` su surface: 3.14 (controlli, ≥3 ✓).
Riempimento contro traccia della barra: **9.96**.

**Tema chiaro** — su `--ground`: ink 14.03 · ink-2 7.30 · ink-3 5.58 · rel-stroke 6.27 ·
outcome-yes 5.59 · outcome-no 6.41 · warn 5.93 · segnale (come fascia) 4.02.
Su `--surface`: ink 17.67 · ink-2 9.19 · ink-3 7.03 · rel-stroke 7.90.
Su `--surface-2`: ink 12.15 · ink-2 6.32 · ink-3 4.83.
`--segnale-ink` sopra `--segnale`: **5.06**. `--edge-strong` su surface: 4.00.
Riempimento contro traccia della barra: **9.39**.

**Tutti i testi ≥ 4.5:1 in entrambi i temi. Tutti gli elementi non testuali ≥ 3:1.**

Due regole che derivano dai numeri e vanno rispettate alla lettera:
- **`--surface-3` non porta mai testo** (in chiaro `ink-3` ci starebbe a 4.06). È un piano di
  pressione e di segnaposto.
- **Il focus dentro un blocco di segnale si inverte**: `outline-color: var(--segnale-ink)`, perché
  un contorno ocra su fondo ocra non esiste.

---

## 4. Layout e navigazione

**Larghezze.** `--w-page: 1120px` massimo. **Colonna singola, sempre. Nessuna colonna laterale, mai
— nemmeno vuota.** Una colonna da 300px è la forma di uno slot pubblicitario: il layout non deve
avere il posto dove metterla, così nessuno potrà mai tentare. Prosa `66ch`, scheda partita `760px`,
lista `940px`.

**Breakpoint**: 375 / 768 / 1024 / 1440. Mobile-first. Nessuno scroll orizzontale di pagina; le
tabelle larghe scorrono dentro il proprio contenitore `overflow-x: auto`.

**Il taglio a piena larghezza.** Sotto i 1024px, `.masthead`, `.striscia-giorni`, `.banda-competizione`
e la lastra della lista escono dalla colonna (`margin-inline: calc(50% - 50vw)` con il padding
interno riportato). Sopra i 1024px restano dentro `--w-list`. È il singolo intervento che più
allontana la pagina dall'aspetto di documento.

**Testata — 56px, appiccicata, con la fascia in cima.**

```
█████████████████████████████████████████████████████  6px --segnale (la fascia)
PRONOSTICI                                    [ CHIARO ]   ← mono +0.16em / interruttore
OGGI    COME STIAMO ANDANDO    COME FUNZIONA               ← mono 13, voce attiva su fascia 3px
─────────────────────────────────────────────────────  1px --edge
```

- `position: sticky; top: 0; z-index: 20; background: var(--surface)`.
- Quando la pagina è scorsa (`data-scrolled` su `<header>`, impostato da un listener passivo), il
  filetto inferiore passa da `--edge` a `--edge-strong`. Nessun'altra reazione, nessuna ombra.
  Senza JavaScript la testata resta perfettamente usabile: l'attributo è cosmetico.
- Voci in Plex Mono 13 maiuscolo `+0.08em`: a 375px le tre entrano in 343px senza abbreviare.
  Nessun menu a scomparsa a nessuna larghezza. Voce attiva: **fascia 3px** `--segnale` sotto la voce
  + `aria-current="page"` (mai solo colore). Bersagli 44×44.
- L'interruttore del tema è un `<button>` con **la parola** dello stato (`CHIARO` / `SCURO`), non
  un'icona sola: 44×44, bordo 1px `--edge-strong`.

**La striscia dei giorni** — è la novità strutturale della v2, e la cosa che più fa "app". Sotto la
testata, su `/giorno/[data]`: sette giorni navigabili in fila, `<a>` reali verso
`/giorno/{data}`, mono 12 maiuscolo su due righe (`SAB` / `22`), 44×44 minimo, `scroll-snap` in
orizzontale sotto i 768px, giorno corrente su `--surface-2` con **fascia 3px** sotto e
`aria-current="date"`. Non è sticky (la testata basta). I giorni senza partite non compaiono.
Sostituisce le due frecce ‹ › della v1, che restano come `<a>` agli estremi della striscia.

**Rotte** (tutte pre-renderizzate, deep-linking obbligatorio):

| Rotta | Contenuto | Sorgente |
|---|---|---|
| `/` | redirect statico al giorno più recente disponibile | — |
| `/giorno/[data]` | lista partite di quel giorno | `data/fixtures/{data}.json` |
| `/partita/[match_id]` | scheda partita | la `fixture` dentro il file del giorno |
| `/come-stiamo-andando` | registro dal vivo + backtest | `accuracy.json` + `backtest.json` |
| `/come-funziona` | criterio, parametri, protocollo | `backtest.json.parameters`, `odds_budget.json` |

Le frecce ieri/domani e le voci della striscia sono `<a href>`: funzionano senza JavaScript,
sono condivisibili, e il back del browser fa la cosa giusta senza codice.

---

## 5. Lo stato di silenzio — progettato per primo

Il ~29% delle partite non ha un pronostico. Quel silenzio è la funzionalità. Deve leggersi come
**severità**, non come guasto — e la differenza sta tutta in tre regole strutturali.

### 5.1 Le tre regole non negoziabili

1. **Stessa lastra.** Il blocco di silenzio ha **la stessa fascia da 6px, lo stesso fondo
   `--surface`, la stessa larghezza, lo stesso padding, lo stesso colore di testo** del blocco di
   pronostico. Mai più chiaro, mai tratteggiato, mai grigio, mai centrato con un'illustrazione.
   In v2 la regola diventa letterale: **è lo stesso contenitore riempito diversamente.**
2. **Il messaggio occupa lo slot della cifra.** Dove ci sarebbe `72` a 132px, c'è la frase a
   `--fs-h2` (28→34px) in **Archivo condensata 700**, non in corpo di testo. **La massa visiva è
   conservata.** È la regola che, da sola, impedisce al silenzio di sembrare un vuoto — e con la
   condensata pesa più di quanto pesasse col serif della v1.
3. **Si mostra il lavoro fatto.** *"Abbiamo esaminato {diagnostics.n_candidates} mercati su questa
   partita. Nessuno passa il nostro criterio."* — il dato c'è (`n_candidates: 98`). È la frase che
   converte un'assenza in uno sforzo, ed è la ragione per cui il silenzio non legge come "rotto".

**Vietato nello stato di silenzio:** icona di avviso o triangolo, bordo tratteggiato del
contenitore, testo in `--ink-3`, fondo diverso da `--surface`, opacità ridotta, skeleton o shimmer,
la parola "errore", "nessun dato", "non disponibile", "N/D", e qualunque illustrazione da empty
state.

### 5.2 Anatomia

```
█████████████████████████████████████████████████  6px --segnale (la stessa fascia)
NESSUN PRONOSTICO                              ≈    ← .label  |  glifo mono 24px --rel-stroke
                                    NON DISTINGUIBILE          ← .label --rel-stroke
                                                    (~48px di respiro)
Il nostro modello dice quasi esattamente
quello che dicono già le quote.                     ← Archivo wdth 70 / 700, --fs-h2, --ink
                                                       occupa lo slot della cifra
Abbiamo esaminato 98 mercati su questa partita.     ← Plex Sans, --fs-body-s, --ink-2
Nessuno passa il nostro criterio.

( confrontato con le quote )                        ← stesso chip del pronostico
─────────────────────────────────────────────────  1px --edge
LE PROBABILITÀ, SENZA CONSIGLIO                     ← .label
1  22      X  25      2  52      Over 2.5  46       ← Plex Mono, tabellare, --ink
─────────────────────────────────────────────────  1px --edge
Perché a volte non diciamo niente →                 ← link a /come-funziona#silenzio
```

Le probabilità grezze si mostrano **come numeri nudi, senza barra, in mono** — cifra da referto, non
da tabellone (§3.2). La barra è il linguaggio del "questo lo consigliamo": darla a numeri che non
consigliamo inviterebbe l'occhio a scegliere la più alta, cioè a ricostruire l'argmax che abbiamo
tolto di mezzo apposta. Per lo stesso motivo qui non entra mai la cifra condensata grande.

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

Stessa altezza, stesso peso, stessa opacità di una riga con pronostico. La differenza è **di forma,
non di tinta** — e in v2 è ancora più netta, perché il contrasto è fra una condensata da 32px e un
corsivo da 15px:

```
[crest] 20:45  Bologna — Lazio     nessun pronostico   ≈        ← Plex Sans CORSIVO 15, --ink
[crest] 18:00  Inter — Monza       12 (nessun pareggio)  90 ├─┤ ( quote )
```

Nella colonna della cifra, dove la riga di pronostico ha il numero condensato allineato a destra, la
riga di silenzio ha **il solo glifo mono a 20px** in `--rel-stroke`. La colonna non si svuota mai: se
si svuotasse, il silenzio tornerebbe a leggersi come un buco.
Il testo resta `--ink` pieno: attenuarlo sarebbe dire che quella riga vale meno.

### 5.5 Il conteggio del giorno — **la rivendicazione**

È l'**unico blocco pieno di segnale della schermata** (§3.1 regola 3).

```
SABATO 22 AGOSTO                          ← .titolo-pagina, Archivo wdth 70 / 700, 40→56

█████████████████████████████████████████  blocco pieno --segnale
█ OGGI TACIAMO SU                        █  ← .label, --segnale-ink
█ 3 partite su 14.                       █  ← le cifre in Archivo wdth 62 / 800, 34px
█████████████████████████████████████████     tutto il testo in --segnale-ink

| Tacere è una risposta: la diamo quando nessun mercato   ← .definizione, su --surface-2
| supera il nostro criterio. Perché →
```

Il blocco c'è **sempre**, anche a zero: *"Oggi abbiamo un pronostico per tutte e 14 le partite."*
È il rituale del prodotto — un sito che stampa i propri silenzi in un blocco pieno, in prima pagina,
sembra severo. È anche l'unico punto in cui il segnale tocca delle cifre, ed è concesso per la
ragione già scritta in v1: **quello non è una stima, è una rivendicazione.**

**Valvola del 40%** (brief §8.2): se `silence_count / total > 0.40`, sotto la rivendicazione compare
una nota su `--surface-2` con fascia sinistra 3px `--edge-strong` — **non** un secondo blocco di
segnale e **non** un banner d'allarme:
> *"Oggi è una giornata insolita: taciamo su più di quattro partite su dieci. Non abbassiamo la
> soglia per riempire la pagina — spieghiamo perché."* → link.

---

## 6. Le due verità: la revisione delle 36 ore

Le quattro transizioni sono, per il brief §7.3, **le schermate che guadagnano più fiducia
dell'intero prodotto**. Trattamento: il **blocco di rettifica**, che riprende una convenzione che
i lettori già conoscono — l'errata corrige di un giornale, che è storicamente un dispositivo di
fiducia, non di imbarazzo.

**Resa v2:** fondo `--surface-2`, **fascia 6px `--segnale` in cima** (come ogni blocco in cui il
prodotto si espone), etichetta mono sotto la fascia, testo in **Plex Sans 20 corsivo**. Nessuna
animazione all'apertura. Il corsivo è riservato a questo e al silenzio in lista, e a nient'altro.

**Posizione — questa è la regola che impedisce di nasconderle:**

| `transition` | Dove | Etichetta mono |
|---|---|---|
| `changed` | **sopra la piega**, subito sotto il pronostico | REVISIONE DELLE 36 ORE — CAMBIATO |
| `prediction_to_silence` | **sopra la piega**, subito sotto il blocco di silenzio | REVISIONE DELLE 36 ORE — RITIRATO |
| `silence_to_prediction` | **sopra la piega**, subito sotto il pronostico | REVISIONE DELLE 36 ORE — NUOVO |
| `confirmed` | sotto la riga di fascia storica | REVISIONE DELLE 36 ORE — CONFERMATO |
| `still_silent` | sotto le probabilità grezze | REVISIONE DELLE 36 ORE — ANCORA NIENTE |
| `first` | nessun blocco | — |

**Testi:** *(invariati dalla v1)*

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
sbagliato, ci sono due stime datate. Due righe impilate, allineate sulla stessa colonna, con le
cifre da referto (mono) e **non** da tabellone: non è il numero del giorno, è la sua storia.

```
PRIMA   (solo modello, 21 ago)   Over 2.5      68 su 100     ← corsivo, --ink-2, chip tratteggiato
  ↓                                                             (glifo mono, non un'icona)
ORA     (con le quote, 22 ago)   Over 1.5      74 su 100     ← tondo, --ink pieno, chip pieno
```

**Nella lista del giorno**, le tre transizioni che cambiano stato portano un tag accanto al mercato:
`RIVISTO` · `RITIRATO` · `NUOVO`, in mono 12 su **fondo `--surface-3`** con `--ink` — un tassello,
non un testo colorato, perché il segnale non colora testo. E, quando ce n'è almeno una,
l'intestazione del giorno aggiunge una riga calcolata dal file stesso: *"Oggi abbiamo rivisto 3
pronostici e ne abbiamo ritirato 1."*

---

## 7. Componenti di sistema

I nomi sono quelli reali in `frontend/components/`.

### 7.1 `<BarraProbabilita p bandP5 bandP95 label />` — la composizione a tabellone

```
 72  SU 100                                        ← .cifra 132px + mono 15 --ink-2
┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐
│██████████████░░│░░│░░│░░│░░│                     ← riempimento continuo; 9 tacche 1px ai decili
└──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘                       tacca del 50 più marcata (è il nostro p_min)
──────────────────────────────                     ← linea di base 1px --prob-baseline
        ├───────────┤                              ← banda p5–p95, TRATTO 2px --rel-stroke
              │                                       tacca centrale su p
| Su 100 partite come questa, in 72 esce «X2».     ← .definizione — SEMPRE
| Fra 67 e 86 su 100 nelle nostre simulazioni.
| Stima media.
```

- Barra: larghezza piena della lastra, **alta 16px** (12px < 768px), raggio 0. In v1 erano 12/10: su
  fondo scuro e sotto una cifra da 132px una barra sottile scompare.
- Il riempimento è **continuo**, le tacche ai decili gli passano sopra: nessun arrotondamento
  a segmenti, quindi nessuna bugia di quantizzazione. Le tacche fanno da righello.
- La tacca del 50 è più marcata: mostrare dov'è il pavimento `p_min` è già un argomento.
- Banda: solo tratto, `--rel-stroke-w-lg` (2px), con serif alle estremità. **Mai riempita, mai
  colorata di una tinta della scala di probabilità, mai ocra.**
- Accessibilità: il gruppo barra+banda è `role="img"` con
  `aria-label="72 su 100. Banda di incertezza fra 67 e 86 su 100."` La riga di definizione è testo
  reale nel DOM, quindi l'informazione esiste anche senza il grafico.

### 7.2 `<ChipProvenienza source />`

Pillola, 32px di altezza, `--fs-label` in mono, testo sempre presente. Pieno = `blended_with_odds`,
tratteggiato = `model_only` (§2). Non è interattivo: nessun hover, nessun cursore a mano.
Se è cliccabile verso `/come-funziona#quote`, allora rispetta i 44px di bersaglio.
**Resta l'unico elemento arrotondato del prodotto.**

### 7.3 `<RigaFascia p />` — il record storico

L'unica affermazione di accuratezza che il prodotto pronuncia sulla scheda. **La fonte è dentro la
frase**, mai un asterisco (brief §9.5):

- Fascia storica: *"Su 100 pronostici in questa fascia (65–80), **nel nostro test storico** ne sono
  usciti 76."* + `n=540 · stagioni 2024-25` in mono micro.
- Appena quella fascia raggiunge `n ≥ 50` dal vivo, **automaticamente**: *"Su 100 pronostici in
  questa fascia (65–80), **fra quelli che abbiamo pubblicato** ne sono usciti 76."* + `n=214 · da set. 2026`.

Fasce: `0.50–0.65` · `0.65–0.80` · `0.80–1.00`, lette da `backtest.json.buckets` o
`accuracy.json.live.buckets`. Il passaggio è per fascia, non globale.
Il `76` di questa frase è **cifra da referto** (mono, dimensione del corpo): non compete con la cifra
del pronostico. Una sola cifra da tabellone per schermata.

### 7.4 `<RigaPartita />` — la griglia incolonnata

```
≥1024px, altezza 52px:
[crest][crest] 20:45  Udinese — Como      X2 (pareggio o ospite)   72  ├─┤  ( quote )
└─ auto ─────┘└ 3.25rem ┘└ 1fr ────────┘└ minmax(9rem,14rem) ─┘└3.5rem┘└56px┘└ auto ┘
```

- `<a>` che avvolge l'intera riga. `display: grid` con le colonne dei token
  (`--col-ora`, `--col-cifra`, `--col-banda`): **le cifre si incolonnano lungo tutta la lista**, e
  scorrere la pagina diventa un confronto. È il prestito da `diretta.it`.
- La cifra è `.cifra-riga` (Archivo `wdth 62` / 700, 26→32px), **allineata a destra**, tabellare.
- Divisore 1px `--edge` fra le righe. Hover: fondo `--surface-2` in 180ms. `:active`: `--surface-3`.
  Mai `transform`, mai ombra, nessuno spostamento di layout.
- Focus: outline 3px `--focus`, `outline-offset: -3px`.
- Sotto i 1024px la riga va su due livelli (72px): crest+ora+squadre sopra, mercato+cifra+banda+chip
  sotto, con la cifra sempre a destra. Mai troncare il nome del mercato: è il contenuto.
- Crest: `<img width height loading="lazy" alt="">` con fondo `--surface-3` come segnaposto — lo
  spazio è riservato, CLS zero. **Se il crest non carica**, ripiego sul `tla` in un quadrato 24px
  mono su `--surface-3`. Mai un'icona di immagine rotta, mai uno spazio che collassa.

### 7.5 `<Masthead />`, `<TemaToggle />`, `<PiePagina />`

- **Masthead**: §4. Fascia 6px in cima, `--surface`, sticky 56px, `data-scrolled`.
- **TemaToggle**: `<button>` con la parola dello stato, 44×44, bordo 1px `--edge-strong`,
  `aria-pressed` non appropriato (non è un interruttore binario di stato ma un cambio di modalità):
  usa `aria-label="Passa al tema chiaro"` che cambia con lo stato.
- **PiePagina**: fascia 6px in cima al piede, poi il testo di gratuità (§9.2) a `--fs-body-s` su
  `--surface`. Il piede è l'ultimo piano della pagina, non una nota a margine.

**Cose che vanno cambiate nello stesso commit dei token, o il prodotto resta a metà:**

| File | Cosa |
|---|---|
| `app/layout.tsx` | i tre import di `next/font/google` (§3.2) e la stringa `className` di `<html>` |
| `app/layout.tsx` | `viewport.themeColor`: `{ color: '#0F0E0C' }` per lo scuro, `'#E6E1D6'` per il chiaro — oggi contiene ancora gli hex della v1 |
| `styles/base.css` | `a { color: var(--accent) }` va sostituito dalla regola link di `tokens.css` (inchiostro + sottolineatura di segnale); `.titolo-pagina` / `.titolo-sezione` vanno tolti da qui perché ora vivono in `tokens.css` con la condensata |
| `styles/base.css` | `.masthead`, `.nav__voce`, `.tema`, `.pie`: fascia, `--surface`, sticky, `data-scrolled` |
| `styles/componenti.css` | `.blocco` → lastra con `.fascia`; `.prob__barra` 12→16px; `.row-partita` da flex a **grid**; `.rettifica`, `.valvola`, `.prova-storica` sui nuovi piani |
| `components/Masthead.tsx` | `<span className="fascia" aria-hidden />` in cima, `data-scrolled`, striscia dei giorni |
| `app/giorno/[data]/page.tsx` | la rivendicazione (blocco pieno) al posto della riga di conteggio; la banda di competizione appiccicata |
| ovunque | gli alias di compatibilità in fondo a `tokens.css` (`--paper`, `--rule-*`, `--accent`, `--ink-muted`, `--fs-display-*`) si cancellano quando l'ultimo riferimento è sparito. Nessun componente **nuovo** può usarli. |

Gli alias esistono perché il sito continui a compilare e a rendere durante il rifacimento: dopo il
solo cambio dei token la pagina è già scura e coerente, e i componenti si convertono uno alla volta.

### 7.6 `<Registro />`, `<ProvaStorica />`, `<SkillDichiarato />`, `<TassoSilenzio />`, `<BarraVerso500/>`, `<CurvaSilenzio />`

Regole comuni, oltre a quelle di `pages/come-stiamo-andando.md`:

- Le tabelle stanno su `--surface`, intestazioni mono su `--surface-2`, divisori `--edge`.
  L'intestazione della tabella è **sticky** dentro il contenitore scorrevole.
- Negli SVG: assi e filetti `--edge-strong`, barre `--prob-fill`, curve `--prob-fill` 1.5px,
  **le marche di soglia dichiarata in `--segnale`** (è struttura, non dato: concesso), le bande
  obiettivo su `--surface-2`. Mai un'area riempita di segnale.
- `<ProvaStorica />` è un altro documento: si apre con **`.fascia--lg` da 12px** e da lì in giù il
  fondo è `--surface-2`. Nessun elemento grafico condiviso con il registro dal vivo.

### 7.7 Icone

Lucide, **tratto 1.75** (a 1.5 su fondo scuro spariscono), dimensioni `16 / 20 / 24` da token. Usate
con parsimonia: chevron per le frecce del giorno, freccia esterna per i link a GitHub, spunta per
`confirmed`. **Nessuna emoji, mai, in nessun contesto.** I glifi matematici (`≈ ± < → ▪ ▫`) sono
**tipografia in Plex Mono**, non icone: non vanno sostituiti con SVG. Nessuna icona nello stato di
silenzio.

---

## 8. Stati: caricamento, vuoto, errore

Il sito è statico: non c'è un fetch che possa essere lento. Questo cambia i tre stati.

- **Caricamento: nessuno skeleton, in nessun punto del prodotto.** Uno skeleton grigio a forma di
  card è visivamente indistinguibile da uno stato di silenzio mal fatto, e quella confusione è
  fatale per l'unico differenziatore che abbiamo. L'HTML arriva già pieno. Le uniche risorse
  differite sono i crest, che hanno lo spazio riservato.
- **Vuoto (nessuna partita quel giorno).** Non è un silenzio e non deve somigliargli: **niente
  fascia, niente lastra**. Testo centrato su `--ground`, Plex Sans 17: *"Il 12 agosto non si gioca in
  nessuno dei campionati che seguiamo."* La striscia dei giorni resta e punta ai giorni che esistono.
- **Errore — `schema_version` diversa da quella attesa.** Il frontend **deve fallire forte**
  (`schema.md`), non degradare. Pagina intera, `role="alert"`, **fascia 6px `--warn`** invece che
  `--segnale`, titolo mono `DATI NON LEGGIBILI`, corpo che dice la versione attesa e quella trovata,
  e un link al repo. Nessun colore da solo: c'è la fascia, il titolo, e il testo.
- **Errore di rete su una risorsa statica**: non esiste come stato progettato — se il CDN non
  risponde non c'è pagina. Non progettare fallback fantasma.

**Non ci sono form nel prodotto** (niente login, niente ricerca lato server). Gli unici controlli
sono i filtri del registro in `/come-stiamo-andando`: sono `<button>` con `aria-pressed`, bordo 1px
`--edge-strong`, stato attivo con **fascia 3px** sotto oltre alla tinta, filtrano righe già presenti
nel DOM, e funzionano su una tabella completa anche senza JavaScript.

---

## 9. Stati commerciali

**Non esistono, per decisione permanente** (`decisioni.md` #2, brief §10 "Mai"): nessun piano,
nessun limite, nessun paywall, nessun upgrade, nessun pagamento, nessun login, nessuna pubblicità,
nessun link a bookmaker in nessuna forma.

Il design ha comunque due obblighi che discendono da questa decisione:

1. **Il layout non deve avere il posto per un annuncio.** Colonna singola, nessun rail laterale,
   nessuna fascia orizzontale libera fra le sezioni, nessun contenitore di larghezza 300/336/728px.
   Se un giorno qualcuno volesse infilarci un banner, dovrebbe rifare il layout — ed è voluto.
   *Nota v2:* la lastra a piena larghezza sotto i 1024px rafforza il vincolo — non c'è margine
   laterale in cui infilare niente.
2. **La gratuità è contenuto, non una nota legale.** In fondo a ogni pagina, in `--fs-body-s`:
   *"Gratis, senza pubblicità, senza affiliazioni. Non guadagniamo se scommetti."* + gioco
   responsabile con il link istituzionale + il link al repo pubblico. È il differenziatore più
   difendibile del prodotto: va detto, non nascosto in un footer di 11px.

---

## 10. Anti-pattern — cosa questo progetto non fa mai

**Estetica generica (studio, `CLAUDE.md`):**
- ❌ Gradiente viola→blu, glassmorphism, `backdrop-filter`, qualunque `box-shadow`
- ❌ `border-radius` uniforme (qui: 0 ovunque, tranne il chip)
- ❌ Tre feature-card equidistanti con icone generiche
- ❌ Un solo grottesco neutro a tre dimensioni (14/16/18)
- ❌ Emoji come icone → SVG Lucide, o tipografia mono per i glifi matematici

**Accessibilità (non negoziabile per estetica):**
- ❌ Testo sotto 4.5:1 · elementi non testuali sotto 3:1
- ❌ Focus invisibile · significato affidato al solo colore
- ❌ Hover che spostano il layout · affordance solo-hover
- ❌ Bersagli sotto 44×44px, spaziatura sotto 8px fra bersagli adiacenti
- ❌ Contenuto nascosto dietro barre fisse; scroll orizzontale di pagina
- ❌ Layout shift: ogni immagine ha `width`/`height`
- ❌ Testo su `--surface-3`

**Specifici della v2 — se ne violi uno, hai rifatto il difetto che stavamo correggendo:**
- ❌ Costruire una gerarchia con soli filetti: se un blocco conta, ha un **piano** o una **fascia**
- ❌ Il segnale come colore di testo, o su un dato di modello
- ❌ Più di un blocco pieno di segnale per schermata
- ❌ Cifra da tabellone e cifra da referto mescolate nello stesso blocco
- ❌ Il serif: non esiste più nel prodotto, in nessun punto
- ❌ La lastra incorniciata sui quattro lati

**Specifici del prodotto — se ne violi uno, hai rotto il prodotto, non lo stile:**
- ❌ Le parole **"value bet", "edge", ROI, rendimento, "quota consigliata", "puntata", "stake"**
- ❌ Qualunque importo da puntare, in qualunque unità
- ❌ `p_raw` (probabilità non shrinkata), `sigma`, `score`, `shrink_alpha`, `reference` mostrati
- ❌ Un'accuratezza aggregata senza la fascia di appartenenza accanto
- ❌ Numeri di `accuracy.json` e di `backtest.json` nello stesso grafico, tabella o media
- ❌ Il silenzio reso come vuoto, errore, skeleton, grigio, attenuato o illustrazione
- ❌ La colonna della cifra lasciata vuota su una riga di silenzio
- ❌ Il barrato sul pronostico precedente in una transizione
- ❌ Verde acido, urgenza, countdown, "ultimi minuti", quote in evidenza, badge "🔥 più popolare"
- ❌ Punteggi in diretta o qualunque cosa che suggerisca un aggiornamento live: il sito non ha
  runtime, e fingere il contrario è una promessa che non possiamo mantenere
- ❌ Barre sulle probabilità grezze mostrate sotto un silenzio
- ❌ Tooltip come unico portatore di un'informazione necessaria

---

## 11. Lista di controllo prima della consegna

**Base:**
- [ ] Nessuna emoji come icona; tutte le icone Lucide, tratto 1.75
- [ ] `cursor: pointer` su tutti gli elementi cliccabili
- [ ] Transizioni 150–300ms, solo colore/opacità
- [ ] Contrasto testo ≥4.5:1 **in entrambi i temi** · non testuali ≥3:1
- [ ] Focus visibile ovunque, invertito dentro i blocchi di segnale
- [ ] `prefers-reduced-motion` e `prefers-contrast: more` rispettati
- [ ] Responsive verificato a 375, 768, 1024, 1440
- [ ] Nessun contenuto nascosto dietro la testata appiccicata; nessuno scroll orizzontale di pagina

**Aggiunte di questo progetto:**
- [ ] Tema chiaro verificato **separatamente**, non dedotto dallo scuro
- [ ] Test in scala di grigi: probabilità e affidabilità restano distinguibili (pieno vs tratto)
- [ ] Lo stato di silenzio ha la stessa lastra, la stessa fascia e la stessa massa di un pronostico,
      nelle tre varianti
- [ ] I tre motivi di silenzio si distinguono senza colore (glifo + etichetta + testo)
- [ ] La colonna della cifra non è mai vuota nella lista
- [ ] Le quattro transizioni sono renderizzate, e le tre che cambiano stato stanno sopra la piega
- [ ] Ogni cifra del prodotto ha la sua riga di definizione operativa sotto
- [ ] Ogni affermazione di accuratezza porta `n` e periodo **dentro la frase**
- [ ] `accuracy.json` e `backtest.json` non si toccano in nessun componente
- [ ] Nessuna delle parole vietate compare nel bundle (`grep -ri "value bet\|edge\|ROI"`)
- [ ] `lang="it"`, skip link a `#contenuto`, tabelle con `<caption>` e `<th scope>`
- [ ] Il layout non contiene nessun contenitore di larghezza compatibile con un banner
- [ ] Il frontend fallisce forte se `schema_version ≠ 1`
- [ ] LCP < 2.5s · CLS < 0.1 · INP < 200ms su `/giorno/[data]` e `/partita/[id]`
- [ ] `grep -r "box-shadow\|backdrop-filter\|linear-gradient" frontend/styles` → **zero risultati**
- [ ] `grep -r "Newsreader\|Public_Sans\|Red_Hat_Mono" frontend` → **zero risultati**

---

## 12. Perché questo sembra un prodotto e non una pagina stampata

Elenco operativo. Se ne mancano più di due, il difetto della v1 è tornato.

1. **Piani, non filetti.** Contenuto su `--surface`, pagina su `--ground`, incassi su `--surface-2`.
2. **Il taglio a piena larghezza** sotto i 1024px: testata, striscia dei giorni, fascia di
   competizione e lastra della lista toccano i bordi dello schermo. Un documento ha i margini; uno
   schermo no.
3. **La testata appiccicata** con reazione allo scorrimento (`--edge` → `--edge-strong`).
4. **La striscia dei giorni**: una superficie di controllo, sempre presente, con lo stato corrente
   marcato da una fascia. È la differenza fra "leggo una pagina" e "sto usando qualcosa".
5. **Le fasce di competizione appiccicate** durante lo scorrimento della lista: sai sempre dove sei.
6. **Colonne fisse e cifre incolonnate**: una lista che si legge in verticale come una tabella.
7. **Feedback di pressione**: hover sale di un piano, `:active` di due. Un foglio non reagisce.
8. **Cifre grandi e condensate**: 132px sulla scheda, 32px in lista. La massa è il prodotto.
9. **Un solo blocco pieno di colore per schermata**, e non è decorativo: è la rivendicazione.
10. **Zero ombre, zero gradienti, zero blur** — la profondità non è mai simulata, è costruita.

---

## 13. Come si batte la concorrenza — specifica visiva

Studiati direttamente il 2026-08-08. `diretta.it` e `nerdytips.com/it` letti integralmente via
proxy di lettura; `one-versus-one.com/it/previsioni` letto in parte (la pagina è quasi tutta
renderizzata da JavaScript: **la lista delle previsioni non è stata letta nel dettaglio**, sono
stati letti navigazione, testata, prezzi e struttura). Quanto segue vale come specifica di design,
non come analisi di mercato.

### 13.1 `diretta.it` — cosa si prende, e cosa no

Non è un concorrente: è la **grammatica di lettura** che il pubblico italiano già conosce.

**Si prende** — e queste tre cose sono già nel sistema:
1. **Il raggruppamento per competizione con banda piena e appiccicata**, con il paese in etichetta e
   il conteggio delle partite a destra. È il modo in cui un italiano si orienta in una lista lunga.
2. **La colonna dell'ora fissa, mono, allineata a sinistra**: è l'ancora dello scorrimento.
3. **La densità**: righe basse, divisori tenui, nessuno spazio sprecato fra righe adiacenti. Il
   respiro sta *fra* i gruppi, non *dentro* la lista.

**Non si prende:** il portale (pubblicità in tre posizioni, rail laterali, decine di competizioni
minori tutte insieme, blocchi "Diretta News" a metà lista, tab `TUTTE/LIVE/CONCLUSI/PROGRAMMA` che
promettono aggiornamento in tempo reale). Noi non abbiamo runtime e non fingiamo di averlo: **niente
tab live, niente minuti che scorrono, niente punteggi in diretta.**

### 13.2 `nerdytips.com/it` — concorrente diretto

**Cosa fa meglio di noi, onestamente:**
- **Copertura**: dichiara oltre 160 campionati. Noi ne copriamo pochi. Su una lista, questo si vede.
- **La riga di pronostico è immediata**: `Remo VS Atletico-MG · X2 · 89%`. Tre informazioni, zero
  attrito, zero gergo. La nostra riga è più ricca ma anche più lenta da decodificare — la griglia
  incolonnata della v2 serve a recuperare esattamente questo terreno.
- **Ha un'identità visiva riconoscibile** (scuro, ciano, CTA forte). La nostra v1 non ne aveva.
- **Le pagine partita hanno molto materiale** (H2H, forma, profili offensivo/difensivo).

**Cosa fa male — e sono i punti su cui non li imitiamo mai:**
- **Le percentuali sono tutte altissime e ordinate dall'alto**: 89, 88, 88… Una lista che mostra
  solo i propri numeri migliori è marketing, non misura. **Non esiste incertezza da nessuna parte:
  nessuna banda, nessun `n`, nessuna calibrazione, nessun caso in cui tacciono.**
- **Il numero è una rivendicazione senza definizione.** "89%" di cosa, su quale base, con quale
  storico? Non è scritto da nessuna parte accanto al numero.
- **"tasso di successo superiore al 75%"** ripetuto in home, nei piani e nelle FAQ, senza fascia,
  senza `n`, senza periodo, senza metodo verificabile.
- **Paywall e prezzi** (`14.29$`, `11.29$`, "Risparmia $46"), badge Trustpilot, **emoji nei piani**
  ("Più Popolare 🔥", "Miglior Offerta ⭐"), CTA "INIZIA SUBITO!". È il registro dell'urgenza
  commerciale, ed è precisamente il registro che il nostro prodotto non ha.
- **Gradiente nell'hero.** Vietato da noi per default.

**Come li superiamo — non imitandoli:**
| Loro | Noi |
|---|---|
| `89%` nudo | `72` **su 100** + la banda `├──┤` + la riga di definizione sotto, sempre |
| lista ordinata per confidenza | lista in ordine di calcio d'inizio: non selezioniamo la vetrina |
| nessun silenzio | il silenzio è **~29% delle righe**, con la stessa lastra e la stessa fascia |
| "75% di successo" globale | accuratezza **per fascia**, con `n` e periodo dentro la frase |
| paywall, prezzi, Trustpilot, emoji | gratis, nessun login, nessun bookmaker, e lo diciamo nel piede |
| motore proprietario "NT Apex" | criterio scritto, parametri pubblicati, commit del codice stampato |

### 13.3 `one-versus-one.com/it/previsioni` — concorrente diretto

**Cosa fa meglio di noi:**
- **Ampiezza del prodotto**: confronti, giocatori, squadre, classifiche, statistiche di lega,
  risultati. Siamo un oggetto molto più piccolo.
- **Mostra la distribuzione, non solo la scelta**: `39% 26% 35%` su 1-X-2 è più onesto della
  "singola percentuale alta" di NerdyTips, e va riconosciuto.
- **Struttura a leghe collassabili** con `Vedi più previsioni`: gestisce bene liste lunghe.

**Cosa fa male:**
- **Nessuna incertezza sulla distribuzione**: tre percentuali secche, nessuna banda, nessun `n`,
  nessuna dichiarazione di quando il modello non sa.
- **Non tace mai.** Ogni partita ha tre numeri, sempre. È l'assunto opposto al nostro.
- **Nessun criterio dichiarato**: "previsioni basate sull'intelligenza artificiale" è tutto quello
  che si legge sul metodo.
- **Paywall** (`Prezzi`, `Scout Pro`) e **login** (`Accedi o Registrare`) davanti a parte del valore.
- **Etichette tradotte male** ("Vittoria Disegno campo Vittoria" per Home/Draw/Away): la cura
  linguistica è bassa, e in italiano si sente.
- **Visivamente neutro**: logo, SVG d'illustrazione nell'hero, card generiche. Nessun carattere.

**Come li superiamo — non imitandoli:**
| Loro | Noi |
|---|---|
| `39% 26% 35%` per ogni partita | **un solo** mercato consigliato, oppure il silenzio dichiarato |
| tre numeri senza incertezza | un numero con la sua banda e la sua definizione operativa |
| "basato sull'IA" | il criterio in `/come-funziona`, i parametri, il protocollo, il commit |
| italiano tradotto a macchina | italiano scritto, e la stessa parola per la stessa cosa ovunque |
| card generiche, hero illustrato | fasce piene, condensata da tabellone, cifre che si incolonnano |
| login e piani | niente login, niente piani |

### 13.4 Il terreno su cui si vince

Nessuno dei due **dichiara il criterio, mostra l'incertezza e a volte tace**. Sono tre cose che si
possono *vedere* prima ancora di leggerle, e il design della v2 esiste per renderle visibili:

- **il criterio** è la riga di definizione operativa sotto ogni numero, sempre presente;
- **l'incertezza** è la banda `├──┤` accanto a ogni cifra, in un linguaggio grafico che non si può
  confondere col riempimento;
- **il silenzio** è la rivendicazione in blocco pieno in cima alla lista, e una riga su tre nella
  lista stessa, con la stessa lastra e la stessa fascia di un pronostico.

Se un giorno queste tre cose smettessero di essere le più visibili della pagina, avremmo perso —
anche con un sito più bello.
