import { intero } from '@/lib/formato';
import type { RecordFascia } from '@/lib/fascia';

/**
 * L'unica affermazione di accuratezza che il prodotto pronuncia sulla scheda.
 *
 * LA FONTE STA DENTRO LA FRASE, mai in un asterisco: "nel nostro test storico"
 * oppure "fra quelli che abbiamo pubblicato". È la differenza fra un numero
 * verificabile e uno slogan.
 *
 * Quando non c'è nemmeno il backtest, la riga non sparisce: dire che non lo
 * sappiamo ancora, e da quando lo sapremo, è ancora un'informazione — non un
 * buco.
 */
export function RigaFascia({ record }: { record: RecordFascia | null }) {
  return (
    <section className="sezione" aria-labelledby="titolo-fascia">
      <h2 id="titolo-fascia" className="label">
        Quanto spesso si avverano pronostici così
      </h2>

      {record ? (
        <>
          <p className="fascia__frase">
            Su 100 pronostici in questa fascia ({record.etichetta}),{' '}
            {record.fonte === 'storico' ? (
              <>nel nostro test storico</>
            ) : (
              <>fra quelli che abbiamo pubblicato</>
            )}{' '}
            ne sono usciti {record.suCento}.
          </p>
          <p className="micro fascia__n">
            n={intero(record.n)} · {record.periodo}
          </p>
        </>
      ) : (
        <p className="fascia__frase">
          Non abbiamo ancora abbastanza pronostici in questa fascia per dire quanto spesso si
          avverano. Lo diremo quando ne avremo 50.
        </p>
      )}
    </section>
  );
}
