import type { Metadata, Viewport } from 'next';
import { Newsreader, Public_Sans, Red_Hat_Mono } from 'next/font/google';
import Script from 'next/script';

import { Masthead } from '@/components/Masthead';
import { PiePagina } from '@/components/PiePagina';
import { giornoDiApertura } from '@/lib/dati';
import '@/styles/tokens.css';
import '@/styles/base.css';
import '@/styles/componenti.css';

/* Self-hosted da next/font: zero layout shift, nessuna chiamata a
   fonts.googleapis.com, compatibile con l'export statico. */
const newsreader = Newsreader({
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '500', '600'],
  style: ['normal', 'italic'],
  variable: '--font-newsreader',
});

const publicSans = Public_Sans({
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '500', '600'],
  variable: '--font-public-sans',
});

const redHatMono = Red_Hat_Mono({
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '500'],
  variable: '--font-red-hat-mono',
});

export const metadata: Metadata = {
  metadataBase: new URL('https://pronostici.example'),
  title: {
    default: 'Pronostici — un pronostico per partita, e il silenzio quando non c’è',
    template: '%s · Pronostici',
  },
  description:
    'Bollettino statistico gratuito sulle partite di calcio: un solo pronostico per partita, la probabilità con la sua definizione, e nessun pronostico quando non abbiamo niente da dire.',
  applicationName: 'Pronostici',
  authors: [{ name: 'Pronostici' }],
  openGraph: {
    type: 'website',
    locale: 'it_IT',
    siteName: 'Pronostici',
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  /* Nessun maximumScale, nessun userScalable: false. Lo zoom non si disabilita. */
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F4F1EA' },
    { media: '(prefers-color-scheme: dark)', color: '#14130F' },
  ],
};

/* Applica il tema salvato prima del primo paint: senza questo, chi ha scelto
   il tema scuro vede un lampo di carta chiara. Non fa altro. */
const TEMA_PRIMA_DEL_PAINT = `try{var t=localStorage.getItem("tema");if(t==="dark"||t==="light")document.documentElement.setAttribute("data-theme",t)}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  /* Letto a build time: la nav "Oggi" punta al giorno reale, non a un redirect. */
  const apertura = giornoDiApertura();

  return (
    <html
      lang="it"
      className={`${newsreader.variable} ${publicSans.variable} ${redHatMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        {/* `beforeInteractive` finisce nell'HTML iniziale ed è eseguito prima
            dell'idratazione: senza, chi ha scelto il tema scuro vede un lampo
            di carta chiara. Con next/script invece di un <script> a mano,
            perché React non esegue gli script resi dai componenti. */}
        <Script id="tema" strategy="beforeInteractive">
          {TEMA_PRIMA_DEL_PAINT}
        </Script>
        <a className="salta-al-contenuto" href="#contenuto">
          Salta al contenuto
        </a>
        <Masthead giornoApertura={apertura} />
        <main id="contenuto">{children}</main>
        <PiePagina />
      </body>
    </html>
  );
}
