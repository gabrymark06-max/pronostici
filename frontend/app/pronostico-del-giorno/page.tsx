import type { Metadata } from 'next';

import { giornoDiApertura } from '@/lib/dati';
import { dataLunga } from '@/lib/formato';
import { MARCHIO } from '@/lib/testi';

/**
 * `/pronostico-del-giorno/` rimanda al giorno piu' recente disponibile.
 *
 * Stessa meccanica di `/`: in export statico non esiste un redirect di server,
 * quindi si usa il refresh nel <head> — che funziona senza JavaScript — piu' un
 * link visibile come ripiego. Il canonical punta al giorno, cosi' la pagina
 * datata resta l'unica indicizzata e non si crea contenuto duplicato.
 *
 * La barra di navigazione punta QUI e non al giorno: l'indirizzo senza data e'
 * quello che si condivide e che si mette nei preferiti, e deve continuare a
 * voler dire «oggi» anche fra un mese.
 */
export function generateMetadata(): Metadata {
  const giorno = giornoDiApertura();
  if (!giorno) return { title: `Pronostico del giorno — ${MARCHIO}` };
  return {
    title: 'Pronostico del giorno',
    alternates: { canonical: `/pronostico-del-giorno/${giorno}/` },
    other: { refresh: `0; url=/pronostico-del-giorno/${giorno}/` },
  };
}

export default function RimandoSchedine() {
  const giorno = giornoDiApertura();

  if (!giorno) {
    return (
      <div className="colonna colonna--lista">
        <div className="giorno-vuoto">
          <p>Non ci sono ancora giornate pubblicate.</p>
          <p>Le schedine compaiono qui quando il calcolo della notte ha girato.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="colonna colonna--lista">
      <div className="giorno-vuoto">
        <p>
          <a href={`/pronostico-del-giorno/${giorno}/`}>
            Vai al pronostico di {dataLunga(giorno)} →
          </a>
        </p>
      </div>
    </div>
  );
}
