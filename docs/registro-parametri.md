# Registro dei cambi di parametro

Il registro dei pronostici è **append-only**: una riga pubblicata non si
riscrive mai. Ma i parametri con cui quelle righe sono state prodotte possono
cambiare, e senza una data quel cambiamento rende il registro non
interpretabile — due righe con la stessa forma potrebbero venire da due sistemi
diversi.

Questo file è quella data. Ogni voce dice **cosa** è cambiato, **quando**, e
**quali righe del registro precedono il cambiamento**.

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
