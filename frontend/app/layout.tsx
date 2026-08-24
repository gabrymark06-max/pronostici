import type { Metadata, Viewport } from 'next';
import { Archivo, DM_Mono, Instrument_Sans } from 'next/font/google';
import Script from 'next/script';

import { PREFISSO, SITO } from '@/lib/sito';
import { Piede } from '@/components/Piede';
import { ProvinciaSessione } from '@/components/Sessione';
import { Testata } from '@/components/Testata';
import { giornoDiApertura } from '@/lib/dati';
import { MARCHIO, PAYOFF } from '@/lib/testi';
import '@/styles/tokens.css';
import '@/styles/base.css';
import '@/styles/componenti.css';

/* Tre famiglie, ruoli disgiunti. Self-hosted da next/font: zero layout shift,
   nessuna chiamata a fonts.googleapis.com, compatibile con l'export statico.

   ARCHIVO è la VOCE. Sostituisce il serif da notiziario che c'era prima, ed è
   il cambio che fa più differenza di tutti gli altri messi insieme: un serif
   sui titoli e sulle cifre faceva leggere il prodotto come un documento, ed è
   esattamente il difetto che il proprietario ha nominato. Archivo è variabile
   sull'asse `wdth` (62-125): a 125 e peso 700 è il logotipo e gli occhielli —
   il taglio dei tabelloni sportivi — a 100 e peso 600 sono le cifre. Una
   famiglia sola che copre due registri, invece di due famiglie.

   INSTRUMENT SANS è il LAVORO, variabile sull'asse `wdth` (75-100): la
   condensazione dei nomi di squadra a 360px è una decisione continua, non un
   secondo font.

   DM MONO è lo STRUMENTO: orari, conteggi, la riga di prova della fascia.

   IL COSTO DEI FONT, misurato e non stimato. Una configurazione precedente
   spediva 620 kB di woff2 in 14 file con nove preload prima del primo paint:
   LCP mobile 5.488ms contro un budget di 2.500, di cui 5.033ms di solo Render
   Delay. Bloccando i woff2 la stessa pagina faceva 3.026ms — i font costavano
   2.462ms. Le regole rimaste in vigore da allora:
     · un solo sottoinsieme, `latin`. I dieci campionati coperti sono in
       italiano, inglese, spagnolo, tedesco, francese, olandese, portoghese:
       tutti dentro `latin`. `latin-ext` serve al polacco e al ceco;
     · nessun corsivo reale: i due usi minuti li copre il corsivo sintetico;
     · pesi statici solo dove il font non è variabile (DM Mono: due, non tre). */
const archivo = Archivo({
  subsets: ['latin'],
  display: 'swap',
  axes: ['wdth'],
  variable: '--font-archivo',
});

const instrument = Instrument_Sans({
  subsets: ['latin'],
  display: 'swap',
  axes: ['wdth'],
  variable: '--font-instrument',
});

const dmMono = DM_Mono({
  subsets: ['latin'],
  display: 'swap',
  weight: ['400', '500'],
  variable: '--font-dm-mono',
});

export const metadata: Metadata = {
  metadataBase: new URL(`${SITO}${PREFISSO}/`),
  title: {
    default: `${MARCHIO} — ${PAYOFF}`,
    template: `%s · ${MARCHIO}`,
  },
  description:
    'Pronostici gratuiti sulle partite di calcio: uno per partita, con la probabilità, la quota equa, quante volte pronostici così si sono avverati, e nessun pronostico quando non abbiamo niente da dire.',
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
  /* Il tema scuro è il DEFAULT DEL PRODOTTO, non una preferenza di sistema: un
     solo valore, e lo script qui sotto lo cambia se l'utente ha scelto il
     chiaro con l'interruttore.
     Il valore è --surface-2, cioè il fondo della BARRA: è la superficie che
     tocca il cromo del browser, e se non coincide si vede una banda di un
     colore diverso sopra la barra dell'indirizzo. */
  themeColor: '#191F26',
};

/* Applica il tema salvato prima del primo paint. Il default è lo scuro, che è
   già `:root`: l'attributo si mette solo per il chiaro. Senza questo, chi ha
   scelto il chiaro vede un lampo di fondo scuro. */
const TEMA_PRIMA_DEL_PAINT = `try{var c="#191F26";if(localStorage.getItem("tema")==="light"){document.documentElement.setAttribute("data-theme","light");c="#EDF1F5"}var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute("content",c)}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  /* Letto a build time: il marchio e il bottone «Oggi» puntano al giorno
     reale, non a un redirect. */
  const apertura = giornoDiApertura();

  return (
    <html
      lang="it"
      className={`${archivo.variable} ${instrument.variable} ${dmMono.variable}`}
      suppressHydrationWarning
    >
      {/* ANCHE QUI, E NON PER LO STESSO MOTIVO DI <html>.

          Su <html> serve a noi: lo script del tema aggiunge `data-theme` prima
          dell'idratazione, quindi il client trova un attributo che il server
          non aveva scritto.

          Su <body> serve contro le ESTENSIONI del browser. ColorZilla scrive
          `cz-shortcut-listen="true"`, i gestori di password e i traduttori
          fanno cose simili, e lo fanno PRIMA che React parta: React vede un
          attributo di troppo e getta un errore rosso a tutto schermo su un
          sito che non ha niente che non va. L'errore non e' riproducibile da
          noi — dipende da cosa ha installato chi guarda — e questa e' la
          ragione per cui va tolto qui e non inseguito.

          `suppressHydrationWarning` vale UN SOLO LIVELLO: copre gli attributi
          di <body> e nient'altro. Dentro, ogni disallineamento vero continua
          a essere segnalato. */}
      <body suppressHydrationWarning>
        {/* `beforeInteractive` finisce nell'HTML iniziale ed è eseguito prima
            dell'idratazione. Con next/script invece di un <script> a mano,
            perché React non esegue gli script resi dai componenti. */}
        <Script id="tema" strategy="beforeInteractive">
          {TEMA_PRIMA_DEL_PAINT}
        </Script>
        <a className="salta-al-contenuto" href="#contenuto">
          Salta al contenuto
        </a>
        {/* LA SESSIONE AVVOLGE TUTTO, barra compresa: la voce «Accedi» sta
            nella barra e deve sapere chi sei quanto la pagina del conto.
            Quando i conti sono spenti questo componente non fa nessuna
            chiamata e non aspetta niente — il sito resta quello di prima. */}
        <ProvinciaSessione>
          <Testata giornoApertura={apertura} />
          <main id="contenuto">{children}</main>
          <Piede />
        </ProvinciaSessione>
      </body>
    </html>
  );
}
