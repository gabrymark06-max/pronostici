import { Marchio } from './Marchio';
import { TemaToggle } from './TemaToggle';
import { VoceConto } from './VoceConto';

/**
 * LA BARRA DI NAVIGAZIONE.
 *
 * L'impianto è quello dei tabelloni di risultati (diretta.it): barra alta e
 * piena larghezza, marchio ben visibile a sinistra, voci con etichetta subito
 * dopo, comandi dell'utente all'estremo destro, confine netto sotto. Di loro
 * si prende la MECCANICA e le proporzioni, mai il marchio né i colori.
 *
 * 72px da 768px in su. Le versioni precedenti stavano fra 52 e 56, ed è la
 * ragione per cui il prodotto si presentava con quello che sembrava un
 * filetto: sotto i ~64px una barra non ha spazio per un marchio letto come
 * marchio, e diventa un bordo dello schermo.
 *
 * LE VOCI SONO QUATTRO E SONO TUTTE PAGINE VERE. Non c'è un menu inventato
 * per riempire, e nessuna è un salto dentro un'altra pagina: «Pronostico del
 * giorno» sono le due schedine, «Tutte le partite» è la lista, «Progressi» è
 * il registro completo, «Come funziona» è la spiegazione. Ognuna ha il suo
 * indirizzo, che è quello che serve per mandarla a qualcuno. Il numero verde e
 * la riga sulla gratuità stanno nel piede, che è il posto in cui si guardano
 * davvero.
 *
 * PERCHÉ NON C'È «ACCEDI». L'impianto di questa barra viene dai siti di
 * pronostici che fanno la stessa cosa, e tutti hanno il bottone dell'accesso
 * all'estremo destro. Lì serve, perché lì i pronostici stanno dietro la
 * registrazione. Qui non c'è niente da sbloccare: il registro è pubblico ed è
 * l'unico argomento che il prodotto ha. Un bottone che non chiude niente
 * costerebbe all'utente e non gli darebbe nulla.
 *
 * NESSUN HAMBURGER A NESSUNA LARGHEZZA. Sotto i 768px la barra tiene marchio e
 * comandi sul primo livello e fa scorrere le voci orizzontalmente sul secondo:
 * quattro voci non si nascondono dietro un bottone.
 */
export function Testata({ giornoApertura }: { giornoApertura: string | null }) {
  const casa = giornoApertura ? `/giorno/${giornoApertura}/` : '/';

  return (
    <header className="barra">
      <div className="colonna colonna--pagina barra__interno">
        <Marchio href={casa} />

        <nav className="barra__voci" aria-label="Sezioni">
          {/* L'indirizzo SENZA DATA, che è quello che si condivide e si mette
              nei preferiti: deve voler dire «oggi» anche fra un mese. Rimanda
              da sé al giorno pubblicato più recente. */}
          <a className="voce" href="/pronostico-del-giorno/">
            <IconaBersaglio />
            <span className="voce__nome">Pronostico del giorno</span>
          </a>

          <a className="voce" href={casa}>
            <IconaGiornata />
            <span className="voce__nome">Tutte le partite</span>
          </a>

          <a className="voce" href="/progressi/">
            <IconaRegistro />
            <span className="voce__nome">Progressi</span>
          </a>

          <a className="voce" href="/come-funziona/">
            <IconaDomanda />
            <span className="voce__nome">Come funziona</span>
          </a>
        </nav>

        <div className="barra__comandi">
          {/* Il conto PRIMA del tema: e' l'unico dei due che porta da qualche
              parte, e all'estremo destro va la cosa piu' importante — che nella
              barra e' sempre l'identita'. */}
          <VoceConto />
          <TemaToggle />
        </div>
      </div>
    </header>
  );
}

/* Le icone parlano una lingua sola: tratto a --icon-stroke, terminazioni
   squadrate, sola geometria ortogonale — la stessa del marchio. Sono
   decorative: l'etichetta accanto dice già tutto a chi ascolta. */

const COMUNI = {
  className: 'voce__icona',
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 'var(--icon-stroke)',
  strokeLinecap: 'square' as const,
  'aria-hidden': true,
  focusable: 'false' as const,
};

function IconaGiornata() {
  return (
    <svg {...COMUNI}>
      <path d="M4 6h16v14H4z" />
      <path d="M4 11h16" />
      <path d="M9 4v3" />
      <path d="M15 4v3" />
      <path d="M8 15h3v3H8z" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** Il bersaglio: la stessa geometria del marchio, a 24px e in solo tratto. */
function IconaBersaglio() {
  return (
    <svg {...COMUNI}>
      <path d="M3 3h18v18H3z" />
      <path d="M8 8h8v8H8z" />
      <path d="M11 11h2v2h-2z" fill="currentColor" stroke="none" />
    </svg>
  );
}

/* «Come funziona» aveva il bersaglio, che ora è del pronostico del giorno: il
   segno del marchio va a quello che il prodotto decide, non alla spiegazione.
   Qui un punto interrogativo costruito con la stessa geometria ortogonale —
   nessuna curva, come tutte le altre. */
function IconaDomanda() {
  return (
    <svg {...COMUNI}>
      <path d="M3 3h18v18H3z" />
      <path d="M9 9V8h6v4h-3v2" />
      <path d="M11 17h2v2h-2z" fill="currentColor" stroke="none" />
    </svg>
  );
}

function IconaRegistro() {
  return (
    <svg {...COMUNI}>
      <path d="M4 20V13" />
      <path d="M10 20V8" />
      <path d="M16 20v-5" />
      <path d="M22 20V4" />
    </svg>
  );
}
