import { decimale, percentuale } from '@/lib/formato';
import type { Backtest } from '@/lib/tipi';

/**
 * La curva silenzio ↔ S_min, con la soglia scelta marcata da una tacca
 * verticale etichettata "la soglia che abbiamo scelto, e poi congelata".
 *
 * Il file porta due valori diversi e vengono marcati ENTRAMBI:
 *   `silence.chosen_s_min`      la soglia scelta sulla griglia del backtest
 *   `parameters.s_min_in_code`  il valore che gira davvero nel codice
 * Mostrarne uno solo, o disegnare la tacca sul più lusinghiero, sarebbe
 * esattamente il tipo di scelta che questa pagina esiste per non fare.
 */

const LARGHEZZA = 640;
const ALTEZZA = 260;
const MARGINE = { alto: 16, destro: 16, basso: 46, sinistro: 46 };

export function CurvaSilenzio({ backtest }: { backtest: Backtest }) {
  const punti = backtest.silence.curve;
  if (punti.length === 0) return null;

  const sMax = Math.max(...punti.map((p) => p.s_min));
  const sMin = Math.min(...punti.map((p) => p.s_min));
  const areaLarga = LARGHEZZA - MARGINE.sinistro - MARGINE.destro;
  const areaAlta = ALTEZZA - MARGINE.alto - MARGINE.basso;

  const x = (s: number) => MARGINE.sinistro + ((s - sMin) / (sMax - sMin)) * areaLarga;
  const y = (t: number) => MARGINE.alto + areaAlta * (1 - Math.min(1, t));

  const percorso = punti
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${x(p.s_min).toFixed(1)},${y(p.silence_rate).toFixed(1)}`)
    .join(' ');

  const scelto = backtest.silence.chosen_s_min;
  const nelCodice = backtest.parameters.s_min_in_code;
  const tassoScelto = punti.find((p) => Math.abs(p.s_min - scelto) < 1e-9)?.silence_rate;

  return (
    <figure className="silenzio-grafico">
      <svg viewBox={`0 0 ${LARGHEZZA} ${ALTEZZA}`} role="img" aria-labelledby="desc-curva">
        {/* Una stringa sola: vedi TassoSilenzio. */}
        <title id="desc-curva">
          {`Quanto tacciamo al variare della soglia S_min: la curva sale da ${percentuale(
            punti[0]?.silence_rate ?? 0,
          )} a ${percentuale(punti[punti.length - 1]?.silence_rate ?? 0)}.`}
        </title>

        {/* Banda obiettivo, sullo stesso asse della curva. */}
        <rect
          className="sg-banda"
          x={MARGINE.sinistro}
          y={y(backtest.silence.band[1])}
          width={areaLarga}
          height={y(backtest.silence.band[0]) - y(backtest.silence.band[1])}
        />

        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line className="sg-filetto" x1={MARGINE.sinistro} x2={LARGHEZZA - MARGINE.destro} y1={y(t)} y2={y(t)} />
            <text className="sg-testo" x={MARGINE.sinistro - 8} y={y(t) + 3} textAnchor="end">
              {percentuale(t)}
            </text>
          </g>
        ))}

        <path className="sg-curva" d={percorso} />

        {/* La soglia scelta e congelata. */}
        <line className="sg-marca" x1={x(scelto)} x2={x(scelto)} y1={MARGINE.alto} y2={y(0)} />
        <text className="sg-testo" x={x(scelto) + 6} y={MARGINE.alto + 12}>
          scelta e congelata: {decimale(scelto, 3)}
        </text>

        {/* Il valore che gira davvero nel codice, quando è un altro. */}
        {typeof nelCodice === 'number' && Math.abs(nelCodice - scelto) > 1e-9 ? (
          <>
            <line
              className="sg-marca sg-marca--codice"
              x1={x(nelCodice)}
              x2={x(nelCodice)}
              y1={MARGINE.alto}
              y2={y(0)}
            />
            {/* Ancorata a destra della propria tacca, così non finisce sopra
                quella della soglia scelta, che sta più a destra. */}
            <text className="sg-testo" x={x(nelCodice) - 6} y={MARGINE.alto + 12} textAnchor="end">
              nel codice: {decimale(nelCodice, 3)}
            </text>
          </>
        ) : null}

        <line className="sg-asse" x1={MARGINE.sinistro} x2={LARGHEZZA - MARGINE.destro} y1={y(0)} y2={y(0)} />
        <text className="sg-testo" x={MARGINE.sinistro} y={ALTEZZA - 26}>
          S_min {decimale(sMin, 3)}
        </text>
        <text className="sg-testo" x={LARGHEZZA - MARGINE.destro} y={ALTEZZA - 26} textAnchor="end">
          S_min {decimale(sMax, 3)}
        </text>
        <text className="sg-testo" x={LARGHEZZA / 2} y={ALTEZZA - 8} textAnchor="middle">
          più alta è la soglia, più spesso taciamo
        </text>
      </svg>

      <figcaption>
        {backtest.silence.decision.replace(/piu'/g, 'più')}.{' '}
        {tassoScelto != null
          ? `Alla soglia scelta il test storico tace sul ${percentuale(tassoScelto, 1)} delle partite.`
          : ''}{' '}
        {typeof nelCodice === 'number' && Math.abs(nelCodice - scelto) > 1e-9
          ? `Il valore che gira nel codice oggi è ${decimale(nelCodice, 3)}, non ${decimale(
              scelto,
              3,
            )}: le due tacche sono entrambe segnate perché la differenza esiste e non la nascondiamo.`
          : ''}
      </figcaption>
    </figure>
  );
}
