/**
 * Scarica i crest delle squadre in public/crests/ e scrive un manifesto
 * URL remota → percorso locale.
 *
 * Perché: oggi.md, Prestazioni — "preferibile: nessuna dipendenza da un terzo
 * a runtime". Con i file in public/ il sito non chiama crests.football-data.org
 * quando qualcuno lo apre.
 *
 * Non è obbligatorio per il build: se il manifesto non c'è, lo strato dati
 * ripiega sulla URL remota, e il componente Crest ha comunque il suo ripiego
 * testuale sul `tla`. Lo script non fallisce mai il build.
 */
import { mkdirSync, readdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const RADICE_DATI = fileURLToPath(new URL('../../data', import.meta.url));
const DESTINAZIONE = fileURLToPath(new URL('../public/crests', import.meta.url));

function tutteLeUrl() {
  const cartella = join(RADICE_DATI, 'fixtures');
  if (!existsSync(cartella)) return new Set();
  const url = new Set();
  for (const nome of readdirSync(cartella).filter((n) => n.endsWith('.json'))) {
    const giorno = JSON.parse(readFileSync(join(cartella, nome), 'utf8'));
    for (const fixture of giorno.fixtures ?? []) {
      for (const lato of ['home', 'away']) {
        const crest = fixture[lato]?.crest;
        if (typeof crest === 'string' && crest.startsWith('http')) url.add(crest);
      }
    }
  }
  return url;
}

const url = tutteLeUrl();
if (url.size === 0) {
  console.log('[crest] nessun crest da scaricare.');
  process.exit(0);
}

mkdirSync(DESTINAZIONE, { recursive: true });

const percorsoManifesto = join(DESTINAZIONE, 'manifesto.json');
const manifesto = existsSync(percorsoManifesto)
  ? JSON.parse(readFileSync(percorsoManifesto, 'utf8'))
  : {};

let scaricati = 0;
let saltati = 0;
let falliti = 0;

for (const sorgente of url) {
  const estensione = extname(new URL(sorgente).pathname) || '.png';
  const nomeFile = new URL(sorgente).pathname.split('/').pop() ?? `${scaricati}${estensione}`;
  const locale = join(DESTINAZIONE, nomeFile);

  if (existsSync(locale)) {
    manifesto[sorgente] = `/crests/${nomeFile}`;
    saltati += 1;
    continue;
  }

  try {
    const risposta = await fetch(sorgente, { signal: AbortSignal.timeout(15000) });
    if (!risposta.ok) throw new Error(`HTTP ${risposta.status}`);
    writeFileSync(locale, Buffer.from(await risposta.arrayBuffer()));
    manifesto[sorgente] = `/crests/${nomeFile}`;
    scaricati += 1;
  } catch (errore) {
    // Un crest mancante non è un motivo per non pubblicare il bollettino:
    // resta la URL remota, e in ultima istanza il ripiego sul `tla`.
    console.warn(`[crest] non scaricato ${sorgente}: ${errore.message}`);
    falliti += 1;
  }
}

writeFileSync(percorsoManifesto, `${JSON.stringify(manifesto, null, 2)}\n`, 'utf8');
console.log(
  `[crest] ${scaricati} scaricati, ${saltati} già presenti, ${falliti} non riusciti. ` +
    `Manifesto: ${Object.keys(manifesto).length} voci.`,
);
