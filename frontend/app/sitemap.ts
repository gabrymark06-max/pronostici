import type { MetadataRoute } from 'next';

import { giorniDisponibili, tutteLePartite } from '@/lib/dati';
import { PREFISSO, SITO } from '@/lib/sito';

/* L'export statico richiede che la rotta sia dichiarata statica. */
export const dynamic = 'force-static';

/* Deciso in fase di build: vedi `lib/sito.ts`. */
const BASE = `${SITO}${PREFISSO}`;

/**
 * Il sito ha quattro tipi di pagina: la giornata, la partita, il pronostico
 * del giorno e i progressi.
 *
 * `/pronostico-del-giorno/` C'E', e con la priorita' piu' alta dopo la radice:
 * non e' piu' un rimando, mostra i pronostici, ed e' l'indirizzo che la gente
 * condivide. Il suo canonical punta alla pagina datata, che e' il modo corretto
 * di dire «stesso contenuto, ma l'indirizzo buono a lungo termine e' quello».
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const fisse: MetadataRoute.Sitemap = [
    { url: `${BASE}/`, changeFrequency: 'daily', priority: 1 },
    { url: `${BASE}/progressi/`, changeFrequency: 'daily', priority: 0.8 },
    { url: `${BASE}/come-funziona/`, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${BASE}/pronostico-del-giorno/`, changeFrequency: 'daily', priority: 0.9 },
  ];

  const giorni = giorniDisponibili();

  const liste: MetadataRoute.Sitemap = giorni.map((data) => ({
    url: `${BASE}/giorno/${data}/`,
    changeFrequency: 'daily',
    priority: 0.7,
  }));

  const schedine: MetadataRoute.Sitemap = giorni.map((data) => ({
    url: `${BASE}/pronostico-del-giorno/${data}/`,
    changeFrequency: 'daily',
    priority: 0.7,
  }));

  const partite: MetadataRoute.Sitemap = [...tutteLePartite().keys()].map((id) => ({
    url: `${BASE}/partita/${id}/`,
    changeFrequency: 'daily',
    priority: 0.6,
  }));

  return [...fisse, ...liste, ...schedine, ...partite];
}
