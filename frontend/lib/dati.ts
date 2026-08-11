/**
 * Lo strato dati. Legge `data/` dal repository IN FASE DI BUILD.
 *
 * Non esiste nessun fetch a runtime, per decisione architetturale (brief 11.2):
 * è il fatto che il sito non possa chiamare niente che impedisce al traffico di
 * esaurire la quota delle quote. Tutte le funzioni qui sono sincrone e girano
 * solo su Node, mai nel browser.
 *
 * Fallimento forte: se `schema_version` non è quella attesa, il build si ferma.
 * Su un sito statico questa è la forma più severa possibile di "fallire forte" —
 * la pagina sbagliata non viene proprio generata (scheda-partita.md, SEO).
 */
import 'server-only';
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

import {
  SCHEMA_VERSION_ATTESA,
  type Accuracy,
  type Backtest,
  type Fixture,
  type GiornoFixtures,
} from './tipi';

/** `data/` sta nella radice del repo, un livello sopra `frontend/`. */
const RADICE_DATI = join(process.cwd(), '..', 'data');

function leggiJson<T>(percorso: string): T {
  return JSON.parse(readFileSync(percorso, 'utf8')) as T;
}

/** Fallisce forte, con un messaggio che dice cosa aggiornare. */
function verificaSchema(versione: number | undefined, file: string): void {
  if (versione !== SCHEMA_VERSION_ATTESA) {
    throw new Error(
      `DATI NON LEGGIBILI — ${file}\n` +
        `  schema_version attesa: ${SCHEMA_VERSION_ATTESA}\n` +
        `  schema_version trovata: ${versione ?? '(assente)'}\n` +
        `  Il contratto è docs/schema.md. Il frontend non degrada in silenzio:\n` +
        `  aggiorna i tipi in lib/tipi.ts insieme al bump, oppure rigenera i dati.`,
    );
  }
}

/* ------------------------------------------------------------------ */
/* Giorni                                                             */
/* ------------------------------------------------------------------ */

const RE_GIORNO = /^(\d{4}-\d{2}-\d{2})\.json$/;

/**
 * Tutte le date che hanno davvero un file, in ordine crescente.
 * È la lista su cui si muovono le frecce ieri/domani: saltano ai giorni che
 * esistono, non a `data ± 1` che potrebbe non esserci mai stato.
 */
export function giorniDisponibili(): string[] {
  const cartella = join(RADICE_DATI, 'fixtures');
  if (!existsSync(cartella)) return [];
  return readdirSync(cartella)
    .map((nome) => RE_GIORNO.exec(nome)?.[1])
    .filter((d): d is string => typeof d === 'string')
    .sort();
}

/** Il giorno da mostrare in home: oggi se esiste, altrimenti il primo dopo, altrimenti l'ultimo. */
export function giornoDiApertura(): string | null {
  const giorni = giorniDisponibili();
  if (giorni.length === 0) return null;
  const oggi = new Date().toISOString().slice(0, 10);
  return giorni.find((g) => g >= oggi) ?? giorni[giorni.length - 1] ?? null;
}

/** Il giorno richiesto, o `null` se quel file non esiste (giorno senza partite mai generato). */
export function leggiGiorno(data: string): GiornoFixtures | null {
  const percorso = join(RADICE_DATI, 'fixtures', `${data}.json`);
  if (!existsSync(percorso)) return null;
  const giorno = leggiJson<GiornoFixtures>(percorso);
  verificaSchema(giorno.schema_version, `data/fixtures/${data}.json`);
  return giorno;
}

/**
 * La finestra della STRISCIA DEI GIORNI: fino a `quanti` giorni che esistono
 * davvero in `data/fixtures/`, centrati sul giorno corrente per quanto
 * possibile. I giorni senza partite non compaiono — la striscia porta solo a
 * pagine che esistono.
 */
export function finestraGiorni(data: string, quanti = 7): string[] {
  const giorni = giorniDisponibili();
  if (giorni.length <= quanti) return giorni;

  const i = giorni.indexOf(data);
  if (i === -1) return giorni.slice(0, quanti);

  const meta = Math.floor(quanti / 2);
  const da = Math.min(Math.max(0, i - meta), giorni.length - quanti);
  return giorni.slice(da, da + quanti);
}

export interface RiepilogoGiorno {
  data: string;
  total: number;
  silence_count: number;
}

/**
 * Il conteggio delle partite per ogni giorno della finestra.
 *
 * Serve al calendario: una casella che dice anche QUANTE partite ci sono
 * smette di essere una destinazione e diventa un'informazione. Si legge a
 * build time come tutto il resto — nessuna chiamata a runtime.
 */
export function riepilogoGiorni(giorni: string[]): RiepilogoGiorno[] {
  return giorni.map((data) => {
    const giorno = leggiGiorno(data);
    return {
      data,
      total: giorno?.total ?? 0,
      silence_count: giorno?.silence_count ?? 0,
    };
  });
}

export interface Vicini {
  precedente: string | null;
  successivo: string | null;
}

/** I giorni adiacenti fra quelli che esistono davvero. */
export function giorniVicini(data: string): Vicini {
  const giorni = giorniDisponibili();
  const i = giorni.indexOf(data);
  if (i === -1) {
    return {
      precedente: [...giorni].reverse().find((g) => g < data) ?? null,
      successivo: giorni.find((g) => g > data) ?? null,
    };
  }
  return { precedente: giorni[i - 1] ?? null, successivo: giorni[i + 1] ?? null };
}

/* ------------------------------------------------------------------ */
/* Partite                                                            */
/* ------------------------------------------------------------------ */

export interface PartitaConGiorno {
  fixture: Fixture;
  data: string;
}

/**
 * Indice match_id → partita. Una partita può comparire in più file (preliminare
 * e definitivo dello stesso giorno non si sovrappongono, ma un match_id resta
 * stabile): vince l'occorrenza più recente, che è quella con più informazione.
 */
export function tutteLePartite(): Map<number, PartitaConGiorno> {
  const indice = new Map<number, PartitaConGiorno>();
  for (const data of giorniDisponibili()) {
    const giorno = leggiGiorno(data);
    if (!giorno) continue;
    for (const fixture of giorno.fixtures) {
      indice.set(fixture.match_id, { fixture, data });
    }
  }
  return indice;
}

export function leggiPartita(matchId: number): PartitaConGiorno | null {
  return tutteLePartite().get(matchId) ?? null;
}

/* ------------------------------------------------------------------ */
/* Accuratezza dal vivo e prova storica                               */
/* ------------------------------------------------------------------ */

/**
 * `accuracy.json` — SOLO il registro dal vivo. I due file non si mescolano
 * mai in un componente: e' `recordDiFascia()` in lib/fascia.ts a SCEGLIERE
 * una delle due fonti e a restituire un solo record gia' etichettato.
 */
export function leggiAccuracy(): Accuracy {
  const dati = leggiJson<Accuracy>(join(RADICE_DATI, 'accuracy.json'));
  verificaSchema(dati.schema_version, 'data/accuracy.json');
  return dati;
}

/** `backtest.json` — SOLO la prova storica. Vedi sopra: i due file non si toccano. */
export function leggiBacktest(): Backtest {
  const dati = leggiJson<Backtest>(join(RADICE_DATI, 'backtest.json'));
  verificaSchema(dati.schema_version, 'data/backtest.json');
  return dati;
}

/* ------------------------------------------------------------------ */
/* Crest                                                              */
/* ------------------------------------------------------------------ */

/**
 * `npm run crests` scarica i loghi in public/crests/ e scrive questo manifesto.
 * Se c'è, si serve il file locale: nessuna dipendenza da un terzo a runtime
 * (oggi.md, Prestazioni). Se non c'è, si ripiega sulla URL remota, e il
 * componente Crest ha comunque il suo ripiego testuale sul `tla`.
 */
export function manifestoCrest(): Record<string, string> {
  const percorso = join(process.cwd(), 'public', 'crests', 'manifesto.json');
  if (!existsSync(percorso)) return {};
  return leggiJson<Record<string, string>>(percorso);
}
