import { dataLungaMaiuscola } from '@/lib/formato';
import { tace, type Fixture } from '@/lib/tipi';

/**
 * LA RIGA DI STATO DEL GIORNO.
 *
 * Sostituisce l'intestazione editoriale della v3 — titolo da 48px, sommario
 * da 19px, conteggio a tacche con la sua legenda, nota di metodo da tre
 * righe: 330px prima della prima partita, cioè più di sette righe di lista
 * spese per dire di che giorno si tratta. In uno strumento di consultazione
 * quel prezzo non si paga.
 *
 * Qui la stessa informazione sta in 44px:
 *   - la data, che resta l'`<h1>` della pagina (per i motori e per chi
 *     ascolta) ma non è più alta 48px, perché chi ha aperto la pagina del 5
 *     settembre sa già che giorno ha aperto;
 *   - i tre conteggi — partite, pronostici, silenzi — in mono, incolonnabili;
 *   - la riga di taratura alla scala del giorno: una tacca per partita,
 *     piena se abbiamo un pronostico, vuota se taciamo.
 *
 * IL SILENZIO NON SI RIMPICCIOLISCE INSIEME ALL'INTESTAZIONE. Il conteggio
 * dei silenzi ha lo stesso peso tipografico del conteggio dei pronostici, e
 * le tacche vuote sono altrettanto visibili di quelle piene: mostrano il
 * silenzio invece di dichiararlo, e lo mostrano come una proporzione
 * misurata, non come un guasto. Il colore non porta niente — piena contro
 * vuota è una differenza di FORMA, e i conteggi qui accanto la nominano in
 * parole.
 */
export function StatoGiorno({ data, fixtures }: { data: string; fixtures: Fixture[] }) {
  const totale = fixtures.length;
  const silenzi = fixtures.filter(tace).length;
  const pronostici = totale - silenzi;

  return (
    <div className="stato pad-lista">
      <h1 className="stato__data">{dataLungaMaiuscola(data)}</h1>

      <p className="stato__conti">
        <span>
          <b>{totale}</b> {totale === 1 ? 'partita' : 'partite'}
        </span>
        <span>
          <b>{pronostici}</b> {pronostici === 1 ? 'pronostico' : 'pronostici'}
        </span>
        <span>
          <b>{silenzi}</b> {silenzi === 1 ? 'silenzio' : 'silenzi'}
        </span>
      </p>

      <span
        className="stato__tacche"
        role="img"
        aria-label={
          silenzi === 0
            ? `${totale} partite, tutte con un pronostico.`
            : `${totale} partite: ${pronostici} con un pronostico, ${silenzi} in silenzio.`
        }
      >
        {fixtures.map((fixture) => (
          <span
            key={fixture.match_id}
            className={`stato__tacca${tace(fixture) ? ' stato__tacca--vuota' : ''}`}
          />
        ))}
      </span>
    </div>
  );
}
