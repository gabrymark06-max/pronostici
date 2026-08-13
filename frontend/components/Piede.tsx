import { GIOCO_RESPONSABILE, GRATUITA, MARCHIO, PAYOFF, POSTA } from '@/lib/testi';

import { Marchio } from './Marchio';
import { Profili } from './Profili';

/**
 * IL PIEDE — su ogni pagina, e con dentro solo cose vere.
 *
 * L'impianto e' quello dei piedi dei siti di pronostici: marchio a sinistra,
 * colonne di collegamenti, una riga di chiusura separata da un filetto con
 * l'eta' minima, il gioco responsabile e il copyright. Di loro si prende la
 * MECCANICA, che e' buona e che la gente sa gia' leggere.
 *
 * DUE COSE CHE NON CI SONO, e per cui non e' una versione ridotta di quel
 * piede ma una versione onesta:
 *
 *  1. NIENTE «CHI SIAMO» E «CONTATTO» finche' non c'e' una pagina dietro. Un
 *     piede pieno di voci morte fa sembrare il sito piu' grande per tre
 *     secondi e meno serio per sempre.
 *  2. NIENTE RAGIONE SOCIALE. «©2026 Tal dei Tali LLC, Delaware» sotto un sito
 *     che non e' una societa' non e' un dettaglio di stile: e' una cosa falsa
 *     scritta nel punto in cui si scrivono le cose vere.
 *
 * I PROFILI E L'INDIRIZZO DI POSTA CI SONO, e sono quelli veri di chi il sito
 * lo fa — dati dal proprietario, non dedotti. Restano nella colonna
 * dell'identita' e non in cima al piede: qui non sono un invito a seguire un
 * marchio, sono il modo di raggiungere una persona.
 *
 * QUELLO CHE C'E' INVECE, e che quel piede non ha: la frase sulla gratuita' in
 * evidenza, e il gioco responsabile in una colonna sua invece che schiacciato
 * in fondo fra il copyright e l'email. E' l'informazione che puo' servire a
 * qualcuno davvero, e sta dove si guarda.
 *
 * IL BERSAGLIO GRANDE NON C'E' PIU'. Riempiva il vuoto a destra della colonna
 * dell'identita' con una filigrana; adesso quel vuoto lo occupano i profili e
 * l'indirizzo di posta, che sono contenuto. Una decorazione che si contende lo
 * spazio con qualcosa di utile perde, sempre.
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
          <Marchio href="/" />
          <p className="piede__payoff">{PAYOFF}</p>
          <p className="piede__gratuita">{GRATUITA}</p>
          <Profili />
          <p className="piede__posta">
            <a href={`mailto:${POSTA}`}>{POSTA}</a>
          </p>
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
            Il gioco d’azzardo può causare dipendenza. Se ti sta prendendo la mano, questo
            numero è gratuito e anonimo.
          </p>
          {/* IL NUMERO PRIMA DEL NOME DEL SERVIZIO. Chi arriva qui in un brutto
              momento cerca delle cifre da comporre, non il titolo dell'ente che
              le gestisce: il numero e' grande, e la spiegazione sta sotto. */}
          <p className="piede__numero">
            <a href={`tel:+39${GIOCO_RESPONSABILE.numero.replace(/\s/g, '')}`}>
              {GIOCO_RESPONSABILE.numero}
            </a>
          </p>
          <p className="piede__orari">{GIOCO_RESPONSABILE.orari}</p>
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
