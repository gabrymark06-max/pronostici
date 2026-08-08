import { suCento } from '@/lib/formato';
import { etichettaBarra, righeDefinizione } from '@/lib/testi';
import type { Pronostico } from '@/lib/tipi';

/**
 * LINGUAGGIO A + LINGUAGGIO B sullo stesso asse, con marche incompatibili.
 *
 *  A — probabilità : cifra grande in serif + barra PIENA a spigoli vivi
 *  B — affidabilità: nessuna cifra grande, solo la parentesi ├───┤ in TRATTO
 *
 * Il riempimento è continuo e le tacche ai decili gli passano sopra: nessun
 * arrotondamento a segmenti, quindi nessuna bugia di quantizzazione. Le tacche
 * fanno da righello, e quella del 50 è più marcata perché è il pavimento p_min.
 *
 * La riga di definizione è testo reale nel DOM: l'informazione esiste anche
 * senza il grafico, e non è mai affidata a un tooltip.
 */
export function BarraProbabilita({ pronostico }: { pronostico: Pronostico }) {
  const percentuale = pronostico.p * 100;
  const conBanda = pronostico.band_p5 !== null && pronostico.band_p95 !== null;
  const da = (pronostico.band_p5 ?? 0) * 100;
  const a = (pronostico.band_p95 ?? 0) * 100;

  const decili = [10, 20, 30, 40, 50, 60, 70, 80, 90];

  return (
    <div className="prob">
      <p className="prob__cifra">
        <span className="prob__numero">{suCento(pronostico.p)}</span>
        <span className="prob__su">su 100</span>
      </p>

      <div className="prob__grafico" role="img" aria-label={etichettaBarra(pronostico)}>
        <div className="prob__barra">
          <div className="prob__riempimento" style={{ width: `${percentuale}%` }} />
          {decili.map((d) => (
            <span
              key={d}
              aria-hidden="true"
              className={`prob__tacca${d === 50 ? ' prob__tacca--pavimento' : ''}`}
              style={{ left: `${d}%` }}
            />
          ))}
        </div>
        <div className="prob__baseline" />

        {conBanda ? (
          <div className="prob__banda" aria-hidden="true">
            <div className="prob__banda-tratto" style={{ left: `${da}%`, width: `${a - da}%` }}>
              <span className="prob__banda-serif prob__banda-serif--sx" />
              <span className="prob__banda-serif prob__banda-serif--dx" />
            </div>
            <span className="prob__banda-centro" style={{ left: `${percentuale}%` }} />
          </div>
        ) : null}
      </div>

      <p className="definizione">
        {righeDefinizione(pronostico).map((riga) => (
          <span key={riga} style={{ display: 'block' }}>
            {riga}
          </span>
        ))}
      </p>
    </div>
  );
}

/**
 * La versione ridotta per la riga di lista: 48px, solo tratto, nessuna cifra.
 * Sotto i 375px sparisce via CSS — restano la cifra e il chip.
 */
export function MiniBanda({ p5, p95 }: { p5: number; p95: number }) {
  const da = p5 * 100;
  const a = p95 * 100;
  return (
    <span className="mini-banda" aria-hidden="true">
      <span className="mini-banda__tratto" style={{ left: `${da}%`, width: `${a - da}%` }}>
        <span className="mini-banda__serif mini-banda__serif--sx" />
        <span className="mini-banda__serif mini-banda__serif--dx" />
      </span>
    </span>
  );
}
