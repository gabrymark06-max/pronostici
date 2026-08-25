# Qualità del sito — misure

Aggiornato: 2026-08-25. Strumento: Lighthouse 13, profilo mobile predefinito
(rete lenta simulata, CPU rallentata 4×), **sul sito pubblicato**.

Prima di questa pagina il sito non era mai stato misurato da nessuna macchina.

## Punteggi — sul sito pubblicato

Misurato su <https://pronostici-sigma.vercel.app/>, che e' dove il sito vive
adesso. La misura precedente era su GitHub Pages: stesse pagine, rete diversa,
e i numeri di un altro indirizzo non descrivono questo.

| | Home | Scheda partita | prima, su Pages |
|---|---|---|---|
| Performance | **98** | 96 | 96 / 97 |
| Accessibilità | **100** | **100** | 100 / 100 |
| Buone pratiche | **100** | **100** | 100 / 100 |
| SEO | **100** | **100** | 100 / 100 |

## Core Web Vitals — tutti dentro il budget

| | Home | Scheda | Budget dello studio |
|---|---|---|---|
| LCP | **1,5 s** | **2,4 s** | < 2,5 s |
| CLS | **0,001** | **0** | < 0,1 |
| TBT | **0 ms** | 50 ms | proxy di INP < 200 ms |

La home guadagna un secondo pieno di LCP rispetto a GitHub Pages — 1,5 s contro
2,5 — ed e' la rete di Vercel, non una modifica al sito: il codice servito e' lo
stesso build. La scheda partita resta a 2,4 s, appena dentro il budget: li' il
peso non e' la rete ma la pagina, che ha il campo delle formazioni e la tavola
dei mercati.

### Perche' la misura in locale era peggiore

Prima del deploy la scheda partita risultava a **2,9 s**, fuori budget. Non era
il sito: 2,33 s di quel numero era TTFB *simulato*, cioe' quanto Lighthouse
finge che ci metta a rispondere un `npx serve` locale applicandogli la sua rete
lenta. Misurato davvero, quel documento arrivava in 1,5 ms.

Non e' stato ottimizzato niente fra le due misure: e' cambiato solo il posto da
cui il sito viene servito. E' il motivo per cui la riga era stata lasciata
aperta invece di inseguire un numero fabbricato dallo strumento.

La home e' esattamente **al** limite, non sotto: e' il numero da riguardare per
primo se un giorno il budget viene sforato.

## Difetti trovati e corretti

- **Due errori in console per ogni pagina.** Il sito chiedeva `/profili/io` a
  ogni apertura anche a chi non ha un profilo: due 401 che il browser scrive
  come errori. Buone pratiche era 96. Corretto con un cookie-indizio leggibile,
  e adesso è 100.
- **Un modulo d'accesso morto pubblicato.** Con i profili spenti — la
  configurazione con cui il sito verrebbe pubblicato — l'export conteneva
  `/accedi` con due campi e un bottone che non potevano funzionare. Adesso quelle
  pagine non escono, e `check-profili-spenti.mjs` lo verifica a ogni build.

## Come rifarla

```bash
npx lighthouse https://gabrymark06-max.github.io/pronostici/ --view
```

Sul sito pubblicato, non in locale: in locale il TTFB simulato domina la misura
e l'LCP esce peggiore di quello che e'.
