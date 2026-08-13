import { intero, suCento } from '@/lib/formato';
import { etichettaFascia, GIOCO_RESPONSABILE, GRATUITA, MARCHIO, REPO } from '@/lib/testi';
import type { Accuracy, Backtest } from '@/lib/tipi';

import { ANCORA_FUNZIONAMENTO, ANCORA_REGISTRO } from './ancore';

/**
 * IL FONDO DELLA PAGINA — come funziona, e quanti ne abbiamo presi.
 *
 * Sono le due domande che chiunque si fa davanti a un sito di pronostici, e
 * qui hanno una risposta con dei numeri sotto invece di una pagina «chi
 * siamo». Stanno in fondo e non in cima perché chi torna vuole le partite: le
 * spiegazioni sono per la prima visita, e la barra ci porta con due ancore.
 *
 * REGOLA ARCHITETTURALE, rispettata qui alla lettera: `accuracy.json` (il
 * registro dal vivo) e `backtest.json` (la prova storica) NON SI MESCOLANO.
 * Non entrano mai nella stessa frase, non si sommano, non si mediano. Sono due
 * blocchi con due intestazioni diverse, e ognuno porta il proprio `n`.
 *
 * PERCHÉ IL VIVO NON È IL NUMERO GRANDE. Dal vivo abbiamo poche decine di
 * pronostici conclusi: a quel campione un tasso oscilla di venti punti per
 * caso, e metterlo grande sarebbe la stessa cosa che fanno i siti che scrivono
 * «accuratezza superiore al 75 per cento» senza dire su quante partite. Il
 * numero grande è quello storico, su migliaia di casi; il vivo sta accanto,
 * più piccolo, con scritto quanti sono e che è presto per leggerlo.
 */
export function Fondo({
  accuracy,
  backtest,
}: {
  accuracy: Accuracy;
  backtest: Backtest;
}) {
  const silenzioSuCento = Math.round(
    (backtest.silence.curve.find((p) => p.s_min === backtest.silence.chosen_s_min)
      ?.silence_rate ?? 0) * 100,
  );

  const vivo = accuracy.live;
  const conclusiDalVivo = vivo.n ?? 0;
  const uscitiDalVivo =
    typeof vivo.hit_rate === 'number' ? Math.round(vivo.hit_rate * conclusiDalVivo) : null;

  const fasce = ['0.50-0.65', '0.65-0.80', '0.80-1.00'] as const;

  return (
    <>
      {/* ---------------------------------------------------------------- */}
      {/* COME FUNZIONA                                                     */}
      {/* ---------------------------------------------------------------- */}
      <section className="fondo fondo--chiaro" id={ANCORA_FUNZIONAMENTO}>
        <div className="colonna colonna--lista">
          <header className="fondo__testata">
            <p className="label">
              <span className="bersaglio" aria-hidden="true" /> Come funziona
            </p>
            <h2 className="titolo-sezione">
              Un pronostico per partita. E niente, quando non c’è niente da dire.
            </h2>
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
              <h3 className="scheda-info__titolo">La quota equa</h3>
              <p className="scheda-info__corpo">
                Accanto a ogni pronostico c’è la quota equa: è 1 diviso la probabilità.
                Sotto quel prezzo la scommessa perde valore, sopra lo guadagna. Dove
                conosciamo il prezzo degli operatori lo mettiamo accanto, così il confronto
                lo fai tu e non lo devi credere a noi.
              </p>
            </article>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* IL REGISTRO                                                        */}
      {/* ---------------------------------------------------------------- */}
      <section className="fondo" id={ANCORA_REGISTRO}>
        <div className="colonna colonna--lista">
          <header className="fondo__testata">
            <p className="label">
              <span className="bersaglio" aria-hidden="true" /> Il registro
            </p>
            <h2 className="titolo-sezione">Quanti ne abbiamo presi</h2>
          </header>

          <div className="registro">
            {/* IL NUMERO GRANDE: la prova storica. Migliaia di casi, quindi è
                l'unico che si può leggere adesso. */}
            <div className="registro__perno">
              <p className="cifra">{suCento(backtest.skill.hit_rate)}</p>
              <p className="registro__unita">su 100 pronostici usciti</p>
              <p className="registro__fonte">
                Prova storica su {intero(backtest.skill.n)} pronostici, dal{' '}
                {backtest.window.from.split('-').reverse().join('/')} al{' '}
                {backtest.window.to.split('-').reverse().join('/')}. Il modello non ha mai
                visto il risultato prima di scrivere il pronostico.
              </p>
            </div>

            {/* LA TAVOLA PER FASCIA. Un tasso medio da solo mente: gli 85 su
                100 sono facili, i 55 no. Qui ogni fascia porta il proprio n. */}
            <div className="registro__tavola">
              {/* Una tavola di dati è l'unico contenuto che WCAG 1.4.10 esenta
                  dal riflusso su una colonna: si scorre DENTRO il proprio
                  riquadro. Senza questo, al 200 % di corpo le quattro colonne
                  facevano scorrere in orizzontale l'intera pagina. */}
              <div className="scorrevole">
              <table className="tabella">
                <caption className="solo-lettori">
                  Pronostici usciti per fascia di probabilità, prova storica
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Fascia</th>
                    <th scope="col">Dichiarato</th>
                    <th scope="col">Usciti</th>
                    <th scope="col">Casi</th>
                  </tr>
                </thead>
                <tbody>
                  {fasce.map((chiave) => {
                    const f = backtest.buckets[chiave];
                    if (!f || typeof f.hit_rate !== 'number') return null;
                    return (
                      <tr key={chiave}>
                        <th scope="row">{etichettaFascia(chiave)}</th>
                        <td className="num">{suCento(f.mean_p ?? 0)}</td>
                        <td className="num registro__uscite">{suCento(f.hit_rate)}</td>
                        <td className="num">{intero(f.n)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              </div>
              <p className="registro__lettura">
                «Dichiarato» è quello che avevamo detto, «usciti» quello che è successo. Le
                due colonne devono somigliarsi: è questo che rende il numero verificabile,
                non quanto è alto.
              </p>
            </div>

            {/* IL VIVO — terza colonna della griglia sugli schermi larghi.
                Il numero storico, come si distribuisce e cosa sta succedendo
                adesso sono tre facce dello stesso fatto: su una riga sola il
                confronto è immediato, incolonnati uno sotto l'altro no.
                Resta più piccolo e con il suo avvertimento. */}
            <div className="vivo">
            <p className="label">Dal vivo, da quando il sito pubblica</p>
            {conclusiDalVivo > 0 && uscitiDalVivo !== null ? (
              <>
                <p className="vivo__riga">
                  <strong>
                    {uscitiDalVivo} su {conclusiDalVivo}
                  </strong>{' '}
                  pronostici conclusi sono usciti. Ne abbiamo pubblicati{' '}
                  {intero(accuracy.progress_to_500.published)} in tutto: gli altri riguardano
                  partite non ancora giocate.
                </p>
                <p className="vivo__avviso">
                  {conclusiDalVivo} è troppo poco per leggerci qualcosa. A questo campione
                  anche un modello che non sa niente può centrarne quasi tutti, e uno che sa
                  qualcosa può sbagliarne diversi di fila. Il numero comincia a dire qualcosa
                  intorno ai {intero(accuracy.progress_to_500.target)} pronostici conclusi —
                  fino ad allora vale la prova storica qui sopra.
                </p>
              </>
            ) : (
              <p className="vivo__riga">
                Nessun pronostico è ancora arrivato a fine partita. Il conteggio comincia con
                il primo risultato.
              </p>
            )}
            <p className="vivo__registro">
              Ogni pronostico è scritto prima della partita in un registro pubblico, e non si
              modifica dopo.{' '}
              <a href={REPO} rel="noopener noreferrer" target="_blank">
                Il registro e il codice sono su GitHub
              </a>
              .
            </p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* PIEDE                                                             */}
      {/* ---------------------------------------------------------------- */}
      <footer className="piede">
        <div className="colonna colonna--lista piede__interno">
          <p className="piede__marchio">{MARCHIO}</p>
          <p className="piede__riga">{GRATUITA}</p>
          <p className="piede__riga">
            Il gioco d’azzardo può causare dipendenza.{' '}
            <a href={GIOCO_RESPONSABILE.href} rel="noopener noreferrer" target="_blank">
              {GIOCO_RESPONSABILE.testo}
            </a>
          </p>
          <p className="piede__riga piede__riga--minuta">
            Questo sito non accetta scommesse, non rimanda a operatori e non ha affiliazioni.
            I pronostici sono stime statistiche, non previsioni: possono sbagliare, e
            sbagliano.
          </p>
        </div>
      </footer>
    </>
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
