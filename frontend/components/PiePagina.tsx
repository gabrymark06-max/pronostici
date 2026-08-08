
import { GIOCO_RESPONSABILE, GRATUITA, REPO } from '@/lib/testi';

/**
 * La gratuità è CONTENUTO, non una nota legale: è il differenziatore più
 * difendibile del prodotto, quindi si dice a --fs-body-s, non in un footer
 * di 11px. Nessun contenitore qui ha una larghezza compatibile con un banner.
 */
export function PiePagina() {
  return (
    <footer className="pie">
      <div className="colonna">
        <p className="pie__gratuita">{GRATUITA}</p>
        <div className="pie__righe">
          <p>
            <a href={GIOCO_RESPONSABILE.href} rel="noopener noreferrer" target="_blank">
              {GIOCO_RESPONSABILE.testo}
            </a>
          </p>
          <p>
            Il codice, i dati e il registro dei pronostici sono pubblici:{' '}
            <a href={REPO} rel="noopener noreferrer" target="_blank">
              github.com/GabrieleMarchesini2006/pronostici
            </a>
          </p>
          <p>
            <a href="/come-funziona/">Come funziona</a> — il criterio, i parametri e il
            protocollo scritto prima dei numeri.
          </p>
        </div>
      </div>
    </footer>
  );
}
