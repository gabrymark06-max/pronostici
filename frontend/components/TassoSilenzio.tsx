import { intero, percentuale } from '@/lib/formato';
import type { Accuracy, MotivoSilenzio } from '@/lib/tipi';

/**
 * Il tasso di silenzio contro la BANDA OBIETTIVO DICHIARATA.
 * Promessa e realtà sullo stesso asse — è l'elemento che nessun concorrente ha.
 *
 * SVG inline, nessuna libreria. Riceve solo `accuracy.json`.
 *
 * Nota di scope: come-stiamo-andando.md chiede barre SETTIMANALI. Oggi tutte
 * le righe del registro sono state scritte lo stesso giorno, quindi una serie
 * per settimana avrebbe una barra sola e direbbe meno di niente. Finché non
 * c'è una storia, si mostrano i due tassi che esistono davvero — preliminare e
 * definitivo — sullo stesso asse e sulla stessa banda dichiarata.
 *
 * Il grafico non è mai l'unico portatore: c'è una <figcaption> che riassume
 * l'andamento a parole e una tabella con gli stessi dati.
 */

const LARGHEZZA = 780;
const ALTEZZA = 220;
const MARGINE = { alto: 12, destro: 172, basso: 34, sinistro: 44 };
const MASSIMO = 0.5; // asse y 0–50%

const NOME_FASE: Record<string, string> = {
  preliminary: 'Preliminare',
  definitive: 'Definitivo',
};

const GLIFO: Record<MotivoSilenzio, string> = {
  S_min: '≈',
  no_candidates: '≈',
  sigma_max: '±',
  p_min: '<',
};

const ETICHETTA_MOTIVO: Record<MotivoSilenzio, string> = {
  S_min: 'non distinguibile',
  no_candidates: 'non distinguibile',
  sigma_max: 'stima instabile',
  p_min: 'troppo improbabile',
};

export function TassoSilenzio({
  accuracy,
  banda,
  limiteDuro = 0.4,
}: {
  accuracy: Accuracy;
  banda: [number, number];
  limiteDuro?: number;
}) {
  const fasi = (['preliminary', 'definitive'] as const)
    .map((fase) => ({ fase, dati: accuracy.silence[fase] }))
    .filter((v): v is { fase: 'preliminary' | 'definitive'; dati: NonNullable<typeof v.dati> } =>
      v.dati != null,
    );

  if (fasi.length === 0) return null;

  const areaAlta = ALTEZZA - MARGINE.alto - MARGINE.basso;
  const areaLarga = LARGHEZZA - MARGINE.sinistro - MARGINE.destro;
  const y = (v: number) => MARGINE.alto + areaAlta * (1 - Math.min(v, MASSIMO) / MASSIMO);
  const passo = areaLarga / fasi.length;
  const larghezzaBarra = Math.min(84, passo * 0.5);

  const dentroLaBanda = fasi.filter(
    (f) => f.dati.rate >= banda[0] && f.dati.rate <= banda[1],
  ).length;

  const motivi = new Map<MotivoSilenzio, number>();
  for (const { dati } of fasi) {
    for (const [motivo, quanti] of Object.entries(dati.by_reason)) {
      if (typeof quanti !== 'number') continue;
      const chiave = motivo as MotivoSilenzio;
      motivi.set(chiave, (motivi.get(chiave) ?? 0) + quanti);
    }
  }

  const descrizione =
    `Tasso di silenzio per fase, contro la banda dichiarata fra ${percentuale(banda[0])} e ` +
    `${percentuale(banda[1])} e il limite duro del ${percentuale(limiteDuro)}.`;

  return (
    <section className="sezione--pesante" aria-labelledby="titolo-tasso">
      <h2 id="titolo-tasso" className="titolo-sezione">
        Quanto stiamo tacendo
      </h2>

      <figure className="silenzio-grafico">
        <svg viewBox={`0 0 ${LARGHEZZA} ${ALTEZZA}`} role="img" aria-labelledby="desc-tasso">
          {/* Una stringa sola: children multipli dentro <title> vengono
              serializzati e riletti in modo diverso, e l'idratazione fallisce. */}
          <title id="desc-tasso">{descrizione}</title>

          {/* La banda che ci siamo dati: promessa e realtà sullo stesso asse. */}
          <rect
            className="sg-banda"
            x={MARGINE.sinistro}
            y={y(banda[1])}
            width={areaLarga}
            height={y(banda[0]) - y(banda[1])}
          />
          <line className="sg-filetto" x1={MARGINE.sinistro} x2={LARGHEZZA - MARGINE.destro} y1={y(banda[0])} y2={y(banda[0])} />
          <line className="sg-filetto" x1={MARGINE.sinistro} x2={LARGHEZZA - MARGINE.destro} y1={y(banda[1])} y2={y(banda[1])} />
          <text className="sg-testo" x={LARGHEZZA - MARGINE.destro + 8} y={(y(banda[0]) + y(banda[1])) / 2 + 3}>
            banda che ci siamo dati
          </text>

          {/* Il limite duro. */}
          <line className="sg-limite" x1={MARGINE.sinistro} x2={LARGHEZZA - MARGINE.destro} y1={y(limiteDuro)} y2={y(limiteDuro)} />
          <text className="sg-testo" x={LARGHEZZA - MARGINE.destro + 8} y={y(limiteDuro) + 3}>
            limite duro
          </text>

          {/* Asse y. */}
          {[0, 0.1, 0.2, 0.3, 0.4, 0.5].map((v) => (
            <text key={v} className="sg-testo" x={MARGINE.sinistro - 8} y={y(v) + 3} textAnchor="end">
              {percentuale(v)}
            </text>
          ))}
          <line className="sg-asse" x1={MARGINE.sinistro} x2={LARGHEZZA - MARGINE.destro} y1={y(0)} y2={y(0)} />

          {fasi.map(({ fase, dati }, i) => {
            const x = MARGINE.sinistro + passo * i + (passo - larghezzaBarra) / 2;
            return (
              <g key={fase}>
                <rect
                  className="sg-barra"
                  x={x}
                  y={y(dati.rate)}
                  width={larghezzaBarra}
                  height={y(0) - y(dati.rate)}
                />
                <text className="sg-testo" x={x + larghezzaBarra / 2} y={ALTEZZA - 18} textAnchor="middle">
                  {NOME_FASE[fase]}
                </text>
                <text className="sg-testo" x={x + larghezzaBarra / 2} y={ALTEZZA - 6} textAnchor="middle">
                  {percentuale(dati.rate)} · n={dati.n}
                </text>
              </g>
            );
          })}
        </svg>

        <figcaption>
          {dentroLaBanda === fasi.length
            ? 'Entrambi i tassi stanno dentro la banda che ci siamo dati, e sotto il limite duro.'
            : dentroLaBanda === 0
              ? 'Nessuno dei due tassi sta dentro la banda che ci siamo dati. La banda resta quella: non la spostiamo per farci stare i numeri.'
              : 'Uno dei due tassi sta dentro la banda che ci siamo dati, l’altro no. La banda resta quella.'}{' '}
          Il tasso di silenzio nel tempo, settimana per settimana, comparirà qui quando avremo
          pubblicato per più settimane.
        </figcaption>
      </figure>

      <details className="dettaglio-dati">
        <summary>Gli stessi dati in tabella</summary>
        <div className="scorrevole">
          <table className="tabella">
            <caption>Partite valutate, partite su cui abbiamo taciuto, e il tasso.</caption>
            <thead>
              <tr>
                <th scope="col">Fase</th>
                <th scope="col">Valutate</th>
                <th scope="col">Silenzi</th>
                <th scope="col">Tasso</th>
              </tr>
            </thead>
            <tbody>
              {fasi.map(({ fase, dati }) => (
                <tr key={fase}>
                  <th scope="row">{NOME_FASE[fase]}</th>
                  <td className="num">{intero(dati.n)}</td>
                  <td className="num">{intero(dati.silent)}</td>
                  <td className="num">{percentuale(dati.rate, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      {motivi.size > 0 ? (
        <>
          <h3 className="label" style={{ marginTop: 'var(--s-5)' }}>
            Per quale motivo abbiamo taciuto
          </h3>
          <div className="grezze">
            {[...motivi.entries()].map(([motivo, quanti]) => (
              <span className="grezze__voce" key={motivo}>
                <span className="silenzio__glifo" aria-hidden="true">
                  {GLIFO[motivo]}
                </span>
                <span className="grezze__etichetta">{ETICHETTA_MOTIVO[motivo]}</span>
                <span className="grezze__valore">{intero(quanti)}</span>
              </span>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}
