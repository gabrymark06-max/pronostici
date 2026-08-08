# Pagina: Come funziona — `/come-funziona`

> **Deroga tipografica dichiarata:** qui il corpo è **Newsreader 19/1.7**, non Public Sans.
> Questa pagina è un articolo; le altre sono un bollettino. È densità deliberata, non incoerenza —
> ed è l'unica pagina del prodotto che si legge invece di consultarsi.
> Larghezza `--w-prose` (68ch). Densità: **bassa**.

## Struttura

```
Come funziona

[1] Il criterio, in un paragrafo
[2] Perché a volte non diciamo niente          ← ancora #silenzio
[3] Le due versioni dello stesso pronostico    ← ancora #revisione
[4] Da dove vengono i dati, e le quote         ← ancora #quote
[5] La tabella dei parametri
[6] Il protocollo pre-registrato
[7] Cosa non facciamo
```

## Regole per sezione

**[1] Il criterio.** Un paragrafo, in italiano, senza formule. Deve essere comprensibile a chi non
sa cosa sia una divergenza KL — e deve restare vero. Traccia:
> *"Per ogni partita calcoliamo la probabilità di undici tipi di mercato a partire dalla stessa
> stima dei gol attesi. Poi cerchiamo quale di quei mercati dice qualcosa che la media del
> campionato — o le quote, quando ci sono — non dicono già. Fra i candidati non scegliamo quello con
> il vantaggio più grande: scegliamo quello che unisce un vantaggio reale a una probabilità alta di
> uscire davvero e a una stima in cui abbiamo fiducia. Se nessuno ce la fa, non diciamo niente."*

Sotto, in `.definizione`, la frase che rende il criterio verificabile: *"Il criterio è scritto nel
codice, in un repository pubblico. Chiunque può leggerlo e rieseguirlo."* + link.

**[2] Il silenzio** — la sezione linkata da ogni stato di silenzio e dall'intestazione del giorno.
Spiega i tre filtri con gli stessi tre glifi usati nell'interfaccia (`≈ ± <`), nello stesso ordine,
con le stesse etichette. La coerenza glifo↔spiegazione è ciò che rende il glifo apprendibile.
Contiene il tasso obiettivo dichiarato (15–30%, limite duro 40%) e il fatto che `S_min` è stato
scelto una volta e congelato: *"È l'unica manopola del sistema, e l'abbiamo girata una volta sola."*

**[3] Le due versioni.** La tabella preliminare/definitivo (T−7g / T−36h, peso 1,0 / 0,35, i due
badge), e la regola dura: *"Una sola revisione, annunciata in anticipo, sempre visibile. Al fischio
d'inizio non tocchiamo più niente. Il pronostico precedente non viene mai cancellato."*
I due chip di provenienza compaiono qui alla loro dimensione reale, affiancati e spiegati: è la
legenda del linguaggio B.

**[4] I dati e le quote.** Le fonti nominate. E il blocco di trasparenza sulla quota di crediti,
letto da `data/odds_budget.json`, reso come una riga di stato in mono — non un grafico:
> `crediti quote usati questo mese  87 / 250` + la scala di degradazione in chiaro.
È una dichiarazione di trasparenza (`schema.md`), e ha lo stesso valore argomentativo della barra
verso i 500: mostra un vincolo invece di nasconderlo.

**[5] I parametri.** `<table>` da `backtest.json.parameters`, con una colonna *"a cosa serve"* in
italiano. `p_min` e `sigma_max` marcati con il tag mono `MAI TOCCATO`, `s_min_in_code` con
`CONGELATO IL {data}`. La tabella è larga: `overflow-x: auto` sul contenitore, mai sulla pagina.

**[6] Il protocollo.** Link a `docs/protocollo-backtest.md` nel repo pubblico, con il commit e la
data. Frase: *"Le regole sono state scritte prima dei numeri. La data del commit lo dimostra, e non
possiamo cambiarla."*

**[7] Cosa non facciamo.** La sezione più importante della pagina per il posizionamento, e va scritta
come contenuto, non come disclaimer legale. Elenco breve, `--fs-h3`:
> Non vendiamo niente. Non abbiamo pubblicità. Non abbiamo link a bookmaker, di nessun tipo.
> Non c'è login e non raccogliamo dati su di te. **Non guadagniamo se scommetti.**
> Non diciamo mai quanto puntare, e non parliamo di rendimento.
> Non pubblichiamo punteggi in diretta: i risultati arrivano con il calcolo della notte.

Chiude con il gioco responsabile — link istituzionale, testo pieno, `--fs-body`, **non** in
caratteri più piccoli del resto. Un disclaimer rimpicciolito contraddice la pagina che lo contiene.

## Note

- Nessuna terza colonna, nessuna card, nessuna icona decorativa, nessun accordion: è testo.
- Ancore stabili (`#silenzio`, `#revisione`, `#quote`, `#parametri`) — ci puntano link da tutto il
  prodotto e non devono rompersi.
- `<h2>` per ogni sezione, indice in cima con link alle ancore su ≥1024px (posizione statica sopra
  il testo, **non** una colonna laterale — vedi `MASTER.md` §4).
