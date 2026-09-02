import type { Metadata } from 'next';

import {
  GraficoCalibrazione,
  GraficoCampionati,
  GraficoCurva,
  type BarraCampionato,
  type PuntoCalibrazione,
} from '@/components/grafici';
import { giorniDisponibili, leggiAccuracy, leggiBacktest, leggiGiorno } from '@/lib/dati';
import { euro, intero, suCento } from '@/lib/formato';
import { conto, PUNTATE } from '@/lib/puntate';
import { etichettaFascia, FASCE, MARCHIO, NOMI_COMPETIZIONE } from '@/lib/testi';

/**
 * I PROGRESSI — la pagina che un sito di pronostici di solito non ha.
 *
 * LA REGOLA CHE GOVERNA TUTTO: `accuracy.json` (il registro dal vivo) e
 * `backtest.json` (la prova storica) NON SI MESCOLANO MAI. Non entrano nella
 * stessa frase, non si sommano, non si mediano, e non finiscono nello stesso
 * grafico. Sono blocchi separati, ognuno con il proprio `n` scritto accanto.
 *
 * IL NUMERO GRANDE E' QUELLO STORICO, e non e' modestia: dal vivo abbiamo poche
 * decine di pronostici conclusi, e a quel campione un tasso oscilla di venti
 * punti per puro caso. Metterlo grande sarebbe fare quello che fanno i siti che
 * scrivono «oltre il 75 per cento» senza dire su quante partite — e questa
 * pagina esiste per essere il contrario di quelli.
 *
 * L'IMPAGINAZIONE E' A GRIGLIA, larga quanto la pagina. La versione precedente
 * incolonnava tutto in una striscia stretta a sinistra e lasciava due terzi
 * dello schermo vuoti: su una pagina fatta di confronti — dichiarato contro
 * uscito, campionato contro campionato — quello che si vuole e' avere i pezzi
 * ACCANTO, non uno sotto l'altro a mille pixel di distanza.
 */
export const metadata: Metadata = {
  title: 'Progressi — quanti ne abbiamo presi',
  description:
    'Il registro completo: la prova storica su migliaia di pronostici, quanto la nostra ' +
    'probabilità dichiarata somiglia a quella che si è avverata, il conto campionato per ' +
    'campionato, e il conteggio dal vivo da quando il sito pubblica.',
  alternates: { canonical: '/progressi/' },
  openGraph: {
    title: 'Progressi — quanti ne abbiamo presi',
    description:
      'La prova storica, la calibrazione, il conto per campionato e il registro dal vivo.',
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

  /* IL CONTO DELLE SCHEDINE si ricompone da zero a ogni build: le schedine
     non stanno nell'archivio, nascono dal file del giorno. Camminare tutti i
     giorni pubblicati costa una lettura per file, la stessa che fa il
     calendario, e in cambio non c'è nessuno stato da tenere sincronizzato. */
  const conti = conto(
    giorniDisponibili().map((data) => ({
      data,
      fixtures: leggiGiorno(data)?.fixtures ?? [],
    })),
  );

  const pubblicati = accuracy.progress_to_500.published;
  const bersaglio = accuracy.progress_to_500.target;
  const avanzamento = Math.min(1, bersaglio > 0 ? pubblicati / bersaglio : 0);

  const silenzioSuCento = Math.round(
    (backtest.silence.curve.find((p) => p.s_min === backtest.silence.chosen_s_min)?.silence_rate ??
      0) * 100,
  );

  const calibrazione: PuntoCalibrazione[] = FASCE.map((chiave) => {
    const f = backtest.buckets[chiave];
    if (!f || typeof f.hit_rate !== 'number' || typeof f.mean_p !== 'number') return null;
    return {
      etichetta: etichettaFascia(chiave),
      dichiarato: f.mean_p,
      uscito: f.hit_rate,
      n: f.n,
    };
  }).filter((p): p is PuntoCalibrazione => p !== null);

  const campionati: BarraCampionato[] = Object.entries(backtest.per_competition)
    .filter(([, v]) => v.with_prediction > 0)
    .sort((a, b) => b[1].with_prediction - a[1].with_prediction)
    .map(([codice, v]) => ({
      nome: NOMI_COMPETIZIONE[codice] ?? codice,
      uscito: v.hit_rate,
      n: v.with_prediction,
    }));

  const curva = backtest.silence.curve.map((p) => ({ x: p.s_min, y: p.silence_rate }));

  /* Lo scarto medio fra dichiarato e uscito, in punti su cento. E' il numero
     che riassume il grafico della calibrazione in una cifra sola, ed e' quello
     che va guardato PRIMA del tasso: un modello tarato male non diventa buono
     perche' prende tanto. */
  const scarto =
    calibrazione.length > 0
      ? Math.round(
          (calibrazione.reduce((acc, p) => acc + Math.abs(p.uscito - p.dichiarato) * p.n, 0) /
            calibrazione.reduce((acc, p) => acc + p.n, 0)) *
            100,
        )
      : null;

  return (
    <div className="colonna colonna--pagina progressi">
      <header className="progressi__testata">
        <h1 className="titolo-sezione">Quanti ne abbiamo presi</h1>
        <p className="progressi__lettura">
          Ogni pronostico è scritto prima della partita, con la data, e non si modifica dopo.
          Questa pagina è il conto di come è andata. Nessun numero qui dentro è una media di due
          cose diverse: la prova storica e il conteggio dal vivo restano separati, ognuno con
          scritto su quante partite è calcolato.
        </p>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* PRIMA FILA: il numero grande, la calibrazione, il silenzio        */}
      {/* ---------------------------------------------------------------- */}
      <h2 className="label progressi__occhiello">
        <span className="bersaglio" aria-hidden="true" /> La prova storica
      </h2>

      <div className="griglia-progressi">
        <section className="carta carta--perno">
          <div className="carta__testa">
            <h3 className="carta__titolo">Quanti ne abbiamo presi</h3>
            <p className="carta__occhiello">
              In due stagioni di partite, ricalcolate una per una senza mai guardare il
              risultato prima.
            </p>
          </div>
          <div className="carta__corpo">
            <p className="cifra">{suCento(backtest.skill.hit_rate)}</p>
            <p className="registro__unita">su 100 pronostici usciti</p>
          </div>
          <p className="carta__nota">
            Su {intero(backtest.skill.n)} pronostici, dal{' '}
            {backtest.window.from.split('-').reverse().join('/')} al{' '}
            {backtest.window.to.split('-').reverse().join('/')}.
          </p>
        </section>

        <section className="carta">
          <div className="carta__testa">
            <h3 className="carta__titolo">Quanto ci somigliamo</h3>
            <p className="carta__occhiello">
              In orizzontale quello che avevamo detto, in verticale quello che è successo. La
              diagonale è la perfezione. <strong>Sopra è un errore quanto sotto.</strong>
            </p>
          </div>
          <div className="carta__corpo">
          <GraficoCalibrazione punti={calibrazione} />
          <table className="tabella tabella--minuta">
            <caption className="solo-lettori">
              Dichiarato, uscito e casi per ogni fascia di probabilità
            </caption>
            <thead>
              <tr>
                <th scope="col">Fascia</th>
                <th scope="col" className="num">
                  Detto
                </th>
                <th scope="col" className="num">
                  Fatto
                </th>
                <th scope="col" className="num">
                  Casi
                </th>
              </tr>
            </thead>
            <tbody>
              {calibrazione.map((p) => (
                <tr key={p.etichetta}>
                  <th scope="row">{p.etichetta}</th>
                  <td className="num" data-etichetta="Detto">
                    {suCento(p.dichiarato)}
                  </td>
                  <td className="num registro__uscite" data-etichetta="Fatto">
                    {suCento(p.uscito)}
                  </td>
                  <td className="num" data-etichetta="Casi">
                    {intero(p.n)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          {scarto !== null ? (
            <p className="carta__nota">
              Scarto medio fra detto e fatto:{' '}
              <strong>
                {scarto} {scarto === 1 ? 'punto' : 'punti'} su 100
              </strong>
              . È il numero da guardare per primo — prima del tasso.
            </p>
          ) : null}
        </section>

        <section className="carta">
          <div className="carta__testa">
            <h3 className="carta__titolo">Quanto stiamo zitti</h3>
            <p className="carta__occhiello">
              Su circa {silenzioSuCento} partite su 100 non diciamo niente. Non è un numero
              scelto per fare scena: è il punto in cui questa curva è stata tagliata.
            </p>
          </div>
          <div className="carta__corpo">
            <GraficoCurva
              punti={curva}
              scelto={backtest.silence.chosen_s_min}
              etichettaX="soglia →"
            />
          </div>
          <p className="carta__nota">
            Più a destra si taglia, più si tace. Il taglio segnato è quello in uso: sotto
            quella soglia il nostro modello dice quasi la stessa cosa del mercato, e un
            pronostico senza niente da aggiungere è rumore.
          </p>
        </section>
      </div>

      {/* ---------------------------------------------------------------- */}
      {/* SECONDA FILA: campionati e dal vivo, affiancati                   */}
      {/* ---------------------------------------------------------------- */}
      <div className="griglia-progressi griglia-progressi--due">
        {campionati.length > 0 ? (
          <section className="carta">
            <div className="carta__testa">
              <h3 className="carta__titolo">Campionato per campionato</h3>
              <p className="carta__occhiello">
                Lo stesso modello non funziona uguale ovunque. La barra è quanti ne abbiamo
                presi; il filo sottile sotto è quanto pesa quel campionato rispetto al più
                popolato.
              </p>
            </div>
            <div className="carta__corpo">
              <GraficoCampionati barre={campionati} />
            </div>
            <p className="carta__nota">
              L’ordine è per numero di partite, non per tasso: mettere in cima chi ha il numero
              più alto premierebbe i campionati con dieci casi, dove quel numero non vuol dire
              niente. Dove il filo è corto, la cifra accanto balla.
            </p>
          </section>
        ) : null}

        {/* IL CONTO DELLE SCHEDINE, in euro e con le perdite dentro.
            Il resto di questa pagina misura la nostra calibrazione: quanto la
            probabilità dichiarata somiglia a quella che si avvera. Questo
            misura un'altra cosa, e più scomoda — cosa sarebbe successo a un
            portafoglio. Le due non coincidono: si può essere calibrati bene e
            perdere soldi, perché il margine dell'operatore sta in mezzo, e su
            una multipla a tre gambe ci sta tre volte.
            IL NUMERO GRANDE È IL NETTO. Un conto che mostra le vincite e tace
            le perdite è quello che fanno i siti che campano di questo. */}
        <section className="carta carta--vivo">
          <div className="carta__testa">
            <h3 className="carta__titolo">Le schedine, in euro</h3>
            <p className="carta__occhiello">
              {euro(PUNTATE.raddoppio)} sul raddoppio e {euro(PUNTATE.multipla)} sulla
              multipla, ogni giorno, ai prezzi che abbiamo trovato davvero.
            </p>
          </div>

          <div className="carta__corpo">
            {conti.giocate.length > 0 ? (
              <>
                <p className="progressi__vivo">
                  <strong>{euro(conti.netto)}</strong>{' '}
                  {conti.netto >= 0 ? 'di guadagno' : 'di perdita'} su{' '}
                  {euro(conti.speso)} giocati in {conti.giocate.length} schedine.
                </p>
                <p className="carta__avviso">
                  {conti.vinte} {conti.vinte === 1 ? 'uscita' : 'uscite'} su{' '}
                  {conti.giocate.length}. È un campione minuscolo e
                  non dice ancora niente: bastano una multipla presa o due raddoppi sbagliati
                  a ribaltare il segno. Serve a esserci, non a concludere.
                </p>
              </>
            ) : (
              <p className="progressi__vivo">
                Nessuna schedina è ancora entrata nel conto. Ci entra quando è finita e quando
                <strong> ognuna</strong> delle sue gambe ha un prezzo che abbiamo trovato:
                moltiplicare quote che nessuno espone darebbe un incasso che nessuno avrebbe
                mai pagato.
              </p>
            )}
          </div>

          {conti.senzaPrezzo > 0 ? (
            <p className="carta__nota">
              Altre {conti.senzaPrezzo} schedine sono finite ma restano fuori dal conto: almeno
              una gamba era su un mercato che nessuna fonte quotava. Fino al 25 agosto 2026
              erano quasi tutte — le schedine pescano i mercati più probabili, e nessun
              comparatore gratuito li prezzava.
            </p>
          ) : null}
        </section>

        <section className="carta carta--vivo">
          <div className="carta__testa">
            <h3 className="carta__titolo">Dal vivo, da quando il sito pubblica</h3>
            <p className="carta__occhiello">
              I pronostici pubblicati da questo sito e già arrivati a fine partita. Sono pochi,
              e il numero va letto sapendolo.
            </p>
          </div>

          <div className="carta__corpo">
          {conclusi > 0 && usciti !== null ? (
            <>
              <p className="progressi__vivo">
                <strong>
                  {usciti} su {conclusi}
                </strong>{' '}
                pronostici conclusi sono usciti.
              </p>
              <p className="carta__avviso">
                {conclusi} è troppo poco per leggerci qualcosa, e lo diciamo prima che tu lo
                legga. A questo campione anche un modello che non sa niente può centrarne quasi
                tutti, e uno che sa qualcosa può sbagliarne diversi di fila. Il numero comincia
                a dire qualcosa intorno ai {intero(bersaglio)} conclusi: fino ad allora vale la
                prova storica qui sopra.
              </p>
            </>
          ) : (
            <p className="progressi__vivo">
              Nessun pronostico è ancora arrivato a fine partita. Il conteggio comincia con il
              primo risultato.
            </p>
          )}

          {/* L'AVANZAMENTO VERSO IL CAMPIONE UTILE. Non e' una barra di
              caricamento: e' la distanza che manca perche' il numero dal vivo
              diventi leggibile, ed e' l'unica risposta onesta a «quando posso
              fidarmi». */}
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
          </div>
          </div>
          <p className="carta__nota">
            Sopra ci sono i pronostici <em>pubblicati</em>, non ancora tutti conclusi: gli altri
            riguardano partite che devono ancora giocarsi.
          </p>
        </section>
      </div>
    </div>
  );
}
