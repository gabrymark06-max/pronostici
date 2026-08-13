import type { Metadata } from 'next';

import { leggiAccuracy, leggiBacktest } from '@/lib/dati';
import { intero, suCento } from '@/lib/formato';
import { etichettaFascia, FASCE, MARCHIO, NOMI_COMPETIZIONE, REPO } from '@/lib/testi';

/**
 * I PROGRESSI — la pagina che un sito di pronostici di solito non ha.
 *
 * Fino a ieri questi numeri stavano in fondo alla lista, dietro un'ancora. Li
 * portiamo su una pagina propria per una ragione che non e' di navigazione:
 * una cosa raggiungibile solo scorrendo fino in fondo e' una cosa che stai
 * nascondendo, e questi sono i numeri su cui il prodotto chiede di essere
 * giudicato. Se stanno in fondo, sembra che ce li abbiano strappati.
 *
 * LA REGOLA CHE GOVERNA TUTTA LA PAGINA: `accuracy.json` (il registro dal
 * vivo) e `backtest.json` (la prova storica) NON SI MESCOLANO MAI. Non entrano
 * nella stessa frase, non si sommano, non si mediano. Sono due sezioni, ognuna
 * con il proprio `n` scritto accanto.
 *
 * IL NUMERO GRANDE E' QUELLO STORICO, e non e' modestia. Dal vivo abbiamo poche
 * decine di pronostici conclusi: a quel campione un tasso oscilla di venti
 * punti per puro caso. Metterlo grande sarebbe fare esattamente quello che
 * fanno i siti che scrivono «oltre il 75 per cento» senza dire su quante
 * partite — e questa pagina esiste per essere il contrario di quelli.
 */
export const metadata: Metadata = {
  title: 'Progressi — quanti ne abbiamo presi',
  description:
    'Il registro completo: la prova storica su migliaia di pronostici, il conteggio dal vivo ' +
    'da quando il sito pubblica, e come si distribuisce per fascia di probabilità e per ' +
    'campionato. Ogni pronostico è scritto prima della partita e non si modifica dopo.',
  alternates: { canonical: '/progressi/' },
  openGraph: {
    title: 'Progressi — quanti ne abbiamo presi',
    description:
      'La prova storica, il registro dal vivo, e la distribuzione per fascia e per campionato.',
    type: 'website',
    siteName: MARCHIO,
  },
};

export default function PaginaProgressi() {
  const accuracy = leggiAccuracy();
  const backtest = leggiBacktest();

  const vivo = accuracy.live;
  const conclusi = vivo.n ?? 0;
  const usciti = typeof vivo.hit_rate === 'number' ? Math.round(vivo.hit_rate * conclusi) : null;

  const pubblicati = accuracy.progress_to_500.published;
  const bersaglio = accuracy.progress_to_500.target;
  const avanzamento = Math.min(1, bersaglio > 0 ? pubblicati / bersaglio : 0);

  const silenzioSuCento = Math.round(
    (backtest.silence.curve.find((p) => p.s_min === backtest.silence.chosen_s_min)?.silence_rate ??
      0) * 100,
  );

  const campionati = Object.entries(backtest.per_competition)
    .filter(([, v]) => v.with_prediction > 0)
    .sort((a, b) => b[1].with_prediction - a[1].with_prediction);

  return (
    <div className="colonna colonna--lista progressi">
      <header className="progressi__testata">
        <h1 className="titolo-sezione">Quanti ne abbiamo presi</h1>
        <p className="progressi__lettura">
          Ogni pronostico è scritto prima della partita, con la data, e non si modifica dopo.
          Questa pagina è il conto di come è andata. Nessun numero qui dentro è una media di
          due cose diverse: la prova storica e il conteggio dal vivo restano separati, ognuno
          con scritto su quante partite è calcolato.
        </p>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* LA PROVA STORICA                                                  */}
      {/* ---------------------------------------------------------------- */}
      <section className="progressi__blocco">
        <h2 className="label">
          <span className="bersaglio" aria-hidden="true" /> La prova storica
        </h2>

        <div className="registro__perno">
          <p className="cifra">{suCento(backtest.skill.hit_rate)}</p>
          <p className="registro__unita">su 100 pronostici usciti</p>
          <p className="registro__fonte">
            Su {intero(backtest.skill.n)} pronostici, dal{' '}
            {backtest.window.from.split('-').reverse().join('/')} al{' '}
            {backtest.window.to.split('-').reverse().join('/')}. Il modello non ha mai visto il
            risultato prima di scrivere il pronostico.
          </p>
        </div>

        <div className="scorrevole">
          <table className="tabella tabella--progressi">
            <caption className="solo-lettori">
              Pronostici usciti per fascia di probabilità, prova storica
            </caption>
            <thead>
              <tr>
                <th scope="col">Fascia</th>
                <th scope="col" className="num">
                  Dichiarato
                </th>
                <th scope="col" className="num">
                  Usciti
                </th>
                <th scope="col" className="num">
                  Casi
                </th>
              </tr>
            </thead>
            <tbody>
              {FASCE.map((chiave) => {
                const f = backtest.buckets[chiave];
                if (!f || typeof f.hit_rate !== 'number') return null;
                return (
                  <tr key={chiave}>
                    <th scope="row">{etichettaFascia(chiave)}</th>
                    <td className="num" data-etichetta="Dichiarato">
                      {suCento(f.mean_p ?? 0)}
                    </td>
                    <td className="num registro__uscite" data-etichetta="Usciti">
                      {suCento(f.hit_rate)}
                    </td>
                    <td className="num" data-etichetta="Casi">
                      {intero(f.n)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="progressi__nota">
          «Dichiarato» è quello che avevamo detto, «usciti» quello che è successo. Le due
          colonne devono <strong>somigliarsi</strong>: è questo che rende il numero
          verificabile, non quanto è alto. Un modello che dichiara 80 e ne prende 95 non è
          bravo, è tarato male — e lo sarebbe anche al contrario.
        </p>
      </section>

      {/* ---------------------------------------------------------------- */}
      {/* PER CAMPIONATO                                                    */}
      {/* ---------------------------------------------------------------- */}
      {campionati.length > 0 ? (
        <section className="progressi__blocco">
          <h2 className="label">
            <span className="bersaglio" aria-hidden="true" /> Campionato per campionato
          </h2>
          <p className="progressi__lettura">
            Lo stesso modello non funziona uguale ovunque. Dove il campione è piccolo il tasso
            balla, e la colonna dei casi serve a saperlo prima di leggere quella accanto.
          </p>
          <div className="scorrevole">
            <table className="tabella tabella--progressi">
              <caption className="solo-lettori">
                Pronostici usciti per campionato, prova storica
              </caption>
              <thead>
                <tr>
                  <th scope="col">Campionato</th>
                  <th scope="col" className="num">
                    Usciti
                  </th>
                  <th scope="col" className="num">
                    Casi
                  </th>
                  <th scope="col" className="num">
                    In silenzio
                  </th>
                </tr>
              </thead>
              <tbody>
                {campionati.map(([codice, v]) => (
                  <tr key={codice}>
                    <th scope="row">{NOMI_COMPETIZIONE[codice] ?? codice}</th>
                    <td className="num registro__uscite" data-etichetta="Usciti">
                      {suCento(v.hit_rate)}
                    </td>
                    <td className="num" data-etichetta="Casi">
                      {intero(v.with_prediction)}
                    </td>
                    <td className="num" data-etichetta="In silenzio">
                      {suCento(v.silence_rate)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="progressi__nota">
            «In silenzio» è quante volte su cento non abbiamo detto niente su quel campionato.
            Sul totale è {silenzioSuCento} su 100: circa una partita su{' '}
            {Math.max(2, Math.round(100 / Math.max(1, silenzioSuCento)))}.
          </p>
        </section>
      ) : null}

      {/* ---------------------------------------------------------------- */}
      {/* DAL VIVO                                                          */}
      {/* ---------------------------------------------------------------- */}
      <section className="progressi__blocco progressi__blocco--vivo">
        <h2 className="label">
          <span className="bersaglio" aria-hidden="true" /> Dal vivo, da quando il sito pubblica
        </h2>

        {conclusi > 0 && usciti !== null ? (
          <>
            <p className="progressi__vivo">
              <strong>
                {usciti} su {conclusi}
              </strong>{' '}
              pronostici conclusi sono usciti.
            </p>
            <p className="progressi__nota progressi__nota--avviso">
              {conclusi} è troppo poco per leggerci qualcosa, e lo diciamo prima che tu lo
              legga. A questo campione anche un modello che non sa niente può centrarne quasi
              tutti, e uno che sa qualcosa può sbagliarne diversi di fila. Il numero comincia a
              dire qualcosa intorno ai {intero(bersaglio)} conclusi: fino ad allora vale la
              prova storica qui sopra.
            </p>
          </>
        ) : (
          <p className="progressi__vivo">
            Nessun pronostico è ancora arrivato a fine partita. Il conteggio comincia con il
            primo risultato.
          </p>
        )}

        {/* L'AVANZAMENTO VERSO IL CAMPIONE UTILE.
            Non e' una barra di caricamento: e' la distanza che manca perche' il
            numero dal vivo diventi leggibile. Metterla qui e' l'unico modo
            onesto di rispondere alla domanda «quando posso fidarmi». */}
        <div className="avanzamento">
          <p className="avanzamento__testa">
            <span className="label">Verso un campione leggibile</span>
            <span className="num">
              {intero(pubblicati)} / {intero(bersaglio)}
            </span>
          </p>
          <div
            className="avanzamento__pista"
            role="img"
            aria-label={`${intero(pubblicati)} pronostici pubblicati su ${intero(bersaglio)}`}
          >
            <div
              className="avanzamento__pieno"
              style={{ inlineSize: `${(avanzamento * 100).toFixed(1)}%` }}
            />
          </div>
          <p className="progressi__nota">
            Pronostici <em>pubblicati</em>, non ancora tutti conclusi: gli altri riguardano
            partite che devono ancora giocarsi.
          </p>
        </div>

        <p className="progressi__nota">
          Ogni pronostico è scritto prima della partita in un registro pubblico, e non si
          modifica dopo.{' '}
          <a href={REPO} rel="noopener noreferrer" target="_blank">
            Il registro e il codice sono su GitHub
          </a>
          , e chiunque può rifare questi conti da sé.
        </p>
      </section>
    </div>
  );
}
