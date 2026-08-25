import type { Metadata } from 'next';

import { leggiBacktest } from '@/lib/dati';
import { MARCHIO } from '@/lib/testi';

/**
 * COME FUNZIONA — una pagina, non piu' un'ancora in fondo alla lista.
 *
 * Era la seconda sezione del piede, raggiungibile scorrendo tutta la giornata
 * o cliccando una voce che portava a un salto dentro un'altra pagina. Due
 * problemi in uno: chi arrivava da un motore di ricerca cercando come funziona
 * atterrava su una lista di partite, e la spiegazione non aveva un indirizzo
 * proprio da mandare a qualcuno.
 *
 * Il testo e' quello che era, parola per parola. Cambia dove sta.
 */
export const metadata: Metadata = {
  title: 'Come funziona',
  description:
    'Un pronostico per partita, e niente quando non c’è niente da dire. Che cos’è il numero ' +
    'da 0 a 100, perché su alcune partite non diciamo niente, e cos’è la quota equa.',
  alternates: { canonical: '/come-funziona/' },
  openGraph: {
    title: 'Come funziona',
    description: 'Un pronostico per partita, e niente quando non c’è niente da dire.',
    type: 'website',
    siteName: MARCHIO,
  },
};

export default function PaginaComeFunziona() {
  const backtest = leggiBacktest();
  const silenzioSuCento = Math.round(
    (backtest.silence.curve.find((p) => p.s_min === backtest.silence.chosen_s_min)?.silence_rate ??
      0) * 100,
  );

  return (
    <div className="colonna colonna--lista come-funziona">
      <header className="fondo__testata">
        <p className="label">
          <span className="bersaglio" aria-hidden="true" /> Come funziona
        </p>
        {/* `h1` e non `h2`: qui questa e' la pagina, non una sezione dentro
            un'altra. Il livello dei titoli descrive la struttura del
            documento, e su una pagina propria il primo livello e' il primo. */}
        <h1 className="titolo-sezione">
          Un pronostico per partita. E niente, quando non c’è niente da dire.
        </h1>
      </header>

      <div className="schede">
        <article className="scheda-info">
          <SegnoUno />
          <h3 className="scheda-info__titolo">Il punteggio, da 0 a 100</h3>
          <p className="scheda-info__corpo">
            Ogni pronostico porta un numero: quante volte su 100 partite come questa
            quell’esito si avvera secondo il nostro modello. Non è una confidenza, non è
            un voto: è una frequenza, e sotto c’è sempre scritto quante volte pronostici
            di quella fascia si sono avverati davvero.
          </p>
        </article>

        <article className="scheda-info">
          <SegnoDue />
          <h3 className="scheda-info__titolo">Il silenzio</h3>
          <p className="scheda-info__corpo">
            Su circa {silenzioSuCento} partite su 100 non diciamo niente. Succede quando
            il nostro modello dice quasi la stessa cosa del mercato, o quando la stima
            oscilla troppo: un pronostico senza vantaggio è rumore, e pubblicarlo per
            riempire la lista sarebbe la cosa più facile e più disonesta che possiamo
            fare.
          </p>
        </article>

        <article className="scheda-info">
          <SegnoTre />
          <h3 className="scheda-info__titolo">Le quote sono quelle vere</h3>
          <p className="scheda-info__corpo">
            Accanto a un pronostico trovi una quota solo quando l’abbiamo letta da un
            operatore che la espone davvero, e ti diciamo su quanti operatori è
            calcolata. Dove nessuno quota quella scommessa non c’è nessun numero: 1
            diviso la nostra probabilità sarebbe una quota che nessuno paga, e messa
            lì somiglierebbe troppo a un prezzo.
          </p>
        </article>
      </div>
    </div>
  );
}

/* I tre segni delle schede. Stessa lingua del marchio: sola geometria
   ortogonale, tratto a --icon-stroke, terminazioni squadrate. Decorativi —
   il titolo accanto dice già tutto. */

const SEGNO = {
  className: 'scheda-info__segno',
  viewBox: '0 0 40 40',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 'var(--icon-stroke)',
  strokeLinecap: 'square' as const,
  'aria-hidden': true,
  focusable: 'false' as const,
};

/** Il punteggio: una scala a tacche con il segno in cima. */
function SegnoUno() {
  return (
    <svg {...SEGNO}>
      <path d="M4 32h32" />
      <path d="M8 32V22" />
      <path d="M15 32V16" />
      <path d="M22 32V10" />
      <path d="M29 32V19" />
      <path d="M20 4h4v4h-4z" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Il silenzio: una griglia in cui una cella è vuota. */
function SegnoDue() {
  return (
    <svg {...SEGNO}>
      <path d="M6 8h12v12H6z" />
      <path d="M22 8h12v12H22z" />
      <path d="M6 24h12v10H6z" />
      <path d="M22 24h12v10H22z" strokeDasharray="3 3" />
    </svg>
  );
}

/** La quota: due pesi su una bilancia ridotta all'osso. */
function SegnoTre() {
  return (
    <svg {...SEGNO}>
      <path d="M20 6v28" />
      <path d="M6 14h28" />
      <path d="M6 14l-2 8h12l-2-8" />
      <path d="M26 14l-2 8h12l-2-8" />
    </svg>
  );
}
