# Qualità del sito — misure

Aggiornato: 2026-08-24. Strumento: Lighthouse 12, profilo mobile predefinito
(rete lenta simulata, CPU rallentata 4×), sull'export statico servito in locale.

Prima di questa pagina il sito non era mai stato misurato da nessuna macchina.

## Punteggi

| | Home | Scheda partita |
|---|---|---|
| Performance | 99 | 94 |
| Accessibilità | **100** | **100** |
| Buone pratiche | **100** | **100** |
| SEO | **100** | **100** |

## Core Web Vitals

| | Home | Scheda | Budget dello studio |
|---|---|---|---|
| LCP | 2,0 s | 2,9 s | < 2,5 s |
| CLS | 0,001 | 0,001 | < 0,1 |
| TBT | 0 ms | 10 ms | proxy di INP < 200 ms |

## L'unico numero fuori budget, e perché non si corregge qui

La scheda partita è a 2,9 s di LCP contro un budget di 2,5 s. **Il 2,33 s di
quel numero è TTFB simulato**, cioè il tempo che Lighthouse *finge* che il
server ci metta a rispondere applicando la sua rete lenta a un `npx serve`
locale. Misurato davvero, quello stesso documento arriva in **1,5 ms**.

Quello che dipende da noi è sano e quasi identico fra le due pagine:

| | Home | Scheda |
|---|---|---|
| Peso totale | 316 KB | 336 KB |
| Esecuzione JS | 132 ms | 147 ms |
| Lavoro sul thread principale | 323 ms | 339 ms |
| Nodi DOM | 115 | 173 |

I font sono già `display: swap`, quindi non bloccano la resa; il resto della
differenza è che sulla scheda l'elemento più grande sta più in basso.

**Conclusione:** l'LCP non è misurabile onestamente finché il sito non è
pubblicato dietro un hosting vero. Questa riga va rifatta dopo il primo deploy,
ed è l'unica delle quattro categorie che oggi non si può chiudere.

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
cd frontend && npm run build && npm run start   # serve out/ su :4321
npx lighthouse http://localhost:4321/ --view
```
