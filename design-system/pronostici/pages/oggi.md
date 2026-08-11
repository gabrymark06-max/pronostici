# Pagina: Oggi — `/giorno/[data]`

> Sovrascrive `MASTER.md` solo dove indicato. Sorgente: `data/fixtures/{data}.json`.
> Larghezza: `--w-list` (940px). Densità: **alta** — è una lista da scorrere.
> **v2:** la lista non è più un elenco su carta, è una **lastra**. Sotto i 1024px esce dalla colonna
> e tocca i bordi dello schermo (`MASTER.md` §3.3).

## Struttura

```
█████████████████████████████████████████████████████████  6px --segnale · testata appiccicata
 PRONOSTICI                                     [ CHIARO ]
 OGGI    COME STIAMO ANDANDO    COME FUNZIONA
──────────────────────────────────────────────────────── 1px --edge

 ‹  MER 19 · GIO 20 · VEN 21 · [SAB 22] · DOM 23 · LUN 24  ›   ← striscia dei giorni, 52px
                                ▔▔▔▔▔▔ fascia 3px --segnale       piena larghezza < 1024px

 SABATO 22 AGOSTO                                    ← .titolo-pagina, 40→56px condensata

 ███████████████████████████████████████████████     ← LA RIVENDICAZIONE
 █ OGGI TACIAMO SU                              █       blocco pieno --segnale
 █ 3 partite su 14.                             █       cifre 34px condensate 800
 ███████████████████████████████████████████████       testo --segnale-ink

 Oggi abbiamo rivisto 3 pronostici e ne abbiamo ritirato 1.   ← --fs-body, --ink
 ┃ Tacere è una risposta: la diamo quando nessun mercato      ← .definizione su --surface-2
 ┃ supera il nostro criterio. Perché →

┌── lastra --surface ────────────────────────────────────────────────────┐
│▓▓ SERIE A                                                    3 partite │ ← banda 34px --surface-2
│  [c][c] 18:00  Inter — Monza      12 (nessun pareggio)  90 ├┤ ( quote )│    appiccicata
│ ───────────────────────────────────────────────────────────────────────│ 1px --edge
│  [c][c] 20:45  Bologna — Lazio    nessun pronostico          ≈         │    corsivo + glifo
│ ───────────────────────────────────────────────────────────────────────│
│  [c][c] 20:45  Udinese — Como     X2  [RIVISTO]         72 ├──┤ (mod.) │
│▓▓ PREMIER LEAGUE                                             5 partite │
│  …                                                                     │
└────────────────────────────────────────────────────────────────────────┘
█████████████████████████████████████  6px --segnale · piede
 Gratis, senza pubblicità, senza affiliazioni. Non guadagniamo se scommetti.
```

## Regole specifiche

**La striscia dei giorni** (`MASTER.md` §4). Sostituisce le due frecce isolate della v1.
- Fino a sette `<a>` verso `/giorno/{data}`, **solo giorni che esistono davvero** in `data/fixtures/`.
- Ogni voce: mono 12 maiuscolo su due righe — `SAB` in `--ink-2`, `22` in `--ink`. 44×44 minimo,
  `padding-inline: var(--s-3)`.
- Giorno corrente: fondo `--surface-2`, **fascia 3px `--segnale`** sotto la voce, `aria-current="date"`.
  Mai il solo colore.
- Le frecce `‹ ›` restano agli estremi come `<a>` 44×44 verso il giorno precedente/successivo
  disponibile, con `aria-label="Giorno precedente, venerdì 21 agosto"`. Se non esiste, sono uno
  `<span aria-disabled>` a opacità 0.4 — non un link morto.
- Sotto i 768px: `overflow-x: auto`, `scroll-snap-type: x mandatory`, il giorno corrente ha
  `scroll-margin-inline: var(--s-5)` e la pagina lo porta in vista **senza animazione**. Il
  contenitore scorre, la pagina no.

**Intestazione del giorno.**
- Data in `.titolo-pagina` (Archivo `wdth 70` / 700, 40→56px), minuscolo con iniziale maiuscola:
  *"Sabato 22 agosto"*. Il giorno corrente porta `Oggi, ` davanti. Formato lungo italiano, mai
  `22/08/2026`. Respiro: 40px sopra, 24px sotto.

**La rivendicazione** — è l'unico blocco pieno di segnale della pagina (`MASTER.md` §5.5).
- `background: var(--segnale)`, tutto il testo in `--segnale-ink`, padding `--s-4` `--s-5`.
- Etichetta mono in cima (`OGGI TACIAMO SU`), poi la frase con **le cifre in Archivo `wdth 62` / 800
  a 34px** inline, allineate alla linea di base del testo.
- C'è **sempre**, anche a zero: *"Oggi abbiamo un pronostico per tutte e 14 le partite."*
- Nessun link dentro il blocco pieno **tranne** quello della definizione, che sta fuori, sotto.
  Se un link ci finisse: `outline-color: var(--segnale-ink)` in focus.
- La riga delle revisioni sta **fuori** dal blocco, sotto, in `--fs-body` su `--ground`.
- Valvola 40%: nota su `--surface-2` con fascia sinistra 3px `--edge-strong`, testo di `MASTER.md`
  §5.5. **Non** un secondo blocco di segnale, **non** un `role="alert"`.

**La banda di competizione.**
- `height: var(--band-h)` (34px), `background: var(--surface-2)`, mono 12 maiuscolo `--ink` a
  sinistra, `«n partite»` in `--ink-3` a destra.
- `position: sticky; top: var(--masthead-h)` — durante lo scorrimento sai sempre in che campionato
  sei. È la convenzione di `diretta.it`, ed è l'unica cosa che se ne prende oltre alla densità.
- Niente logo di competizione: solo il nome. Nessun filetto sopra: la banda **è** il separatore.
- Le partite sono raggruppate per competizione, in ordine di primo calcio d'inizio; dentro il gruppo,
  per orario (i file arrivano già ordinati).

**Riga-partita.** Componente `<RigaPartita />`, griglia di `MASTER.md` §7.4.
- ≥1024px: una sola riga da 52px, colonne fisse, **cifra allineata a destra in `--col-cifra`**.
- <1024px: due livelli, 72px. Sopra: crest + ora + squadre. Sotto: mercato + cifra + banda + chip,
  con la cifra sempre all'estrema destra, così la colonna resta leggibile anche a 375px.
- <375px la mini-banda `├─┤` si omette; cifra e chip restano. La cifra non si omette mai.
- Hover `--surface-2`, `:active` `--surface-3`, focus outline 3px interno. Nessun `transform`.

**Il silenzio in lista** (`MASTER.md` §5.4). Testo *"nessun pronostico"* in **Plex Sans corsivo 15**,
`--ink` pieno, e nella colonna della cifra **il glifo mono a 20px** (`≈ ± <`) in `--rel-stroke`.
La colonna della cifra non resta mai vuota.

**Tag di transizione.** `RIVISTO` · `RITIRATO` · `NUOVO`: mono 12 maiuscolo `--ink` su fondo
`--surface-3`, padding `2px 6px`, raggio 0. **Non** testo colorato — il segnale non colora testo.
`confirmed` e `still_silent` non producono tag: non è successo niente da annunciare.

**Esito a partita conclusa.** Se la fixture ha `result`, la riga aggiunge il punteggio in mono e
l'esito con **parola + glifo + colore**, mai colore solo: `3–1 · uscito ▪` (`--outcome-yes`) oppure
`0–0 · non uscito ▫` (`--outcome-no`). Le righe concluse restano a piena opacità: il registro è il
prodotto.

## Accessibilità

- La lista è una `<ul>` di `<li>`; ogni riga è un `<a>` che avvolge tutto il contenuto.
- La striscia dei giorni è una `<nav aria-label="Giorni">` con una `<ul>` di `<a>`.
- L'ora è in `<time datetime>`; il crest ha `alt=""` (decorativo — il nome della squadra è testo).
- La banda appiccicata è alta 34px e la testata 56px: nessun contenuto resta coperto, perché ogni
  ancora interna porta `scroll-margin-top: calc(var(--masthead-h) + var(--band-h))`.
- Ordine di tab = ordine visivo: striscia dei giorni, poi le righe dall'alto.
- Skip link a `#contenuto` prima della nav.

## Prestazioni

- I crest sono ~14 immagini remote da `crests.football-data.org`: `loading="lazy"` da sotto la
  piega, `width`/`height` espliciti, `decoding="async"`, e il dominio in `next.config` come
  `images.remotePatterns` (o copiati in `public/` in fase di build — preferibile: nessuna dipendenza
  da un terzo a runtime).
- CLS zero: nessun elemento entra o si sposta dopo il primo paint. La striscia dei giorni ha altezza
  fissa (`--striscia-h`) anche prima che il JavaScript porti in vista il giorno corrente.
- Il listener di `data-scrolled` sulla testata è `{ passive: true }` e scrive una sola volta per
  soglia attraversata: non tocca il layout, non causa reflow.
