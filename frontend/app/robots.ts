import type { MetadataRoute } from 'next';

import { indirizzo } from '@/lib/sito';

/* L'export statico richiede che la rotta sia dichiarata statica. */
export const dynamic = 'force-static';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/' },
    sitemap: indirizzo('/sitemap.xml'),
  };
}
