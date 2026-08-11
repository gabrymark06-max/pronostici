# Pagina: Scheda partita — `/partita/[match_id]`

> La schermata principale. Larghezza `--w-card` (760px). Densità: **bassa sopra la piega**
> (`--s-7`/`--s-8` fra i blocchi), **alta sotto** (tabelle a `--s-3`). È il contrasto di densità
> che dice all'occhio dove finisce il giudizio e dove comincia il materiale.
>
> **v2:** il pronostico non è un blocco su carta, è **una lastra** (`--surface`) che sta sul fondo
> pagina, con la fascia da 6px in cima. Sotto i 1024px la lastra tocca i bordi dello schermo.
> La cifra è il protagonista assoluto: 132px, condensata, e **una sola per schermata**.

## Gerarchia sopra la piega — l'ordine è vincolante (brief §14.3)

```
‹ Torna a sabato 22 agosto                                      ← link: ink + sottolineatura segnale

UDINESE CALCIO — COMO 1907                                      ← .titolo-pagina, 40→56 condensata
[crest][crest]  Serie A · giornata 1 · sabato 22 agosto, 20:45  ← .label

┌── lastra --surface ───────────────────────────────────────────────────┐
│████████████████████████████████████████████████████████ 6px --segnale │  ← LA FASCIA
│ IL NOSTRO PRONOSTICO                                                  │  ← .label
│                                                                       │
│ X2 (pareggio o ospite)                                                │  ← ① IL PRONOSTICO
│                                                       Archivo wdth 70 / 700, --fs-h2
│                                                                       │
│ 72  SU 100                                                            │  ← ② LA PROBABILITÀ
│ ▔▔▔ .cifra: Archivo wdth 62 / 800, 80→132px, ls -.035em, lh .84       │
│      «SU 100» in Plex Mono 15 --ink-2, sulla linea di base            │
│ ┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐                   │
│ │█████████████████████████████░░░░░░░░│░░░░│░░░░│░│  barra 16px       │
│ └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘                   │
│ ──────────────────────────────────────────────────  1px --prob-baseline│
│                     ├──────────────┤                banda, tratto 2px │
│                           │                                            │
│ ┃ Su 100 partite come questa, in 72 esce «X2 (pareggio                │ ← .definizione
│ ┃ o ospite)». Fra 67 e 86 su 100 nelle nostre simulazioni.            │   incassata su --surface-2
│ ┃ Stima media.                                                        │
│                                                                       │
│ ( solo modello statistico )                                           │ ← chip tratteggiato
└───────────────────────────────────────────────────────────────────────┘

[ blocco di revisione, se transition ∈ {changed, silence_to_prediction} ]
  fondo --surface-2, fascia 6px --segnale, corsivo Plex Sans 20

████████████████████████████████████████ 6px --segnale
QUANTO SPESSO SI AVVERANO PRONOSTICI COSÌ                       ← ③ RECORD DI FASCIA
Su 100 pronostici in questa fascia (65–80), nel nostro
test storico ne sono usciti 76.                                    il «76» è cifra da referto: mono
n=540 · stagioni 2024-25                                        ← mono --fs-micro, --ink-3

████████████████████████████████████████ 6px --segnale
PERCHÉ                                                          ← ④ LE RAGIONI
—  Gol attesi: Udinese 0.95, Como 1.59 (totale 2.54).
—  X2: 72 su 100, 11 punti sopra la media di riferimento (61 su 100).
—  [terza ragione, se c'è]
```

**Una sola cifra da tabellone per schermata.** Il `76` del record di fascia, i gol attesi delle
ragioni, le quote e le probabilità grezze sono **cifre da referto** (Plex Mono, dimensione del
corpo). Se una seconda cifra cresce, il `72` smette di dominare e la schermata torna piatta.

**Nessun altro elemento entra sopra la piega.** Non le altre famiglie di mercato, non la forma
recente, non le quote, non i runner-up. La misura di successo di questa schermata è che a 375px, con
il testo di sistema al massimo, i quattro blocchi ①②③④ siano leggibili in un solo scorrimento breve.

## Regole per blocco

**① Il pronostico.** `prediction.label` così com'è — sono nomi di mercato standard già appresi
(`competitors.md` §4), non si traducono e non si abbelliscono. Se `prediction` è `null`, questo
blocco e ② sono sostituiti in blocco dallo **stato di silenzio** di `MASTER.md` §5.2, **nella stessa
lastra, con la stessa fascia da 6px, lo stesso padding e la stessa posizione**. Nessun altro
cambiamento di layout, nessun cambio di fondo, nessuna opacità ridotta. Il messaggio va nello slot
della cifra a `--fs-h2` in Archivo condensata 700.

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
   Glifi quadrati con la lettera dentro: `V` `N` `P` in mono su fondo `--surface-3` (vinta) /
   `--surface-2` (pari) / contorno 1px `--edge-strong` (persa) — la lettera è il portatore di
   significato, il fondo è rinforzo. Mai il segnale: non è un dato che si celebra.
   *Nota di scope:* richiede un campo che `schema.md` v1 non ha ancora. Se non arriva, la sezione
   non si finge: non compare.
3. **Le quote, se `phase === "definitive"`** e `odds` è presente: **in decimale** (convenzione
   portante), in tabella mono, con l'etichetta `quote di mercato, sgonfiate` e la data di rilevazione.
   **Mai un link a un bookmaker. Mai un nome di bookmaker in evidenza. Mai una quota accanto al
   pronostico consigliato**: sopra la piega le quote non entrano.
4. **Esito, a partita conclusa.** `result` + `outcome`: punteggio in Archivo condensata 700 a
   `--fs-h2` (non `--fs-cifra`: la cifra da tabellone resta una sola), poi
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
