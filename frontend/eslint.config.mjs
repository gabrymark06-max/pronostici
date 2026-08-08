import coreWebVitals from 'eslint-config-next/core-web-vitals';
import typescript from 'eslint-config-next/typescript';

const configurazione = [
  { ignores: ['.next/**', 'out/**', 'node_modules/**', 'next-env.d.ts', 'public/**'] },
  ...coreWebVitals,
  ...typescript,
  {
    rules: {
      // I crest sono 24px, locali dopo `npm run crests`, con width/height
      // espliciti. next/image richiederebbe un runtime di ottimizzazione che
      // l'export statico, per decisione architetturale, non ha.
      '@next/next/no-img-element': 'off',

      // La navigazione è fatta di <a> veri, non di <Link>.
      // In export statico i prefetch RSC di <Link> chiedono payload che
      // l'export non produce (404 a ogni riga di lista), e il router client
      // non ha niente da guadagnare: non c'è stato condiviso fra le pagine.
      // Il design system chiede esattamente questo (MASTER §4): link che
      // "funzionano senza JavaScript, sono condivisibili, e il back del
      // browser fa la cosa giusta senza codice".
      '@next/next/no-html-link-for-pages': 'off',
    },
  },
];

export default configurazione;
