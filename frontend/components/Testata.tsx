import { GIOCO_RESPONSABILE, REPO } from '@/lib/testi';

import { Marchio } from './Marchio';
import { TemaToggle } from './TemaToggle';

/**
 * LA TESTATA.
 *
 * Prima era una riga sottile: marchio in serif e due bottoni squadrati a
 * destra, alta quanto un filetto. Un prodotto che si presenta con un filetto
 * non si presenta. Ora e' una barra: il segno a sinistra, le voci con icona ed
 * etichetta accanto, i comandi a destra, e un confine netto sotto.
 *
 * L'impianto e' quello dei tabelloni di risultati (diretta.it): logo ben
 * visibile a sinistra, voci con icona + etichetta subito dopo, comandi
 * dell'utente all'estremo destro. Di loro si prende la MECCANICA, mai il
 * marchio ne' i colori: la nostra identita' resta acromatica.
 *
 * LE VOCI SONO TRE PERCHE' TRE SONO LE COSE VERE. Non c'e' un menu inventato:
 * «Oggi» porta al giorno di apertura, e le altre due sono i rimandi che devono
 * esistere sempre — il codice pubblico e il numero verde. Vivevano nel piede,
 * che e' stato tolto; qui sono piu' visibili di quanto siano mai state in
 * fondo alla pagina.
 *
 * Il confine con il contenuto e' la riga di taratura a piena larghezza: lo
 * stesso segno del marchio, alla scala della pagina.
 *
 * Nessun hamburger a nessuna larghezza: sotto i 768px la barra passa su due
 * livelli invece di nascondere le voci dietro un bottone.
 */
export function Testata({ giornoApertura }: { giornoApertura: string | null }) {
  const casa = giornoApertura ? `/giorno/${giornoApertura}/` : '/';

  return (
    <header className="testata">
      <div className="colonna colonna--lista testata__interno">
        <Marchio href={casa} />

        <nav className="testata__voci" aria-label="Sezioni">
          <a className="voce" href={casa}>
            <IconaGiornata />
            <span className="voce__nome">Oggi</span>
          </a>

          <a
            className="voce"
            href={REPO}
            rel="noopener noreferrer"
            target="_blank"
            aria-label="Codice e registro pubblici, si apre in una nuova scheda"
          >
            <IconaCodice />
            <span className="voce__nome">Codice</span>
          </a>

          <a
            className="voce"
            href={GIOCO_RESPONSABILE.href}
            rel="noopener noreferrer"
            target="_blank"
            aria-label={`${GIOCO_RESPONSABILE.testo}. Si apre in una nuova scheda`}
          >
            <IconaVerde />
            <span className="voce__nome">Numero verde</span>
          </a>
        </nav>

        <div className="testata__comandi">
          <TemaToggle />
        </div>
      </div>

      {/* Il confine fra il cromo e il contenuto: l'elemento firma a piena
          larghezza, fuori dalla colonna perche' il confine e' della pagina. */}
      <span className="taratura testata__confine" aria-hidden="true" />
    </header>
  );
}

/* Le icone parlano la stessa lingua dei tre riquadri «come si legge»: tratto a
   --icon-stroke, terminazioni squadrate, sola geometria ortogonale. Sono
   decorative: l'etichetta accanto dice gia' tutto a chi ascolta. */

function IconaGiornata() {
  return (
    <svg
      className="voce__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 6h16v14H4z" />
      <path d="M4 11h16" />
      <path d="M9 4v3" />
      <path d="M15 4v3" />
      <path d="M8 15h3v3H8z" fill="currentColor" stroke="none" />
    </svg>
  );
}

function IconaCodice() {
  return (
    <svg
      className="voce__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      strokeLinejoin="miter"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M9 7l-5 5 5 5" />
      <path d="M15 7l5 5-5 5" />
    </svg>
  );
}

function IconaVerde() {
  return (
    <svg
      className="voce__icona"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="var(--icon-stroke)"
      strokeLinecap="square"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 4h16v16H4z" />
      <path d="M12 11v6" />
      <path d="M12 7v1.5" />
    </svg>
  );
}
