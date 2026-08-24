import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const qui = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Export statico: nessun runtime, nessuna API route, nessun segreto.
  // Decisione architetturale del brief 11.2 — non una preferenza.
  output: 'export',

  // Cartelle con lo slash finale: l'hosting statico serve out/x/index.html
  // senza bisogno di regole di rewrite.
  trailingSlash: true,

  // Nessuna ottimizzazione immagini: richiederebbe un runtime.
  // I crest sono 24px e vengono scaricati in public/ in fase di build.
  images: { unoptimized: true },

  // Il codice non deve poter compilare con errori di tipo.
  typescript: { ignoreBuildErrors: false },

  // IL PREFISSO, quando il sito non sta alla radice del dominio.
  //
  // GitHub Pages serve da `utente.github.io/nome-repo/`: senza questo ogni
  // percorso assoluto punterebbe alla radice del dominio e si otterrebbe una
  // pagina bianca con tutti i 404. Su un dominio dedicato resta vuoto e non
  // cambia niente — e' la stessa build.
  ...(process.env.NEXT_PUBLIC_PREFISSO
    ? {
        basePath: process.env.NEXT_PUBLIC_PREFISSO,
        assetPrefix: process.env.NEXT_PUBLIC_PREFISSO,
      }
    : {}),

  // Il progetto Next vive in frontend/, ma legge data/ dalla radice del repo.
  outputFileTracingRoot: join(qui, '..'),
};

export default nextConfig;
