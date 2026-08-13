import { intero, suCento } from '@/lib/formato';

/**
 * I GRAFICI DEI PROGRESSI — SVG scritti a mano, nessuna libreria.
 *
 * PERCHE' NON UNA LIBRERIA. Questo sito non carica JavaScript sulle pagine di
 * contenuto, per decisione architetturale: e' un export statico e non ha un
 * runtime. Una libreria di grafici sarebbe la prima cosa a romperlo, e in
 * cambio darebbe animazioni e riquadri al passaggio del mouse — cioe' proprio
 * quello che a un numero di calibrazione non serve. Un `<svg>` calcolato in
 * fase di build si vede senza JavaScript, si stampa, si legge da chi ascolta se
 * gli si mette accanto il testo, e pesa zero.
 *
 * OGNI GRAFICO E' ACCOMPAGNATO DAL SUO DATO IN CHIARO. Un disegno che non si
 * puo' leggere in cifre e' un disegno di cui bisogna fidarsi, ed e' il
 * contrario di quello che questa pagina fa. `role="img"` con `aria-label`
 * riassuntivo, e la tavola con i numeri li' accanto o sotto.
 *
 * LA TAVOLOZZA E' QUELLA DEI TOKEN e non una tavolozza da grafici. Nessuna
 * scala di colori categorici: l'inchiostro per il dato, il verde solo dove il
 * sito lo usa gia' (un esito centrato), il vermiglio solo dove il prodotto
 * decide qualcosa. Un grafico con sei colori nuovi sarebbe un secondo sistema
 * visivo dentro il primo.
 */

/* Le proporzioni sono in unita' del viewBox, e il disegno si adatta con
   `width: 100%`: nessuna misura in pixel, nessun calcolo a runtime. */
const L = 320;
const A = 200;
const M = { s: 34, d: 8, alto: 10, basso: 24 };

const dentroL = L - M.s - M.d;
const dentroA = A - M.alto - M.basso;

function x(frazione: number): number {
  return M.s + frazione * dentroL;
}
function y(frazione: number): number {
  return M.alto + (1 - frazione) * dentroA;
}

/* ------------------------------------------------------------------ */

export interface PuntoCalibrazione {
  etichetta: string;
  dichiarato: number;
  uscito: number;
  n: number;
}

/**
 * LA CALIBRAZIONE — il grafico piu' importante della pagina.
 *
 * Sull'asse orizzontale quello che avevamo detto, sul verticale quello che e'
 * successo. La diagonale e' la perfezione: un punto sopra vuol dire che ne
 * abbiamo presi piu' di quanti ne avevamo promessi, uno sotto il contrario.
 * ENTRAMBI SONO ERRORI, ed e' la cosa che questo disegno dice meglio di
 * qualunque tabella — la bravura non e' stare in alto, e' stare sulla riga.
 *
 * La grandezza del quadrato porta quante partite ci sono dietro: un punto
 * lontano dalla riga su cinquanta casi e uno su duemila non vanno guardati
 * allo stesso modo, e senza questa informazione il grafico inviterebbe a
 * farlo.
 */
export function GraficoCalibrazione({ punti }: { punti: PuntoCalibrazione[] }) {
  if (punti.length === 0) return null;
  const nMax = Math.max(...punti.map((p) => p.n), 1);

  return (
    <svg
      className="grafico"
      viewBox={`0 0 ${L} ${A}`}
      role="img"
      aria-label={
        'Calibrazione: ' +
        punti
          .map(
            (p) =>
              `nella fascia ${p.etichetta} avevamo dichiarato ${suCento(p.dichiarato)} su 100 e ne sono usciti ${suCento(p.uscito)} su 100, su ${intero(p.n)} casi`,
          )
          .join('; ')
      }
    >
      {/* La griglia, quattro linee e basta: piu' fitta diventerebbe un reticolo
          che compete con i dati. */}
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <line key={f} className="grafico__griglia" x1={x(0)} y1={y(f)} x2={x(1)} y2={y(f)} />
      ))}

      {/* LA DIAGONALE. Tratteggiata perche' non e' un dato: e' il bersaglio. */}
      <line className="grafico__diagonale" x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} />

      {punti.map((p) => {
        /* Il lato cresce con la RADICE del numero di casi: e' l'area a dover
           essere proporzionale, non il lato, altrimenti una fascia con quattro
           volte i casi sembra sedici volte piu' pesante. */
        const lato = 4 + 7 * Math.sqrt(p.n / nMax);
        return (
          <g key={p.etichetta}>
            {/* Il filo verticale fino alla diagonale: E' l'errore, e si legge
                come lunghezza invece che come distanza da stimare a occhio. */}
            <line
              className="grafico__errore"
              x1={x(p.dichiarato)}
              y1={y(p.uscito)}
              x2={x(p.dichiarato)}
              y2={y(p.dichiarato)}
            />
            <rect
              className="grafico__punto"
              x={x(p.dichiarato) - lato / 2}
              y={y(p.uscito) - lato / 2}
              width={lato}
              height={lato}
            />
          </g>
        );
      })}

      {[0, 0.5, 1].map((f) => (
        <text key={`ax-${f}`} className="grafico__tacca" x={x(f)} y={A - 8} textAnchor="middle">
          {Math.round(f * 100)}
        </text>
      ))}
      {[0, 0.5, 1].map((f) => (
        <text key={`ay-${f}`} className="grafico__tacca" x={M.s - 6} y={y(f) + 3} textAnchor="end">
          {Math.round(f * 100)}
        </text>
      ))}
    </svg>
  );
}

/* ------------------------------------------------------------------ */

export interface BarraCampionato {
  nome: string;
  uscito: number;
  n: number;
}

/**
 * IL CONTO PER CAMPIONATO — barre orizzontali, non verticali.
 *
 * I nomi dei campionati sono lunghi e sono etichette: in verticale finirebbero
 * ruotati o troncati. In orizzontale si leggono, e l'occhio confronta le
 * lunghezze lungo un bordo comune, che e' il confronto piu' facile che
 * esista.
 *
 * L'ordine e' per numero di casi, non per tasso: mettere in cima chi ha il
 * numero piu' alto significherebbe premiare i campionati con dieci partite,
 * dove quel numero non vuol dire niente.
 */
export function GraficoCampionati({ barre }: { barre: BarraCampionato[] }) {
  if (barre.length === 0) return null;
  const nMax = Math.max(...barre.map((b) => b.n), 1);

  return (
    <ul className="barre">
      {barre.map((b) => (
        <li key={b.nome} className="barra-riga">
          <span className="barra-riga__nome">{b.nome}</span>
          <span className="barra-riga__pista">
            <span
              className="barra-riga__pieno"
              style={{ inlineSize: `${(b.uscito * 100).toFixed(1)}%` }}
            />
            {/* La tacca dei casi: quanto pesa questa riga rispetto alla piu'
                popolata. Sta SOTTO la barra e non dentro, cosi' non si
                confonde con il tasso. */}
            <span
              className="barra-riga__peso"
              style={{ inlineSize: `${((b.n / nMax) * 100).toFixed(1)}%` }}
            />
          </span>
          <span className="barra-riga__valore num">{suCento(b.uscito)}</span>
          <span className="barra-riga__n num">{intero(b.n)}</span>
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ */

export interface PuntoCurva {
  x: number;
  y: number;
}

/**
 * LA CURVA DEL SILENZIO — quanto tacere al variare della soglia.
 *
 * Serve a mostrare che la quota di silenzio non e' un capriccio ne' un numero
 * scelto per fare scena: e' il punto in cui una curva e' stata tagliata, e la
 * curva si vede tutta. Il taglio scelto e' segnato.
 */
export function GraficoCurva({
  punti,
  scelto,
  etichettaX,
}: {
  punti: PuntoCurva[];
  scelto: number | null;
  etichettaX: string;
}) {
  if (punti.length < 2) return null;
  const xs = punti.map((p) => p.x);
  const min = Math.min(...xs);
  const max = Math.max(...xs);
  const larghezza = max - min || 1;
  const posX = (v: number) => x((v - min) / larghezza);

  const traccia = punti
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${posX(p.x).toFixed(1)} ${y(p.y).toFixed(1)}`)
    .join(' ');

  const puntoScelto = scelto === null ? null : punti.find((p) => p.x === scelto);

  return (
    <svg
      className="grafico"
      viewBox={`0 0 ${L} ${A}`}
      role="img"
      aria-label={
        `Quanto si tace al variare della soglia, da ${suCento(punti[0]?.y ?? 0)} su 100 a ` +
        `${suCento(punti[punti.length - 1]?.y ?? 0)} su 100` +
        (puntoScelto ? `. La soglia scelta tace ${suCento(puntoScelto.y)} volte su 100.` : '')
      }
    >
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <line key={f} className="grafico__griglia" x1={x(0)} y1={y(f)} x2={x(1)} y2={y(f)} />
      ))}

      <path className="grafico__linea" d={traccia} />

      {puntoScelto ? (
        <>
          <line
            className="grafico__scelto"
            x1={posX(puntoScelto.x)}
            y1={y(0)}
            x2={posX(puntoScelto.x)}
            y2={y(puntoScelto.y)}
          />
          <rect
            className="grafico__punto grafico__punto--scelto"
            x={posX(puntoScelto.x) - 4}
            y={y(puntoScelto.y) - 4}
            width={8}
            height={8}
          />
        </>
      ) : null}

      {[0, 0.5, 1].map((f) => (
        <text key={`y-${f}`} className="grafico__tacca" x={M.s - 6} y={y(f) + 3} textAnchor="end">
          {Math.round(f * 100)}
        </text>
      ))}
      <text className="grafico__tacca" x={x(0.5)} y={A - 6} textAnchor="middle">
        {etichettaX}
      </text>
    </svg>
  );
}
