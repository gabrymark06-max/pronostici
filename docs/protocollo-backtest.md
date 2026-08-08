# Protocollo di backtest — pre-registrato

**Scritto il 2026-08-08, prima di eseguire il backtest e prima di guardare
qualunque risultato.** È il senso stesso del documento: ciò che rende
credibile un backtest non sono i suoi numeri, è che le regole siano state
fissate prima e non siano modificabili dopo.

Riferimenti: [brief.md §9.2 condizione 2](brief.md),
[research/selezione-pronostico.md §7](research/selezione-pronostico.md).

---

## 0. Perché esiste questo file

[Bailey, Borwein, López de Prado & Zhu (2014)](https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf)
mostrano che con cinque anni di dati bastano ~45 configurazioni indipendenti
perché sia quasi garantito produrre in-sample una strategia con Sharpe 1 e
Sharpe atteso out-of-sample **zero**. Noi abbiamo **due stagioni**, cioè un
budget statistico molto più stretto.

Conseguenza, dichiarata prima di iniziare:

> **Numero di configurazioni provate: 1.**
>
> I parametri sono quelli motivati a priori della ricerca §8.3. Non si fa
> grid search. `S_min` non è cercata: viene **letta** da una curva prodotta
> nella stessa singola esecuzione, con una regola scritta qui sotto prima di
> vederla.

Se questo numero dovesse cambiare, va aggiornato **qui**, con la data, e il
backtest va rieseguito da capo. Un numero non scritto rende il backtest non
interpretabile.

---

## 1. Cosa misura, e cosa non misura

**Misura:** il pronostico **preliminare**, quello da solo modello, con
`w = 1,0`.

**Non misura:** il pronostico definitivo. Le quote storiche non esistono nel
nostro archivio e non possono esistere: con 500 crediti al mese non si
ricostruisce il mercato di due stagioni passate. Il ramo `w = 0,35` del
sistema **non è validato storicamente**, e questo va scritto accanto a ogni
numero che ne derivi.

È una limitazione seria e la si dichiara invece di aggirarla. L'unica prova
che avremo sul ramo con le quote sarà il registro dal vivo, dove le due fasi
si misurano separatamente (brief §7.2).

---

## 2. Regola di walk-forward

1. **Griglia settimanale.** Le partite si valutano a blocchi di 7 giorni. Per
   ogni blocco `[d, d+7)` il modello è rifittato con `as_of = d`.
2. **Taglio stretto.** Nel fit entrano **solo** le partite concluse con data
   `< d`, dentro una finestra di 730 giorni. Una partita non può mai
   contribuire alla propria previsione (è il taglio già imposto da
   `dataset.build_dataset`, che è lo stesso codice della produzione).
3. **Anche il base rate è un parametro stimato.** Si ricalcola a ogni `d`
   sulle sole partite concluse prima di `d`, per campionato, accorciato verso
   la media multi-campionato con Bayes empirico. Usare la frequenza
   dell'intero dataset sarebbe look-ahead mascherato.
4. **Riscaldamento.** Un blocco si valuta solo se il campionato ha almeno
   **200 partite concluse** nella finestra di addestramento. Sotto quella
   soglia non si valuta e non si conta: non è un risultato scartato, è un
   periodo in cui il sistema, in produzione, non avrebbe parlato.
5. **Split.** La ricerca §7.1 chiede tre finestre disgiunte: fit del modello,
   fit del calibratore, valutazione. In v1 **non c'è un calibratore** (brief
   §10: la calibrazione si misura, non si corregge), quindi le finestre
   necessarie sono due, e il walk-forward le rende disgiunte per costruzione.
6. **Stesso codice della produzione.** Il backtest chiama `pipeline.score_fixture`,
   la stessa funzione che usano `score` e `finalize`. Se un giorno divergesse,
   il backtest non misurerebbe più il sistema che va online.

---

## 3. Parametri congelati

| Parametro | Valore | Origine |
|---|---|---|
| Emivita del decadimento | **365 giorni** | ricerca §8.3 |
| Finestra di addestramento | **730 giorni** | tutto lo storico disponibile |
| B (bootstrap) | **300 draw** | errore relativo sulla sd ≈ 4% |
| w (peso del modello) | **1,0** | nel backtest non ci sono quote |
| τ (sd a priori per famiglia) | **0,08** | valore iniziale, ricerca §8.3 |
| `p_min` | **0,50** | sicurezza, mai toccato |
| `σ_max` | **0,12** | sicurezza, mai toccato |
| `ρ_max` (clustering) | **0,80** | ricerca §8.3 |
| `max_goals` | **12** | massa troncata misurata e riportata |
| Passo di walk-forward | **7 giorni** | |
| Minimo per valutare | **200 partite** in addestramento | §2.4 |
| `S_min` | **da leggere**, vedi §4 | l'unica manopola |

I due parametri di sicurezza (`p_min`, `σ_max`) **non sono toccabili**. Se
mordono spesso, il problema è a monte nel modello e va sistemato il modello,
non la soglia (ricerca §10.2).

---

## 4. Regola di scelta di `S_min`, scritta prima di vedere la curva

Il backtest produce, per ogni partita valutata, il massimo punteggio fra i
candidati che superano i due filtri di sicurezza. Da lì si ottiene la
funzione *tasso di silenzio* → `S_min`, che è una lettura, non una ricerca.

**La regola, in quest'ordine:**

1. Si prende il valore di `S_min` il cui tasso di silenzio è **più vicino al
   25%**, sulla griglia `S_min ∈ {0,001, 0,002, ..., 0,050}`.
2. Il valore scelto deve cadere nella banda **15–30%**. Se la curva intera
   sta fuori dalla banda, **`S_min` non si muove**: resta a 0,005 e si
   restringe lo *scope* (brief §8.5), cioè si pubblicano solo le leghe e le
   famiglie che parlano. Non si abbassa il criterio per ottenere il numero
   che si voleva.
3. Il valore scelto si scrive in `model/selection.py` con la data e il
   riferimento a questo documento, e non si tocca più fino a una revisione
   annuale.

---

## 5. Regola di interruzione, scritta prima

`τ̂²` per famiglia si stima col metodo dei momenti:
`τ̂² = max(0, Var(p̂ − b) − media(σ²))`.

- Se `τ̂² ≤ 0` per una famiglia, quella famiglia **esce** dall'insieme dei
  candidati: la sua dispersione attorno al base rate è tutta rumore di stima.
- Se `τ̂² ≤ 0` su quasi tutte le famiglie, **il progetto si ferma** e la
  decisione torna all'utente: il prodotto onesto diventa una pagina di
  probabilità senza consigli (brief, rischio 1).

---

## 6. Metriche riportate

1. **Skill dichiarato contro skill realizzato** (ricerca §10.1) — la metrica
   di testa. Se il sistema è calibrato le due medie coincidono.
2. **Log loss** contro la baseline del base rate del campionato. Batterla è
   il minimo sindacale. (La seconda baseline, le quote sgonfiate, qui non
   esiste — vedi §1.)
3. **Hit rate per bucket** grossolano (0,50–0,65 / 0,65–0,80 / 0,80+) con `n`
   accanto a ciascuno.
4. **Tasso di silenzio** e curva silenzio ↔ `S_min`.
5. **Quante volte ha morso ciascun filtro.**
6. **`τ̂²` per famiglia.**

---

## 7. Separazione dal registro dal vivo

I numeri di questo backtest vivono in `data/backtest.json` e **non entrano
mai** in `data/accuracy.json`, che contiene solo pronostici pubblicati prima
della partita. Nessuna media fra i due, nessun grafico condiviso, mai.

Sulla pagina "Come stiamo andando" il registro dal vivo viene **prima**,
anche quando è quasi vuoto; il backtest sta sotto, con il suo titolo e con il
suo limite stampato accanto al numero:

> *Un backtest non è un track record: è la stessa persona che decide le regole
> e conta i punti. Per questo lo teniamo separato, e per questo abbiamo scritto
> le regole prima.*

---

## 8. Riproducibilità

```bash
python -m pronostici.jobs.backtest
```

Il file prodotto porta con sé: la data, l'hash del commit del codice che l'ha
generato, i parametri effettivamente usati e il conteggio delle
configurazioni. Chiunque abbia il repository può rieseguirlo e ottenere gli
stessi numeri: il seme del bootstrap è fissato.
