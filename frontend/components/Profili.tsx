import { PROFILI } from '@/lib/testi';
import { interno } from '@/lib/sito';

/**
 * I QUATTRO PROFILI, disegnati nella lingua del sito.
 *
 * NON SONO I LOGHI UFFICIALI. Sono glifi ridisegnati con lo stesso tratto di
 * tutte le altre icone — 24 di riquadro, spessore `--icon-stroke`, terminazioni
 * squadrate, nessun pieno di colore — perche' quattro loghi a colori dentro un
 * piede monocromatico sono quattro macchie che si prendono l'attenzione che
 * dovrebbe andare al numero verde qui accanto. Restano riconoscibili: la forma
 * di ognuno e' quella, e' solo ridotta all'ossatura.
 *
 * IL BERSAGLIO E' QUADRATO E GRANDE 44. I cerchi del piede del concorrente
 * sono 40 e non arrivano al minimo tattile; qui il riquadro coincide col
 * bersaglio, come nelle righe della lista, e a 44px lo prendi anche con il
 * pollice.
 *
 * OGNI COLLEGAMENTO PORTA IL NOME NEL SUO NOME ACCESSIBILE, e dice che si apre
 * altrove: un'icona senza etichetta e' un bottone muto per chi la pagina la
 * ascolta, e quattro bottoni muti di fila sono quattro «link» letti uno dopo
 * l'altro.
 */

const SEGNO = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 'var(--icon-stroke)',
  strokeLinecap: 'square' as const,
  'aria-hidden': true,
  focusable: 'false' as const,
};

/** Riquadro, obiettivo, e il punto in alto a destra. */
function SegnoInstagram() {
  return (
    <svg {...SEGNO} className="profilo__segno">
      <rect x="3.5" y="3.5" width="17" height="17" />
      <circle cx="12" cy="12" r="4" />
      <rect x="16" y="6.5" width="1.6" height="1.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** La nota: gambo con l'uncino in alto e la testa in basso a sinistra. */
function SegnoTikTok() {
  return (
    <svg {...SEGNO} className="profilo__segno">
      <path d="M14 3.5v11.5a4 4 0 1 1-4-4" />
      <path d="M14 3.5c0 3 2 4.7 5 4.8" />
    </svg>
  );
}

/** Due tratti incrociati. */
function SegnoX() {
  return (
    <svg {...SEGNO} className="profilo__segno">
      <path d="M4.5 4.5l15 15" />
      <path d="M19.5 4.5l-15 15" />
    </svg>
  );
}

/** Riquadro con dentro le due lettere ridotte a tratti. */
function SegnoLinkedIn() {
  return (
    <svg {...SEGNO} className="profilo__segno">
      <rect x="3.5" y="3.5" width="17" height="17" />
      <path d="M8 10.5v6" />
      <rect x="7.2" y="7.2" width="1.6" height="1.6" fill="currentColor" stroke="none" />
      <path d="M12 16.5v-6" />
      <path d="M12 12.6c0-1.2 1-2.1 2.2-2.1s2.2.9 2.2 2.1v3.9" />
    </svg>
  );
}

const SEGNI: Record<string, () => React.ReactElement> = {
  Instagram: SegnoInstagram,
  TikTok: SegnoTikTok,
  X: SegnoX,
  LinkedIn: SegnoLinkedIn,
};

export function Profili() {
  return (
    <ul className="profili">
      {PROFILI.map((p) => {
        const Segno = SEGNI[p.nome];
        return (
          <li key={p.nome}>
            <a
              className="profilo"
              href={interno(p.href)}
              rel="noopener noreferrer me"
              target="_blank"
              /* Il nome accessibile comincia col nome del profilo: chi usa il
                 comando vocale dice «clicca Instagram». */
              aria-label={`${p.nome} — si apre in una nuova scheda`}
            >
              {Segno ? <Segno /> : p.nome}
            </a>
          </li>
        );
      })}
    </ul>
  );
}
