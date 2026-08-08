# Pagina: Oggi — `/giorno/[data]`

> Sovrascrive `MASTER.md` solo dove indicato. Sorgente: `data/fixtures/{data}.json`.
> Larghezza: `--w-list` (880px). Densità: **alta** — è una lista da scorrere.

## Struttura

```
┌ masthead + nav ─────────────────────────────────────────────────────┐
│                                                                     │
│  ‹ VEN 21        SABATO 22 AGOSTO        DOM 23 ›   ← frecce 44×44  │
│                                                                     │
│  Oggi taciamo su 3 partite su 14.                   ← --fs-body     │
│  Oggi abbiamo rivisto 3 pronostici e ne abbiamo ritirato 1.         │
│  | Tacere è una risposta: la diamo quando nessun mercato supera     │
│  | il nostro criterio. Perché →                     ← .definizione  │
│                                                                     │
│ ═════════════════════════════════════════════════   2px rule-heavy  │
│  SERIE A                                            ← .label        │
│ ─────────────────────────────────────────────────   1px rule-hair   │
│  [crest] 18:00  Inter — Monza      12 (nessun pareggio)  90 ├┤ [chip]│
│ ─────────────────────────────────────────────────                   │
│  [crest] 20:45  Bologna — Lazio    nessun pronostico  ≈             │
│ ─────────────────────────────────────────────────                   │
│  [crest] 20:45  Udinese — Como     X2  72 ├──┤ [chip]  RIVISTO      │
│ ═════════════════════════════════════════════════                   │
│  PREMIER LEAGUE                                                     │
│  …                                                                  │
└ footer: gratuità + gioco responsabile + link al repo ───────────────┘
```

## Regole specifiche

**Intestazione del giorno.**
- Data in Newsreader 600, `--fs-display-l`, minuscolo con iniziale maiuscola: *"Sabato 22 agosto"*.
  Il giorno corrente porta anche `Oggi, ` davanti. Formato lungo italiano, mai `22/08/2026`.
- Frecce: `<a>` di 44×44 verso `/giorno/{data±1}` **saltando ai giorni che esistono davvero** in
  `data/fixtures/`. `aria-label="Giorno precedente, venerdì 21 agosto"`. Se non c'è un giorno
  precedente disponibile, la freccia è un `<span>` con `aria-disabled` e opacità 0.4 — non un link
  morto.
- **La riga dei silenzi c'è sempre**, anche a zero. Le cifre in Newsreader 600 `--accent`, il resto
  in `--ink`. Mai attenuata, mai un badge, mai un'icona.
- La riga delle revisioni compare solo se il giorno contiene almeno una transizione fra
  `changed | prediction_to_silence | silence_to_prediction`. Si calcola dal file, non serve altro.
- Valvola 40% (`silence_count / total > 0.40`): nota su `--paper-alt`, filetto sinistro 3px
  `--rule-accent`, testo di `MASTER.md` §5.5. Non è un `role="alert"`: non è un errore.

**Raggruppamento.** Le partite sono raggruppate per competizione, in ordine di primo calcio
d'inizio; dentro il gruppo, per orario (i file arrivano già ordinati). Titolo di gruppo `.label` con
un filetto 2px `--rule-heavy` sopra. Niente logo di competizione: solo il nome.

**Riga-partita.** Componente `<RigaPartita />` di `MASTER.md` §7.4. Layout a 375px su due livelli.
La mini-banda `├─┤` nella riga è larga 48px, solo tratto, e si **omette sotto i 375px** — la cifra e
il chip restano.

**Tag di transizione.** `RIVISTO` · `RITIRATO` · `NUOVO` in Red Hat Mono 12, `--accent`, in coda
alla riga. `confirmed` e `still_silent` **non** producono tag: non è successo niente da annunciare.

**Esito a partita conclusa.** Se la fixture ha `result`, la riga aggiunge il punteggio in mono e
l'esito del pronostico con **parola + glifo + colore**, mai colore solo:
`3–1 · uscito ▪` (`--outcome-yes`) oppure `0–0 · non uscito ▫` (`--outcome-no`).
Le righe concluse restano a piena opacità: il registro è il prodotto.

## Accessibilità

- La lista è una `<ul>` di `<li>`; ogni riga è un `<a>` che avvolge tutto il contenuto.
- L'ora è in `<time datetime>`; il crest ha `alt=""` (decorativo — il nome della squadra è testo).
- Ordine di tab = ordine visivo: frecce, poi le righe dall'alto.
- Skip link a `#contenuto` prima della nav.

## Prestazioni

- I crest sono ~14 immagini remote da `crests.football-data.org`: `loading="lazy"` da sotto la
  piega, `width`/`height` espliciti, `decoding="async"`, e il dominio in `next.config` come
  `images.remotePatterns` (o copiati in `public/` in fase di build — preferibile: nessuna dipendenza
  da un terzo a runtime).
- CLS zero: nessun elemento entra o si sposta dopo il primo paint.
