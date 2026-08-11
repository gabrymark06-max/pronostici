import { nomeCampionato } from '@/lib/campionati';

import { Bandiera } from './Bandiera';
import { ancoraCampionato } from './ancore';

export interface VoceCampionato {
  codice: string;
  partite: number;
  silenzi: number;
}

/**
 * LA BARRA DEI CAMPIONATI — da 1024px in su.
 *
 * È la convenzione dei siti di risultati, e ha due lavori veri: permette di
 * saltare a un campionato senza scorrere quaranta righe, e dà al prodotto la
 * forma che chi arriva da quei siti si aspetta di trovare.
 *
 * Sono `<a href="#campionato-sa">`, non bottoni: funzionano senza
 * JavaScript, sono condivisibili, e il back del browser fa la cosa giusta.
 * Lo scorrimento è fluido perché `html { scroll-behavior: smooth }`, e si
 * spegne con `prefers-reduced-motion`. L'ancora atterra sotto le due barre
 * appiccicate grazie a `scroll-margin-top` su `:target`.
 *
 * Sotto i 1024px la barra non esiste — i campionati restano solo come gruppi
 * nella lista. Non è un cassetto dietro un hamburger: un comando che a volte
 * c'è e a volte è sepolto è peggio di un comando che a volte non c'è.
 */
export function BarraCampionati({ voci }: { voci: VoceCampionato[] }) {
  if (voci.length === 0) return null;

  return (
    <nav className="barra-leghe" aria-labelledby="titolo-campionati">
      <p className="barra-leghe__titolo label" id="titolo-campionati">
        Campionati
      </p>
      <ul>
        {voci.map((voce) => (
          <li key={voce.codice}>
            <a
              className="barra-leghe__voce"
              href={`#${ancoraCampionato(voce.codice)}`}
              aria-label={etichetta(voce)}
            >
              <Bandiera competizione={voce.codice} />
              <span className="barra-leghe__nome">{nomeCampionato(voce.codice)}</span>
              <span className="barra-leghe__n" aria-hidden="true">
                {voce.partite}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/* Il numero accanto al nome è muto per l'occhio — è il conteggio delle
   partite — ma per chi ascolta va detto per esteso, silenzi compresi: è la
   stessa informazione che la testata del gruppo dà in chiaro. */
function etichetta({ codice, partite, silenzi }: VoceCampionato): string {
  const nome = nomeCampionato(codice);
  const quante = partite === 1 ? '1 partita' : `${partite} partite`;
  if (silenzi === 0) return `${nome}, ${quante}`;
  return `${nome}, ${quante}, ${silenzi} in silenzio`;
}
