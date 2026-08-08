# Pagina: Come stiamo andando — `/come-stiamo-andando`

> Larghezza `--w-page` per le tabelle, `--w-prose` per i testi. Densità: **alta**.
> Sorgenti: `data/accuracy.json` (registro dal vivo) e `data/backtest.json` (prova storica).
>
> **Regola architetturale, non stilistica:** i due file non si incontrano mai. Componenti diversi,
> file diversi, nessuna prop condivisa, nessuna media, nessun grafico comune. Se un componente
> riceve entrambi, il componente è sbagliato.

## Ordine delle sezioni — l'ordine è il messaggio

Il registro dal vivo viene **prima**, anche quando è quasi vuoto. La cosa vera precede la cosa
grande.

### 1. Il numero in testa — skill dichiarato contro realizzato

Il titolo della pagina, non la curva di calibrazione (brief §14.6).

```
Come stiamo andando

Dicevamo di saperne tanto così.        ████████████████░░░░░░  0,079
Ne sapevamo davvero tanto così.        ███░░░░░░░░░░░░░░░░░░░  0,014
                                         └─ banda di incertezza in tratto

| Le due barre misurano quanta informazione i nostri pronostici
| portavano rispetto alla media del campionato. Se il sistema è
| calibrato coincidono. Se la seconda resta sotto, siamo stati
| troppo sicuri di noi.
n=147 · dal 1 settembre 2026
```

- Due barre **sullo stesso asse**, stessa larghezza massima, una sotto l'altra. Linguaggio A
  (pieno) per entrambe, perché sono la stessa grandezza misurata due volte; la banda di incertezza
  su `skill_realized` è linguaggio B (tratto), come ovunque.
- La riga di commento è obbligatoria e cambia con il segno del divario:
  *realizzato ≥ dichiarato* → *"Finora siamo stati leggermente prudenti."*
  *divario < 20%* → *"Finora le due misure coincidono."*
  *divario ≥ 20%* → **"Finora siamo stati più sicuri di quanto i risultati giustifichino."**
  Dirlo quando è sfavorevole è il punto dell'intera pagina.

**Avvio a freddo — `live.n < 100`.** Il blocco non si nasconde: si sostituisce con la propria
soglia dichiarata.
> *"Abbiamo pubblicato **{live.n}** pronostici dal {data}. Sono troppo pochi per questo confronto:
> compare da 100. Sotto ci sono i numeri grezzi, senza sintesi."*

Stesso contenitore, stesso filetto, stessa massa visiva — è lo stesso principio dello stato di
silenzio, applicato a una pagina. `accuracy.json` oggi ha `live.n = 0`: **questo è lo stato che si
vede il giorno del lancio, ed è quello da disegnare per primo su questa pagina.**

### 2. Il registro dal vivo — nudo

Compare da `n ≥ 1`. `<table>` con `<caption>` *"Ogni pronostico che abbiamo pubblicato prima della
partita."* Colonne: data · partita · fase · mercato · probabilità · esito.

- Cifre in Red Hat Mono tabellare. Righe alte 44px, divisori 1px `--rule-hair`.
- Esito: `uscito ▪` / `non uscito ▫` / `in attesa —`, parola + glifo + colore.
- Fase: chip di provenienza pieno/tratteggiato, lo stesso componente della scheda.
- I silenzi **sono nel registro**, con `nessun pronostico` in Newsreader corsivo e il glifo del
  motivo. Un registro che elenca solo i pronostici nasconderebbe metà della propria disciplina.
- Filtri: `<button aria-pressed>` per fase, esito, competizione. Filtrano righe **già presenti nel
  DOM**; senza JavaScript la tabella resta completa e leggibile. Nessun filtro è preselezionato.
- Sopra ~200 righe: paginazione con link reali (`?p=2`), non scroll infinito.

### 3. Hit rate per fascia

Compare da `n ≥ 150`. Tre righe, non un grafico:

| Fascia | Dicevamo (media) | È uscito | n |
|---|---|---|---|
| 50–65 | 57 su 100 | 56 su 100 | 405 |
| 65–80 | 75 su 100 | 76 su 100 | 540 |
| 80–100 | 91 su 100 | 92 su 100 | 3182 |

- Ogni riga porta una **mini-barra doppia** (dichiarato / osservato) sullo stesso asse: lo scarto si
  legge come disallineamento, senza dover leggere due numeri.
- **`enough: false` → riga in `--ink-muted`, tag mono `TROPPO POCHI`, e la barra sostituita da un
  filetto vuoto.** Non nascosta (brief §9.4, `schema.md`). Rifiutarsi di disegnare è a sua volta un
  dato, e va disegnato come tale.
- La curva di calibrazione a 5 punti compare solo da `n ≥ 500` con `n ≥ 50` per fascia. Prima non
  esiste — e la pagina lo dice: *"La curva di calibrazione compare da 500 pronostici. Ne mancano
  {500 − n}."*

### 4. Tasso di silenzio nel tempo

SVG inline, nessuna libreria. Barre settimanali (`silence.rate`), asse y 0–50%.

**Elemento che nessun concorrente ha: la banda obiettivo dichiarata.** Una fascia orizzontale
`--paper-alt` con filetti 1px fra 15% e 30% (`backtest.json.silence.band`), etichettata
*"banda che ci siamo dati"*, più una linea 1px al 40% etichettata *"limite duro"*. Promessa e
realtà sullo stesso asse.
Sotto: la ripartizione per motivo (`by_reason`) come tre cifre mono con i loro glifi `≈ ± <`.
Accessibilità: `<figure>` + `<figcaption>` che riassume l'andamento a parole, e una `<table>` con
gli stessi dati in `<details>` — il grafico non è mai l'unico portatore.

### 5. La barra verso i 500

Terzo trattamento, distinto da entrambi i linguaggi: non è una probabilità e non è un'affidabilità.

```
51 ─────────────────────────────────────────────── 500
   ███████░│░░░░░░░│░░░░░░░│░░░░░░░│░░░░░░░│         ← tacche ogni 100
| Da 500 pronostici dal vivo, questa pagina mostrerà quelli.
| Il backtest resterà sotto, per confronto.
```

Riempimento `--ink-2` (non `--prob-fill`), altezza 8px, tacche mono ogni 100. `role="img"` con
`aria-label="51 pronostici pubblicati su 500."` La barra è essa stessa un dispositivo di fiducia:
è una scadenza che il prodotto si dà in pubblico.

### 6. La separazione — deve essere impossibile da confondere

```
════════════════════════════════════════════════════  4px --rule-heavy, piena larghezza
PROVA STORICA (BACKTEST)                              ← Newsreader 600 --fs-display-l
                                                      ← da qui in giù: fondo --paper-alt
```

Da questo punto la sezione ha **un fondo diverso** (`--paper-alt`), un titolo proprio e una
larghezza propria. Visivamente è un altro documento dentro la stessa pagina. Nessun elemento
grafico è condiviso con le sezioni 1–5.

### 7. La prova storica

**Prima i numeri, il limite.** Testo di apertura, `--fs-body`, non un asterisco, non un
`<details>` (brief §9.6):
> *"Un backtest non è un track record: è la stessa persona che decide le regole e conta i punti.
> Per questo lo teniamo separato, e per questo abbiamo scritto le regole prima. Il numero che conta
> è quello sopra."*

Poi, in mono, la ricevuta — sono i campi che rendono il backtest interpretabile e vanno stampati,
non messi in una FAQ:

```
configurazioni provate    1
commit del codice         7d6ff3e   → link al repo
generato il               8 agosto 2026
protocollo                docs/protocollo-backtest.md →
non misurato              il ramo con le quote (w = 0,35): le quote storiche non
                          esistono nel nostro archivio e con 500 crediti al mese
                          non possono esistere
misura                    solo il pronostico preliminare, w = 1,0
```

Poi: fasce (`buckets`), per competizione (`per_competition`, con `silence_rate` accanto a
`hit_rate` — sono la stessa storia), tabella dei parametri, e la curva silenzio↔`S_min` con
`chosen_s_min` marcato da una tacca verticale etichettata *"la soglia che abbiamo scelto, e poi
congelata"*.

**Onestà obbligata:** `log_loss_over_2_5.model_better = false` va stampato, non omesso.
*"Su Over 2.5 il nostro modello non batte il tasso base del campionato. Lo diciamo perché è vero, ed
è una delle ragioni per cui tacciamo spesso."* Nascondere il dato sfavorevole in una pagina che
esiste per mostrare i dati sfavorevoli sarebbe l'unico errore fatale possibile qui.

## Anti-pattern specifici di questa pagina

- ❌ Un numero di `accuracy.json` e uno di `backtest.json` nella stessa tabella, barra o media
- ❌ Un'accuratezza aggregata senza la fascia accanto
- ❌ Nascondere una fascia con `enough: false`
- ❌ Nascondere `model_better: false`
- ❌ La curva di calibrazione mostrata prima di `n ≥ 500`
- ❌ Il backtest sopra il registro dal vivo, per qualunque motivo
- ❌ Le parole ROI, rendimento, profitto, "value"
