import type { Metadata, Viewport } from 'next';
import { DM_Mono, Instrument_Sans, Newsreader } from 'next/font/google';
import Script from 'next/script';

import { Testata } from '@/components/Testata';
import { giornoDiApertura } from '@/lib/dati';
import { MARCHIO, PAYOFF } from '@/lib/testi';
import '@/styles/tokens.css';
import '@/styles/base.css';
import '@/styles/componenti.css';

/* Tre famiglie, ruoli disgiunti. Self-hosted da next/font: zero layout shift,
   nessuna chiamata a fonts.googleapis.com, compatibile con l'export statico.

   Newsreader e' VARIABILE sull'asse `opsz` (6-72): e' cio' che permette alla
   stessa famiglia di reggere una cifra da 104px e il nome di un campionato da
   22px senza sembrare, nel primo caso, un titolo di giornale ingrandito. Con
   un font variabile non si passa `weight`: l'asse wght e' gia' incluso.

   Instrument Sans e' variabile sull'asse `wdth` (75-100): la condensazione
   dei nomi di squadra a 375px e' una decisione continua, non un secondo font. */
const newsreader = Newsreader({
  subsets: ['latin', 'latin-ext'],
  display: 'swap',
  axes: ['opsz'],
  style: ['normal', 'italic'],
  variable: '--font-newsreader',
});

const instrument = Instrument_Sans({
  subsets: ['latin', 'latin-ext'],
  display: 'swap',
  axes: ['wdth'],
  variable: '--font-instrument',
});

const dmMono = DM_Mono({
  subsets: ['latin'],
  display: 'swap',
  weight: ['300', '400', '500'],
  variable: '--font-dm-mono',
});

export const metadata: Metadata = {
  metadataBase: new URL('https://pronostici.example'),
  title: {
    default: `${MARCHIO} — ${PAYOFF}`,
    template: `%s · ${MARCHIO}`,
  },
  description:
    'Bollettino statistico gratuito sulle partite di calcio: un solo pronostico per partita, la probabilità con la sua definizione, quante volte pronostici così si sono avverati, e nessun pronostico quando non abbiamo niente da dire.',
  applicationName: MARCHIO,
  authors: [{ name: MARCHIO }],
  openGraph: {
    type: 'website',
    locale: 'it_IT',
    siteName: MARCHIO,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  /* Nessun maximumScale, nessun userScalable: false. Lo zoom non si disabilita. */
  /* Il tema scuro è il DEFAULT DEL PRODOTTO, non una preferenza di sistema:
     un solo valore, e lo script qui sotto lo cambia se l'utente ha scelto il
     chiaro con l'interruttore.
     Il valore è --surface-2, cioè il fondo della TESTATA: è la superficie che
     tocca il cromo del browser, e se non coincide si vede una banda di un
     grigio diverso sopra la barra. */
  themeColor: '#151A20',
};

/* Applica il tema salvato prima del primo paint. Il default è lo scuro, che è
   già `:root`: l'attributo si mette solo per il chiaro. Senza questo, chi ha
   scelto il chiaro vede un lampo di fondo scuro. */
const TEMA_PRIMA_DEL_PAINT = `try{var c="#151A20";if(localStorage.getItem("tema")==="light"){document.documentElement.setAttribute("data-theme","light");c="#E3E8ED"}var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute("content",c)}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  /* Letto a build time: il marchio e il bottone "Oggi" puntano al giorno
     reale, non a un redirect. */
  const apertura = giornoDiApertura();

  return (
    <html
      lang="it"
      className={`${newsreader.variable} ${instrument.variable} ${dmMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        {/* `beforeInteractive` finisce nell'HTML iniziale ed è eseguito prima
            dell'idratazione. Con next/script invece di un <script> a mano,
            perché React non esegue gli script resi dai componenti. */}
        <Script id="tema" strategy="beforeInteractive">
          {TEMA_PRIMA_DEL_PAINT}
        </Script>
        <a className="salta-al-contenuto" href="#contenuto">
          Salta al contenuto
        </a>
        <Testata giornoApertura={apertura} />
        <main id="contenuto">{children}</main>
      </body>
    </html>
  );
}
