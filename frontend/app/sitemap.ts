import type { MetadataRoute } from 'next';

import { giorniDisponibili, tutteLePartite } from '@/lib/dati';

/* L'export statico richiede che la rotta sia dichiarata statica. */
export const dynamic = 'force-static';

const BASE = 'https://pronostici.example';

/**
 * Il sito ha due tipi di pagina e basta: la giornata e la partita.
 * Le rotte `/come-funziona/` e `/come-stiamo-andando/` non esistono piu' e
 * non compaiono qui.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const fisse: MetadataRoute.Sitemap = [
    { url: `${BASE}/`, changeFrequency: 'daily', priority: 1 },
  ];

  const giorni: MetadataRoute.Sitemap = giorniDisponibili().map((data) => ({
    url: `${BASE}/giorno/${data}/`,
    changeFrequency: 'daily',
    priority: 0.7,
  }));

  const partite: MetadataRoute.Sitemap = [...tutteLePartite().keys()].map((id) => ({
    url: `${BASE}/partita/${id}/`,
    changeFrequency: 'daily',
    priority: 0.6,
  }));

  return [...fisse, ...giorni, ...partite];
}
