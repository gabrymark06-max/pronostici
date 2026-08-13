import { GIOCO_RESPONSABILE, GRATUITA, MARCHIO, PAYOFF } from '@/lib/testi';

import { Marchio } from './Marchio';

/**
 * IL PIEDE — su ogni pagina, e con dentro solo cose vere.
 *
 * L'impianto e' quello dei piedi dei siti di pronostici: marchio a sinistra,
 * colonne di collegamenti, una riga di chiusura separata da un filetto con
 * l'eta' minima, il gioco responsabile e il copyright. Di loro si prende la
 * MECCANICA, che e' buona e che la gente sa gia' leggere.
 *
 * QUATTRO COSE CHE NON CI SONO, e per cui non e' una versione ridotta di
 * quel piede ma una versione onesta:
 *
 *  1. NIENTE ICONE SOCIAL. Questo prodotto non ha un account da nessuna parte.
 *     Quattro cerchi che portano alla pagina d'accesso di un social sono la
 *     cosa piu' facile da mettere in un piede e la piu' facile da smascherare.
 *  2. NIENTE «CHI SIAMO» E «CONTATTO» finche' non c'e' una pagina dietro. Un
 *     piede pieno di voci morte fa sembrare il sito piu' grande per tre
 *     secondi e meno serio per sempre.
 *  3. NIENTE INDIRIZZO DI POSTA inventato, e nemmeno uno personale messo li'
 *     senza che il proprietario l'abbia deciso: un indirizzo in un piede
 *     pubblico ci resta, e lo raccolgono le macchine prima delle persone.
 *  4. NIENTE RAGIONE SOCIALE. «©2026 Tal dei Tali LLC, Delaware» sotto un sito
 *     che non e' una societa' non e' un dettaglio di stile: e' una cosa falsa
 *     scritta nel punto in cui si scrivono le cose vere.
 *
 * QUELLO CHE C'E' INVECE, e che quel piede non ha: la frase sulla gratuita' in
 * evidenza, e il gioco responsabile in una colonna sua invece che schiacciato
 * in fondo fra il copyright e l'email. E' l'informazione che puo' servire a
 * qualcuno davvero, e sta dove si guarda.
 *
 * L'ELEMENTO FIRMA. Il bersaglio del marchio torna qui come glifo grande e
 * tenue dietro la colonna dell'identita': e' lo stesso segno del logotipo, del
 * punto elenco dei titoli e della tacca del misurino, alla sua scala piu'
 * grande. Non e' decorazione — e' la quarta ricorrenza dello stesso segno, che
 * e' quello che rende un piede riconoscibile invece che generico.
 */

/* L'anno si legge in fase di build. Il sito si ricostruisce ogni notte, quindi
   il primo gennaio si aggiorna da solo senza che nessuno se ne ricordi. */
const ANNO = new Date().getFullYear();

const VOCI: { testo: string; href: string }[] = [
  { testo: 'Pronostico del giorno', href: '/pronostico-del-giorno/' },
  { testo: 'Tutte le partite', href: '/' },
  { testo: 'Progressi', href: '/progressi/' },
  { testo: 'Come funziona', href: '/come-funziona/' },
];

export function Piede() {
  return (
    <footer className="piede">
      <div className="colonna colonna--pagina piede__interno">
        <div className="piede__identita">
          {/* Il glifo grande dietro: decorativo e dichiarato tale. Sta sotto al
              testo nell'ordine del documento perche' chi ascolta la pagina non
              deve incontrare un elemento vuoto prima del marchio. */}
          <Marchio href="/" />
          <p className="piede__payoff">{PAYOFF}</p>
          <p className="piede__gratuita">{GRATUITA}</p>
          <svg
            className="piede__filigrana"
            viewBox="0 0 32 32"
            aria-hidden="true"
            focusable="false"
          >
            <rect x="1" y="1" width="30" height="30" />
            <rect x="8" y="8" width="16" height="16" />
            <rect className="piede__filigrana-centro" x="13" y="13" width="6" height="6" />
          </svg>
        </div>

        <nav className="piede__colonna" aria-label="Pagine del sito">
          <h2 className="label piede__titolo">Il sito</h2>
          <ul className="piede__voci">
            {VOCI.map((v) => (
              <li key={v.href}>
                <a href={v.href}>{v.testo}</a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="piede__colonna">
          <h2 className="label piede__titolo">Prima di giocare</h2>
          <p className="piede__eta">
            <span className="piede__bollo">18+</span> Vietato ai minori.
          </p>
          <p className="piede__riga">
            Il gioco d’azzardo può causare dipendenza. Se ti sta prendendo la mano, il numero
            qui sotto è gratuito e anonimo.
          </p>
          <p className="piede__riga">
            <a href={GIOCO_RESPONSABILE.href} rel="noopener noreferrer" target="_blank">
              {GIOCO_RESPONSABILE.testo}
            </a>
          </p>
        </div>
      </div>

      <div className="colonna colonna--pagina piede__chiusura">
        <p className="piede__minuta">
          © {ANNO} {MARCHIO}. Questo sito non accetta scommesse, non rimanda a operatori e non
          ha affiliazioni.
        </p>
        <p className="piede__minuta">
          I pronostici sono stime statistiche, non previsioni: possono sbagliare, e sbagliano.
        </p>
      </div>
    </footer>
  );
}
