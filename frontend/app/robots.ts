import type { MetadataRoute } from 'next';

/* L'export statico richiede che la rotta sia dichiarata statica. */
export const dynamic = 'force-static';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/' },
    sitemap: 'https://pronostici.example/sitemap.xml',
  };
}
