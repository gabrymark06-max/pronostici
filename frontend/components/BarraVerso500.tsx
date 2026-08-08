import { intero } from '@/lib/formato';

/**
 * TERZO TRATTAMENTO, distinto da entrambi i linguaggi: non è una probabilità
 * e non è un'affidabilità, quindi non usa né --prob-fill né --rel-stroke.
 * Riempimento --ink-2, 8px, tacche ogni 100.
 *
 * La barra è essa stessa un dispositivo di fiducia: è una scadenza che il
 * prodotto si dà in pubblico.
 */
export function BarraVerso500({
  pubblicati,
  obiettivo,
}: {
  pubblicati: number;
  obiettivo: number;
}) {
  const quota = Math.min(1, pubblicati / obiettivo);
  const tacche = [];
  for (let v = 100; v < obiettivo; v += 100) tacche.push(v);

  return (
    <section className="sezione--pesante" aria-labelledby="titolo-500">
      <h2 id="titolo-500" className="titolo-sezione">
        Verso i {intero(obiettivo)} pronostici
      </h2>

      <div className="verso-500">
        <p className="verso-500__estremi micro">
          <span>{intero(pubblicati)}</span>
          <span>{intero(obiettivo)}</span>
        </p>
        <div
          className="verso-500__pista"
          role="img"
          aria-label={`${pubblicati} pronostici pubblicati su ${obiettivo}.`}
        >
          <div className="verso-500__riempimento" style={{ width: `${quota * 100}%` }} />
          {tacche.map((v) => (
            <span
              key={v}
              className="verso-500__tacca"
              aria-hidden="true"
              style={{ left: `${(v / obiettivo) * 100}%` }}
            />
          ))}
        </div>
      </div>

      <p className="definizione">
        Da {intero(obiettivo)} pronostici dal vivo, questa pagina mostrerà quelli.
        <br />
        Il backtest resterà sotto, per confronto.
      </p>
    </section>
  );
}
