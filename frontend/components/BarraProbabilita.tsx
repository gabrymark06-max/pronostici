import { suCento } from '@/lib/formato';
import { etichettaBarra, righeDefinizione } from '@/lib/testi';
import type { Pronostico } from '@/lib/tipi';

/**
 * LINGUAGGIO A + LINGUAGGIO B sullo stesso asse, con marche incompatibili.
 *
 *  A — probabilita' : LA CIFRA (Newsreader con asse ottico alto, tabellare)
 *                     + barra PIENA a spigoli vivi
 *  B — affidabilita': nessuna cifra grande, solo la parentesi ├───┤ in TRATTO
 *
 * L'unita' e' «su 100» in mono sulla linea di base, mai `%` e mai grande. E'
 * l'unica cifra monumentale della schermata: se una seconda cresce, questa
 * smette di dominare e la pagina torna piatta.
 *
 * Il riempimento e' continuo e le tacche ai decili gli passano sopra: nessun
 * arrotondamento a segmenti, quindi nessuna bugia di quantizzazione. Le
 * tacche fanno da righello, e quella del 50 e' piu' marcata perche' e' il
 * pavimento sotto il quale non consigliamo mai.
 *
 * La riga di definizione e' testo reale nel DOM: l'informazione esiste anche
 * senza il grafico, e non e' mai affidata a un tooltip.
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
        <span className="cifra">{suCento(pronostico.p)}</span>
        <span className="prob__su">su 100</span>
      </p>

      <div className="prob__grafico" role="img" aria-label={etichettaBarra(pronostico)}>
        <div className="prob__barra">
          <div className="prob__riempimento" style={{ width: `${percentuale}%` }} />
        </div>
        <div className="prob__baseline" />

        {/* Il righello sta SOTTO la barra: sopra il riempimento le tacche la
            spezzavano in dieci segmenti e la facevano leggere come una
            quantizzazione che non esiste. */}
        <div className="prob__righello" aria-hidden="true">
          {decili.map((d) => (
            <span
              key={d}
              className={`prob__tacca${d === 50 ? ' prob__tacca--pavimento' : ''}`}
              style={{ left: `${d}%` }}
            />
          ))}
          <span className="prob__pavimento-etichetta">50</span>
        </div>

        {conBanda ? (
          <div className="prob__banda" aria-hidden="true">
            <div className="prob__banda-tratto" style={{ left: `${da}%`, width: `${a - da}%` }}>
              <span className="prob__banda-serif prob__banda-serif--sx" />
              <span className="prob__banda-serif prob__banda-serif--dx" />
            </div>
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
