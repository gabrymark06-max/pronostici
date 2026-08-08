# Come si sceglie UN solo pronostico per partita

**Decisione da sbloccare:** con quale criterio statistico si ordina un insieme di ~11 mercati correlati, derivati dalla stessa matrice di gol, per sceglierne **uno** da consigliare — funzionando sia con le quote sia senza, e rispettando il vincolo *"se è presente una value bet alta ma è veramente difficile che esca, non gliela consigliamo"*.

**Data della ricerca: 2026-08-08.** Fonti primarie (paper con DOI/arXiv, documentazione ufficiale). Dove non ho potuto verificare, è scritto in fondo, nella sezione "Non verificato".

---

## Risposta in una riga

Ordina i mercati con la **divergenza di Kullback-Leibler fra la probabilità del modello (dopo shrinkage) e una probabilità di riferimento** — le quote sgonfiate dal margine dove esistono, la frequenza storica del mercato dove non esistono. Non è un'euristica: è **esattamente** il tasso di crescita logaritmica ottimale di Kelly, che è la quantità che penalizza da sola i pronostici improbabili, senza bisogno di aggiungere un filtro arbitrario.

A parità di vantaggio del 10%, il punteggio cade di **124 volte** passando da un pronostico al 75% a uno al 2%. Il vincolo di prodotto dell'utente non va imposto: è già dentro la matematica.

---

## 1. Perché l'edge grezzo inganna

### 1.1 Il favourite-longshot bias, misurato sul calcio

L'evidenza quantitativa più recente e più direttamente utilizzabile è in **[Forecast Sports Outcomes under Efficient Market Hypothesis (arXiv:2604.17194)](https://arxiv.org/html/2604.17194)**: 90.014 partite di calcio, stagioni 2012–2024, 5 bookmaker (Bet365, Bet&Win, Interwetten, Pinnacle, William Hill), dati da football-data.co.uk.

Il metodo *power* converte le quote in probabilità come

```
q_i = (1/o_i)^β  ,  con β scelto in modo che Σ_i (1/o_i)^β = 1
```

Con β = 1 si ricade nella normalizzazione ingenua. Il paper riporta le costanti β stimate:

| Bookmaker | β stimato |
|---|---|
| Pinnacle | 1.06 |
| Bet365 | 1.08 |
| Bet&Win | 1.12 |
| William Hill | 1.12 |
| Interwetten | 1.15 |

> "the optimal power constant for our proposed FL-GLM is greater than 1 for all bookmakers" — β > 1 misura la quantità di favourite-longshot bias; più grande β, più forte il bias.

**Cosa significa per noi, concretamente:** se sgonfi il margine con la normalizzazione ingenua (dividere ogni 1/o per la somma), **sovrastimi la probabilità equa dei longshot**. Cioè fabbrichi vantaggio finto esattamente sui mercati dove il vantaggio è più difficile da avere. È il modo più semplice per costruire un sistema che sembra trovare value bet e non ne trova nessuna.

Il paper segnala anche un effetto secondario: i metodi che correggono il FLB **sottostimano il pareggio**, cioè il bias sull'1X2 non è uniforme fra esiti.

Il fenomeno è documentato in tutta la letteratura sui mercati a quota fissa — vedi ad esempio [Whelan, *Risk aversion and favourite–longshot bias in a competitive fixed-odds betting market*, Economica 2024](https://onlinelibrary.wiley.com/doi/10.1111/ecca.12500) e la rassegna [*Are Sports Bettors Biased toward Longshots, Favorites, or Both?*, Risks 9(1):22, 2021](https://www.mdpi.com/2227-9091/9/1/22) (pagina restituita HTTP 403 alla verifica diretta; citata come lead, non come prova).

### 1.2 L'errore relativo esplode sulle probabilità piccole

Questo è il punto più importante, e vale **anche senza quote**. Un calcolo mio, riproducibile, sulla nostra situazione: 2 stagioni, ~760 partite per campionato, 76 partite per squadra.

Con decadimento esponenziale a emivita di un anno su una finestra di 730 giorni, la dimensione campionaria efficace per squadra è **65,8 partite su 76** (con emivita 180 giorni scende a 47,9). Dall'informazione di Fisher di un Poisson, l'errore standard sul logaritmo della forza d'attacco è circa `1/√(n_eff · λ)` ≈ 0,10–0,14. Sommando attacco e difesa delle due squadre, `SE(log μ_totale) ≈ 0,15`. Propagata:

| SE(log μ) | intervallo di μ (centro 2,70) | P(Over 2.5) |
|---|---|---|
| 0,10 | 2,44 – 2,98 | 0,442 – 0,573 |
| **0,15** | **2,32 – 3,14** | **0,410 – 0,607** |
| 0,20 | 2,21 – 3,30 | 0,380 – 0,640 |

**Una banda a una sigma di ±10 punti percentuali su Over 2.5.** Un "vantaggio" di 5 punti sul mercato è dentro il rumore. Questo è il numero che deve governare tutto il design: con 2 stagioni, la maggior parte delle differenze fra la nostra probabilità e quella di riferimento **non è informazione, è varianza campionaria**.

> Questi valori sono una stima di ordine di grandezza, derivata da me, non un risultato citato. Vanno sostituiti dalla deviazione standard bootstrap vera (§5.2), che è economica da calcolare.

---

## 2. Kelly: si può usare per **ordinare**, non solo per dimensionare

### 2.1 Le formule

Da **[Chu, Wu, Swartz, *Modified Kelly criteria*, JQAS 2018](https://degruyterbrill.com/document/doi/10.1515/jqas-2017-0122/html?lang=en)** ([PDF aperto](https://www.sfu.ca/~tswartz/papers/kelly.pdf)), che riporta la proposizione di Kelly (1956) in forma esplicita, eq. (3):

```
k(p) = (pθ − 1)/(θ − 1)   se p > 1/θ
       0                   altrimenti
```

con `θ` = quota decimale europea. Il tasso di crescita atteso è

```
G(f) = p·log(1 + f(θ−1)) + (1−p)·log(1 − f)
```

Per portafogli di scommesse simultanee, da **[Hubáček, Šourek, Železný, *Optimal sports betting strategies in practice: an experimental review*, IMA J. Management Mathematics 2021, DOI 10.1093/imaman/dpaa029, arXiv:2107.08827](https://arxiv.org/abs/2107.08827)**:

```
maximize  E[log(O · f)]   subject to  Σ f_i = 1,  f_i ≥ 0
```

**Kelly frazionale** (eq. 5.1 dello stesso paper): `f_ω = ω·f_{1..n−1} + (1−ω)·f_n`, con `f_n` = contante. Per ω = 0,5 è il famoso "half-Kelly".

**Kelly con vincolo di drawdown** (eq. 5.2): `P(W_t^min < α) ≤ β`. La formulazione convessa esatta è in **[Busseti, Ryu, Boyd, *Risk-Constrained Kelly Gambling*, arXiv:1603.06183](https://arxiv.org/abs/1603.06183)**:

```
maximize  E log(rᵀb)
s.t.      1ᵀb = 1,  b ≥ 0
          E (rᵀb)^(−λ) ≤ 1       con  λ = log β / log α
```

Se questo vincolo convesso è soddisfatto, allora `Prob(W^min < α) < β`. λ è un parametro di avversione al rischio: λ→0 riporta a Kelly puro, λ→∞ forza scommesse prive di rischio.

**Kelly distribuzionalmente robusto** (eq. 5.5–5.6): `maximize min_{p∈Π} Σ p_i log(O_i·f)` con insieme di ambiguità a scatola `Π = {p_i : |p_i − P̂(r_i)| ≤ η·P̂(r_i)}`.

### 2.2 L'evidenza empirica che conta di più

Sempre Hubáček et al., dataset **calcio: 32.000 partite, 3 esiti, margine 3%, modello in svantaggio KL rispetto al bookmaker (AKL ≈ −0,013)** — cioè un modello serio (rete neurale su statistiche dettagliate, quote di chiusura Pinnacle) resta **peggio del mercato**. Risultati (Tabella 7):

| strategia | mediana(W_f) | rovina % |
|---|---|---|
| Kelly puro | 2,3e−09 | **100** |
| MSharpe puro | 1,8e−10 | **100** |
| KellyFrac | 10,05 | 0 |
| KellyDrawdown | 10,25 | 0 |
| KellyRobust | 6,2 | 0 |

Conclusione del paper: *"an adaptive variant of the popular fractional Kelly method is a very suitable choice across a wide range of settings"*, e le strategie ottimali in forma pura *"often led to ruin instead of maximal profit"*.

Due lezioni dirette per noi:
1. **Un modello su 2 stagioni sarà quasi certamente peggio del mercato.** Se una rete neurale su dati ricchi è in svantaggio KL contro Pinnacle, un Dixon-Coles su 760 partite lo è di più. Il prodotto non deve promettere di battere il mercato.
2. **Kelly puro non è usabile.** Nemmeno come ordinatore, se applicato alle probabilità grezze.

### 2.3 L'incertezza sul parametro: cosa fa e cosa non fa

Risultato importante e controintuitivo, da Chu-Wu-Swartz eq. (14)–(15). Con perdita logaritmica e prior `p ~ Beta(a,b)`, il posteriore è `p|x ~ Beta(x+a, n−x+b)` e il Bayes estimator della frazione è

```
f₀ = (p̂θ − 1)/(θ − 1)   con  p̂ = (x+a)/(n+a+b)  = media a posteriori
```

cioè **Kelly valutato sulla media a posteriori**. La formula non cambia. Motivo: `G(f)` è lineare in p, quindi l'attesa a posteriori dipende solo dalla media.

> **Conseguenza operativa, non negoziabile:** lo shrinkage va fatto **sulla probabilità**, non sulla frazione di Kelly. Se costruisci correttamente la media a posteriori, poi usi la formula normale. Aggiungere un fattore frazionale ω è una difesa *ulteriore* contro l'errore di modello (non contro l'errore di stima), ed è quella che l'evidenza empirica di §2.2 giustifica.

[Baker & McHale, *Optimal Betting Under Parameter Uncertainty: Improving the Kelly Criterion*, Decision Analysis 10(3):189–199, 2013, DOI 10.1287/deca.2013.0271](https://pubsonline.informs.org/doi/abs/10.1287/deca.2013.0271) arriva alla stessa direzione per via frequentista, imponendo `k·s*(q)` con `0 < k < 1` e studiando quanto vale k. Non ho potuto leggere la formula esatta (paywall) — la descrizione qui è quella data da Chu-Wu-Swartz §1.

---

## 3. Il teorema che unifica tutto

Questa è la parte che risolve il problema, e viene da **Cover & Thomas, *Elements of Information Theory*, cap. 6 "Gambling and Data Compression"** ([PDF del capitolo](https://ftp.esat.kuleuven.be/pub/SISTA/decock/voor_xander/referenties/Cover&Thomas/6.pdf)).

Teorema 6.1.2 (il gioco proporzionale è log-ottimale):
```
W*(p) = Σ p_i log o_i − H(p)          (6.10)
```

Ed eq. (6.16)–(6.18), quando le quote sono eque rispetto a una distribuzione `r_i = 1/o_i`:

```
W(b, p) = D(p‖r) − D(p‖b)             (6.18)
```

> "the doubling rate is the difference between the distance of the bookie's estimate from the true distribution and the distance of the gambler's estimate from the true distribution. Hence the gambler can make money only if his estimate is better than the bookie's"

Teorema 6.1.3 (conservazione): `W*(p) + H(p) = log m`. *"Low entropy races are the most profitable."*
Teorema 6.2.1: l'aumento del tasso di crescita dovuto a informazione laterale è **esattamente l'informazione mutua** `I(X;Y)`.

### 3.1 Il caso binario: G* = KL, esattamente

Per una singola scommessa binaria con la possibilità di tenere contante, ho verificato algebricamente che

```
f* = (po − 1)/(o − 1)
G* = p·ln(po) + (1−p)·ln(o(1−p)/(o−1))
   = p·ln(p/q) + (1−p)·ln((1−p)/(1−q))
   = D(p ‖ q)                            con q = 1/o
```

(passaggio chiave: `(o−1)/o = 1 − q`.)

**Il tasso di crescita ottimale di Kelly su una scommessa binaria È la divergenza KL fra la tua probabilità e quella implicita nella quota.** Non un'approssimazione. Questa singola identità dà simultaneamente: un ordinatore, un dimensionatore, e una misura di informazione.

### 3.2 La verifica numerica del vincolo di prodotto

Vantaggio fissato al 10% (`p·o − 1 = 0,10`), al variare della probabilità (calcolo mio, riproducibile in tre righe di Python):

| p | quota o | Kelly f* | Sharpe della singola | **Score = G\* = KL (nats)** |
|---|---|---|---|---|
| 0,75 | 1,47 | 0,2143 | 0,1575 | **0,011192** |
| 0,50 | 2,20 | 0,0833 | 0,0909 | **0,004149** |
| 0,30 | 3,67 | 0,0375 | 0,0595 | **0,001838** |
| 0,15 | 7,33 | 0,0158 | 0,0382 | **0,000768** |
| 0,05 | 22,0 | 0,0048 | 0,0209 | **0,000231** |
| 0,02 | 55,0 | 0,0019 | 0,0130 | **0,000090** |

Stesso vantaggio del 10%. Il punteggio cade di **124 volte**. Il "value bet alto ma difficile che esca" viene declassato automaticamente, senza una soglia inventata.

(Lo Sharpe della singola scommessa, per completezza: `E[R] = po − 1`, `Var[R] = p(1−p)o²`, quindi `Sharpe = (po−1)/(o√(p(1−p)))`. Ordina in modo simile ma è meno interpretabile e non è additivo su più partite. Vedi §6.)

### 3.3 E senza quote?

Stessa formula, altro riferimento. Se non c'è quota, il "bookmaker" contro cui misuri l'informazione è **chi non sa nulla della partita specifica e usa la frequenza storica del mercato**. Cioè `q = base rate`. Il punteggio diventa "quanta informazione ho su questa partita, oltre a quella che avrei senza guardarla".

Verifica sul caso che l'utente ha in mente (calcolo mio, base rate plausibili):

| Mercato | p modello | base rate | lift (p/b) | **Score KL** |
|---|---|---|---|---|
| Over 0.5 | 0,970 | 0,965 | 1,005 | **0,00039** |
| Multigol 2-4 | 0,600 | 0,550 | 1,091 | **0,00509** |
| BTTS | 0,580 | 0,510 | 1,137 | **0,00985** |
| Over 1.5 | 0,850 | 0,790 | 1,076 | **0,01175** |
| 1X | 0,780 | 0,710 | 1,099 | **0,01257** |
| Risultato esatto 2-1 | 0,110 | 0,075 | 1,467 | **0,00780** |
| Home win | 0,550 | 0,450 | 1,222 | **0,02007** |
| **Over 2.5** | 0,620 | 0,520 | 1,192 | **0,02028** |

Guarda le due righe che contano:
- **"Over 0.5 al 97%"**: confidenza altissima, punteggio 0,0004 — praticamente zero. Formalizza esattamente ciò che l'utente intende con "non dice niente".
- **"Risultato esatto 2-1"**: il lift più alto della tabella (+47%), ma punteggio 0,0078 — sotto Over 1.5 e sotto 1X. Il longshot con grande vantaggio relativo perde contro il pronostico probabile con vantaggio modesto.

**Lo stesso identico codice serve i due casi. Cambia solo `q`.** È esattamente la degradazione sensata richiesta.

---

## 4. Calibrazione

### 4.1 Come si misura

La decomposizione di Murphy del Brier score, riportata testualmente in **[Ferro & Fricker, *A bias-corrected decomposition of the Brier score*, Q. J. R. Meteorol. Soc. 2012, DOI 10.1002/qj.1924](https://empslocal.ex.ac.uk/people/staff/ferro/Publications/ferro-fricker2012copyright.pdf)**, eq. (1)–(4):

```
B = REL − RES + UNC

REL = Σ_k (n_k/n)(π_k − x̄_k)²      reliability   (0 = perfetta)
RES = Σ_k (n_k/n)(x̄_k − x̄)²        resolution    (0 = pessima)
UNC = x̄(1 − x̄)                     incertezza climatologica
```

`REL` è la calibrazione. **`RES` è l'informatività** — è la formalizzazione aggregata di ciò che il nostro score KL misura sulla singola previsione. È la ragione per cui "Over 0.5 al 97%" non vale niente: perfettamente affidabile, risoluzione nulla.

**Trappola che ci riguarda direttamente**, dallo stesso paper, eq. (7)–(9): con n finito i tre termini sono **distorti**. La reliability è *sovrastimata*, l'uncertainty *sottostimata*, la resolution di solito *sovrastimata*:

```
bias(REL) = (1/n) Σ_k ν_{k,n} μ_k(1 − μ_k)  ≥ 0
bias(UNC) = − μ(1 − μ)/n                     ≤ 0
```

Con 760 partite per campionato per stagione e binning in ~10 bin, questi bias non sono trascurabili. La decomposizione corretta proposta, eq. (11)–(12):

```
REL' = REL − (1/n) Σ_{k∈K1} [n_k/(n_k−1)] x̄_k(1 − x̄_k)
RES' = RES − (1/n) Σ_{k∈K1} [n_k/(n_k−1)] x̄_k(1 − x̄_k) + x̄(1 − x̄)/(n−1)
```

Un decomposizione non distorta è dimostrata **impossibile**; questa ha bias minore. Usa questa, non quella standard.

### 4.2 Quale regola di punteggio

Contesa aperta in letteratura, e va risolta esplicitamente:

- **[Constantinou & Fenton, JQAS 8(1), 2012](https://econpapers.repec.org/article/bpjjqsprt/v_3a8_3ay_3a2012_3ai_3a1_3an_3a12.htm)** sostengono l'RPS perché 1X2 è una scala ordinale (il pareggio è "più vicino" alla vittoria casa che alla vittoria ospite).
- **[Wheatcroft, *Evaluating probabilistic forecasts of football matches: the case against the Ranked Probability Score*, JQAS, arXiv:1908.08980](https://arxiv.org/abs/1908.08980)** ribatte che la sensibilità alla distanza *"contributes nothing to achieving the actual objectives of scoring rules"* e trova sperimentalmente che **l'ignorance score (logaritmico) batte sia RPS sia Brier** nel discriminare i modelli.

**Decisione:** usa il **log loss** come metrica primaria — è locale, è la regola coerente con il nostro score (che è espresso in nats), e ha l'evidenza sperimentale a favore. Riporta anche Brier con decomposizione Ferro-Fricker, perché è quella che ti dà reliability e resolution separate. L'RPS solo sull'1X2, se lo vuoi per confrontarti con la letteratura.

### 4.3 Come si corregge

Dalla **[documentazione ufficiale scikit-learn 1.9.0, `modules/calibration`](https://scikit-learn.org/stable/modules/calibration.html)**:

> "Overall, `'isotonic'` will perform as well as or better than `'sigmoid'` when there is enough data **(greater than ~ 1000 samples)** to avoid overfitting."

> "The sigmoid method ... is most effective for small sample sizes or when the un-calibrated model is under-confident"

> "`CalibratedClassifierCV` uses a cross-validation approach to ensure unbiased data is always used to fit the calibrator."

E sull'uso del Brier come metrica di calibrazione:

> "A lower Brier loss ... does not necessarily mean a better calibrated model, it could also mean a worse calibrated model with much more discriminatory power."

**Terza opzione, migliore per il nostro caso:** la **beta calibration** di **[Kull, Silva Filho, Flach, AISTATS 2017, PMLR v54](https://proceedings.mlr.press/v54/kull17a.html)**:

```
μ_beta(s; a,b,c) = 1 / (1 + 1/( e^c · s^a / (1−s)^b ))
```

Si stima chiamando una **regressione logistica sulle feature `log(s)` e `−log(1−s)`** (§3.3 del paper: "reduce these tasks to fitting logistic regression in a different feature space"). Tre parametri, quindi robusta su pochi dati, ma — a differenza di Platt — **contiene la funzione identità** (a = b = 1, c = 0) e può correggere distorsioni *inverse-sigmoidali*, cioè probabilità troppo estreme. Che è esattamente il difetto atteso di un Dixon-Coles su pochi dati sui mercati derivati.

Dal paper: *"logistic calibration can easily uncalibrate a perfectly calibrated classifier"*, perché la famiglia logistica non contiene l'identità. Motivo sufficiente per non usare Platt.

**Raccomandazione:** beta calibration per famiglia di mercati, stimata su predizioni walk-forward out-of-sample. Isotonica solo se hai messo insieme >1000 punti per famiglia (fattibile mettendo insieme i campionati).

---

## 5. Incertezza della stima e shrinkage

### 5.1 La maledizione dell'ottimizzatore

Questa è la fonte più importante di tutta la ricerca per la nostra decisione specifica, perché il nostro problema **è** un argmax su alternative rumorose e correlate.

**[Smith & Winkler, *The Optimizer's Curse: Skepticism and Postdecision Surprise in Decision Analysis*, Management Science 52(3):311–322, 2006, DOI 10.1287/mnsc.1050.0451](https://jimsmith.host.dartmouth.edu/wp-content/uploads/2022/04/The_Optimizers_Curse.pdf)**.

**Proposizione 1.** Se `V_1..V_n` sono stime condizionatamente non distorte di `μ_1..μ_n` e `i* = argmax V_i`, allora
```
E[μ_i* − V_i*] ≤ 0
```
con disuguaglianza stretta se c'è qualche probabilità di scegliere l'alternativa sbagliata.

**Quanto costa, in numeri dal paper:**

| n. alternative | delusione attesa (in unità di σ della stima) |
|---|---|
| 3 | 0,85 σ |
| 4 | 1,03 σ |
| 10 | **1,54 σ** |

Con σ ≈ 0,10 sulla probabilità (§1.2) e 11 mercati candidati, **la sovrastima attesa del pronostico scelto è dell'ordine di 15 punti percentuali** se le stime fossero indipendenti. Non è un dettaglio: è più grande di qualunque vantaggio realistico.

**La correlazione ci salva parzialmente.** Tabella 2 del paper, 4 alternative, correlazione comune a coppie:

| corr(μ vere) \ corr(stime) | 0,00 | 0,25 | 0,50 | 0,75 | 0,90 |
|---|---|---|---|---|---|
| 0,00 | 0,73 | 0,59 | 0,41 | 0,22 | 0,09 |
| 0,50 | 0,84 | 0,69 | **0,52** | 0,29 | 0,12 |
| 0,75 | 0,92 | 0,77 | 0,58 | **0,36** | 0,18 |

> "increasing the correlation among the V_i s decreases the expected disappointment; increasing the correlation among the μ_i s has the opposite effect ... Even with modestly high degrees of correlation, say, with both correlations at 0.5 or 0.75, the expected disappointment remains substantial at 52% or 36%"

I nostri mercati sono correlati **molto** più di 0,75 (Over 1.5 e Over 2.5 vengono dalla stessa μ). Quindi la delusione attesa scende parecchio. **Ma non a zero, e va comunque corretta.**

**La correzione prescritta dal paper**, eq. (6a)–(6c), caso normale indipendente con `μ_i ~ N(μ̄_i, σ²_μi)` e `V_i | μ_i ~ N(μ_i, σ²_Vi)`:

```
α_i = 1 / (1 + σ²_Vi/σ²_μi)
v̂_i = α_i·V_i + (1 − α_i)·μ̄_i
σ²_{μi|Vi} = (1 − α_i)·σ²_μi
```

e poi **si ordina sulle medie a posteriori `v̂_i`, non sulle stime grezze `V_i`**. È shrinkage verso la media a priori, con peso pari all'affidabilità relativa della stima. Nel caso correlato (§3.3 del paper) la forma matriciale è `α = Σ[Σ + Ψ]⁻¹`, `v̂ = αV + (I − α)μ̄`.

### 5.2 Come si ottiene σ nel nostro caso

Bootstrap parametrico del Dixon-Coles. È l'unica strada onesta con 2 stagioni, ed è economica:

1. Stima `(attacco_i, difesa_i, home_adv, ρ)` sui dati pesati.
2. Per `b = 1..B`: ricampiona i punteggi dal modello stimato (o ricampiona le partite con pesi), rifitta, ottieni `(λ_h^b, λ_a^b, ρ^b)`.
3. Per ogni draw costruisci la matrice congiunta e calcola **tutti gli 11 mercati** — questo dà `p̂_m = media_b` e `σ_m = sd_b` per ogni mercato, **coerenti fra loro perché vengono dalla stessa matrice**.

`B = 300` è sufficiente per una sd (errore relativo sulla sd ≈ 1/√(2B) ≈ 4%). Con 760 partite un fit di Dixon-Coles è dell'ordine dei decimi di secondo, quindi 300 rifit per aggiornamento giornaliero sono gestibili in un job pianificato.

L'alternativa bayesiana piena — `μ ~ ` gerarchico sulle forze delle squadre, à la **[Baio & Blangiardo, *Bayesian hierarchical model for the prediction of football results*, Journal of Applied Statistics 37(2):253–264, 2010, DOI 10.1080/02664760802684177](https://www.tandfonline.com/doi/full/10.1080/02664760802684177)** — è più corretta e dà lo shrinkage delle forze di squadra gratis. Il paper avverte però di **overshrinkage** del modello gerarchico semplice, e propone una mistura per correggerlo. Se non vuoi montare uno stack MCMC in produzione, il bootstrap parametrico + shrinkage esplicito di §5.1 arriva quasi allo stesso posto con un decimo della complessità.

### 5.3 Stima empirica di τ (la varianza a priori)

Non inventare `σ²_μ`. Stimalo dai dati, con il metodo dei momenti (Bayes empirico):

```
τ̂² = max( 0 ,  Var_m( p̂_m − b_m )  −  media_m( σ²_m ) )
```

calcolato su un backtest walk-forward, **per famiglia di mercato**. Legge: "la dispersione osservata delle nostre previsioni attorno al base rate, meno quella spiegabile dal solo rumore di stima".

> **Se `τ̂² ≤ 0`, il modello non ha risoluzione dimostrabile oltre il rumore su quella famiglia di mercati.** È il risultato più importante che questo backtest possa produrre, e va conosciuto prima di lanciare, non dopo.

Effetto dello shrinkage su un caso concreto (p̂ = 0,62, base = 0,52):

| σ (bootstrap) | τ | α | p̃ | Score prima → dopo |
|---|---|---|---|---|
| 0,02 | 0,08 | 0,94 | 0,614 | 0,0203 → 0,0180 |
| 0,05 | 0,08 | 0,72 | 0,592 | 0,0203 → 0,0106 |
| 0,10 | 0,08 | 0,39 | 0,559 | 0,0203 → 0,0031 |

Con la σ realistica della §1.2 (≈0,10) lo score si riduce di **6,5 volte**. Questo è il prezzo onesto di avere 2 stagioni.

---

## 6. Punteggio unico ordinabile: cosa esiste in letteratura

| Formulazione | Formula | Fonte | Giudizio per noi |
|---|---|---|---|
| **Tasso di crescita log / KL** | `D(p‖q) = p ln(p/q) + (1−p) ln((1−p)/(1−q))` | Cover & Thomas 6.18; Kelly 1956 | **Scelto.** Esatto, additivo fra partite, interpretabile in nats, misurabile a posteriori (§9) |
| Frazione di Kelly | `(pθ−1)/(θ−1)` | Chu et al. eq. 3 | Ordina in modo simile ma è una taglia di puntata, non una misura di informazione; non funziona senza quote |
| Sharpe della singola | `(po−1)/(o√(p(1−p)))` | Hubáček et al. eq. 4.6 | Ordina in modo simile; criticato nel paper stesso perché "penalizes excess losses as well as excess returns" e "quite sensitive to errors in the probabilistic estimates" |
| Utilità attesa con drawdown | `E(rᵀb)^(−λ) ≤ 1` | Busseti-Ryu-Boyd | Sovradimensionato: ha senso per un portafoglio con capitale, non per scegliere un pronostico da mostrare |
| Kelly robusto | `max min_{p∈Π} Σ p_i log(O_i f)` | Sun & Boyd; Hubáček eq. 5.5–5.6 | Alternativa allo shrinkage; nel loro esperimento è la più stabile ma la meno performante. Lo shrinkage bayesiano (§5.1) è più semplice e meglio motivato |
| Edge grezzo `pθ − 1` | — | — | **Da evitare.** È esattamente l'errore che il vincolo dell'utente vieta |

---

## 7. Backtesting onesto

### 7.1 Protocollo

1. **Walk-forward stretto, per giornata.** Allena solo su partite con data `<` la data della partita da prevedere. Mai mescolare. Hubáček et al. lo dichiarano esplicitamente: *"trained following the natural order of the matches in time, so that all of their estimates are actual future predictions"*.
2. **Il base rate è a sua volta un parametro stimato.** Deve essere calcolato solo da partite passate, per campionato e stagione. Usare la frequenza dell'intero dataset è look-ahead mascherato ed è facilissimo da sbagliare.
3. **Split a tre.** Fit del Dixon-Coles, fit del calibratore, e valutazione devono usare finestre disgiunte. `CalibratedClassifierCV` con `cv` fa la parte centrale, ma la separazione temporale la devi imporre tu.
4. Metriche: log loss (primaria), Brier con decomposizione Ferro-Fricker, reliability diagram per bin di probabilità, hit rate per bucket.

### 7.2 La trappola del tuning

**[Bailey, Borwein, López de Prado, Zhu, *Pseudo-Mathematics and Financial Charlatanism*, Notices of the AMS 61(5), maggio 2014](https://www.davidhbailey.com/dhbpapers/backtest-pseudo.pdf)**: con soli 5 anni di dati, **non più di 45 configurazioni di modello indipendenti** possono essere provate prima che sia quasi garantito produrre una strategia con Sharpe in-sample pari a 1 e Sharpe atteso out-of-sample **pari a zero**.

Noi abbiamo **2 stagioni**. E i parametri da tarare sono: emivita ξ, τ per famiglia, ω, p_min, soglia di clustering, forma del calibratore, peso mercato/modello. Sono già più configurazioni di quante ne possiamo permettere.

**Regole conseguenti, da rispettare:**
- Fissa i parametri sui **valori iniziali motivati** di §8, non su una grid search.
- Tocca al massimo **due** parametri, e solo su una finestra di validazione, con il test set congelato.
- **Conta e scrivi nel repo quante configurazioni hai provato.** Se il numero non è scritto, il backtest non è interpretabile — è il punto centrale del paper.
- Il "numero effettivo di prove indipendenti" non è il conteggio letterale se le configurazioni sono correlate — López de Prado propone di raggrupparle. Vale anche per i nostri 11 mercati: le prove effettive sono il numero di **cluster** (§8.3), non 11.

### 7.3 Closing line value

Il benchmark di riferimento nel settore è confrontare la propria probabilità con la quota **di chiusura** sgonfiata. Sull'efficienza del mercato calcistico, [Angelini & De Angelis, *Efficiency of online football betting markets*, International Journal of Forecasting 35, 2019](https://www.sciencedirect.com/science/article/abs/pii/S0169207018301134): 41 bookmaker, 11 campionati europei, 11 anni — 8 mercati efficienti sulle quote migliori, 3 con inefficienze sfruttabili.

**Per noi il CLV è in gran parte non disponibile**, ed è un vincolo, non un'opzione: con 500 crediti/mese non possiamo campionare la chiusura di ogni partita. Realisticamente: prendi la chiusura su un campione ridotto e fisso (es. una sola lega, una chiamata a giornata poco prima del kickoff) e usalo come **audit periodico**, non come metrica continua. Documenta che il resto del sistema non è validato contro il mercato.

Un contrappunto che vale la pena conoscere: **[Hubáček & Šír, *Beating the market with a bad predictive model*, arXiv:2010.12508](https://arxiv.org/abs/2010.12508)** mostra che *"it is possible to make systematic profits with a completely inferior price-predicting model"* se lo si addestra a **decorrelarsi** dal mercato. Interessante teoricamente; **non lo raccomando qui**, perché è l'opposto di un prodotto che deve mostrare pronostici plausibili e spiegabili a un utente.

---

## 8. Raccomandazione operativa

### 8.1 La pipeline

```
Per ogni partita:

(1) MATRICE DEI GOL
    Dixon-Coles con pesi esponenziali su 2 stagioni  ->  (λ_h, λ_a, ρ)
    Se esistono quote (1X2 / O-U / handicap):
        de-vig con metodo POWER  ->  q_mercato
        risolvi ai minimi quadrati (λ_h*, λ_a*) che riproducono q_mercato
        log λ_finale = w·log λ_modello + (1−w)·log λ_mercato
    Costruisci UNA matrice M[i][j], i,j = 0..10

(2) INCERTEZZA
    B draw bootstrap/posteriori -> B matrici
    per ogni mercato m:  p̂_m = media_b ,  σ_m = sd_b

(3) RIFERIMENTO
    b_m = frequenza storica del mercato (campionato+stagione, solo passato,
          shrinkata verso la media multi-campionato)

(4) SHRINKAGE                       [Smith & Winkler eq. 6]
    α_m = 1 / (1 + σ²_m/τ²_famiglia)
    p̃_m = α_m·p̂_m + (1 − α_m)·b_m

(5) PUNTEGGIO                       [Cover & Thomas eq. 6.18]
    S_m = p̃_m·ln(p̃_m/b_m) + (1 − p̃_m)·ln((1 − p̃_m)/(1 − b_m))

(6) FILTRI DURI
    scarta se  p̃_m < p_min          (non consigliamo cose improbabili)
    scarta se  σ_m  > σ_max         (stima troppo instabile)
    scarta se  S_m  < S_min         (non dice niente)

(7) CLUSTERING PER CORRELAZIONE — dalla matrice, non stimata
    ρ(A,B) = [P(A∩B) − P(A)P(B)] / √(P(A)(1−P(A))·P(B)(1−P(B)))
    single-linkage su |ρ| ≥ ρ_max  ->  cluster
    scegli il CLUSTER con S massimo
    dentro il cluster scegli il membro con p̃ MASSIMO   <- vincolo di prodotto

(8) SE NESSUN CANDIDATO SOPRAVVIVE: nessun pronostico. Dillo.
```

### 8.2 La formula, in Python

```python
import numpy as np

def kl_binary(p, q, eps=1e-9):
    """Score = tasso di crescita log ottimale di Kelly = D(p||q).
    q = quota sgonfiata dove c'è, base rate dove non c'è."""
    p = np.clip(p, eps, 1 - eps)
    q = np.clip(q, eps, 1 - eps)
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))

def shrink(p_hat, sigma, q_ref, tau):
    """Media a posteriori, Smith & Winkler (2006) eq. 6a-6b."""
    alpha = 1.0 / (1.0 + (sigma ** 2) / (tau ** 2))
    return alpha * p_hat + (1 - alpha) * q_ref, alpha

def market_corr(M, mask_a, mask_b):
    """Correlazione esatta fra due mercati binari, dalla matrice congiunta.
    M: matrice (n+1)x(n+1) di P(gol_casa=i, gol_osp=j).
    mask_*: maschere booleane della stessa forma."""
    pa, pb = M[mask_a].sum(), M[mask_b].sum()
    pab = M[mask_a & mask_b].sum()
    den = np.sqrt(pa * (1 - pa) * pb * (1 - pb))
    return 0.0 if den == 0 else (pab - pa * pb) / den

def devig_power(odds, n_winners=1, lo=0.5, hi=3.0, tol=1e-10):
    """Metodo power: trova beta t.c. sum (1/o_i)^beta = n_winners.
    beta > 1 comprime i longshot -> corregge il favourite-longshot bias."""
    inv = 1.0 / np.asarray(odds, dtype=float)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        s = (inv ** mid).sum()
        if abs(s - n_winners) < tol:
            break
        lo, hi = (mid, hi) if s > n_winners else (lo, mid)
    return inv ** mid, mid
```

Il resto (bootstrap, clustering, filtri) è meccanico.

### 8.3 Parametri, valori iniziali e perché

| Parametro | Valore iniziale | Motivazione |
|---|---|---|
| **emivita del decadimento** | **365 giorni** | Corrisponde al ξ ampiamente riportato per Dixon-Coles 1997 (ξ = 0,0065 per mezza settimana ⇒ emivita ≈ 1 anno). ⚠️ non verificato sul paper, vedi §11. Con 730 giorni disponibili dà n_eff = 65,8/76 per squadra; a 180 giorni scenderebbe a 47,9 e la σ crescerebbe del 17% |
| **B (bootstrap)** | **300** | Errore relativo sulla sd ≈ 1/√(2B) ≈ 4%. Sufficiente per lo shrinkage; oltre è spreco |
| **w (peso modello vs mercato)** | **0,35** quando ci sono quote, **1,0** quando non ci sono | Il mercato batte i modelli: nel dataset calcio di Hubáček et al. (32.000 partite) un modello serio è a KL ≈ −0,013 rispetto a Pinnacle. Dare al nostro DC su 760 partite più di un terzo del peso non è difendibile |
| **τ (sd a priori per famiglia)** | **stima empirica**, `τ̂² = max(0, Var(p̂ − b) − media(σ²))`; se non hai ancora backtest, parti da **0,08** | Bayes empirico, metodo dei momenti (§5.3). 0,08 è la dispersione plausibile di P(Over 2.5) fra partite. Se il dato empirico dice τ̂² ≤ 0, non c'è segnale |
| **p_min** | **0,50** | Traduzione diretta del vincolo dell'utente: consigliamo solo esiti più probabili che no. Nota: lo score KL già rende rarissimo un pick sotto 0,5 (§3.2), quindi il floor è una **garanzia** più che un filtro. Verificare nel backtest quante volte è vincolante; se è vincolante spesso, il problema è a monte |
| **σ_max** | **0,12** | Circa una sigma della §1.2. Sopra, la stima è talmente instabile che il tip è arbitrario |
| **S_min** | **0,005 nats** | Sotto questa soglia il pronostico porta meno di ~0,007 bit: indistinguibile dal base rate. Calibrata sulla tabella di §3.3, dove "Over 0.5 al 97%" vale 0,0004 e "Multigol 2-4" vale 0,0051 |
| **ρ_max (clustering)** | **0,80** | Coerente con Smith & Winkler Tab. 2: sopra 0,75 di correlazione la delusione attesa da argmax scende sotto 0,36σ. Tipicamente riduce 11 mercati a 4–5 cluster: è quello il numero effettivo di prove |
| **ω (Kelly frazionale)** | **non applicabile** — non mostrare puntate | L'app non gestisce capitale. Se un giorno mostrerà uno stake, parti da ω = 0,3 (Hubáček et al.: Kelly puro → 100% di rovina sul calcio) |
| **calibratore** | **beta calibration** per famiglia; isotonica solo se >1000 punti nella famiglia | Kull et al. 2017 (contiene l'identità, corregge distorsioni inverse-sigmoidali); soglia dalla doc scikit-learn 1.9.0 |

### 8.4 Come si gestisce la correlazione: le tre cose che fa

Il clustering non è cosmetica. Risolve tre problemi diversi con un solo meccanismo:

1. **Stabilità dell'output.** Senza cluster, l'argmax salta fra Over 1.5, Over 2.5 e Multigol 2-4 per differenze di rumore. L'utente vede un sistema capriccioso. Con i cluster, la scelta della *famiglia* è stabile e la scelta *dentro* la famiglia è deterministica (massimo p̃).
2. **La maledizione dell'ottimizzatore.** Il numero effettivo di alternative su cui si fa argmax scende da 11 a 4–5. Da Smith & Winkler: delusione attesa da 1,54σ (10 alternative indipendenti) a ~0,4σ.
3. **Il vincolo di prodotto, applicato dove morde di più.** Il tie-break "dentro il cluster scegli il p̃ più alto" preferisce sistematicamente Over 1.5 a Over 2.5, doppia chance a 1X2, multigol largo a multigol stretto — quando lo score è confrontabile. È letteralmente "non consigliamo la cosa difficile da azzeccare".

La correlazione **si calcola esatta**, non si stima: viene dalla matrice congiunta. È il vantaggio concreto di aver deciso che tutti i mercati derivano da un'unica matrice.

---

## 9. Cosa mostrare all'utente, e cosa non promettere

**Mostra:**

| Elemento | Forma |
|---|---|
| Il pronostico | "Over 1.5" — uno solo, in evidenza |
| La probabilità | `p̃` (già shrinkata), come **"85 su 100"**, non "confidenza 85%" |
| L'incertezza | banda bootstrap p5–p95: "fra 78 e 90 su 100" |
| L'accuratezza storica | **"pronostici come questo si sono verificati 412 volte su 500"** — è il reliability diagram trasformato in una frase, ed è la sola affermazione di accuratezza verificabile che puoi fare |
| La provenienza | badge esplicito: **"confrontato con le quote"** vs **"solo modello statistico"** |
| Il motivo | 1–2 frasi generate dalla matrice: le due μ attese, il base rate del campionato, e di quanto ci discostiamo |
| Il non-pronostico | se nessun candidato passa i filtri: **"Nessun pronostico: questa partita non ci dice niente di più della media."** |

**Non mostrare, mai:**
- "value bet", "edge", ROI, percentuali di rendimento
- importi da puntare
- una confidenza che non sia stata shrinkata (`p̂` grezza)
- un'accuratezza aggregata su tutti i pronostici insieme senza dire in quale bucket di probabilità (nasconde il fatto che gli 85% sono facili e i 55% no)

Lo stato "nessun pronostico" è la funzionalità più onesta del prodotto e probabilmente la più differenziante rispetto ai siti di pronostici. Va progettato bene, non trattato come errore.

---

## 10. Come si misura a posteriori se il sistema funziona

Qui c'è il vantaggio nascosto della scelta di §3: **lo score è la stessa quantità che si misura ex post.**

### 10.1 Il test principale: skill dichiarato vs skill realizzato

Per ogni pronostico pubblicato, dopo la partita:

```
skill_realizzato = ln(p̃/b)        se l'evento si è verificato
                 = ln((1−p̃)/(1−b)) se non si è verificato
```

Se le previsioni sono calibrate, **la media dello skill realizzato deve uguagliare la media dello score dichiarato**. Verificato per simulazione (400.000 prove, calcolo mio):

| scenario | score medio dichiarato | skill medio realizzato |
|---|---|---|
| previsioni calibrate | 0,02985 | **0,03021** ✅ |
| previsioni sovraconfidenti (×1,6) | 0,07895 | **0,01358** ❌ |

Il divario è enorme e immediato quando c'è sovraconfidenza. **Questo singolo confronto è il cruscotto del sistema.** Se `realizzato < dichiarato` in modo persistente: `τ` è troppo grande, cioè lo shrinkage è troppo debole. Riducilo e ricontrolla.

È anche l'unica metrica che l'utente potrebbe capire se decidessi di mostrarla: "quanto dicevamo di sapere / quanto sapevamo davvero".

### 10.2 Le altre quattro misure

1. **Reliability diagram per bucket** (bin di 5 punti di probabilità), su tutti i pronostici pubblicati, con la decomposizione **Ferro-Fricker** — non quella standard, che con i nostri n sovrastima REL e RES.
2. **Log loss vs due baseline**: (a) il base rate del campionato, (b) le quote sgonfiate dove esistono. Battere (a) è il minimo sindacale. Non battere (b) è normale e va scritto nella pagina "come funziona".
3. **Hit rate per bucket**, la versione leggibile del punto 1. È il numero da mettere in interfaccia.
4. **Quante volte hanno morso i filtri**, per filtro. Se `p_min` scarta il 40% dei pronostici, non stai applicando un vincolo di prodotto: stai nascondendo che il modello punta sistematicamente su cose improbabili, e va sistemato il modello.

Aggiungi **audit CLV periodico** su un campione ristretto (§7.3), non su tutto.

---

## 11. Gotchas — quello che morderà chi implementa

- **De-vig ingenuo = vantaggio finto sui longshot.** Con β misurato fra 1,06 e 1,15, normalizzare dividendo per la somma delle inverse gonfia la probabilità equa degli esiti improbabili. Usa il metodo power. È dieci righe di bisezione.
- **500 crediti/mese ⇒ la stessa partita ha due verità.** Prima che arrivino le quote il pronostico viene da `w = 1,0`; dopo, da `w = 0,35`, e può **cambiare**. Decidi ora: o congeli il tip alla prima pubblicazione (e mostri la versione), o dichiari che si aggiorna. Un tip che cambia senza spiegazione distrugge la fiducia più di un tip sbagliato.
- **Risultato esatto e HT/FT non vinceranno quasi mai.** Con p tipiche fra 0,05 e 0,12 lo score KL li mette sistematicamente sotto. È corretto e voluto, ma significa che il prodotto mostrerà quasi sempre O/U, doppia chance, BTTS, multigol, 1X2. Se serve varietà è una decisione di prodotto, non statistica — e va presa consapevolmente, non ottenuta storpiando il punteggio.
- **I mercati non sono solo correlati: alcuni sono annidati** (Over 2.5 ⊂ Over 1.5). La formula di ρ dalla matrice li gestisce correttamente; una correlazione stimata sui dati storici no.
- **I base rate variano molto per campionato e per stagione.** Eredivisie e Ligue 1 non hanno lo stesso numero di gol. Calcolali per campionato, solo su partite passate, shrinkati verso la media multi-campionato (altrimenti con 380 partite di una stagione il base rate stesso ha una sd di ~2,5 punti).
- **Il calibratore non va stimato sui dati del fit.** È l'errore più facile e il più devastante: produce un reliability diagram perfetto e una calibrazione reale pessima.
- **Mercati primo tempo:** football-data.org dà il punteggio HT, ma serve una **seconda matrice** con i suoi λ. L'approssimazione "λ_HT ≈ 0,45·λ_FT" è comune ma non l'ho verificata su fonte primaria — trattala come parametro da stimare, non da assumere.
- **Windows:** nulla di problematico. `numpy` + `scipy.optimize` bastano; non serve `cvxpy` perché non facciamo ottimizzazione di portafoglio.
- **Non fare grid search.** §7.2: con 2 stagioni e ~7 iperparametri sei già oltre il budget statistico. Parti dai valori di §8.3 e tocca al massimo due parametri.

---

## 12. Non verificato

| Cosa | Perché | Come si verifica |
|---|---|---|
| **ξ = 0,0065 per mezza settimana / emivita ≈ 1 anno** di Dixon-Coles | Il paper è a pagamento ([DOI 10.1111/1467-9876.00065](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/1467-9876.00065)). Il valore è riportato in modo concorde da fonti secondarie, non l'ho letto nell'originale | Leggere il paper, oppure ignorarlo e tarare l'emivita con log loss walk-forward su una griglia di 3 valori (180 / 365 / 540 giorni) |
| **Formula esatta del fattore di shrinkage di Baker & McHale (2013)** | Paywall INFORMS. Ho solo la descrizione data da Chu-Wu-Swartz (§1): impongono `k·s*(q)` con `0<k<1` | Leggere Decision Analysis 10(3):189–199. Non è bloccante: usiamo la via bayesiana di Smith & Winkler, che è più adatta al nostro problema di selezione |
| **Formula MinBTL e `E[max SR_N]`** di Bailey et al. | Il PDF su ams.org è solo immagini; ho verificato l'esempio numerico (5 anni ⇒ ≤45 configurazioni) ma non l'algebra | Recuperare la versione SSRN 2308659 in testo. Il principio è già sufficiente per la nostra disciplina di tuning |
| **n_eff = 65,8 e SE(log μ) ≈ 0,15** | Sono calcoli miei da informazione di Fisher Poisson, non risultati citati | Sostituirli con la sd bootstrap vera al primo fit. È la prima cosa da misurare |
| **τ = 0,08 come valore iniziale** | È una congettura sulla dispersione di P(Over 2.5) fra partite | Sostituire con `τ̂²` empirico (§5.3) appena esiste un backtest walk-forward |
| **Beta calibration su mercati calcistici derivati** | L'evidenza di Kull et al. è su dataset UCI, non su calcio. Nessuna valutazione pubblicata trovata sui mercati gol | Confrontare beta vs sigmoid vs isotonica per log loss out-of-sample nel nostro backtest, per famiglia di mercato |
| **λ_HT ≈ 0,45·λ_FT** | Non trovata fonte primaria | Stimarlo dai punteggi HT di football-data.org: è un rapporto medio calcolabile direttamente |
| **the-odds-api restituisce quote di chiusura** | Non verificato; incide sulla fattibilità dell'audit CLV di §7.3 | Controllare la doc dell'API dopo la registrazione della key |
| **Risks 9(1):22 (rassegna FLB)** | HTTP 403 alla verifica diretta | Citata come lead. L'evidenza quantitativa che usiamo viene da arXiv:2604.17194, che ho letto |

---

## Fonti

| # | Fonte | Cosa ne abbiamo preso | Verificata |
|---|---|---|---|
| 1 | Cover & Thomas, *Elements of Information Theory*, cap. 6 — [PDF](https://ftp.esat.kuleuven.be/pub/SISTA/decock/voor_xander/referenties/Cover&Thomas/6.pdf) | Teoremi 6.1.1–6.1.3, 6.2.1; eq. 6.10, 6.18. Il punteggio | ✅ testo letto |
| 2 | Smith & Winkler, Management Science 52(3):311–322, 2006, [DOI 10.1287/mnsc.1050.0451](https://pubsonline.informs.org/doi/10.1287/mnsc.1050.0451) — [PDF](https://jimsmith.host.dartmouth.edu/wp-content/uploads/2022/04/The_Optimizers_Curse.pdf) | Proposizione 1; eq. 6a–6c; Tab. 2 (correlazione); 0,85σ / 1,03σ / 1,54σ | ✅ testo letto |
| 3 | Hubáček, Šourek, Železný, IMA JMM 2021, [DOI 10.1093/imaman/dpaa029](https://doi.org/10.1093/imaman/dpaa029), [arXiv:2107.08827](https://arxiv.org/abs/2107.08827) | Kelly frazionale eq. 5.1; drawdown 5.2; robusto 5.5–5.6; MSharpe 4.6; Tab. 7 (calcio: Kelly puro = 100% rovina) | ✅ testo letto |
| 4 | Chu, Wu, Swartz, JQAS 2018, [DOI 10.1515/jqas-2017-0122](https://degruyterbrill.com/document/doi/10.1515/jqas-2017-0122/html?lang=en) — [PDF](https://www.sfu.ca/~tswartz/papers/kelly.pdf) | Kelly eq. 3; prior/posterior Beta eq. 11–12; **eq. 15: Kelly sulla media a posteriori** | ✅ testo letto |
| 5 | Ferro & Fricker, QJRMS 2012, [DOI 10.1002/qj.1924](http://onlinelibrary.wiley.com/doi/10.1002/qj.1924/abstract) — [PDF](https://empslocal.ex.ac.uk/people/staff/ferro/Publications/ferro-fricker2012copyright.pdf) | Decomposizione di Murphy eq. 1–4; bias eq. 7–9; correzione eq. 11–12 | ✅ testo letto |
| 6 | Kull, Silva Filho, Flach, AISTATS 2017, [PMLR v54](https://proceedings.mlr.press/v54/kull17a.html) | Formula beta calibration; §3.3 (fit via regressione logistica); critica a Platt | ✅ testo letto |
| 7 | scikit-learn 1.9.0, [`modules/calibration`](https://scikit-learn.org/stable/modules/calibration.html) | Soglia ~1000 campioni isotonica; sigmoid per piccoli campioni; CalibratedClassifierCV; caveat sul Brier | ✅ doc ufficiale |
| 8 | [arXiv:2604.17194](https://arxiv.org/html/2604.17194) | Metodi di de-vig; β = 1,06–1,15 su 90.014 partite 2012–2024; effetto sul pareggio | ✅ HTML letto |
| 9 | Busseti, Ryu, Boyd, [arXiv:1603.06183](https://arxiv.org/abs/1603.06183) | Kelly con vincolo di drawdown; λ = log β / log α | ✅ abstract + formulazione |
| 10 | Wheatcroft, [arXiv:1908.08980](https://arxiv.org/abs/1908.08980), JQAS | Caso contro l'RPS; ignorance score vince | ✅ abstract |
| 11 | Constantinou & Fenton, JQAS 8(1), 2012 | Caso a favore dell'RPS (posizione opposta a #10) | ✅ abstract |
| 12 | Baio & Blangiardo, J. Appl. Stat. 37(2):253–264, 2010, [DOI 10.1080/02664760802684177](https://www.tandfonline.com/doi/full/10.1080/02664760802684177) | Modello gerarchico bayesiano; avvertimento sull'**overshrinkage** | ✅ abstract |
| 13 | Bailey, Borwein, López de Prado, Zhu, Notices AMS 61(5), 2014 | 5 anni ⇒ ≤45 configurazioni; prove effettive ≠ conteggio letterale | ⚠️ esempio verificato, algebra no |
| 14 | Angelini & De Angelis, Int. J. Forecasting 35, 2019, [DOI](https://www.sciencedirect.com/science/article/abs/pii/S0169207018301134) | Efficienza dei mercati calcistici: 8 efficienti su 11 | ✅ abstract |
| 15 | Hubáček & Šír, [arXiv:2010.12508](https://arxiv.org/abs/2010.12508) | Decorrelazione dal mercato; contrappunto scartato | ✅ abstract |
| 16 | Baker & McHale, Decision Analysis 10(3), 2013, [DOI 10.1287/deca.2013.0271](https://pubsonline.informs.org/doi/abs/10.1287/deca.2013.0271) | Kelly ridotto sotto incertezza del parametro | ⚠️ paywall, via #4 |
| 17 | Dixon & Coles, JRSS-C 46(2):265–280, 1997, [DOI 10.1111/1467-9876.00065](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/1467-9876.00065) | Modello base, pseudo-verosimiglianza pesata | ⚠️ paywall |
