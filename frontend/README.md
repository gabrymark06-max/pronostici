# Frontend — Pronostici

Next.js App Router in **export statico** (`output: 'export'`). Legge i JSON di `../data/`
**in fase di build**. Nessun runtime, nessuna API route, nessun segreto, nessuna variabile
d'ambiente: per questo non c'è un `.env.example`.

Non è una preferenza ma una decisione architetturale (`docs/brief.md` §11.2): il fatto che
il sito non possa fare chiamate a runtime è ciò che impedisce al traffico di esaurire la
quota mensile delle quote.

## Avvio locale

```bash
cd frontend
npm install
npm run crests     # una volta: scarica i loghi in public/crests/ (richiede rete)
npm run dev        # http://localhost:3000
```

`npm run crests` è facoltativo. Senza, i crest vengono serviti dalle URL remote e, se non
caricano, il componente ripiega sulla sigla della squadra.

## Comandi

| Comando | Cosa fa |
|---|---|
| `npm run dev` | sviluppo (sincronizza prima i token) |
| `npm run build` | build + export statico in `out/` + controllo delle parole vietate |
| `npm run start` | serve `out/` su http://localhost:4321 per guardare l'export vero |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint |
| `npm run crests` | scarica i crest in `public/crests/` |
| `npm run sync:tokens` | ricopia i token dal design system |

## I due controlli automatici che non si tolgono

1. **`check:tokens`** gira prima di ogni build e fallisce se `styles/tokens.css` ha
   divergito da `design-system/pronostici/tokens.css`. È l'unico modo perché "nessun hex
   grezzo nei componenti" resti vero nel tempo. Se fallisce: `npm run sync:tokens`.

2. **`check-parole-vietate`** gira dopo ogni build e fallisce se nel testo visibile
   dell'export compare una delle parole che il prodotto non pronuncia mai
   (`scripts/check-parole-vietate.mjs`). Se una di quelle parole entra in pagina non hai
   rotto lo stile: hai rotto il prodotto.

## Fallimento forte sullo schema

Se un file di `data/` ha una `schema_version` diversa da quella attesa in `lib/tipi.ts`,
**il build si ferma** e stampa file, versione attesa e versione trovata. Su un sito
statico questa è la forma più severa possibile di "fallire forte": la pagina sbagliata non
viene proprio generata. Il contratto è `docs/schema.md`; cambiarlo richiede di aggiornare
`lib/tipi.ts` insieme al bump.

## Struttura

```
app/
  layout.tsx                  font, tema, masthead, piè di pagina
  page.tsx                    / → rimando statico al giorno più recente
  giorno/[data]/page.tsx      la lista del giorno
  partita/[match_id]/page.tsx la scheda partita
  come-stiamo-andando/        registro dal vivo + prova storica (separati)
  come-funziona/              l'articolo: criterio, parametri, protocollo
components/                   i componenti del design system
lib/
  tipi.ts                     il contratto di docs/schema.md in TypeScript
  dati.ts                     lettura di data/ a build time, fallimento forte
  testi.ts                    le frasi del design system, in un posto solo
  formato.ts  mercati.ts  fascia.ts
styles/
  tokens.css                  GENERATO dal design system — non si modifica a mano
  base.css  componenti.css
```

## Deploy

L'output è `out/`: file statici, nessun server.

**Vercel** — Root Directory `frontend`, Framework `Next.js`, Output Directory `out`.
Nessuna variabile d'ambiente da impostare.

**Cloudflare Pages** (uscita pronta) — Build command `npm run build`, Build output `out`,
Root directory `frontend`.

**Qualunque CDN o hosting statico** — carica `out/`. Con `trailingSlash: true` ogni rotta
è una cartella con dentro `index.html`, quindi non servono regole di rewrite.

Il sito va ricostruito quando i job notturni scrivono in `data/`: è il commit su `data/`
che deve far partire il build.

## Note di implementazione

- **La navigazione è fatta di `<a>` veri, non di `<Link>`.** In export statico i prefetch
  RSC di `<Link>` chiedono payload che l'export non produce (404 su ogni riga di lista), e
  non c'è stato condiviso fra le pagine da preservare.
- **`<details>` nativi** per le altre famiglie di mercato: funzionano senza JavaScript e il
  contenuto è nel DOM per i crawler.
- **I filtri del registro** filtrano righe già presenti nel DOM: senza JavaScript la
  tabella resta completa e leggibile.
- **Nessuno skeleton, in nessun punto.** L'HTML arriva già pieno, e uno skeleton grigio a
  forma di card sarebbe indistinguibile da uno stato di silenzio mal fatto.
