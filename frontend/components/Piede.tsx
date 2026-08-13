import { GIOCO_RESPONSABILE, GRATUITA, MARCHIO } from '@/lib/testi';

/**
 * IL PIEDE — su ogni pagina, e non piu' solo sulla lista.
 *
 * Prima questo stava dentro `Fondo`, insieme a «come funziona» e al registro, e
 * `Fondo` compariva solo nella pagina della giornata. Con le pagine nuove —
 * pronostico del giorno, progressi, come funziona — significava che tre pagine
 * su cinque non portavano la riga sul gioco d'azzardo. Non e' una riga
 * decorativa e non e' facoltativa: sta nel telaio, cosi' non puo' mancare da
 * nessuna parte.
 *
 * QUI NON C'E' UN LINK AL CODICE. C'era, e portava al repository pubblico. Non
 * c'e' piu' per decisione del proprietario. Di conseguenza sono state riscritte
 * anche le frasi che rimandavano a quel link: dire «chiunque puo' verificare»
 * senza dare il posto dove farlo sarebbe una promessa piu' debole di prima, non
 * piu' forte. Quello che resta si regge da solo — i pronostici hanno una data e
 * non si riscrivono — ed e' vero comunque.
 */
export function Piede() {
  return (
    <footer className="piede">
      <div className="colonna colonna--lista piede__interno">
        <p className="piede__marchio">{MARCHIO}</p>
        <p className="piede__riga">{GRATUITA}</p>
        <p className="piede__riga">
          Il gioco d’azzardo può causare dipendenza.{' '}
          <a href={GIOCO_RESPONSABILE.href} rel="noopener noreferrer" target="_blank">
            {GIOCO_RESPONSABILE.testo}
          </a>
        </p>
        <p className="piede__riga piede__riga--minuta">
          Questo sito non accetta scommesse, non rimanda a operatori e non ha affiliazioni. I
          pronostici sono stime statistiche, non previsioni: possono sbagliare, e sbagliano.
        </p>
      </div>
    </footer>
  );
}
