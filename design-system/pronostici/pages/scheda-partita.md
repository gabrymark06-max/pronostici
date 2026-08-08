# Pagina: Scheda partita — `/partita/[match_id]`

> La schermata principale. Larghezza `--w-card` (720px). Densità: **bassa sopra la piega**
> (`--s-7`/`--s-8` fra i blocchi), **alta sotto** (tabelle a `--s-3`). È il contrasto di densità
> che dice all'occhio dove finisce il giudizio e dove comincia il materiale.

## Gerarchia sopra la piega — l'ordine è vincolante (brief §14.3)

```
‹ Torna a sabato 22 agosto                                      ← link --accent

[crest]  UDINESE CALCIO  —  COMO 1907  [crest]                  ← Newsreader 600 --fs-display-l
Serie A · giornata 1 · sabato 22 agosto, 20:45                  ← .label

══════════════════════════════════════════════════════ 2px --rule-accent
IL NOSTRO PRONOSTICO                                            ← .label

X2 (pareggio o ospite)                                          ← Newsreader 600 --fs-display-l
                                                                   ① IL PRONOSTICO

 72  su 100                                                     ← ② LA PROBABILITÀ
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐                Newsreader 600 --fs-display-xl
│█████████████████████████████░░░░░░░░│░░░░│░░░░│░│                riempimento continuo + decili
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
───────────────────────────────────────────────────  1px --prob-baseline
                    ├──────────────┤                            ← banda p5–p95, solo tratto
                          │
| Su 100 partite come questa, in 72 esce «X2 (pareggio          ← .definizione — ELEMENTO FIRMA
| o ospite)». Fra 67 e 86 su 100 nelle nostre simulazioni.
| Stima media.

( solo modello statistico )                                     ← chip tratteggiato

[ blocco di revisione, se transition ∈ {changed, silence_to_prediction} ]

────────────────────────────────────────────────────  1px --rule-hair
QUANTO SPESSO SI AVVERANO PRONOSTICI COSÌ                       ← ③ RECORD DI FASCIA
Su 100 pronostici in questa fascia (65–80), nel nostro
test storico ne sono usciti 76.
n=540 · stagioni 2024-25                                        ← mono --fs-micro

────────────────────────────────────────────────────
PERCHÉ                                                          ← ④ LE RAGIONI
—  Gol attesi: Udinese 0.95, Como 1.59 (totale 2.54).
—  X2: 72 su 100, 11 punti sopra la media di riferimento (61 su 100).
—  [terza ragione, se c'è]
══════════════════════════════════════════════════════ 2px --rule-heavy
```

**Nessun altro elemento entra sopra la piega.** Non le altre famiglie di mercato, non la forma
recente, non le quote, non i runner-up. La misura di successo di questa schermata è che a 375px, con
il testo di sistema al massimo, i quattro blocchi ①②③④ siano leggibili in un solo scorrimento breve.

## Regole per blocco

**① Il pronostico.** `prediction.label` così com'è — sono nomi di mercato standard già appresi
(`competitors.md` §4), non si traducono e non si abbelliscono. Se `prediction` è `null`, questo
blocco e ② sono sostituiti in blocco dallo **stato di silenzio** di `MASTER.md` §5.2, con lo stesso
filetto di testata e la stessa posizione. Nessun altro cambiamento di layout.

**② La probabilità.** `p` (già shrinkata) × 100 arrotondata all'intero, resa come `72` + `su 100`.
Mai il simbolo `%`. Mai la parola "confidenza". Mai `p_raw`.
Le tre righe di `.definizione` sono obbligatorie e in quest'ordine: definizione operativa, banda in
parole, qualifica della banda (stretta / media / larga, da `MASTER.md` §2).

**③ Il record di fascia.** `MASTER.md` §7.3. Durante l'avvio a freddo la fonte è il test storico e
**la parola "test storico" è dentro la frase**, mai un asterisco. Se la fascia non ha nemmeno il
backtest (`enough: false`), la riga diventa: *"Non abbiamo ancora abbastanza pronostici in questa
fascia per dire quanto spesso si avverano. Lo diremo quando ne avremo 50."* — che è ancora
un'informazione, non un buco.

**④ Le ragioni.** `reasons[]` è già italiano pronto: si stampa così com'è, **massimo tre voci**,
lista con trattino em, `--fs-body`, `--lh-body`, nessun grassetto interno, nessuna icona.
Elenco corto in stile Metaculus "Key Factors" — mai un paragrafo di prosa.
Se `transition ≠ first`, `reasons[0]` è la frase della transizione: in quel caso **non** va
duplicata qui, perché appare già nel blocco di revisione.

## Il blocco di revisione delle 36 ore

Specificato in `MASTER.md` §6. Sulla scheda ha due posizioni e non ne ha altre:
sopra la piega per `changed`, `prediction_to_silence`, `silence_to_prediction`; subito sotto ③ per
`confirmed` e `still_silent`. È **contenuto**, mai un `<details>` chiuso, mai un tooltip, mai una
nota a piè di pagina, e non ha animazione di ingresso.

Il confronto PRIMA/ORA è una `<table>` di due righe con `<th scope="row">` = *Prima* / *Ora*, così
lo screen reader legge la coppia come una coppia. Il glifo `↓` fra le due righe è mono, decorativo,
`aria-hidden`.

## Sotto la piega — in quest'ordine

1. **Le altre famiglie di mercato.** Un `<details>` per famiglia (`double_chance`, `over_under`,
   `handicap_asian`, …) alimentato da `runners_up` e `raw_probabilities`. Chiuso di default:
   mostrarli aperti significherebbe rifare il cimitero di numeri di FootyStats e riconsegnare
   l'argmax all'utente. `<summary>` con 44px di altezza, freccia Lucide che ruota in
   `--dur-3`. **Nessuna barra** dentro: solo cifre mono tabellari. La barra resta il linguaggio del
   solo mercato consigliato.
2. **Forma recente W-D-L** con legenda esplicita (convenzione portante, `competitors.md` §4).
   Glifi quadrati con la lettera dentro: `V` `N` `P` in mono su fondo `--prob-track` /
   `--paper-alt` — la lettera è il portatore di significato, il colore è rinforzo.
   *Nota di scope:* richiede un campo che `schema.md` v1 non ha ancora. Se non arriva, la sezione
   non si finge: non compare.
3. **Le quote, se `phase === "definitive"`** e `odds` è presente: **in decimale** (convenzione
   portante), in tabella mono, con l'etichetta `quote di mercato, sgonfiate` e la data di rilevazione.
   **Mai un link a un bookmaker. Mai un nome di bookmaker in evidenza. Mai una quota accanto al
   pronostico consigliato**: sopra la piega le quote non entrano.
4. **Esito, a partita conclusa.** `result` + `outcome`: punteggio in Newsreader 600, poi
   *"Il nostro pronostico X2 è uscito ▪"* / *"non è uscito ▫"*, parola + glifo + colore.
   Questo blocco, quando esiste, sale **sopra** il punto 1 — l'esito è più importante dei mercati
   alternativi.
5. **Link a `/come-stiamo-andando`** in chiaro: *"Tutti i nostri pronostici, con quanti ne abbiamo
   presi →"*. È il collegamento che rende il record raggiungibile da ogni consiglio
   (`competitors.md` §5.3).

## Accessibilità

- `<h1>` = "Udinese Calcio — Como 1907". `<h2>` per pronostico / perché / altre famiglie / esito.
- Il gruppo barra+banda: `role="img"` con l'`aria-label` di `MASTER.md` §7.1.
- Il chip di provenienza è testo, non un colore: leggibile da screen reader senza `aria-label`.
- I `<details>` sono nativi: funzionano senza JavaScript, sono raggiungibili da tastiera e il loro
  contenuto è nel DOM per i crawler.
- Nessun `title` porta informazione che non sia anche testo visibile.

## SEO

`metadata` esportato per rotta: title *"Udinese — Como: il nostro pronostico"*, description = la
definizione operativa, OpenGraph con le due squadre e la data. Sitemap che elenca tutti i giorni e
tutte le partite generate. `schema_version` diversa da 1 → la pagina non si genera affatto.
