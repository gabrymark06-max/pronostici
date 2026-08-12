# Registro dei cambi di parametro

Il registro dei pronostici è **append-only**: una riga pubblicata non si
riscrive mai. Ma i parametri con cui quelle righe sono state prodotte possono
cambiare, e senza una data quel cambiamento rende il registro non
interpretabile — due righe con la stessa forma potrebbero venire da due sistemi
diversi.

Questo file è quella data. Ogni voce dice **cosa** è cambiato, **quando**, e
**quali righe del registro precedono il cambiamento**.

---

## 2026-08-12 — l'handicap asiatico esce dal catalogo

**Cosa cambia:** la famiglia `handicap_asian` non viene più calcolata. Non è
solo esclusa dalla selezione come over/under: è proprio fuori dal catalogo dei
mercati, quindi non compare nemmeno fra i mercati alternativi della scheda.

**Perché:** non è una decisione statistica, ed è quella giusta lo stesso. Il
proprietario, che è anche il primo lettore, l'ha detta in una riga: «non lo
conosco e non mi piace». Su 207 pronostici pubblicati, 36 erano asiatici — il
17 per cento della produzione detto in una forma che chi la riceve non sa
leggere. Un numero corretto scritto in una lingua sbagliata non è un
pronostico.

**Non si perde informazione.** Le linee binarie asiatiche sono esattamente
equivalenti a mercati che restano: `ah_home_-0.5` è la vittoria casa,
`ah_home_+1.5` è un handicap europeo. Il raggruppamento in famiglie già le
trattava come lo stesso evento; togliendole, la scelta cade sulla formulazione
che il lettore conosce. L'handicap **europeo** resta: «Handicap -1 casa» è la
lingua delle schedine italiane.

**Effetto misurato sulla produzione:** 205 pronostici rigenerati, tasso di
silenzio al 28,0 % (dentro la banda 15–30 % del protocollo). Le famiglie si
ridistribuiscono su gol di squadra (84), doppia chance (46), 1X2 (35),
handicap europeo (27), entrambe segnano (9).

**Righe precedenti al cambiamento:** 293, di cui **33 su partite già
cominciate** — fra queste le 14 con esito — che **non sono state toccate**. Le
260 righe rimosse riguardavano tutte partite non ancora giocate, tutte in fase
preliminare, nessuna con un verdetto: rimuoverle non cancella nessuna prova e
non sposta di un bit i numeri di `accuracy.json`, che si calcolano sulle sole
righe giudicate. Lo script che l'ha fatto è
`scripts/migrazione_2026_08_12_handicap_asiatico.py` e dichiara le tre
condizioni che una riga deve soddisfare per essere rimossa.

**Cosa resta visibile:** tre pronostici asiatici sulle partite del 9 agosto,
tutti e tre già giudicati e tutti e tre usciti. Restano perché sono stati
davvero pubblicati e davvero giudicati: riscriverli è precisamente ciò che
questo prodotto rimprovera agli altri.

**Backtest:** rifatto. Il numero pubblicato prima del 12 agosto (86 su 100 su
4127 pronostici) era stato misurato con l'handicap asiatico nel catalogo, e
togliendo una famiglia cambia quale mercato viene scelto anche su partite il
cui pronostico era già un altro.

---

## 2026-08-12 — i prezzi di mercato si attaccano fuori da `finalize`

**Cosa cambia:** un job nuovo, `jobs/quote`, attacca le quote alle partite dei
prossimi quattordici giorni senza toccare pronostico, fase o registro. Il
campo `odds` guadagna `prices` (i prezzi lordi) e `market_p` (le probabilità
sgonfiate, estese a tutti i mercati che le quote determinano in modo esatto).

**Perché:** la colonna «mercato» del sito era vuota su **205 pronostici su
205**, per tre cause sovrapposte. Le quote si prendevano solo dentro la
finestra di `finalize` (10 partite su 283); la fonte gratuita quota 1X2 e
Over/Under mentre il pronostico scelto era sempre un altro mercato; e le
probabilità sgonfiate non venivano nemmeno salvate.

**Perché un job separato e non una finestra più larga.** `finalize` prende una
decisione irripetibile e va eseguito il più tardi possibile, quando le quote
sono più informative. Allargarne la finestra avrebbe riempito la colonna
peggiorando la decisione. Un prezzo è informazione e si riscrive ogni giorno;
una decisione si prende una volta sola.

**Effetto misurato:** da 0 a 21 pronostici su 205 con un confronto di mercato,
e da 10 a 60 partite con un prezzo. Il resto sono gol di squadra ed entrambe
segnano, che nessuna quota gratuita determina — e non si derivano per
somiglianza.

**Costo:** venti crediti al giorno con dieci campionati attivi, contro i 500
mensili del piano gratuito. Sopra il tetto entra in funzione la scala di
degradazione già esistente: prima escono i campionati minori, poi il mercato
dei totali.

**Effetto collaterale corretto:** `--dry-run` faceva chiamate di rete vere
senza poi salvare il contatore. Il contatore locale divergeva da quello del
fornitore, e la divergenza metteva in pausa il job — cioè un dry run poteva
spegnere le quote in produzione. Ora il contatore si salva sempre, e
`--reconcile` riallinea e toglie la pausa quando serve.

---

## 2026-08-11 — la famiglia over/under esce dalla selezione

**Cosa cambia:** over/under non può più essere il pronostico consigliato.
Resta calcolata, resta mostrata sulla scheda, resta confrontata con le quote.

**Perché:** il backtest del 2026-08-08 aveva pubblicato il risultato negativo
(log loss 0,69919 contro 0,68856 del tasso storico su Over 2.5). L'indagine su
sette configurazioni ha escluso emivita, correzione di Dixon-Coles e
troncamento: la stima per-partita dei gol totali semplicemente non porta
informazione. Dettaglio nell'emendamento del protocollo.

**Righe precedenti al cambiamento:** 280, di cui **11 con un pronostico
over/under** e 14 con un esito già registrato.

**Perché il registro non è stato azzerato.** Al cambio precedente (`S_min`, 8
agosto) fu azzerato: nessuna partita si era ancora conclusa e nessuno aveva
visto quelle righe. Qui no — ci sono esiti reali. Cancellarli sarebbe
esattamente ciò che il prodotto promette di non fare, e un track record che si
azzera quando fa comodo non è un track record. Le righe restano; questa voce
dice come leggerle.

---

## 2026-08-11 — i tau per famiglia sostituiscono il valore unico

**Cosa cambia:** lo shrinkage usa i `τ` misurati per ciascuna famiglia dal
backtest (da 0,021 sul risultato esatto a 0,119 su 1X2) invece del valore unico
0,08 per tutte.

**Perché:** 0,08 era il valore di partenza dichiarato dalla ricerca §5.3
*finché non esisteva un backtest*. Ora esiste, e lasciare il segnaposto quando
il dato c'è è una scelta, non un'omissione.

**Effetto atteso:** le famiglie con `τ` più basso del segnaposto (risultato
esatto, multigol, over/under) vengono riportate verso il riferimento più
aggressivamente, quindi vinceranno la selezione più di rado. È il
comportamento corretto: un `τ` piccolo significa che quella famiglia varia poco
fra una partita e l'altra, e uno scarto grande dalla media è più probabilmente
rumore.

---

## 2026-08-08 — `S_min` da 0,005 a 0,008

**Cosa cambia:** la soglia sotto la quale non si dà un pronostico.

**Perché:** il protocollo, scritto prima della corsa, prescrive di fissare il
tasso di silenzio obiettivo (25%) e di **leggere** la soglia dalla curva. Il
backtest ha misurato 26,0% a 0,008; a 0,005 il silenzio era al 17,4%.

**Righe precedenti:** azzerate. Erano 51, nessuna conclusa, nessuna mai
pubblicata.
