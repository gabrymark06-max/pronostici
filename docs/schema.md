# Lo schema di `data/` — il contratto col frontend

`schema_version` corrente: **1**.

Il frontend non sa niente di Dixon-Coles; il backend non sa niente di React.
Il confine fra i due è **questo file**, e va cambiato solo con un bump
esplicito di `schema_version` annunciato qui.

**Regola di compatibilità:** aggiungere una chiave è compatibile e non alza la
versione; rinominarla, toglierla o cambiarne il significato la alza. Il
frontend deve fallire forte se `schema_version` non è quella che si aspetta,
invece di degradare in silenzio.

---

## `data/fixtures/{YYYY-MM-DD}.json`

Un file per giorno. È quello che la home legge.

```jsonc
{
  "schema_version": 1,
  "date": "2026-08-22",
  "generated_at": "2026-08-21T10:00:00Z",
  "silence_count": 3,       // quante partite del giorno senza pronostico
  "total": 14,
  "fixtures": [ /* ordinate per orario */ ]
}
```

### Una `fixture`

| Campo | Tipo | Note |
|---|---|---|
| `match_id` | int | identificativo football-data, stabile |
| `competition` | string | codice di `competitions.py` |
| `utc_date` | string | ISO 8601 con `Z` |
| `matchday` | int \| null | |
| `home`, `away` | `{name, tla, crest}` | `crest` è una URL di logo |
| `phase` | `"preliminary"` \| `"definitive"` | |
| `source` | `"model_only"` \| `"blended_with_odds"` | il badge di provenienza |
| `model_weight` | float | `1.0` oppure `0.35` |
| `expected_goals` | `{home, away}` | |
| `reasons` | string[] | 2–4 frasi già in italiano, pronte da mostrare |
| `raw_probabilities` | oggetto | 1X2, over/under 2.5, BTTS — **sempre presenti**, anche quando si tace |
| `diagnostics` | oggetto | `n_candidates`, `n_clusters`, `filter_bites`, `truncated_mass` |
| `prediction` | oggetto \| **null** | null = si tace |
| `silence` | `{reason}` \| null | valorizzato se e solo se `prediction` è null |
| `half_time` | oggetto | facoltativo: mercati primo tempo e HT/FT |
| `transition` | string | solo in fase `definitive` |
| `previous` | oggetto | solo in fase `definitive` |
| `odds` | oggetto | prezzi e probabilità di mercato — vedi sotto |
| `result` | `{home, away}` | comparso dopo il fischio finale |
| `outcome` | 0 \| 1 | il pronostico si è avverato |

`prediction` e `silence` sono **mutuamente esclusivi**. Il silenzio è un tipo
di prima classe, non un ramo `else`: va modellato nei tipi.

### `odds`

Presente su ogni partita per cui abbiamo letto le quote — non solo in fase
`definitive`. Le due cose sono separate da quando esiste `jobs/quote`: attaccare
un prezzo è informazione e si rifà ogni giorno, finalizzare è una decisione e si
fa una volta sola.

```jsonc
{
  "n_bookmakers": 23,
  "markets": ["1x2_away", "1x2_draw", "1x2_home", "over_2.5", "under_2.5"],

  // ① I PREZZI LORDI, margine incluso. Le nostre chiavi, non le loro.
  //    Solo i cinque mercati quotati direttamente dalla fonte gratuita.
  //    Sono l'unico numero che qualcuno possa davvero giocare.
  "prices": { "1x2_home": 2.33, "over_2.5": 2.05 },
  "price_scope": "it",          // "it" = operatori ADM, "eu" = mediana europea
  "price_books": 1,

  // ② LE PROBABILITA SGONFIATE, estese a tutti i mercati che le quote
  //    determinano in modo ESATTO: undici chiavi a partire da cinque quote.
  //    Le tre doppie chance sono somme di esiti 1X2; l'handicap europeo ±1 e
  //    il multigol 0-2 hanno la stessa maschera di un mercato già coperto.
  //    Nessuna approssimazione: è la stessa estensione che usa il modello.
  "market_p": { "1x2_home": 0.5742, "dc_x2": 0.4259, "under_2.5": 0.4159 },

  // ③ Solo dopo `finalize`: il margine misurato al momento della decisione.
  "devig": { "h2h": 1.061, "totals_2.5": 1.11 },
  "fetched": "network"
}
```

**Cosa il frontend deve tenere distinto.** `1/market_p[k]` è la quota **equa**
del mercato e si confronta pari a pari con la nostra `1/p`. `prices[k]` è il
prezzo **lordo** e non si confronta con la nostra quota equa: il margine
farebbe sembrare il mercato sistematicamente più avaro di quanto sia. Un
mercato può avere `market_p` senza `prices` — è il caso normale per la doppia
chance, che il mercato determina ma nessuno ci quota direttamente.

**Cosa NON c'è, e non si deriva.** Gol di squadra, entrambe segnano e multigol
stretti non sono determinati da 1X2 + over/under: su quelle scommesse entrambi
i campi sono assenti, e restano assenti.

### `prediction`

```jsonc
{
  "key": "over_1.5",            // chiave di mercato, stabile
  "family": "over_under",
  "label": "Over 1.5",          // etichetta italiana pronta
  "p": 0.7169,                  // DOPO shrinkage — l'unica mostrabile
  "p_raw": 0.7717,              // stima grezza: NON mostrare mai
  "sigma": 0.0564,
  "band_p5": 0.6698,            // banda bootstrap
  "band_p95": 0.8633,
  "shrink_alpha": 0.67,         // quanto peso ha avuto la stima
  "reference": 0.6066,          // base rate, o quota sgonfiata se ci sono quote
  "score": 0.026628,            // divergenza KL, in nats
  "cluster_members": ["eh_-1_away", "dc_x2"],
  "runners_up": [ /* stessa forma, altri cluster */ ]
}
```

### `silence.reason`

Tre valori, e mappano uno a uno sui tre testi dell'interfaccia (brief §8.4).
Non è un booleano proprio perché i tre messaggi sono diversi:

| `reason` | Significa | Testo |
|---|---|---|
| `S_min` | nessun candidato porta informazione | *"Il nostro modello dice quasi esattamente quello che dice già la media del campionato."* |
| `sigma_max` | stima troppo instabile | *"Abbiamo troppe poche partite affidabili su [squadra] per dare un numero in cui crediamo."* |
| `p_min` | l'unica differenza è troppo improbabile | *"Quello che vediamo di diverso è troppo improbabile perché ve lo consigliamo."* |
| `no_candidates` | nessun mercato calcolabile (caso raro) | trattare come `S_min` |

### `transition` e `previous` (solo fase definitiva)

| `transition` | Significa |
|---|---|
| `first` | non c'era un preliminare da confrontare |
| `confirmed` | le quote confermano lo stesso mercato |
| `changed` | il consiglio è cambiato |
| `prediction_to_silence` | avevamo un consiglio, lo ritiriamo |
| `silence_to_prediction` | tacevamo, ora abbiamo qualcosa |
| `still_silent` | tacevamo e continuiamo a tacere |

`previous` porta `{phase, written_at, market_key, market_label, p, silence_reason}`.
La frase pronta è già la prima voce di `reasons`.

Le due transizioni che cambiano stato sono, per il brief §7.3, le schermate
che guadagnano più fiducia dell'intero prodotto. Non sono un caso limite.

---

## `data/ledger/{stagione}.jsonl`

Append-only, una riga JSON per pronostico. **Due righe permanenti per
partita**: `preliminary` e `definitive`. Il preliminare non viene mai
cancellato né riscritto.

`prediction_id` = `"{match_id}:{phase}"`, deterministico: rieseguire un job
non crea righe nuove.

Stessi campi della `prediction`, più: `phase`, `written_at`, `source`,
`model_weight`, `silence_reason`, `filter_bites`, `transition`,
`previous_market_key`, `previous_market_label`, `previous_p`,
`skill_declared`.

Dopo la partita, e **solo** dopo, `settle` riempie `outcome`, `ft_home`,
`ft_away`, `skill_realized`, `settled_at`. È l'unica scrittura non-append del
sistema, può toccare solo quei cinque campi, e solo quando valgono ancora
`null`.

---

## `data/accuracy.json`

Il contenuto della pagina "Come stiamo andando". Contiene **solo** pronostici
pubblicati prima della partita.

```jsonc
{
  "live":     { "n", "skill_declared_mean", "skill_realized_mean",
                "skill_realized_se", "calibration_gap", "hit_rate", "buckets" },
  "by_phase": { "preliminary": {...}, "definitive": {...} },
  "silence":  { "preliminary": {"n","silent","rate","by_reason"}, "definitive": {...} },
  "transitions": { "changed": 12, "confirmed": 30, ... },
  "progress_to_500": { "published": 147, "target": 500 }
}
```

`skill_declared_mean` contro `skill_realized_mean` è **il numero in testa alla
pagina**. Se il sistema è calibrato le due medie coincidono; se il realizzato
resta sotto, siamo sovraconfidenti.

Ogni `bucket` porta `enough: false` sotto 30 osservazioni: va mostrato in
grigio con "troppo pochi", **non nascosto**.

---

## `data/backtest.json`

I numeri della "Prova storica". Prodotto da `jobs/backtest.py` secondo
[protocollo-backtest.md](protocollo-backtest.md).

**Non va mai aggregato con `accuracy.json`.** Sezione separata, titolo
separato, e il limite stampato accanto al numero. Porta con sé
`configurations_tried`, `code_commit` e `not_measured` proprio perché il
frontend possa stamparli.

---

## `data/leagues/{codice}/params.json`

Parametri e 300 draw bootstrap per campionato. **Il frontend non lo legge**:
è input dei job. Pesa qualche centinaio di kB per campionato.

## `data/archive/{codice}/{stagione}.json`

Ogni partita mai ingerita. La finestra gratuita di football-data scorre; senza
questo archivio lo storico si accorcerebbe da solo. Il frontend non lo legge.

## `data/odds_budget.json`

Contatore dei crediti quote del mese, con tetto, stato di pausa e gradino di
degradazione attivo. Può essere mostrato in "Come funziona": è una dichiarazione
di trasparenza, non un dato interno.
