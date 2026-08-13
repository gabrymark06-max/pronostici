import type { MetadataRoute } from 'next';

import { giorniDisponibili, tutteLePartite } from '@/lib/dati';

/* L'export statico richiede che la rotta sia dichiarata statica. */
export const dynamic = 'force-static';

const BASE = 'https://pronostici.example';

/**
 * Il sito ha quattro tipi di pagina: la giornata, la partita, il pronostico
 * del giorno e i progressi.
 *
 * GLI INDIRIZZI SENZA DATA NON ENTRANO. `/pronostico-del-giorno/` e' un
 * rimando con `refresh` nel <head> e il suo canonical punta al giorno: metterlo
 * qui accanto alla pagina datata sarebbe dichiarare due indirizzi per lo stesso
 * contenuto. Ci sta solo `/`, che e' la radice e va dichiarata comunque.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const fisse: MetadataRoute.Sitemap = [
    { url: `${BASE}/`, changeFrequency: 'daily', priority: 1 },
    { url: `${BASE}/progressi/`, changeFrequency: 'daily', priority: 0.8 },
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
